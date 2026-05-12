import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
    get_job_context,
    room_io,
)
from livekit import rtc, api
from livekit.plugins import google, noise_cancellation, silero
from google.genai import types

load_dotenv()
logger = logging.getLogger("telephony-realtime-agent")


# Function tools to enhance your agent's capabilities
@function_tool
async def get_current_time() -> str:
    """Get the current time."""
    return f"The current time is {datetime.now().strftime('%I:%M %p')}"


async def hangup_call():
    """Delete the room to end the call for all participants."""
    ctx = get_job_context()
    if ctx is None:
        return
    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(room=ctx.room.name)
    )


class TelephonyAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")  # Main instructions are in RealtimeModel

    @function_tool
    async def hang_up(self, ctx: RunContext):
        """Hang up the phone call. Use when the user says goodbye or wants to end the call."""
        await ctx.session.generate_reply(
            instructions="Say a brief, warm goodbye like 'Thank you for calling. Goodbye!'"
        )
        await asyncio.sleep(2)
        await hangup_call()


def prewarm(proc):
    """Pre-warm the VAD model."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """Main entry point for the realtime telephony voice agent."""
    await ctx.connect()
    
    logger.info(f"Call started - Room: {ctx.room.name}")

    # Determine time-based greeting
    hour = datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 18:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"

    # Initialize Google Realtime Model
    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Zephyr",
        instructions=f"""You are a friendly and helpful AI assistant answering phone calls. 

Your personality:
- Professional yet warm and approachable
- Speak clearly and at a moderate pace for phone calls
- Keep responses concise but complete
- Ask clarifying questions when needed

Your capabilities:
- Answer questions on a wide range of topics
- Tell the current time when asked
- Have natural conversations
- Use the get_current_time tool when someone asks for the time

Always identify yourself as an AI assistant when asked.
Keep responses conversational and under 30 seconds for phone clarity.

Start by saying: "{time_greeting}! Thank you for calling. How can I help you today?"
When the user says goodbye or wants to end the call, use the hang_up tool.""",
        temperature=0.7,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,  # Disable thinking for faster responses
        ),
    )

    # Initialize the agent session with realtime model
    session = AgentSession(
        llm=model,
        vad=ctx.proc.userdata["vad"],
    )

    # Start the agent session
    await session.start(
        agent=TelephonyAssistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # The greeting is already in the model instructions
    # No need to call generate_reply as the model will handle it
    logger.info("Agent session started and ready for incoming calls")


if __name__ == "__main__":
    # Configure logging for better debugging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent with the name that matches your dispatch rule
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        agent_name="telephone_agent"  # This must match your dispatch rule
    ))
