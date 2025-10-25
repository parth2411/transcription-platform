# backend/app/config.py - Enhanced for Large Video Support
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/transcription_db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External APIs
    GROQ_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    
    # File Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    
    # Redis (for background tasks)
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://your-frontend-domain.com"
    ]
    
    # Enhanced App Settings for Large Videos
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB for uploads
    MAX_VIDEO_DURATION_MINUTES: int = 120    # 2 hours max
    CHUNK_SIZE_MINUTES: int = 8              # Process in 8-minute chunks
    GROQ_MAX_FILE_SIZE: int = 24 * 1024 * 1024  # 24MB (under Groq's 25MB limit)
    
    # Timeout Settings
    DOWNLOAD_TIMEOUT_SECONDS: int = 600      # 10 minutes for download
    PROCESSING_TIMEOUT_SECONDS: int = 300    # 5 minutes per chunk
    TRANSCRIPTION_TIMEOUT_SECONDS: int = 1800 # 30 minutes total
    
    ALLOWED_FILE_TYPES: List[str] = [
        "audio/wav", "audio/mp3", "audio/m4a", "audio/mpeg", 
        "video/mp4", "video/mov", "video/avi", "video/mkv",
        "audio/x-wav", "audio/x-m4a", "video/quicktime",
        "application/octet-stream"
    ]
    
    # Video Quality Settings
    AUDIO_QUALITY: str = "5"        # Medium quality (0=best, 9=worst)
    AUDIO_FORMAT: str = "mp3"       # Use MP3 for better compression
    SAMPLE_RATE: int = 16000        # 16kHz for speech (lower than 44.1kHz)
    AUDIO_CHANNELS: int = 1         # Mono for smaller files
    
    # Enhanced Subscription Limits
    FREE_TIER_LIMIT: int = 5                    # transcriptions per month
    FREE_TIER_DURATION_LIMIT: int = 10         # 10 minutes max per video
    PRO_TIER_LIMIT: int = 100                  # transcriptions per month
    PRO_TIER_DURATION_LIMIT: int = 60          # 60 minutes max per video
    BUSINESS_TIER_LIMIT: int = -1              # unlimited
    BUSINESS_TIER_DURATION_LIMIT: int = 120    # 120 minutes max per video

    # Rate Limiting for Groq API (Free Tier Protection)
    GROQ_RATE_LIMIT_RPM: int = 25              # Requests per minute (Groq free: 30, we use 25 for safety)
    GROQ_RATE_LIMIT_RPD: int = 10000           # Requests per day (Groq free: 14,400, we use 10k for safety)
    GROQ_RATE_LIMIT_ENABLED: bool = True       # Enable/disable rate limiting

    # Speaker Diarization Settings
    HUGGINGFACE_TOKEN: str = ""                # Required for pyannote.audio
    DIARIZATION_ENABLED: bool = False          # Enable/disable speaker diarization
    MIN_SPEAKERS: int = 1                      # Minimum number of speakers
    MAX_SPEAKERS: int = 10                     # Maximum number of speakers

    class Config:
        env_file = ".env"

settings = Settings()