import asyncio
import logging
import os
import json
from collections import deque
from datetime import datetime

import httpx
from dotenv import load_dotenv
from livekit import agents, api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    function_tool,
    get_job_context,
)
from google.genai import types
from livekit.plugins import google, silero

# Import Supabase helper (replaces Backboard)
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from supabase_helper import (
    get_user_profile,
    get_conversation_history,
    search_knowledge_base,
    store_session_transcript
)

logger = logging.getLogger("voice-agent")

load_dotenv(".env.local")

# Emotion detection API (emotion-backend must be running)
EMOTION_API_URL = os.getenv("EMOTION_API_URL", "http://localhost:8000/predict")
EMOTION_TEXT_API_URL = os.getenv("EMOTION_TEXT_API_URL", "http://localhost:8000/predict-text")
EMOTION_BUFFER_SECONDS = 5  # seconds of audio to buffer before analysis
EMOTION_SAMPLE_RATE = 16000  # must match emotion model expectation
ALLOWED_VOICES = [
    voice.strip()
    for voice in os.getenv("LIVEKIT_AGENT_VOICES", "Zephyr,Puck").split(",")
    if voice.strip()
]
DEFAULT_VOICE = os.getenv("LIVEKIT_DEFAULT_VOICE", ALLOWED_VOICES[0] if ALLOWED_VOICES else "Zephyr")

# Store transcript during the session
call_transcript: list[dict] = []
call_start_time: datetime | None = None
should_exit = False
transcript_stored = False  # Prevent double-storage

# Shared emotion state — updated by background audio tap + text analysis
current_emotion: dict | None = None    # from audio
current_text_emotion: dict | None = None  # from text
current_mood: dict | None = None  # fused speech-aware mood snapshot
mood_history: deque = deque(maxlen=12)
last_user_utterance_time: datetime | None = None

# Emotion label map for readable prompt injection
# Audio model labels (superb/wav2vec2-base-superb-er)
EMOTION_NAMES = {
    "ang": "angry", "hap": "happy", "sad": "sad",
    "neu": "neutral", "fear": "fearful", "dis": "disgusted", "sur": "surprised",
    "angry": "angry", "happy": "happy", "sad": "sad",
    "neutral": "neutral", "fear": "fearful", "disgust": "disgusted", "surprise": "surprised",
}

# Text model labels (j-hartmann/emotion-english-distilroberta-base)
TEXT_EMOTION_NAMES = {
    "anger": "angry", "joy": "happy", "sadness": "sad",
    "neutral": "neutral", "fear": "fearful", "disgust": "disgusted", "surprise": "surprised",
}

POSITIVE_EMOTIONS = {"happy", "joy", "surprised"}
NEGATIVE_EMOTIONS = {"sad", "fearful", "angry", "disgusted", "disgust", "anger", "fear"}
NEUTRAL_EMOTIONS = {"neutral", "calm"}
FILLER_WORDS = {
    "um", "uh", "er", "erm", "hmm", "huh", "like", "so", "mhm", "hmmmm", "hmmmmm",
}
FILLER_PHRASES = ("you know", "i mean", "kind of", "sort of", "you see")
HESITATION_MEDIUM = 0.12
HESITATION_HIGH = 0.22


def extract_speech_features(text: str) -> dict:
    """Derive lightweight prosody + pacing features from the transcript."""
    global last_user_utterance_time

    now = datetime.utcnow()
    pause_seconds = None
    if last_user_utterance_time is not None:
        pause_seconds = (now - last_user_utterance_time).total_seconds()
    last_user_utterance_time = now

    raw_words = [w.strip(".,!?;:()[]\"").lower() for w in text.split()]
    words = [w for w in raw_words if w]
    word_count = len(words)
    char_count = len(text)
    avg_word_length = (sum(len(w) for w in words) / word_count) if word_count else 0

    filler_hits = 0
    text_lower = text.lower()
    for phrase in FILLER_PHRASES:
        filler_hits += text_lower.count(phrase)
    filler_hits += sum(1 for w in words if w in FILLER_WORDS)

    hesitation_ratio = (filler_hits / word_count) if word_count else 0
    question_marks = text.count("?")
    exclamations = text.count("!")

    return {
        "utterance_time": now.isoformat(),
        "pause_seconds": pause_seconds,
        "word_count": word_count,
        "char_count": char_count,
        "avg_word_length": round(avg_word_length, 2),
        "filler_count": filler_hits,
        "hesitation_ratio": round(hesitation_ratio, 3),
        "question_marks": question_marks,
        "exclamations": exclamations,
    }


