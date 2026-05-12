"""Simple test to verify LiveKit console mode behavior"""
import asyncio
import logging
from livekit import agents
from livekit.agents import JobContext, room_io
from livekit.plugins import silero

logger = logging.getLogger("test-agent")
logging.basicConfig(level=logging.INFO)

async def entrypoint(ctx: JobContext):
    logger.info(f"✅ Connected! Room: {ctx.room.name}")
    await ctx.connect()
    
    logger.info("💬 Session will run for 5 seconds then exit gracefully...")
    await asyncio.sleep(5)
    
    logger.info("👋 Exiting gracefully...")
    # This should complete before CLI shuts down

def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="test_agent",
        )
    )
