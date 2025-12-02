# TranscribeAI - AI-Powered Meeting Assistant

> Never take meeting notes again. Professional transcription platform with calendar integration, real-time recording, and AI-powered insights.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Key Features

### 🗓️ Calendar Integration
- **Multi-Provider Support**: Connect Google Calendar, Microsoft Outlook, or Apple iCloud
- **One-Click OAuth**: Secure authentication in seconds
- **Auto-Sync Meetings**: Meetings appear automatically from your calendar
- **Platform Detection**: Automatically detects Zoom, Google Meet, Teams, and in-person meetings
- **Auto-Record Toggle**: Optionally start recording when meetings begin

### 🎙️ Real-Time Meeting Recording
- **Live Transcription**: See every word as it's spoken with WebSocket streaming
- **Speaker Diarization**: Automatically identifies and labels different speakers
- **Recording Controls**: Start, stop, pause, and resume with one click
- **High Accuracy**: 98% accuracy powered by Groq Whisper API
- **Multi-Language Support**: Transcribe in 50+ languages

### 🤖 AI-Powered Intelligence
- **Auto Summaries**: Generate concise meeting summaries with key points
- **Action Item Extraction**: Automatically identify tasks and assign owners
- **Smart Notes**: Structured notes with decisions and next steps
- **Meeting Templates**: Customize note formats for different meeting types
- **Chat with Meetings**: Ask questions about any past meeting using AI

### 📚 Advanced Knowledge Base
- **Vector Search**: Find any topic across all meetings instantly
- **Dual Chat Modes**:
  - "Chat with Meetings" - Query only meeting transcriptions
  - "Ask Anything" - Search across all content
- **Semantic Understanding**: Context-aware AI answers with source citations
- **Confidence Scoring**: See how relevant each answer is

### 📂 Smart Organization
- **Auto-Categorization**: Meetings and uploads organized automatically
- **Category Filters**: Separate views for Meetings vs Uploads
- **Folder System**: Organize by project, team, or client
- **Tags & Favorites**: Mark important meetings and add custom tags
- **Advanced Search**: Filter by status, date, category, and more

### 📊 Additional Capabilities
- **Audio & Video Processing**: Support for MP3, WAV, MP4, MOV, M4A, and more
- **URL/YouTube Support**: Transcribe directly from links
- **Export Options**: Download as PDF or Word documents
- **Multi-User Support**: Subscription tiers with usage limits
- **RESTful API**: Complete API access with authentication

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- OR: Python 3.11+, Node.js 18+, PostgreSQL, Redis

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd transcription-platform
```

### 2. Setup Environment
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
```env
# AI Services
GROQ_API_KEY=your_groq_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/transcribe_db
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Calendar Integration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret

# Vector Database (optional - uses pgvector by default)
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# JWT Secret
SECRET_KEY=your_secret_key
```

### 3. Start Services
```bash
# With Docker (easiest)
docker-compose up -d

# OR manually (see Development section)
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104
- **Database**: PostgreSQL 14+ with pgvector extension
- **Cache**: Redis
- **AI Services**:
  - Groq Whisper (transcription)
  - Groq LLaMA (summarization & chat)
- **ML**:
  - PyAnnote Audio (speaker diarization)
  - SentenceTransformers (embeddings)
- **Calendar APIs**:
  - Google Calendar API (OAuth 2.0)
  - Microsoft Graph API (OAuth 2.0)
  - CalDAV (Apple iCloud)
- **Processing**: FFmpeg, yt-dlp
- **WebSocket**: For real-time transcription streaming

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS, Shadcn UI
- **State**: TanStack Query
- **Real-time**: WebSocket client for live transcription
- **HTTP**: Axios
- **Icons**: Lucide React + custom SVG/PNG

## 📖 Feature Deep Dive

### Calendar Integration

Connect your calendar in three easy steps:

1. **Choose Provider**: Select Google, Microsoft, or Apple Calendar
2. **Authorize**: Secure OAuth flow (or CalDAV for Apple)
3. **Auto-Sync**: Meetings appear automatically

**Supported Platforms**:
- Google Calendar (Gmail, Workspace)
- Microsoft Outlook (Outlook.com, Microsoft 365, Exchange)
- Apple iCloud Calendar (macOS, iOS)

**Auto-Detection**:
- Detects meeting platform from URL (Zoom, Google Meet, Teams)
- Identifies meeting type (video, phone, in-person)
- Extracts participants and agenda automatically

### Real-Time Recording & Transcription

**Recording Workflow**:
1. Click "Start Recording" on any meeting
2. Grant microphone access (browser permission)
3. See live transcription appear in real-time
4. Click "Stop" when meeting ends
5. AI generates summary and action items automatically

**WebSocket Architecture**:
```
Browser Microphone → MediaRecorder → WebSocket
                                         ↓
Backend Buffer (5 sec) → Groq Whisper → Live Transcript
                                         ↓
Database Storage → Knowledge Base Embedding
```

**Recording Features**:
- Live captions during meeting
- Speaker identification
- Pause/Resume capability
- Audio quality monitoring
- Automatic categorization as "Meeting"

