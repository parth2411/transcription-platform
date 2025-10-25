# Transcription Platform - Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Rate Limiting](#rate-limiting)
- [Speaker Diarization](#speaker-diarization)
- [Troubleshooting](#troubleshooting)

---

## Overview

This is an AI-powered transcription platform with the following features:
- Audio/Video transcription using Groq Whisper API
- Speaker diarization (optional)
- AI-powered summarization
- Vector-based knowledge base with RAG
- Real-time recording and transcription
- Export to PDF/Word

### Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Next.js 14 (React 18)
- **Database**: PostgreSQL
- **Vector DB**: Qdrant
- **Cache**: Redis
- **AI APIs**: Groq (Whisper + LLaMA)

---

## Prerequisites

### Required Services
1. **PostgreSQL** (v14+)
2. **Redis** (v6+)
3. **Qdrant** (Cloud or Self-hosted)

### Required API Keys
1. **Groq API Key** - Get from [console.groq.com](https://console.groq.com/keys)
   - Free tier: 30 requests/min, 14,400/day
   - Used for transcription and summarization

2. **Qdrant API** - Get from [cloud.qdrant.io](https://cloud.qdrant.io)
   - Free tier available
   - Used for vector storage and semantic search

3. **HuggingFace Token** (Optional) - For speaker diarization
   - Get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### System Requirements
- Python 3.11+
- Node.js 18+
- FFmpeg (for audio processing)
- 2GB+ RAM (4GB+ recommended)
- 10GB+ disk space

---

## Environment Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd transcription-platform
```

### 2. Backend Environment

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install ffmpeg

# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Windows)
# Download from https://ffmpeg.org/download.html
```

### 3. Frontend Environment

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Security (REQUIRED - Generate strong key)
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database (REQUIRED)
DATABASE_URL=postgresql://user:password@localhost:5432/transcription_db

# Groq API (REQUIRED)
GROQ_API_KEY=gsk_your_actual_key_here

# Qdrant (REQUIRED)
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_key_here

# Rate Limiting (Recommended for Free Tier)
GROQ_RATE_LIMIT_ENABLED=true
GROQ_RATE_LIMIT_RPM=25
GROQ_RATE_LIMIT_RPD=10000

# Speaker Diarization (OPTIONAL)
DIARIZATION_ENABLED=false
HUGGINGFACE_TOKEN=your_hf_token_here
```

**Important**:
- Never commit `.env` to git
- Use `.env.example` as a template
- Rotate keys immediately if exposed

### 5. Database Setup

```bash
cd backend

# Create database
createdb transcription_db

# Or using psql
psql -U postgres
CREATE DATABASE transcription_db;
\q

# Run migrations
alembic upgrade head
```

---

## Local Development

### Start Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:3000`

### Start with Docker Compose

```bash
docker-compose up -d
```

Services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

---

## Production Deployment

### Option 1: Docker Deployment

#### Build Images

```bash
# Backend
cd backend
docker build -t transcription-backend:latest .

# Frontend
cd frontend
docker build -t transcription-frontend:latest .
```

#### Deploy with Docker Compose

```bash
# Production compose file
docker-compose -f docker-compose.prod.yml up -d
```

#### Environment Variables in Production

Create `.env` file with production values:

```env
# Use strong, unique values for production
SECRET_KEY=<64-char-random-string>
DATABASE_URL=postgresql://prod_user:strong_password@db:5432/transcription_prod
ALLOWED_ORIGINS=https://yourdomain.com
```

### Option 2: Platform Deployment (Railway, Render, etc.)

#### Railway Deployment

1. Create new project on Railway
2. Add PostgreSQL and Redis services
3. Deploy backend:
   ```bash
   railway up
   ```
4. Add environment variables in Railway dashboard
5. Deploy frontend similarly

#### Environment Variables to Set:
- All variables from `.env.example`
- Set `DATABASE_URL` to Railway PostgreSQL URL
- Set `REDIS_URL` to Railway Redis URL
- Set `ALLOWED_ORIGINS` to your frontend URL

### Option 3: Manual Server Deployment

#### Backend (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3.11 python3-pip ffmpeg postgresql-client redis-tools nginx

# Clone and setup
git clone <repo> /var/www/transcription-platform
cd /var/www/transcription-platform/backend

# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn

# Setup systemd service
sudo nano /etc/systemd/system/transcription-backend.service
```

```ini
[Unit]
Description=Transcription Backend
After=network.target postgresql.service redis.service

[Service]
User=www-data
WorkingDirectory=/var/www/transcription-platform/backend
Environment="PATH=/var/www/transcription-platform/backend/.venv/bin"
EnvironmentFile=/var/www/transcription-platform/.env
ExecStart=/var/www/transcription-platform/backend/.venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    app.main:app

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable transcription-backend
sudo systemctl start transcription-backend
```

#### Frontend

```bash
cd /var/www/transcription-platform/frontend

# Build frontend
npm install
npm run build

# Setup with PM2
npm install -g pm2
pm2 start npm --name "transcription-frontend" -- start
pm2 save
pm2 startup
```

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/transcription

# Backend
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable and restart nginx
sudo ln -s /etc/nginx/sites-available/transcription /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Rate Limiting

The platform includes built-in rate limiting for Groq API to protect free tier limits:

### Default Settings
- **RPM (Requests Per Minute)**: 25 (Groq free tier: 30)
- **RPD (Requests Per Day)**: 10,000 (Groq free tier: 14,400)

### Configuration

In `.env`:
```env
GROQ_RATE_LIMIT_ENABLED=true
GROQ_RATE_LIMIT_RPM=25
GROQ_RATE_LIMIT_RPD=10000
```

### How It Works
1. **Sliding Window**: Tracks requests in real-time
2. **Automatic Waiting**: Pauses requests when limit reached
3. **Retry Logic**: Automatically retries failed requests
4. **Graceful Degradation**: Falls back on errors

### Monitor Rate Limits

Check current usage via API:
```bash
curl http://localhost:8000/api/rate-limit/stats
```

---

## Speaker Diarization

Speaker diarization identifies and segments different speakers in audio.

### Setup

1. **Get HuggingFace Token**
   - Create account at [huggingface.co](https://huggingface.co)
   - Generate token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

2. **Accept Model License**
   - Visit [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - Accept the license agreement

3. **Install Dependencies**
   ```bash
   pip install pyannote.audio torch torchaudio
   ```

4. **Enable in Environment**
   ```env
   DIARIZATION_ENABLED=true
   HUGGINGFACE_TOKEN=hf_your_token_here
   MIN_SPEAKERS=1
   MAX_SPEAKERS=10
   ```

### Usage

When creating transcription, set `speaker_diarization=true`:

```json
{
  "file": "<audio_file>",
  "speaker_diarization": true,
  "generate_summary": true
}
```

### Output Format

```json
{
  "transcription_text": "Full transcription...",
  "diarization_data": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.5,
      "end": 5.2,
      "text": "Hello, welcome to the meeting.",
      "duration": 4.7
    },
    {
      "speaker": "SPEAKER_01",
      "start": 5.5,
      "end": 10.3,
      "text": "Thanks for having me.",
      "duration": 4.8
    }
  ],
  "speaker_count": 2
}
```

---

## Troubleshooting

### Common Issues

#### 1. Groq Rate Limit Errors

**Error**: `Rate limit exceeded`

**Solution**:
- Enable rate limiting in `.env`
- Reduce `GROQ_RATE_LIMIT_RPM` value
- Upgrade to Groq paid tier

#### 2. FFmpeg Not Found

**Error**: `FFmpeg not found`

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### 3. Database Connection Failed

**Error**: `Could not connect to PostgreSQL`

**Solution**:
- Check `DATABASE_URL` format
- Verify PostgreSQL is running
- Check firewall rules
- Test connection: `psql $DATABASE_URL`

#### 4. Qdrant Connection Failed

**Error**: `Qdrant client initialization failed`

**Solution**:
- Verify `QDRANT_URL` and `QDRANT_API_KEY`
- Check Qdrant service status
- Ensure network connectivity
- Try setting `prefer_grpc=False`

#### 5. Out of Memory

**Error**: `MemoryError` during transcription

**Solution**:
- Reduce `CHUNK_SIZE_MINUTES` in config
- Increase server RAM
- Enable swap space
- Process smaller files

#### 6. Diarization Not Working

**Error**: `Diarization failed` or `Model not found`

**Solution**:
- Accept model license on HuggingFace
- Verify `HUGGINGFACE_TOKEN` is valid
- Install: `pip install pyannote.audio torch`
- Check GPU/CPU compatibility

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

View logs:
```bash
# Docker
docker-compose logs -f backend

# Systemd
sudo journalctl -u transcription-backend -f

# Direct
tail -f backend/logs/app.log
```

### Health Checks

Check service health:

```bash
# Backend
curl http://localhost:8000/health

# Database
psql $DATABASE_URL -c "SELECT 1"

# Redis
redis-cli ping
```

---

## Security Best Practices

### 1. Environment Variables
- Never commit `.env` to git
- Use strong, random `SECRET_KEY`
- Rotate API keys regularly
- Use secrets management in production

### 2. Database
- Use strong passwords
- Enable SSL connections
- Restrict network access
- Regular backups

### 3. API Keys
- Restrict API key permissions
- Monitor usage
- Set up alerts for unusual activity
- Use separate keys for dev/prod

### 4. File Uploads
- Validate file types
- Scan for malware
- Set size limits
- Use isolated storage

### 5. Rate Limiting
- Enable for all public APIs
- Monitor abuse
- Set appropriate limits
- Implement IP-based restrictions

---

## Monitoring & Maintenance

### Monitoring

1. **Application Metrics**
   - Response times
   - Error rates
   - Queue lengths
   - Memory usage

2. **API Usage**
   - Groq API calls
   - Rate limit hits
   - Failed requests

3. **Storage**
   - Disk space
   - Database size
   - Upload directory

### Maintenance Tasks

```bash
# Daily
- Check error logs
- Monitor API usage
- Verify backups

# Weekly
- Clean up old uploads
- Analyze performance
- Review rate limits

# Monthly
- Update dependencies
- Security patches
- Database optimization
- Rotate logs
```

### Backup Strategy

```bash
# Database backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_YYYYMMDD.sql

# Automated backup (cron)
0 2 * * * /path/to/backup-script.sh
```

---

## Performance Optimization

### Backend
- Use Gunicorn with multiple workers
- Enable database connection pooling
- Implement caching (Redis)
- Use CDN for static files

### Frontend
- Enable Next.js optimizations
- Compress images
- Lazy load components
- Use CDN

### Database
- Add indexes on frequently queried fields
- Regular VACUUM and ANALYZE
- Monitor slow queries
- Use read replicas for scaling

---

## Support & Resources

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]
- **Discord/Slack**: [Community link]
- **Email**: support@yourdomain.com

---

## License

[Your License]

## Contributors

[Your team/contributors]
