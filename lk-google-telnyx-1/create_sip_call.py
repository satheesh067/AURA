"""
Simple script to create SIP participant (outbound call) via LiveKit API
No CLI needed - works directly with Python
"""

import os
import sys
from dotenv import load_dotenv
from livekit import api as livekit_api

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    print("❌ Missing LiveKit credentials in .env.local")
    sys.exit(1)


def create_sip_participant(phone_number: str):
    """Create a SIP participant to call a phone number."""
    
    # Validate phone number format
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
    
    print(f"\n📞 Creating SIP participant for: {phone_number}")
    
    try:
        # Create LiveKit API client
        at = livekit_api.AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )
        
        # The room name will be auto-generated or you can specify one
        room_name = f"call_{phone_number.replace('+', '').replace('-', '')}"
        
        at.identity = "sip-bot"
        at.name = f"Calling {phone_number}"
        at.grants = livekit_api.VideoGrants(
            room_join=True,
            room=room_name,
        )
        
        token = at.to_jwt()
        
        # Extract host from LIVEKIT_URL
