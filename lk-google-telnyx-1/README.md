# 🎙️ LiveKit + Google Gemini Voice Agent

**Real-time Voice AI Agent with Emotion Detection, Memory Persistence & Telephony Support**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LiveKit](https://img.shields.io/badge/LiveKit-Agents-orange)
![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5-green)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 📋 Overview

This project is a **production-ready voice AI agent** that combines:
- **Google Gemini 2.5 Flash Native Audio** for natural voice conversations
- **LiveKit** for real-time audio streaming and room management
- **Emotion Detection** from both voice (audio) and text (transcript)
- **Supabase** for persistent memory and conversation history
- **Telephony Support** for inbound/outbound phone calls via SIP

---

## 🗂️ Project Structure

```
lk-google-telnyx-1/
├── src/                          # Main source code
│   ├── agent.py                  # Primary voice agent (emotion-aware)
│   ├── outbound_agent.py         # Outbound telephony agent
│   ├── telephony_agent.py        # Inbound telephony agent
│   └── __init__.py
├── call_via_livekit.py           # Make calls via LiveKit API
├── make_call.py                  # Make calls via Twilio SIP
├── supabase_helper.py            # Database operations (memory, profiles)
├── setup_dispatch.py             # Setup LiveKit dispatch rules
├── start_agent.bat               # Windows batch script to start agent
├── .env.example                  # Environment variables template
├── pyproject.toml                # Python project configuration
└── README.md                     # This file
```

---

## 🔧 File Descriptions

### **Core Agents**

#### `src/agent.py` (702 lines) - Main Voice Agent
The primary emotion-aware voice agent with full features:

| Component | Description |
|-----------|-------------|
| **Emotion Detection** | Analyzes user voice (audio) and words (text) to detect emotions |
| **Speech Features** | Extracts hesitation, filler words, pause duration, word count |
| **Mood Fusion** | Combines audio + text emotions into a unified mood score |
| **Memory Integration** | Recalls user info from Supabase (name, past conversations) |
| **Transcript Storage** | Auto-saves conversations to Supabase at session end |
| **Function Tools** | `recall_information`, `lookup_info`, `end_conversation` |

**Key Functions:**
```python
async def entrypoint(ctx: JobContext)        # Main entry point
async def tap_user_audio(ctx)                # Background emotion detection
async def analyze_text_emotion(text)         # Text sentiment analysis
def update_speech_mood(text, features, emotion)  # Fuse mood signals
def extract_speech_features(text)            # Hesitation/pacing analysis
```

**Emotion Labels Supported:**
- Audio: `angry`, `happy`, `sad`, `neutral`, `fearful`, `disgusted`, `surprised`
- Text: `anger`, `joy`, `sadness`, `neutral`, `fear`, `disgust`, `surprise`

---

#### `src/outbound_agent.py` (151 lines) - Outbound Calls
Agent for **making** phone calls to users:

```python
class OutboundAssistant(Agent):
    @function_tool
    async def hang_up(self, ctx: RunContext):
        """End the call gracefully"""
```

**Usage:**
1. Create room via LiveKit CLI: `livekit-cli egress create-sip-participant <phone>`
2. Start agent: `python src/outbound_agent.py start`
3. Agent auto-joins and initiates conversation

---

#### `src/telephony_agent.py` (119 lines) - Inbound Calls
Agent for **receiving** phone calls:

```python
class TelephonyAssistant(Agent):
    @function_tool
    async def hang_up(self, ctx: RunContext):
        """Hang up when user says goodbye"""
    
    @function_tool
    async def get_current_time() -> str:
        """Tell user the current time"""
```

**Features:**
- Time-based greetings (Good morning/afternoon/evening)
- Professional phone etiquette
- Noise cancellation optimized for telephony

---

### **Helper Scripts**

#### `supabase_helper.py` (231 lines) - Database Operations
Handles all Supabase interactions:

| Function | Description |
|----------|-------------|
| `get_user_profile(user_id)` | Fetch user name, age, questionnaire |
| `get_user_reminders(user_id)` | Fetch active wellness reminders |
| `get_conversation_history(user_id)` | Get past messages (limit 10) |
| `search_knowledge_base(query)` | Search knowledge articles |
| `store_session_transcript(...)` | Save session to database |

---

#### `call_via_livekit.py` (101 lines) - LiveKit Calls
Make outbound calls using LiveKit's built-in phone numbers:

```python
def make_sip_call(to_phone: str, from_phone: str = "+14842951134"):
    """Create SIP egress to dial out"""
```

---

#### `make_call.py` (100 lines) - Twilio Calls
Make outbound calls via Twilio → LiveKit SIP bridge:

```python
def make_call_to_livekit(phone_number: str, room_name: str):
    """Twilio dials user, connects to LiveKit room via SIP"""
```

---

#### `setup_dispatch.py` (51 lines) - Dispatch Rules
Configure LiveKit to auto-route rooms to agents:

```bash
# Route voice-session-* rooms to voice_agent
lk app dispatch create \
  --name 'voice-session-dispatch' \
  --rule-type individual \
  --room-prefix 'voice-session-' \
  --agent-name 'voice_agent'
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env.local` with:

```env
# LiveKit Cloud
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Supabase (Memory & Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Optional: Speech Services
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Optional: Twilio (for make_call.py)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

### Emotion Detection API

The agent expects an emotion backend running at:
- Audio: `http://localhost:8000/predict` (WAV file upload)
- Text: `http://localhost:8000/predict-text` (JSON payload)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd lk-google-telnyx-1

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Install packages
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env.local
# Edit .env.local with your credentials
```

### 3. Start the Agent

**Windows:**
```bash
start_agent.bat
```

**Linux/Mac:**
```bash
python src/agent.py start
```

### 4. Make a Test Call

**Option A: Via LiveKit CLI**
```bash
livekit-cli egress create-sip-participant +1234567890
```

**Option B: Via Python Script**
```bash
python call_via_livekit.py
```

---

## 🧠 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LiveKit Cloud                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   SIP Trunk  │    │    Room      │    │  Dispatch │ │
│  │   (Telnyx)   │◄──►│  Management  │◄──►│   Rules   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   Python Agent                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Google Gemini 2.5 Flash              │  │
│  │           (Native Audio Model + TTS)              │  │
│  └──────────────────────────────────────────────────┘  │
│                             │                            │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Silero     │    │   Emotion    │    │ Supabase  │ │
│  │     VAD      │    │  Detection   │    │  Memory   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🎭 Emotion Detection Flow

```
User Speaks
     │
     ├───────────────────────────────┐
     │                               │
     ▼                               ▼
┌─────────────┐               ┌─────────────┐
│ Audio Stream│               │  Transcript │
│  (5 sec)    │               │   (text)    │
└─────────────┘               └─────────────┘
     │                               │
     ▼                               ▼
┌─────────────┐               ┌─────────────┐
│ /predict    │               │/predict-text│
│ (wav2vec2)  │               │(distilroberta)
└─────────────┘               └─────────────┘
     │                               │
     └───────────┬───────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Mood Fusion    │
        │ (audio + text + │
        │  speech pacing) │
        └─────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Mood: "calm"    │
        │ Score: +0.35    │
        │ Trend: improving│
        └─────────────────┘
```

---

## 📊 Mood Scoring Algorithm

The agent fuses multiple signals into a mood score:

| Signal | Weight | Positive | Negative |
|--------|--------|----------|----------|
| Audio Emotion | ±0.45 | happy, surprised | sad, angry, fearful |
| Text Emotion | ±0.35 | joy, surprise | anger, sadness, fear |
| Long Pause (>7s) | -0.20 | | ✓ |
| Quick Response | +0.05 | ✓ | |
| Detailed Response (30+ words) | +0.10 | ✓ | |
| Very Short Reply (≤4 words) | -0.10 | | ✓ |
| High Hesitation (≥22%) | -0.25 | | ✓ |
| Mild Hesitation (≥12%) | -0.15 | | ✓ |

**Final Mood Labels:**
- `energized` (score ≥ 0.45)
- `calm` (score ≥ 0.15)
- `neutral` (-0.15 to 0.15)
- `concerned` (score ≤ -0.15)
- `distressed` (score ≤ -0.45)

---

## 🛠️ Function Tools

The agent exposes these tools to the LLM:

### `recall_information(question: str)`
```python
# Example: "What is my name?"
# Returns: "From previous conversations: Your name is John..."
```

### `lookup_info(question: str)`
```python
# Example: "What are your office hours?"
# Returns: Knowledge base article match
```

### `end_conversation()`
```python
# Called when user says goodbye
# Saves transcript to Supabase, then exits
```

---

## 📞 Telephony Configuration

### SIP Trunk Setup (Telnyx/Vobiz)

1. Create SIP trunk in LiveKit Cloud Dashboard
2. Configure inbound/outbound routing
3. Set dispatch rule to route calls to `telephone_agent`

### Phone Number Provisioning

LiveKit Cloud provides provisioned numbers:
- `+14842951134` (example FROM number)

---

## 🐛 Debugging

### Logs

The agent logs detailed information:

```
INFO:voice-agent:👤 USER: How are you?
INFO:voice-agent:🎭 Emotion context: voice: happy (82%); text: joy (91%)
INFO:voice-agent:🧠 Speech mood → CALM (score +0.35) | pause=2.1s words=3 fillers=0
INFO:voice-agent:🤖 AGENT: I'm doing great, thanks for asking!
```

### Test Scripts

```bash
# Test LiveKit connection
python test_livekit.py

# Check memory usage
python check_memory.py

# Diagnostic test
python diagnostic_test.py
```

---

## 📦 Dependencies

```toml
[project.dependencies]
livekit-agents[silero,google]~=1.3
livekit-plugins-noise-cancellation~=0.2
python-dotenv
google-genai
httpx
supabase>=2.0.0
```

---

## 🤝 Integration Points

| Service | Purpose | Required |
|---------|---------|----------|
| LiveKit Cloud | Real-time audio, rooms, dispatch | ✅ Yes |
| Google Gemini | LLM + TTS | ✅ Yes |
| Supabase | Memory, transcripts, profiles | ⚡ Optional |
| Emotion Backend | Audio/text emotion detection | ⚡ Optional |
| Telnyx/Twilio | Phone number provisioning | ⚡ For telephony |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🚧 Roadmap

- [ ] WebRTC browser integration
- [ ] Multi-language support
- [ ] Custom wake word detection
- [ ] Webhook callbacks for call events
- [ ] Admin dashboard for call monitoring

---

**Built with ❤️ using LiveKit Agents + Google Gemini**