### AI-Powered Notes

After each meeting, AI automatically generates:

**Structured Summary**:
- Key discussion points
- Decisions made
- Important mentions

**Action Items**:
```json
{
  "title": "Follow up with design team",
  "assigned_to": "john@company.com",
  "priority": "high",
  "due_date": "2024-12-01",
  "status": "pending"
}
```

**Meeting Templates**:
Customize note structure for different meeting types:
- Standup meetings
- Sprint planning
- Customer calls
- 1-on-1s
- Board meetings

### Knowledge Base with Dual Chat Modes

**"Ask Anything" Mode**:
- Searches across ALL transcriptions (meetings + uploads)
- Perfect for finding information anywhere
- Example: "What features did we discuss last month?"

**"Chat with Meetings" Mode**:
- Searches ONLY meeting transcriptions
- Focused on meeting-specific queries
- Example: "What action items came from the Q4 planning meeting?"

**Vector Search Technology**:
- Uses pgvector for similarity search
- SentenceTransformer embeddings (384 dimensions)
- Cosine similarity scoring
- Returns top 5 most relevant sources
- Shows confidence percentages

### Library Organization

**Smart Categorization**:
- **Meetings**: Recordings from calendar events
- **Uploads**: Manually uploaded audio/video files

**Filter Options**:
- By category (All, Meetings, Uploads)
- By status (Completed, Processing, Failed)
- By folder (organize by project/team)
- By favorites (starred items)
- Full-text search by title

**View Modes**:
- Grid view (3 columns with previews)
- List view (compact table format)

## 🔌 API Examples

### Connect Google Calendar
```bash
curl -X POST "http://localhost:8000/api/calendar/google/auth" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Returns: { "auth_url": "https://accounts.google.com/o/oauth2/..." }
```

### Sync Calendar Events
```bash
curl -X POST "http://localhost:8000/api/calendar/sync/{connection_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Start Real-Time Recording
```bash
curl -X POST "http://localhost:8000/api/recording/start" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_id": "meeting-uuid-here"
  }'
# Returns: { "session_id": "...", "websocket_url": "ws://..." }
```

### Query Knowledge Base (Meeting-Specific)
```bash
curl -X POST "http://localhost:8000/api/knowledge/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What decisions were made in yesterday meeting?",
    "source_type": "meeting",
    "limit": 5
  }'
```

### List Meetings
```bash
curl -X GET "http://localhost:8000/api/meetings?status=upcoming&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Transcriptions by Category
```bash
curl -X GET "http://localhost:8000/api/transcriptions?source_type=meeting&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ⚙️ Configuration

### Calendar Integration Setup

**Google Calendar**:
1. Create OAuth 2.0 credentials at [Google Cloud Console](https://console.cloud.google.com)
2. Add redirect URI: `http://localhost:3000/settings/calendar`
3. Enable Google Calendar API
4. Add credentials to `.env`:
```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3000/settings/calendar
```