def _score_from_label(label: str | None, positive_weight: float, negative_weight: float) -> float:
    if label is None:
        return 0.0
    canonical = label.lower()
    if canonical in POSITIVE_EMOTIONS:
        return positive_weight
    if canonical in NEGATIVE_EMOTIONS:
        return -negative_weight
    if canonical in NEUTRAL_EMOTIONS:
        return 0.0
    return 0.0


def update_speech_mood(text: str, speech_features: dict | None, text_emotion: dict | None):
    """Fuse audio + text + pacing cues into a speech-aware mood snapshot."""
    global current_mood, mood_history

    features = dict(speech_features or extract_speech_features(text or ""))
    features.setdefault("utterance_time", datetime.utcnow().isoformat())
    features.setdefault("word_count", 0)
    features.setdefault("filler_count", 0)
    features.setdefault("hesitation_ratio", 0.0)

    audio_label = None
    audio_score = None
    if current_emotion:
        audio_label = EMOTION_NAMES.get(current_emotion.get("label", ""), current_emotion.get("label"))
        audio_score = round(current_emotion.get("score", 0.0), 3)

    text_label = None
    text_score = None
    if text_emotion:
        text_label = TEXT_EMOTION_NAMES.get(text_emotion.get("label", ""), text_emotion.get("label"))
        text_score = round(text_emotion.get("score", 0.0), 3)

    score = 0.0
    explanation: list[str] = []

    audio_delta = _score_from_label(audio_label, 0.45, 0.45)
    if audio_delta:
        score += audio_delta
        explanation.append(f"voice sounds {audio_label}")

    text_delta = _score_from_label(text_label, 0.35, 0.35)
    if text_delta:
        score += text_delta
        explanation.append(f"words feel {text_label}")

    pause_seconds = features.get("pause_seconds")
    if pause_seconds is not None:
        if pause_seconds > 7:
            score -= 0.2
            explanation.append("long pause before speaking")
        elif pause_seconds < 2:
            score += 0.05
            explanation.append("quick response cadence")

    word_count = features.get("word_count", 0)
    if word_count >= 30:
        score += 0.1
        explanation.append("long, detailed response")
    elif word_count <= 4 and word_count > 0:
        score -= 0.1
        explanation.append("very short reply")

    hesitation_ratio = features.get("hesitation_ratio", 0.0)
    if hesitation_ratio >= HESITATION_HIGH:
        score -= 0.25
        explanation.append("strong hesitation markers")
    elif hesitation_ratio >= HESITATION_MEDIUM:
        score -= 0.15
        explanation.append("mild hesitation words")

    # Clamp score to [-1, 1]
    score = max(min(score, 1.0), -1.0)

    if score >= 0.45:
        mood_label = "energized"
    elif score >= 0.15:
        mood_label = "calm"
    elif score <= -0.45:
        mood_label = "distressed"
    elif score <= -0.15:
        mood_label = "concerned"
    else:
        mood_label = "neutral"

    prior_score = mood_history[-1]["score"] if mood_history else None
    trend = None
    if prior_score is not None:
        delta = round(score - prior_score, 3)
        if delta >= 0.15:
            trend = "improving"
        elif delta <= -0.15:
            trend = "slipping"
        else:
            trend = "steady"

    mood_entry = {
        "timestamp": features.get("utterance_time"),
        "label": mood_label,
        "score": round(score, 3),
        "trend": trend,
        "signals": {
            "audio": {"label": audio_label, "score": audio_score},
            "text": {"label": text_label, "score": text_score},
            "pause_seconds": pause_seconds,
            "word_count": word_count,
            "hesitation_ratio": features.get("hesitation_ratio"),
            "filler_count": features.get("filler_count"),
        },
        "notes": ", ".join(explanation) if explanation else None,
    }

    mood_history.append(mood_entry)
    current_mood = mood_entry

    logger.info(
        "🧠 Speech mood → %s (score %+0.2f) | pause=%ss words=%s fillers=%s voice=%s text=%s",
        mood_label.upper(),
        score,
        "n/a" if pause_seconds is None else round(pause_seconds, 1),
        word_count,
        features.get("filler_count"),
        audio_label,
        text_label,
    )


