#!/bin/bash

# Transcription Platform - Quick Setup Script
# This script helps you get started quickly with the transcription platform

set -e

echo "=================================================="
echo "  Transcription Platform - Quick Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing .env file"
    else
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created new .env file from template"
    fi
else
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env file from template"
fi

echo ""
echo "=================================================="
echo "  Step 1: Environment Configuration"
echo "=================================================="
echo ""

# Generate SECRET_KEY
echo "Generating secure SECRET_KEY..."
SECRET_KEY=$(openssl rand -hex 32)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/your-super-secret-key-change-in-production-at-least-32-characters-long/${SECRET_KEY}/" .env
else
    sed -i "s/your-super-secret-key-change-in-production-at-least-32-characters-long/${SECRET_KEY}/" .env
fi
echo -e "${GREEN}✓${NC} Generated SECRET_KEY"

echo ""
echo -e "${YELLOW}Important: You need to add your API keys to .env:${NC}"
echo "  - GROQ_API_KEY (required) - Get from: https://console.groq.com/keys"
echo "  - QDRANT_URL (required) - Get from: https://cloud.qdrant.io"
echo "  - QDRANT_API_KEY (required)"
echo "  - HUGGINGFACE_TOKEN (optional, for diarization)"
echo ""

read -p "Press Enter to edit .env file now, or Ctrl+C to exit..."
${EDITOR:-nano} .env

echo ""
echo "=================================================="
echo "  Step 2: Choose Setup Method"
echo "=================================================="
echo ""
echo "How would you like to run the platform?"
echo "  1) Docker Compose (recommended, easiest)"
echo "  2) Manual setup (requires Python 3.11+, Node.js 18+)"
echo ""
read -p "Enter choice (1 or 2): " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    echo ""
    echo "Setting up with Docker Compose..."
    echo ""

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗${NC} Docker is not installed"
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗${NC} Docker Compose is not installed"
        echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Docker and Docker Compose are installed"
    echo ""
    echo "Building and starting containers..."
    docker-compose up -d

    echo ""
    echo -e "${GREEN}=================================================="
    echo "  ✓ Setup Complete!"
    echo "==================================================${NC}"
    echo ""
    echo "Services are starting up. Please wait ~30 seconds, then access:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "To stop services:"
    echo "  docker-compose down"
    echo ""

elif [[ $REPLY == "2" ]]; then
    echo ""
    echo "Setting up manually..."
    echo ""

    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} found"
    else
        echo -e "${RED}✗${NC} Python 3 not found"
        echo "Please install Python 3.11+ from: https://www.python.org/downloads/"
        exit 1
    fi

    # Check Node.js version
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓${NC} Node.js ${NODE_VERSION} found"
    else
        echo -e "${RED}✗${NC} Node.js not found"
        echo "Please install Node.js 18+ from: https://nodejs.org/"
        exit 1
    fi

    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN}✓${NC} FFmpeg found"
    else
        echo -e "${YELLOW}!${NC} FFmpeg not found"
        echo "Install FFmpeg:"
        echo "  - Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "  - macOS: brew install ffmpeg"
        echo "  - Windows: https://ffmpeg.org/download.html"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Setup backend
    echo ""
    echo "Setting up backend..."
    cd backend

    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi

    echo "Activating virtual environment..."
    source .venv/bin/activate

    echo "Installing Python dependencies..."
    pip install -r requirements.txt

    echo ""
    echo "Setting up database..."
    read -p "Do you have PostgreSQL installed and a database created? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Running database migrations..."
        alembic upgrade head
        echo -e "${GREEN}✓${NC} Database migrations complete"
    else
        echo -e "${YELLOW}!${NC} Please set up PostgreSQL and run: alembic upgrade head"
    fi

    cd ..

    # Setup frontend
    echo ""
    echo "Setting up frontend..."
    cd frontend

    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies (this may take a few minutes)..."
        npm install
    else
        echo -e "${GREEN}✓${NC} Node modules already installed"
    fi

    cd ..

    echo ""
    echo -e "${GREEN}=================================================="
    echo "  ✓ Setup Complete!"
    echo "==================================================${NC}"
    echo ""
    echo "To start the backend:"
    echo "  cd backend"
    echo "  source .venv/bin/activate"
    echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "To start the frontend (in another terminal):"
    echo "  cd frontend"
    echo "  npm run dev"
    echo ""
    echo "Then access:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo ""

else
    echo "Invalid choice. Exiting."
    exit 1
fi

echo "=================================================="
echo "  Next Steps"
echo "=================================================="
echo ""
echo "1. Register a new user account"
echo "2. Upload an audio/video file or paste a URL"
echo "3. Enable speaker diarization if needed"
echo "4. Generate AI summaries"
echo "5. Query your knowledge base"
echo ""
echo "For help and documentation:"
echo "  - README.md - Quick overview"
echo "  - DEPLOYMENT.md - Comprehensive deployment guide"
echo "  - API Docs - http://localhost:8000/docs"
echo ""
echo "Need help? Check the documentation or open an issue on GitHub."
echo ""
