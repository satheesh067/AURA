# Download the helper library from https://www.twilio.com/docs/python/install
import os
import uuid
from dotenv import load_dotenv
from twilio.rest import Client
from livekit import api as livekit_api

# Load environment variables from .env.local
load_dotenv(".env.local")

# Twilio credentials
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio_client = Client(account_sid, auth_token)

# LiveKit credentials
LIVEKIT_URL = os.environ["LIVEKIT_URL"]
LIVEKIT_API_KEY = os.environ["LIVEKIT_API_KEY"]
LIVEKIT_API_SECRET = os.environ["LIVEKIT_API_SECRET"]

# Phone numbers
TO_PHONE = "+918667382469"  # Recipient
FROM_PHONE = "+14842951132"  # Your Twilio number


def create_livekit_sip_participant_token(room_name: str):
    """Create a SIP participant token for LiveKit."""
    at = livekit_api.AccessToken(
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    sip_identity = f"sip_{uuid.uuid4().hex[:8]}"
    at.identity = sip_identity
    at.name = "SIP Participant"
    at.grants = livekit_api.VideoGrants(
        room_join=True,
        room=room_name,
    )
    return at.to_jwt()


def make_call_to_livekit(phone_number: str, room_name: str):
    """
    Make a Twilio call that connects to a LiveKit room via SIP.
    
    The call flow:
    1. Twilio dials the phone number
    2. TwiML instruction connects the call to LiveKit SIP endpoint
    3. Call arrives in LiveKit room as SIP participant
    4. agent.py detects the participant and answers
    """
    
    print(f"\n🚀 Initiating call to {phone_number}...")
    print(f"📍 Room: {room_name}")
    
    # Generate SIP token for the call
    sip_token = create_livekit_sip_participant_token(room_name)
    
    # LiveKit SIP endpoint format: sips://[token]@[livekit-url]
    # Extract domain from LIVEKIT_URL (wss://domain -> domain)
    livekit_domain = LIVEKIT_URL.replace("wss://", "").replace("ws://", "")
    
    # SIP address for LiveKit
    sip_address = f"sips:{sip_token}@{livekit_domain}/{room_name}"
    
    # TwiML that connects call to SIP
    twiml_instructions = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna-Generative">Connecting you to the AI assistant...</Say>
    <Dial>
        <Sip>{sip_address}</Sip>
    </Dial>
</Response>"""
    
    print(f"📞 TwiML: Connecting to {livekit_domain}")
    
    try:
        call = twilio_client.calls.create(
            twiml=twiml_instructions,
            to=phone_number,
            from_=FROM_PHONE,
        )
        
        print(f"✅ Call created successfully!")
        print(f"📌 Call SID: {call.sid}")
        print(f"🎤 Status: {call.status}")
        print(f"\n⏳ Waiting for agent to answer...")
        print(f"💡 Make sure agent.py is running: python src/agent.py start")
        
        return call.sid
        
    except Exception as e:
        print(f"❌ Error creating call: {e}")
        return None


if __name__ == "__main__":
    # Generate unique room name for this call
    room_name = f"call_{uuid.uuid4().hex[:8]}"