async def analyze_text_emotion(text: str, speech_features: dict | None = None):
    """Send user transcript to /predict-text, then fuse into speech-aware mood."""
    global current_text_emotion

    features = dict(speech_features or extract_speech_features(text))
    features.setdefault("text_snapshot", text)
    mood_updated = False

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                EMOTION_TEXT_API_URL,
                json={"text": text},
                timeout=10.0,
            )
            if resp.status_code == 200:
                result = resp.json()
                current_text_emotion = result
                label = TEXT_EMOTION_NAMES.get(result.get("label", ""), result.get("label", "unknown"))
                score = result.get("score", 0)
                logger.info(
                    f"🎭 ═══════════════════════════════════════════════\n"
                    f"   📝 TEXT EMOTION: {label.upper()} ({score:.0%})\n"
                    f"   📄 From: \"{text[:60]}\"\n"
                    f"   🎭 ═══════════════════════════════════════════════"
                )
                update_speech_mood(text, features, result)
                mood_updated = True
            else:
                logger.warning(f"📝 Text emotion API returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"📝 Text emotion error: {e}")
    finally:
        if not mood_updated:
            update_speech_mood(text, features, None)


async def end_session():
    """End the session by deleting the room."""
    ctx = get_job_context()
    if ctx is None:
        return
    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(room=ctx.room.name)
    )


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")

    @function_tool
    async def recall_information(self, ctx: RunContext, question: str):
        """Recall information from memory about the user or past conversations.
        Use this when the user asks about themselves, their name, what they're working on,
        or any details from previous conversations.
        
        Args:
            question: What to recall (e.g., "user's name", "what is user working on")
        """
        try:
            # Try to get user_id from context if available
            user_id = getattr(ctx, 'user_id', None)
            if user_id:
                history = await get_conversation_history(user_id, limit=10)
                if history:
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
                    return f"From previous conversations: {history_text}"
            
            return "No information found in memory."
        except Exception as e:
            logger.error(f"recall_information failed: {e}")
            return "Unable to recall information right now."

    @function_tool
    async def end_conversation(self, ctx: RunContext):
        """End the conversation. Use when the user says goodbye or wants to stop talking."""
        global should_exit, call_transcript, call_start_time, transcript_stored
        logger.info("🔚 end_conversation tool called")
        should_exit = True
        
        # Store transcript to Supabase before session ends
        if not transcript_stored:
            logger.info(f"📤 Storing transcript to Supabase ({len(call_transcript)} messages)...")
            try:
                # Get user_id from context if available
                user_id = getattr(ctx, 'user_id', None)
                if user_id:
                    duration = (datetime.now() - call_start_time).total_seconds() if call_start_time else 0
                    success = await store_session_transcript(
                        user_id=user_id,
                        mode='voice',
                        transcript=call_transcript,
                        mood_timeline=list(mood_history),
                        duration_seconds=int(duration)
                    )
                    if success:
                        transcript_stored = True
                        logger.info("✅ Transcript stored in Supabase")
                    else:
                        logger.warning("❌ Failed to store transcript in Supabase")
                else:
                    logger.warning("❌ user_id not available, skipping transcript storage")
            except Exception as e:
                logger.error(f"❌ Error storing transcript: {e}")
        
        logger.info(f"🚩 should_exit set to: {should_exit}")
        
        # Close the session to stop accepting input and exit gracefully
        logger.info("🛑 Closing session...")
        try:
            await ctx.session.close()
        except Exception as e:
            logger.warning(f"Session close error (expected): {e}")
        
        return "Goodbye! Have a great day!"

    @function_tool
    async def lookup_info(self, ctx: RunContext, question: str):
        """Look up information from the knowledge base to answer a question.
        Use this when the user asks about specific information, policies, products,
        services, or anything that might be in documentation.
        
        Args:
            question: The question or topic to search for.
        """
        try:
            answer = await search_knowledge_base(question)
            if answer:
                await ctx.session.generate_reply(
                    instructions=f"Based on our knowledge base: {answer}. Summarize this conversationally in 2-3 sentences."
                )
            else:
                await ctx.session.generate_reply(
                    instructions="I couldn't find specific information about that. Let the user know and offer to help with something else."
                )
        except Exception as e:
            logger.error(f"lookup_info failed: {e}")
            await ctx.session.generate_reply(
                instructions="I had trouble looking that up. Ask the user to try again."
            )


