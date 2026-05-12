"""
Make outbound call via LiveKit API
Uses your built-in LiveKit phone numbers to call any number
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from livekit import api as livekit_api

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Your LiveKit provisioned number
FROM_PHONE = "+14842951134"

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    print("❌ Missing LiveKit credentials in .env.local")
    sys.exit(1)


def make_sip_call(to_phone: str, from_phone: str = FROM_PHONE):
    """Make an outbound call using LiveKit with your provisioned number."""
    
    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone
    
    print(f"\n📞 Calling: {to_phone}")
    print(f"📱 From: {from_phone}")
    
    # Generate room name
    room_name = f"call_{uuid.uuid4().hex[:8]}"
    
    # Extract host
    host = LIVEKIT_URL.replace("wss://", "").replace("ws://", "")
    
    # SIP address - call TO number from your FROM number
    sip_address = f"sips:{to_phone}@{host}"
    
    # Create JWT token for authentication
    at = livekit_api.AccessToken(
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    at.identity = "api-client"
    at.grants = livekit_api.VideoGrants(room_join=True, room="*")
    jwt_token = at.to_jwt()
    
    # LiveKit API endpoint for creating egress
    api_url = f"https://{host}/api/egress"
    
    # Create egress request with FROM number
    payload = {
        "room_name": room_name,
        "output": {
            "type": "SIP",
            "sip": {
                "address": sip_address,
                "headers": {
                    "From": f"<sips:{from_phone}@{host}>"
                }
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Call created successfully!")
            print(f"📍 Room: {room_name}")
            print(f"📌 Egress ID: {result.get('egress_id', 'N/A')}")
            print(f"🎤 Status: {result.get('state', 'STARTING')}")
            print(f"\n💡 Next steps:")
            print(f"   1. Start agent: python src/agent.py start")
            print(f"   2. Agent will auto-join and answer the call")
            print(f"   3. Caller will hear the AI agent greeting")
            return result
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to create call: {e}")
        print(f"\nℹ️  Make sure your LiveKit is configured correctly")
        print(f"   LIVEKIT_URL: {LIVEKIT_URL}")
        return None