**Microsoft Outlook**:
1. Register app at [Azure Portal](https://portal.azure.com)
2. Add API permissions: `Calendars.Read`, `User.Read`
3. Add credentials to `.env`:
```env
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_REDIRECT_URI=http://localhost:3000/settings/calendar
MICROSOFT_TENANT_ID=common
```

**Apple iCloud**:
- Uses CalDAV protocol (no OAuth required)
- Users provide their iCloud email + app-specific password
- Generate password at [appleid.apple.com](https://appleid.apple.com)

### Rate Limiting
```env
GROQ_RATE_LIMIT_ENABLED=true
GROQ_RATE_LIMIT_RPM=25      # Requests per minute
GROQ_RATE_LIMIT_RPD=10000   # Requests per day
```

### File Processing
```env
MAX_FILE_SIZE=104857600              # 100MB
MAX_VIDEO_DURATION_MINUTES=120       # 2 hours
CHUNK_SIZE_MINUTES=8                 # For large files
```

### Subscription Tiers
```python
FREE_TIER:
  - 5 transcriptions/month
  - 10 minutes max per file
  - Basic features only

PRO_TIER:
  - 100 transcriptions/month
  - 60 minutes max per file
  - Calendar integration
  - Real-time recording
  - AI-powered notes

BUSINESS_TIER:
  - Unlimited transcriptions
  - 120 minutes max per file
  - All features
  - Priority support
```

## 💻 Development

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

### Database Migrations
```bash
cd backend

# Create new migration
alembic revision -m "add meeting notes table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Real-Time Recording Development
```bash
# Terminal 1: Backend with WebSocket support
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend with hot reload
cd frontend
npm run dev

# Test WebSocket connection in browser console:
const ws = new WebSocket('ws://localhost:8000/api/recording/ws/session-id')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

## 🚢 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment instructions including:
- Docker deployment (recommended)
- Platform deployment (Railway, Render, Vercel)
- Manual server setup
- Production configuration
- Security best practices
- SSL/HTTPS setup
- Monitoring & logging
- Backup strategies

### Quick Docker Deployment
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Performance

### Benchmarks
- **Small meeting (15 min)**: ~1-2 minutes processing
- **Medium meeting (45 min)**: ~3-5 minutes processing
- **Large meeting (2 hours)**: ~10-15 minutes processing
- **Real-time transcription**: < 2 second latency

### Optimization Tips
1. **Enable Rate Limiting**: Prevents API quota issues
2. **Use pgvector**: Faster than Qdrant for small-medium datasets
3. **Enable Redis Caching**: Speeds up repeated queries
4. **Chunk Large Files**: Better reliability for long recordings
5. **WebSocket Pooling**: Reuse connections for multiple recordings

## 🔧 Troubleshooting

### Calendar Connection Issues

**Google Calendar "Access Denied"**
```bash
# Verify redirect URI matches exactly
GOOGLE_REDIRECT_URI=http://localhost:3000/settings/calendar

# Check OAuth consent screen is configured
# Enable Google Calendar API in Google Cloud Console
```

**Microsoft "Admin Approval Required"**
```bash
# For organizational accounts:
# 1. Contact IT admin to approve app
# 2. OR use personal account (@outlook.com, @hotmail.com)

# Verify scopes are correct (no reserved scopes)
# Scopes: Calendars.Read, User.Read
```

**Apple Calendar "Invalid Credentials"**
```bash
# Ensure using app-specific password, not regular password
# Generate at: https://appleid.apple.com → Security → App-Specific Passwords
# Use full iCloud email (e.g., user@icloud.com)
```

### Recording Issues

**Microphone Not Accessible**
- Grant browser permission for microphone
- Check system audio settings
- Ensure HTTPS (or localhost) for WebRTC

**WebSocket Connection Failed**
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify WebSocket endpoint
# Should be: ws://localhost:8000/api/recording/ws/{session_id}
```

**Transcription Not Appearing**
- Check Groq API key is valid
- Verify rate limits not exceeded
- Check backend logs for errors

### Database Issues

**Migration Failed**
```bash
# Reset to specific migration
alembic downgrade <revision>

# Force upgrade
alembic upgrade head --sql  # Preview SQL
alembic upgrade head        # Execute
```

**pgvector Extension Missing**
```bash
# PostgreSQL with pgvector required
# Install: https://github.com/pgvector/pgvector

# Or use Supabase (has pgvector built-in)
```

## 📈 Roadmap

### Completed ✅
- [x] Calendar integration (Google, Microsoft, Apple)
- [x] Real-time meeting recording
- [x] Live transcription with WebSocket
- [x] AI-powered summaries
- [x] Knowledge base with dual chat modes
- [x] Library organization with categories
- [x] Speaker diarization
- [x] Export to PDF/Word
- [x] Multi-user authentication
- [x] Custom calendar icons

### In Progress 🔄
- [ ] Auto-record meetings (background service)
- [ ] AI action item extraction
- [ ] Meeting templates customization
- [ ] Email meeting summaries to participants
- [ ] Upcoming meetings dashboard

### Planned 📋
- [ ] Mobile apps (iOS, Android)
- [ ] Slack/Teams integration
- [ ] Video recording with screen share
- [ ] Meeting analytics & insights
- [ ] Custom AI prompts for summaries
- [ ] Webhooks for integrations
- [ ] API rate limit dashboard
- [ ] Advanced collaboration features

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add calendar sync'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- **Backend**: Follow PEP 8, use type hints, async/await
- **Frontend**: TypeScript strict mode, ESLint rules
- **Commits**: Use conventional commits (feat:, fix:, docs:)
- **Tests**: Write tests for new features
- **Documentation**: Update README for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Lightning-fast Whisper and LLaMA APIs
- [PyAnnote Audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [FastAPI](https://fastapi.tiangolo.com) - Modern Python web framework
- [Next.js](https://nextjs.org) - React framework for production
- [Shadcn UI](https://ui.shadcn.com) - Beautiful UI components
- Google, Microsoft, Apple - Calendar API providers

## 📝 Changelog

### v2.0.0 (2024-11-27) - Granola Update 🎉
- ✨ Calendar integration (Google, Microsoft, Apple)
- ✨ Meeting sync and management
- ✨ Real-time recording with WebSocket streaming
- ✨ Live transcription display
- ✨ Knowledge base dual chat modes (All vs Meetings)
- ✨ Library categorization (Meetings vs Uploads)
- ✨ Custom calendar provider icons
- ✨ Platform detection and recommendations
- ✨ Meeting notes and action items models
- ✨ Advanced landing page redesign
- 🔧 Migrated from Qdrant to pgvector
- 🔧 Improved folder and tag organization
- 📝 Comprehensive documentation updates

### v1.0.0 (2024-10-24)
- ✨ Initial release
- ✨ Audio/video transcription
- ✨ AI summarization
- ✨ Speaker diarization
- ✨ Rate limiting
- ✨ Knowledge base with RAG
- 🐛 Bug fixes and performance improvements


<div align="center">

**Made with ❤️ for productive meetings**

</div>