async def tap_user_audio(ctx: JobContext):
    """Background task: tap user microphone audio, detect emotion every N seconds."""
    global current_emotion

    try:
        # Wait for a remote participant to join
        participant = await ctx.wait_for_participant()
        logger.info(f"🎭 Emotion tap: subscribed to participant {participant.identity}")

        # Console mode uses mock participants — audio stream is not supported
        try:
            audio_stream = rtc.AudioStream.from_participant(
                participant=participant,
                track_source=rtc.TrackSource.SOURCE_MICROPHONE,
                sample_rate=EMOTION_SAMPLE_RATE,
                num_channels=1,
            )
        except Exception as e:
            logger.info(f"🎭 Audio emotion tap unavailable (console mode?): {e}")
            logger.info("🎭 Text-based emotion detection is still active")
            return

        frames: list[rtc.AudioFrame] = []
        buffered_duration = 0.0

        async for event in audio_stream:
            frame = event.frame
            frames.append(frame)
            buffered_duration += frame.samples_per_channel / frame.sample_rate

            if buffered_duration >= EMOTION_BUFFER_SECONDS:
                # Combine buffered frames into a single WAV
                try:
                    combined = rtc.combine_audio_frames(frames)
                    wav_bytes = combined.to_wav_bytes()

                    # POST to emotion backend
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            EMOTION_API_URL,
                            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                            timeout=10.0,
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            current_emotion = result
                            label = EMOTION_NAMES.get(result.get("label", ""), result.get("label", "unknown"))
                            score = result.get("score", 0)
                            logger.info(f"🎭 Emotion detected: {label} ({score:.0%})")
                        else:
                            logger.warning(f"🎭 Emotion API returned {resp.status_code}")
                except Exception as e:
                    logger.warning(f"🎭 Emotion detection error: {e}")

                # Reset buffer
                frames.clear()
                buffered_duration = 0.0

        await audio_stream.aclose()
    except asyncio.CancelledError:
        logger.info("🎭 Emotion audio tap cancelled")
    except Exception as e:
        logger.error(f"🎭 Emotion audio tap failed: {e}")


def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load(
        min_speech_duration=0.2,    # filter out very short noise bursts
        min_silence_duration=0.8,   # wait 800ms of silence before ending user turn
        activation_threshold=0.45,  # balanced - avoids echo/noise false triggers
    )


