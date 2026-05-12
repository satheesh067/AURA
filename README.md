# AURA - AI-Powered Emotion Recognition & Voice Interaction System

![GitHub](https://img.shields.io/badge/GitHub-satheesh067/AURA-blue?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

AURA is an advanced AI system that combines emotion detection, real-time voice interaction, and gamification to provide personalized mental health and wellness support. The system uses cutting-edge technologies including LiveKit for real-time communication, Google Gemini for AI conversations, and Deepgram for speech recognition.

## 🌟 Key Features

### 🧠 Emotion Detection & Analysis
- Real-time emotion detection from facial expressions and voice patterns
- Multi-modal emotion recognition (visual + audio)
- Sentiment analysis for text-based interactions
- Emotional state tracking and history

### 🎤 Voice Interaction
- Real-time voice calls with AI assistant
- Speech-to-text powered by Deepgram
- Text-to-speech synthesis (Google or Cartesia)
- SIP trunk integration via Telnyx
- Multi-participant voice sessions with LiveKit

### 🎮 Gamification Engine
- Achievement badges and milestones
- Streaks and rewards tracking
- Leaderboards and rankings
- Daily challenges and goals
- Progress visualization dashboards
- Experience points (XP) system

### 💬 Text Chat Interface
- Real-time text chat with AI
- Message history and conversation context
- Rich media support
- User typing indicators

### 📊 Dashboard & Analytics
- Real-time emotion tracking dashboard
- Historical analysis and trends
- Personal health metrics
- Recommendations based on emotional patterns
- Crisis detection and emergency protocols

### 🔐 Security & Privacy
- End-to-end encryption for voice calls
- Secure API authentication with JWT
- Environment-based configuration
- No hardcoded credentials
- HIPAA-compliant data handling (when applicable)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  - Dashboard | Chat | Voice Calls | Gamification UI    │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼──────────┐
│  Phone Call    │   │  Emotion Backend  │
│  Backend       │   │  (Real-time)      │
│  (Node.js/Py) │   │  (Python/FastAPI) │
└───────┬────────┘   └────────┬──────────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  External Services  │
        ├─────────────────────┤
        │ - LiveKit (VoIP)    │
        │ - Deepgram (STT)    │
        │ - Google Gemini     │
        │ - Cartesia (TTS)    │
        │ - Telnyx (SIP)      │
        │ - Supabase (DB)     │
        │ - MySQL (Cache)     │
        └─────────────────────┘
```

## 📦 Project Structure

```
AURA/
├── frontend/                    # React + Vite frontend
│   ├── src/
│   │   ├── pages/              # Dashboard, Chat, Voice, etc.
│   │   ├── components/         # Reusable UI components
│   │   ├── contexts/           # Auth & state management
│   │   └── styles/             # CSS modules
│   └── package.json
│
├── phone-call-backend/         # Node.js/Python backend
│   ├── server.js               # Express API server
│   ├── agent.py                # AI agent orchestration
│   ├── api_server.py           # Additional APIs
│   ├── gamification_api.js     # Gamification endpoints
│   ├── recommendations_api.js  # AI recommendations
│   └── requirements.txt
│
├── emotion-backend/            # Real-time emotion detection
│   ├── app/
│   │   ├── server.py           # FastAPI server
│   │   ├── config.py           # Configuration
│   │   └── utils.py            # Utilities
│   ├── realtime_emotion.py     # Real-time processing
│   └── requirements.txt
│
└── lk-google-telnyx-1/        # Voice integration
    ├── call_via_livekit.py    # LiveKit voice calls
    ├── create_sip_call.py     # SIP call creation
    ├── outbound_agent.py      # Outbound call handler
    └── src/                    # Agent implementations
```

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+
- **Python** 3.9+
- **Git**
- API Keys for:
  - LiveKit Cloud (voice/video)
  - Google API (Gemini LLM + TTS)
  - Deepgram (speech-to-text)
  - Supabase (database)
  - (Optional) Cartesia, Telnyx, MySQL

### 1. Clone Repository

```bash
git clone https://github.com/satheesh067/AURA.git
cd AURA
```

### 2. Setup Frontend

```bash
cd frontend
npm install

# Create .env.example from .env.example file and fill in your credentials
cp .env.example .env

# Start development server
npm run dev
```

### 3. Setup Phone Call Backend

```bash
cd ../phone-call-backend

# Install Node dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Create .env from .env.example
cp .env.example .env
# Edit .env with your API keys

# Start the server
npm start
# Or run API server
python api_server.py
```

### 4. Setup Emotion Backend

```bash
cd ../emotion-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python app/server.py
```

### 5. Setup Voice Integration (Optional)

```bash
cd ../lk-google-telnyx-1

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run voice agent
python src/outbound_agent.py
```

## 🔑 Environment Setup

Each component requires specific environment variables. Use the `.env.example` files as templates:

### Frontend (.env.example)
```env
VITE_APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
VITE_APPWRITE_PROJECT_ID=your-project-id
VITE_GOOGLE_API_KEY=your_google_api_key
```

### Phone Call Backend (.env.example)
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
GOOGLE_API_KEY=your_google_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
JWT_SECRET=your-secret-key-change-in-production-use-32-chars-min
```

### Emotion Backend
```env
See emotion-backend/.env.example
```

### Voice Integration
```env
See lk-google-telnyx-1/.env.example
```

## 📡 API Endpoints

### Text Chat API
```
POST /api/chat
- Send message and receive AI response
- Body: { message: string, conversationId?: string }
- Returns: { response: string, emotion: string }

GET /api/chat/history
- Get conversation history
- Query: conversationId
- Returns: Array of messages with timestamps
```

### Voice Call API
```
POST /api/voice/call
- Initiate voice call
- Body: { phoneNumber: string, duration?: number }
- Returns: { callId: string, status: string }

GET /api/voice/status/:callId
- Check call status
- Returns: { status: string, duration: number }

POST /api/voice/end/:callId
- End active call
```

### Emotion Detection API
```
POST /api/emotion/detect
- Analyze emotion from audio/video
- Body: FormData with file or stream
- Returns: { emotion: string, confidence: number, details: {} }

GET /api/emotion/history
- Get emotion tracking history
- Query: userId, startDate, endDate
- Returns: Array of emotion records
```

### Gamification API
```
GET /api/gamification/user/progress
- Get user progress and achievements
- Returns: { level: number, xp: number, badges: [], streaks: {} }

POST /api/gamification/user/challenge/:challengeId
- Complete a challenge
- Returns: { xp_gained: number, badges_earned: [] }

GET /api/gamification/leaderboard
- Get global leaderboard
- Query: limit, offset
- Returns: Array of user rankings
```

### Recommendations API
```
GET /api/recommendations
- Get personalized recommendations
- Query: userId, type (health|wellness|mental)
- Returns: Array of recommendations with reasoning
```

## 🔒 Security Features

- **Environment Variables**: All sensitive data stored in `.env` files (never committed)
- **JWT Authentication**: Secure API endpoint protection
- **CORS Configuration**: Restricted cross-origin requests
- **Input Validation**: All user inputs sanitized
- **Rate Limiting**: API rate limits to prevent abuse
- **Encrypted Storage**: Sensitive data encrypted at rest

## 📊 Database Schema

### Supabase (Primary)
- `users` - User profiles and authentication
- `conversations` - Chat and voice conversation logs
- `emotions` - Real-time emotion tracking
- `achievements` - User achievements and badges
- `gamification_scores` - XP and ranking data

### MySQL (Cache/Secondary)
- Caching layer for high-frequency queries
- Real-time leaderboard updates
- Session management

## 🧪 Testing

```bash
# Frontend tests
cd frontend
npm run test

# Backend tests
cd phone-call-backend
python -m pytest tests/

# Emotion backend tests
cd emotion-backend
python -m pytest tests/
```

## 📈 Performance & Scaling

- **Real-time Processing**: WebSocket connections for instant updates
- **Horizontal Scaling**: Stateless backend services
- **Caching**: Redis/MySQL for high-frequency data
- **CDN**: Frontend assets served via CDN
- **Load Balancing**: API endpoints behind load balancer

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards
- Use ESLint for JavaScript/React
- Use Black for Python formatting
- Follow REST API conventions
- Write meaningful commit messages
- Document new features in README

## 🐛 Known Issues & Limitations

- Emotion detection works best in well-lit environments
- Voice quality depends on internet connection
- Some API services have rate limits
- Real-time features require WebSocket support

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support & Contact

- **Issues**: GitHub Issues for bug reports and feature requests
- **Documentation**: Check the wiki for detailed guides
- **Email**: For security issues, please email security@example.com

## 🙏 Acknowledgments

- **LiveKit** - Real-time communication infrastructure
- **Google Cloud** - Gemini LLM and Cloud Services
- **Deepgram** - Speech recognition
- **Supabase** - Database and authentication
- **React & Vite** - Frontend framework
- **FastAPI** - Python web framework

## 📚 Additional Resources

- [AURA Conference Paper](./AURA_Conference_Paper.tex)
- [Gamification Implementation Guide](./GAMIFICATION_QUICK_START.md)
- [Supabase Setup Guide](./README_SUPABASE.md)
- [Deployment Guide](./TESTING_DEPLOYMENT_GUIDE.md)
- [Quick Reference](./QUICK_REFERENCE.md)

---

**Last Updated**: May 2026  
**Current Version**: 1.0.0  
**Status**: Production Ready

For the latest updates, visit: https://github.com/satheesh067/AURA
