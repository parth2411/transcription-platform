# backend/app/config.py
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
    
    # App Settings
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
    "audio/wav", "audio/mp3", "audio/m4a", "audio/mpeg", 
    "video/mp4", "video/mov", "video/avi", "video/mkv",
    "audio/x-wav", "audio/x-m4a", "video/quicktime",
    "application/octet-stream"  # For files with unclear MIME types
    ]
    
    # Subscription Limits
    FREE_TIER_LIMIT: int = 5  # transcriptions per month
    PRO_TIER_LIMIT: int = 100
    BUSINESS_TIER_LIMIT: int = -1  # unlimited
    
    class Config:
        env_file = ".env"

settings = Settings()