async def entrypoint(ctx: JobContext):
    global call_transcript, call_start_time, should_exit, transcript_stored, current_emotion, current_text_emotion, current_mood, mood_history, last_user_utterance_time
    
    # Reset state for this session
    call_transcript = []
    call_start_time = datetime.now()
    should_exit = False
    transcript_stored = False
    current_emotion = None
    current_text_emotion = None
    current_mood = None
    mood_history.clear()
    last_user_utterance_time = None
    emotion_task: asyncio.Task | None = None
    
    await ctx.connect()
    
    logger.info(f"Session started - Room: {ctx.room.name}")

    # --- Recall memories from Supabase (replaces Backboard) ---
    memory_context = ""
    user_id = None
    
    # Try to extract user_id and voice from metadata
    requested_voice = None
    try:
        if hasattr(ctx, 'job') and ctx.job and ctx.job.metadata:
            data = json.loads(ctx.job.metadata) if isinstance(ctx.job.metadata, str) else ctx.job.metadata
            user_id = data.get("user_id")
            requested_voice = data.get("voice")
    except Exception as e:
        logger.warning(f"Could not extract metadata fields: {e}")

    if not requested_voice and getattr(ctx.room, "metadata", None):
        try:
            room_metadata = json.loads(ctx.room.metadata) if isinstance(ctx.room.metadata, str) else ctx.room.metadata
            requested_voice = room_metadata.get("voice")
        except Exception as e:
            logger.warning(f"Could not extract voice from room metadata: {e}")

    if requested_voice and requested_voice not in ALLOWED_VOICES:
        logger.warning("Requested voice '%s' is not allowed. Falling back to %s.", requested_voice, DEFAULT_VOICE)
        requested_voice = None

    selected_voice = requested_voice or DEFAULT_VOICE
    
    # Store user_id in context for tools to access
    if user_id:
        ctx.user_id = user_id
    
    # Load conversation history if user_id available
    if user_id:
        try:
            profile = await get_user_profile(user_id)
            memory = profile.get("memory", "")
            if memory:
                memory_context = (
                    f"\n\n=== CONVERSATION CONTEXT ===\n"
                    f"Earlier in previous sessions, you and the user established:\n"
                    f"{memory}\n"
                    f"When the user asks questions related to these facts (their name, what they're doing, etc.), "
                    f"answer based on what you already know from earlier. This is continuation of your ongoing conversation."
                )
                logger.info(f"✅ Loaded memory from Supabase for user {user_id}")
            else:
                logger.info(f"📝 New user or no memory found for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not load memory from Supabase: {e}")
    else:
        logger.info("ℹ️ No user_id provided, starting fresh conversation")

    # Build model instructions
    instructions_text = f"""You are a friendly, playful voice assistant.
Your responses should be conversational and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
When the user says goodbye or wants to stop, use the end_conversation tool.
IMPORTANT: When the user asks ANYTHING about themselves, their past, their context, or what you remember about them - such as their name, location, what they're working on, where they are, what they told you before - ALWAYS use the recall_information tool FIRST to check your memory.
When the user asks about specific information, policies, or services, use the lookup_info tool.
Keep the responses short (under like 60 words).
You will occasionally receive context about the user's emotional state detected from their voice. Use this to adjust your response tone naturally. Be more gentle and supportive if they sound sad, more calm and understanding if angry, more enthusiastic if happy, and reassuring if fearful. Do not explicitly mention that you are detecting their emotions.{memory_context}"""
    
    logger.info(f"📋 Model instructions length: {len(instructions_text)} chars")
    if memory_context:
        logger.info(f"🧠 Memory context IS included in instructions")
    else:
        logger.info(f"⚠️  Memory context is EMPTY - agent won't have any memories")

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice=selected_voice,
        instructions=instructions_text,
        temperature=0.6,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
        ),
    )

    session = AgentSession(
        llm=model,
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.8,         # wait 800ms of silence before finalizing user turn
        max_endpointing_delay=4.0,         # hard cap at 4s
        allow_interruptions=True,          # allow real interruptions
        min_interruption_words=1,          # 1 word is enough to count as a real interruption
        min_interruption_duration=0.3,     # user must speak 300ms to count as a real interruption
        false_interruption_timeout=1.5,    # after 1.5s of silence, decide interruption was false and resume
        resume_false_interruption=True,    # resume agent speech after a false interruption
    )

    @ctx.room.on("data_received")
    def on_data_received(payload, participant, kind):
        try:
            data = json.loads(payload.decode())
        except Exception:
            return

        if data.get("type") == "voice_preview":
            text = str(data.get("text") or "").strip()
            if text:
                asyncio.create_task(session.say(text, allow_interruptions=True))

    # --- Event listeners for transcript logging ---
    # Set to False to disable transcript collection (for debugging latency)
    ENABLE_TRANSCRIPT = True
    
    if ENABLE_TRANSCRIPT:
        @session.on("conversation_item_added")
        def on_conversation_item(event):
            """Log and store conversation items (works with realtime models)."""
            msg = getattr(event, 'item', event)
            role = getattr(msg, 'role', 'unknown')
            
            # Extract content
            if hasattr(msg, 'text_content') and callable(msg.text_content):
                content = msg.text_content()
            elif hasattr(msg, 'content'):
                if isinstance(msg.content, list) and len(msg.content) > 0:
                    content = msg.content[0] if isinstance(msg.content[0], str) else str(msg.content[0])
                else:
                    content = str(msg.content)
            else:
                content = str(msg)
            
            # Log
            if role == 'user':
                logger.info(f"👤 USER: {content}")

                speech_features = extract_speech_features(content or "")

                # --- Analyze text emotion (async, non-blocking) ---
                if content and len(content.strip()) > 2:
                    asyncio.ensure_future(analyze_text_emotion(content, speech_features))
                else:
                    update_speech_mood(content, speech_features, None)

                # --- Log combined emotion state (no extra reply triggered) ---
                emotion_parts = []
                if current_emotion is not None:
                    audio_label = EMOTION_NAMES.get(
                        current_emotion.get("label", ""),
                        current_emotion.get("label", "unknown"),
                    )
                    audio_score = int(current_emotion.get("score", 0) * 100)
                    emotion_parts.append(f"voice: {audio_label} ({audio_score}%)")

                if current_text_emotion is not None:
                    text_label = TEXT_EMOTION_NAMES.get(
                        current_text_emotion.get("label", ""),
                        current_text_emotion.get("label", "unknown"),
                    )
                    text_score = int(current_text_emotion.get("score", 0) * 100)
                    emotion_parts.append(f"text: {text_label} ({text_score}%)")

                if emotion_parts:
                    logger.info(f"🎭 Emotion context: {'; '.join(emotion_parts)}")
            elif role == 'assistant':
                logger.info(f"🤖 AGENT: {content}")
            
            call_transcript.append({"role": role, "content": content})

            # Publish to room so frontend UI shows the transcript live
            if content and role in ('user', 'assistant'):
                payload = json.dumps({
                    "type": "transcript",
                    "speaker": role,
                    "text": content,
                }).encode()
                asyncio.ensure_future(
                    ctx.room.local_participant.publish_data(payload, reliable=True)
                )
    
    # --- End event listeners ---

    # Wrap everything in try/finally to ensure transcript is stored
    try:
        await session.start(
            agent=Assistant(),
            room=ctx.room,
            # Note: BVC noise cancellation removed — its AEC warm-up cycle was
            # suppressing user speech before the Gemini model could hear it.
            # Raw audio (used by emotion detection) was fine; processed audio was not.
        )

        await session.generate_reply(
            instructions="Greet the user warmly, like 'Hey! How can I help you today?'"
        )

        # Start emotion detection in background
        emotion_task = asyncio.create_task(tap_user_audio(ctx))
        logger.info("🎭 Emotion detection background task started")
        
        logger.info("💬 Waiting for conversation to end...")
        
        # Wait for session to end (when should_exit becomes True)
        while not should_exit:
            await asyncio.sleep(0.5)
        
        logger.info("🛑 Exit signal received, closing session...")
        
    finally:
        # Cancel emotion detection task
        if emotion_task is not None and not emotion_task.done():
            emotion_task.cancel()
            try:
                await emotion_task
            except asyncio.CancelledError:
                pass
            logger.info("🎭 Emotion detection task stopped")

        # Backup: Store transcript if not already stored (e.g., if session ended unexpectedly)
        if not transcript_stored and len(call_transcript) > 0:
            logger.info(f"📤 [BACKUP] Storing transcript to Supabase ({len(call_transcript)} messages)...")
            try:
                # Get user_id from context if available
                user_id = getattr(ctx, 'user_id', None)
                if user_id:
                    duration = (datetime.now() - call_start_time).total_seconds() if call_start_time else 0
                    success = await store_session_transcript(
                        user_id=user_id,
                        mode='voice',
                        transcript=call_transcript,
                        mood_timeline=list(mood_history),
                        duration_seconds=int(duration)
                    )
                    if success:
                        logger.info("✅ [BACKUP] Transcript stored in Supabase")
                    else:
                        logger.warning("❌ [BACKUP] Failed to store transcript in Supabase")
                else:
                    logger.warning("❌ [BACKUP] user_id not available, skipping transcript storage")
            except Exception as e:
                logger.error(f"❌ Failed to store transcript: {e}")
        elif transcript_stored:
            logger.info("✅ Transcript already stored (skipping duplicate)")
        
        # Close session
        try:
            await session.aclose()
            logger.info("✅ Session closed")
        except Exception as e:
            logger.error(f"❌ Error closing session: {e}")
        
        logger.info("👋 Session ended, exiting...")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="voice_agent",
        )
    )
