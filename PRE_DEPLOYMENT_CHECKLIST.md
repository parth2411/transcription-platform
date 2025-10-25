# Pre-Deployment Checklist

**CRITICAL**: Complete ALL items before deploying to production

---

## ⚠️ IMMEDIATE ACTIONS (DO FIRST!)

### 1. Rotate Exposed API Keys 🔴 CRITICAL
Your API keys were exposed in git history. You MUST rotate them immediately:

- [ ] **Groq API Key**
  - Go to: https://console.groq.com/keys
  - Revoke the exposed key (starts with `gsk_0gCBVG...`)
  - Generate new key
  - Update `.env` file

- [ ] **Qdrant API Key**
  - Go to: https://cloud.qdrant.io (your cluster settings)
  - Revoke exposed key
  - Generate new key
  - Update `.env` file

- [ ] **Secret Key**
  - Generate new strong secret key:
    ```bash
    openssl rand -hex 32
    ```
  - Update `.env` file

---

## 🔐 Security Setup

- [ ] Verify `.env` file is NOT in git
  ```bash
  git status  # Should NOT show .env
  ```

- [ ] Verify `.gitignore` excludes sensitive files
  ```bash
  cat .gitignore  # Should include .env, *.backup, etc.
  ```

- [ ] Review and fill out `.env` file with correct values
  ```bash
  cp .env.example .env
  nano .env  # Edit with your values
  ```

- [ ] Set strong `SECRET_KEY` (at least 32 characters)

- [ ] Configure `ALLOWED_ORIGINS` for production domain

---

## 📦 Environment Configuration

- [ ] Database URL is correct
  ```env
  DATABASE_URL=postgresql://user:password@host:port/dbname
  ```

- [ ] Redis URL is configured (if using background tasks)
  ```env
  REDIS_URL=redis://localhost:6379
  ```

- [ ] Groq API key is set and valid
  ```env
  GROQ_API_KEY=gsk_your_new_key_here
  ```

- [ ] Qdrant connection details are correct
  ```env
  QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
  QDRANT_API_KEY=your_new_key_here
  ```

- [ ] Rate limiting is configured
  ```env
  GROQ_RATE_LIMIT_ENABLED=true
  GROQ_RATE_LIMIT_RPM=25
  GROQ_RATE_LIMIT_RPD=10000
  ```

- [ ] Speaker diarization settings (if needed)
  ```env
  DIARIZATION_ENABLED=false  # Set to true if using
  HUGGINGFACE_TOKEN=your_token_here  # Only if diarization enabled
  ```

---

## 🗄️ Database Setup

- [ ] PostgreSQL is installed and running
  ```bash
  psql --version
  ```

- [ ] Database is created
  ```bash
  createdb transcription_db
  # or
  psql -U postgres -c "CREATE DATABASE transcription_db;"
  ```

- [ ] Database connection works
  ```bash
  psql $DATABASE_URL -c "SELECT 1;"
  ```

- [ ] Run database migrations
  ```bash
  cd backend
  alembic upgrade head
  ```

- [ ] Verify migrations applied
  ```bash
  alembic current
  ```

---

## 📱 Backend Setup

- [ ] Python 3.11+ is installed
  ```bash
  python3 --version
  ```

- [ ] Virtual environment is created
  ```bash
  cd backend
  python3 -m venv .venv
  ```

- [ ] Dependencies are installed
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

- [ ] FFmpeg is installed
  ```bash
  ffmpeg -version
  ```

- [ ] Backend starts without errors
  ```bash
  uvicorn app.main:app --reload
  ```

- [ ] API docs are accessible
  - Open: http://localhost:8000/docs

- [ ] Health check passes
  ```bash
  curl http://localhost:8000/health
  ```

---

## 🎨 Frontend Setup

- [ ] Node.js 18+ is installed
  ```bash
  node --version
  ```

- [ ] Dependencies are installed
  ```bash
  cd frontend
  npm install
  ```

- [ ] Frontend builds successfully
  ```bash
  npm run build
  ```

- [ ] Frontend starts without errors
  ```bash
  npm run dev
  ```

- [ ] Frontend connects to backend
  - Open: http://localhost:3000
  - Check browser console for errors

---

## 🧪 Testing

- [ ] Run automated tests (if available)
  ```bash
  cd backend
  pytest
  ```

- [ ] Run API test script
  ```bash
  ./test_api.sh
  ```

- [ ] Test user registration
  - Create new account via web UI

- [ ] Test file upload transcription
  - Upload a small audio file (< 5 minutes)
  - Verify transcription completes
  - Check for errors in logs

- [ ] Test URL transcription (if using YouTube)
  - Paste a YouTube URL
  - Verify download and transcription works

- [ ] Test rate limiting
  - Make multiple API calls rapidly
  - Verify rate limiter activates
  - Check logs for rate limit messages

- [ ] Test speaker diarization (if enabled)
  - Upload audio with multiple speakers
  - Verify speakers are detected
  - Check diarization data in response

