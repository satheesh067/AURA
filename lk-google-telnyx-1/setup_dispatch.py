#!/usr/bin/env python3
"""
Setup LiveKit dispatch rule to route voice-session-* rooms to the voice_agent.
Run this once to configure your LiveKit Cloud project.
"""

import os
import sys
from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    print("❌ Missing LiveKit credentials in .env.local")
    print("   Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
    sys.exit(1)

print("🔧 Setting up LiveKit dispatch rule...")
print(f"   URL: {LIVEKIT_URL}")
print(f"   Agent: voice_agent")
print(f"   Room pattern: voice-session-*")
print()

try:
    # Create API client
    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    # Note: The LiveKit Python SDK doesn't have direct dispatch rule creation yet
    # You'll need to use the CLI or dashboard
    print("⚠️  The LiveKit Python SDK doesn't support dispatch rule creation yet.")
    print()
    print("📋 Please use ONE of these methods:")
    print()
    print("1️⃣  LiveKit CLI (recommended):")
    print("   lk cloud auth")
    print("   lk app dispatch create \\")
    print("     --name 'voice-session-dispatch' \\")
    print("     --rule-type individual \\")
    print("     --room-prefix 'voice-session-' \\")
    print("     --agent-name 'voice_agent'")
    print()
    print("2️⃣  LiveKit Cloud Dashboard:")
    print("   https://cloud.livekit.io/")
    print("   → Agents → Dispatch Rules → Create")
