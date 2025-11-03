# AI-Powered Transcription Platform

> Professional audio/video transcription with AI-powered summarization, speaker diarization, and intelligent knowledge base

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

### Core Capabilities
- Audio & Video Transcription (Groq Whisper API)
- AI-Powered Summarization (LLaMA 3.1)
- Speaker Diarization (PyAnnote Audio)
- Real-Time Recording & Transcription
- Vector-Based Knowledge Base with RAG
- Multi-Format Support (MP3, WAV, MP4, MOV, M4A, etc.)
- URL/YouTube Video Processing

### Advanced Features
- Rate Limiting for API Protection
- Chunked Processing for Large Files (up to 2 hours)
- Smart Title Generation
- Export to PDF/Word
- Semantic Search Across Transcriptions
- Multi-User Support with Subscription Tiers
- RESTful API with Authentication

## Quick Start

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

### 3. Start Services
```bash
# With Docker (easiest)
docker-compose up -d

# OR manually (see DEPLOYMENT.md for details)
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Architecture

```
transcription-platform/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── routes/      # API endpoints
│   │   ├── services/    # Business logic
│   │   │   ├── rate_limiter.py
│   │   │   ├── diarization_service.py
│   │   │   ├── transcription_service.py
│   │   │   └── groq_service.py
│   │   ├── models.py    # Database models
│   │   └── config.py    # Configuration
│   └── requirements.txt
│
├── frontend/            # Next.js application
│   ├── src/
│   │   ├── app/        # App Router pages
│   │   ├── components/ # React components
│   │   └── types/      # TypeScript definitions
│   └── package.json
│
├── .env.example         # Environment template
├── docker-compose.yml   # Docker setup
├── DEPLOYMENT.md        # Deployment guide
└── README.md           # This file
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104
- **Database**: PostgreSQL 14+ (SQLAlchemy ORM)
- **Vector DB**: Qdrant (for semantic search)
- **Cache**: Redis
- **AI APIs**:
  - Groq (Whisper API for transcription)
  - Groq (LLaMA for summarization)
- **ML**: PyAnnote Audio (speaker diarization)
- **Processing**: FFmpeg, yt-dlp

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI**: React 18, TailwindCSS, Shadcn UI
- **State**: TanStack Query
- **HTTP**: Axios

## Key Features Explained

### 1. Rate Limiting
Protects your Groq API free tier with intelligent rate limiting:
- **Sliding window algorithm**: Tracks requests in real-time
- **Automatic retries**: Handles temporary failures
- **Configurable limits**: Adjust based on your tier

```python
# Automatic rate limiting for all Groq API calls
GROQ_RATE_LIMIT_RPM=25  # Requests per minute
GROQ_RATE_LIMIT_RPD=10000  # Requests per day
```

### 2. Speaker Diarization
Identifies and labels different speakers in audio:
- **Powered by PyAnnote**: State-of-the-art diarization
- **Automatic speaker counting**: 1-10 speakers
- **Timestamp alignment**: Accurate speaker segments
- **Export formats**: JSON, formatted text, detailed view

```json
{
  "speaker": "SPEAKER_00",
  "start": 0.5,
  "end": 5.2,
  "text": "Hello, welcome to the meeting."
}
```

### 3. Large File Support
Handles videos up to 2 hours:
- **Intelligent chunking**: Splits into 8-minute segments
- **Automatic compression**: Stays under API limits
- **Progress tracking**: Real-time status updates
- **Error recovery**: Resilient processing

### 4. Knowledge Base (RAG)
Semantic search across all your transcriptions:
- **Vector embeddings**: SentenceTransformers
- **Qdrant integration**: Fast similarity search
- **Context-aware**: Finds relevant content
- **Source tracking**: Links back to transcriptions

## API Examples

### Transcribe File
```bash
curl -X POST "http://localhost:8000/api/transcriptions/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@audio.mp3" \
  -F "language=en" \
  -F "generate_summary=true" \
  -F "speaker_diarization=true"
```

### Transcribe URL
```bash
curl -X POST "http://localhost:8000/api/transcriptions/url" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=VIDEO_ID",
    "language": "auto",
    "generate_summary": true
  }'
```

