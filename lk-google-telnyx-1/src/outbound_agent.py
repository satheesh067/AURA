"""
OUTBOUND TELEPHONY AGENT
========================

This agent handles OUTBOUND calls initiated via LiveKit CLI.

HOW TO USE:
1. Your LiveKit CLI is already configured for outbound (in your setup)
2. Run: livekit-cli egress create-sip-participant <phone_number>
   This creates an outbound call and a room for the agent
3. Run: python outbound_agent.py start
   This starts the agent worker that will join the room
4. The agent will automatically answer and start the conversation

ENVIRONMENT VARIABLES:
- LIVEKIT_URL: Your LiveKit cloud URL
- LIVEKIT_API_KEY: LiveKit API key
- LIVEKIT_API_SECRET: LiveKit API secret
- GOOGLE_API_KEY: Google API key for Gemini
"""

import asyncio
import logging
import os
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
logger = logging.getLogger("outbound-telephony-agent")

# ============================================================================
# LIVEKIT CREDENTIALS - SET IN .env.local
# ============================================================================
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    raise ValueError("Missing required LiveKit credentials in .env.local")


class OutboundAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")

    @function_tool
    async def hang_up(self, ctx: RunContext):
        """Hang up the phone call."""
        await ctx.session.generate_reply(
            instructions="Say a brief goodbye like 'Thank you for your time. Goodbye!'"
        )
        await asyncio.sleep(2)
        ctx_job = get_job_context()
        if ctx_job:
            await ctx_job.api.room.delete_room(
                api.DeleteRoomRequest(room=ctx_job.room.name)
            )


async def dial_sip_call(phone_number: str, room_name: str) -> bool:
    """
    NOTE: Dialing is handled by LiveKit CLI.
    This function is for reference only.
    
    To make an outbound call:
    1. Use LiveKit CLI: livekit-cli egress create-sip-participant <phone_number>
    2. This creates a room and SIP participant
    3. Start this agent with: python outbound_agent.py start
    4. Agent will join the room and start the conversation
    """
    logger.info(f"Use LiveKit CLI to dial: livekit-cli egress create-sip-participant {phone_number}")
    return True


def prewarm(proc):
    """Pre-warm VAD model."""
    proc.userdata["vad"] = silero.VAD.load()


async def make_outbound_call(phone_number: str):
    """
    NOTE: Not used when LiveKit CLI handles dialing.
    
    To make an outbound call:
    1. Use LiveKit CLI: livekit-cli egress create-sip-participant <phone_number>
    2. This creates the room and SIP participant
    3. The agent will join automatically
    """
    logger.info(f"To call {phone_number}, use: livekit-cli egress create-sip-participant {phone_number}")


async def entrypoint(ctx: JobContext):
    """Entry point for outbound agent - joins room created by LiveKit CLI."""
    await ctx.connect()
    
    logger.info(f"Outbound agent connected - Room: {ctx.room.name}")

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Zephyr",
        instructions="""You are an AI agent handling an outbound call.

Your behavior:
- Introduce yourself and the purpose of the call professionally
- Be warm and conversational
- Listen carefully to the recipient
- Use the hang_up tool when the conversation is complete
- Keep responses concise and natural

This is a professional outbound call, so maintain a respectful tone.""",
        temperature=0.7,
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
        ),
    )

    session = AgentSession(
        llm=model,
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        agent=OutboundAssistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        ),
    )

    # Start the conversation
    await session.generate_reply(
        instructions="Introduce yourself and the purpose of this call."
    )