- [ ] Test summary generation
  - Enable "Generate Summary" option
  - Verify summary is created
  - Check quality of summary

- [ ] Test knowledge base query (if using)
  - Add transcription to knowledge base
  - Run a semantic search query
  - Verify relevant results returned

---

## 🐳 Docker Setup (Optional)

- [ ] Docker is installed
  ```bash
  docker --version
  ```

- [ ] Docker Compose is installed
  ```bash
  docker-compose --version
  ```

- [ ] `.dockerignore` files exist
  - `backend/.dockerignore`
  - `frontend/.dockerignore`

- [ ] Docker images build successfully
  ```bash
  docker-compose build
  ```

- [ ] Services start with Docker Compose
  ```bash
  docker-compose up -d
  ```

- [ ] All containers are running
  ```bash
  docker-compose ps
  ```

- [ ] Check container logs for errors
  ```bash
  docker-compose logs
  ```

---

## 📚 Documentation

- [ ] README.md is up to date
- [ ] DEPLOYMENT.md covers your deployment method
- [ ] .env.example has all required variables
- [ ] API documentation is accessible
- [ ] Team members have access to deployment docs

---

## 🔍 Code Quality

- [ ] No backup files in repository
  ```bash
  find . -name "*.backup" -o -name "*.bak"
  ```

- [ ] No TODO comments for critical issues
  ```bash
  grep -r "TODO" --include="*.py" --include="*.tsx"
  ```

- [ ] No console.log statements in production code (frontend)
  ```bash
  grep -r "console.log" frontend/src/
  ```

- [ ] No print statements in production code (backend)
  ```bash
  grep -r "print(" backend/app/ | grep -v "logger"
  ```

- [ ] All imports are used (no unused imports)

---

## 🚀 Deployment Preparation

### For Docker Deployment

- [ ] Production docker-compose file is configured
- [ ] Environment variables are set in deployment platform
- [ ] Persistent volumes are configured for database
- [ ] Health checks are configured
- [ ] Resource limits are set

### For Platform Deployment (Railway, Render, etc.)

- [ ] Platform account is created
- [ ] Database service is provisioned
- [ ] Redis service is provisioned (if needed)
- [ ] Environment variables are set in platform
- [ ] Build commands are configured
- [ ] Start commands are configured
- [ ] Health check endpoint is configured

### For Manual Server Deployment

- [ ] Server is provisioned (Ubuntu 20.04+ recommended)
- [ ] Domain name is configured (if using)
- [ ] SSL certificates are ready (Let's Encrypt recommended)
- [ ] Nginx or similar reverse proxy is configured
- [ ] Systemd services are created
- [ ] Firewall rules are configured
- [ ] Log rotation is set up

---

## 🔒 Production Security

- [ ] HTTPS/TLS is enabled
- [ ] CORS is properly configured
- [ ] File upload limits are set
- [ ] Rate limiting is enabled
- [ ] Error messages don't expose sensitive info
- [ ] Database backups are configured
- [ ] Monitoring/alerting is set up

---

## 📊 Monitoring Setup

- [ ] Error logging is configured
- [ ] Access logs are enabled
- [ ] Application metrics are tracked
- [ ] Disk space monitoring
- [ ] Database connection monitoring
- [ ] API usage tracking
- [ ] Rate limit statistics tracking

---

## 🔄 Post-Deployment

- [ ] Verify all services are running
- [ ] Test critical user flows
- [ ] Check error logs
- [ ] Monitor resource usage
- [ ] Set up backup schedule
- [ ] Document deployment process
- [ ] Create rollback plan

---

## 📞 Emergency Contacts

Document these for production issues:

- [ ] Who to contact for database issues: _______________
- [ ] Who to contact for API issues: _______________
- [ ] Who has access to production environment: _______________
- [ ] Escalation process documented: _______________

---

## 🎯 Final Checklist

Before going live:

- [ ] All API keys are rotated and secure
- [ ] Environment variables are set correctly
- [ ] Database migrations are applied
- [ ] All tests pass
- [ ] Documentation is complete
- [ ] Monitoring is set up
- [ ] Backup strategy is in place
- [ ] Rollback plan is ready
- [ ] Team is trained on deployment process
- [ ] Support channels are ready

---

## ✅ Ready for Production?

If ALL items above are checked, you're ready to deploy! 🚀

### Quick Start Command

Using setup script:
```bash
./setup.sh
```

Or manually:
```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (in another terminal)
cd frontend
npm run dev
```

Or with Docker:
```bash
docker-compose up -d
```

---

## 📖 Additional Resources

- [README.md](README.md) - Project overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - Recent changes
- API Docs: http://localhost:8000/docs

---

## 🆘 Need Help?

If you encounter issues:
1. Check DEPLOYMENT.md troubleshooting section
2. Review application logs
3. Verify environment variables
4. Test API endpoints with test_api.sh
5. Check database connectivity

---

**Remember**: Security first! Always rotate exposed API keys before deployment.