### Query Knowledge Base
```bash
curl -X POST "http://localhost:8000/api/knowledge/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were the key points discussed?",
    "max_results": 5
  }'
```

## Configuration

### Essential Settings

```env
# API Keys (REQUIRED)
GROQ_API_KEY=your_groq_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# Rate Limiting (RECOMMENDED)
GROQ_RATE_LIMIT_ENABLED=true
GROQ_RATE_LIMIT_RPM=25
GROQ_RATE_LIMIT_RPD=10000

# Speaker Diarization (OPTIONAL)
DIARIZATION_ENABLED=false
HUGGINGFACE_TOKEN=your_hf_token

# File Limits
MAX_FILE_SIZE=104857600  # 100MB
MAX_VIDEO_DURATION_MINUTES=120  # 2 hours
CHUNK_SIZE_MINUTES=8
```

### Subscription Tiers

```python
FREE_TIER:
  - 5 transcriptions/month
  - 10 minutes max per video

PRO_TIER:
  - 100 transcriptions/month
  - 60 minutes max per video

BUSINESS_TIER:
  - Unlimited transcriptions
  - 120 minutes max per video
```

## Development

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Database Migrations
```bash
cd backend

# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment instructions including:
- Docker deployment
- Platform deployment (Railway, Render, etc.)
- Manual server setup
- Production configuration
- Security best practices
- Monitoring & maintenance

## Project Status

### Completed Features
- ✅ Audio/Video transcription
- ✅ AI summarization
- ✅ Speaker diarization implementation
- ✅ Rate limiting for Groq API
- ✅ Large file support (2+ hours)
- ✅ Real-time recording
- ✅ Knowledge base with RAG
- ✅ Export to PDF/Word
- ✅ Multi-user authentication
- ✅ Subscription tiers
- ✅ Docker deployment

### In Development
- 🔄 Enhanced error handling
- 🔄 Webhook support
- 🔄 Batch processing
- 🔄 Mobile app

### Planned Features
- 📋 Language detection improvements
- 📋 Custom vocabulary support
- 📋 API rate limit dashboard
- 📋 Advanced analytics
- 📋 Team collaboration features

## Performance

### Benchmarks
- **Small file (5 min)**: ~30-60 seconds
- **Medium file (30 min)**: ~2-5 minutes
- **Large file (2 hours)**: ~10-20 minutes

### Optimization Tips
- Enable rate limiting to avoid quota issues
- Use chunked processing for files > 10 minutes
- Enable Redis caching
- Use CDN for static assets
- Scale horizontally with multiple workers

## Troubleshooting

### Common Issues

**Rate Limit Errors**
```bash
# Enable rate limiting in .env
GROQ_RATE_LIMIT_ENABLED=true
```

**FFmpeg Not Found**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

**Database Connection Failed**
```bash
# Check DATABASE_URL format
DATABASE_URL=postgresql://user:password@host:port/dbname
```

See [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md#troubleshooting) for more solutions.

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards
- **Backend**: Follow PEP 8, use type hints
- **Frontend**: Follow Airbnb style guide, use TypeScript
- **Commits**: Use conventional commits
- **Tests**: Write tests for new features

## Security

### Reporting Vulnerabilities
Please report security vulnerabilities to: security@yourdomain.com

### Best Practices
- Never commit `.env` files
- Rotate API keys regularly
- Use strong passwords
- Enable HTTPS in production
- Keep dependencies updated

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Groq](https://groq.com) for amazing Whisper and LLaMA APIs
- [PyAnnote Audio](https://github.com/pyannote/pyannote-audio) for speaker diarization
- [Qdrant](https://qdrant.tech) for vector database
- [FastAPI](https://fastapi.tiangolo.com) for the excellent framework
- [Next.js](https://nextjs.org) for the frontend framework

## Changelog

### v1.0.0 (2025-10-24)
- ✨ Initial release
- ✨ Rate limiting implementation
- ✨ Speaker diarization support
- ✨ Improved error handling
- ✨ Production-ready deployment configs
- 🐛 Fixed async issues in transcription service
- 📝 Comprehensive documentation

---

Made with ❤️ for the transcription community
