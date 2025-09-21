from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum

Base = declarative_base()

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"

class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    subscription_tier = Column(String(20), default=SubscriptionTier.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    monthly_usage = Column(Integer, default=0, nullable=False)
    
    # Enhanced user preferences
    preferred_source_language = Column(String(10), default="auto", nullable=False)
    auto_translate_to_english = Column(Boolean, default=False, nullable=False)
    enable_speaker_diarization = Column(Boolean, default=False, nullable=False)
    default_add_to_knowledge = Column(Boolean, default=True, nullable=False)
    
    # Payment integration
    stripe_customer_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    transcriptions = relationship("Transcription", back_populates="user")
    realtime_sessions = relationship("RealtimeSession", back_populates="user")
    language_usage_stats = relationship("LanguageUsageStats", back_populates="user")

class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Enhanced language support
    language = Column(String(10), default="auto", nullable=False)  # Original field
    source_language = Column(String(10), nullable=True)  # Detected source language
    target_language = Column(String(10), nullable=True)  # Translation target
    is_translated = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Float, nullable=True)
    
    # Content fields
    transcription_text = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    
    # Processing options
    generate_summary = Column(Boolean, default=True, nullable=False)
    speaker_diarization = Column(Boolean, default=False, nullable=False)
    add_to_knowledge_base = Column(Boolean, default=True, nullable=False)
    
    # Enhanced speaker diarization
    speaker_count = Column(Integer, nullable=True)
    diarization_method = Column(String(50), nullable=True)
    
    # Processing metadata
    status = Column(String(20), default=TranscriptionStatus.PENDING, nullable=False)
    processing_time_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Real-time processing data
    real_time_chunks = Column(JSON, nullable=True)
    audio_quality_score = Column(Float, nullable=True)
    processing_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="transcriptions")

    def to_dict(self):
        """Convert transcription to dictionary for API responses"""
        return {
            'id': str(self.id),
            'title': self.title,
            'status': self.status,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'duration_seconds': self.duration_seconds,
            'transcription_text': self.transcription_text,
            'summary_text': self.summary_text,
            'source_language': self.source_language or self.language,
            'target_language': self.target_language,
            'is_translated': self.is_translated,
            'confidence_score': self.confidence_score,
            'speaker_count': self.speaker_count,
            'diarization_method': self.diarization_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processing_time_seconds': self.processing_time_seconds,
            'error_message': self.error_message
        }

class RealtimeSession(Base):
    __tablename__ = "realtime_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    
    # Session timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Accumulated content
    accumulated_text = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    
    # Language settings
    source_language = Column(String(10), default="auto", nullable=False)
    translate_to_english = Column(Boolean, default=False, nullable=False)
    speaker_diarization_enabled = Column(Boolean, default=False, nullable=False)
    
    # Session metadata
    session_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="realtime_sessions")

class LanguageUsageStats(Base):
    __tablename__ = "language_usage_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=True)
    usage_count = Column(Integer, default=1, nullable=False)
    total_duration_seconds = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="language_usage_stats")

# Enhanced Query class for knowledge base (if you have queries table)
class Query(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    source_count = Column(Integer, nullable=True)
    
    # Enhanced query features
    query_language = Column(String(10), default="en", nullable=False)
    auto_translated = Column(Boolean, default=False, nullable=False)
    query_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# # backend/app/models.py
# from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ARRAY, Float, ForeignKey
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# from sqlalchemy.ext.declarative import declarative_base
# import uuid
# from datetime import datetime

# Base = declarative_base()

# class User(Base):
#     __tablename__ = "users"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email = Column(String(255), unique=True, nullable=False, index=True)
#     password_hash = Column(String(255), nullable=False)
#     first_name = Column(String(100))
#     last_name = Column(String(100))
#     subscription_tier = Column(String(50), default="free")
#     is_active = Column(Boolean, default=True)
#     is_verified = Column(Boolean, default=False)
#     monthly_usage = Column(Integer, default=0)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
#     # Relationships
#     transcriptions = relationship("Transcription", back_populates="user", cascade="all, delete-orphan")
#     knowledge_queries = relationship("KnowledgeQuery", back_populates="user", cascade="all, delete-orphan")

# class Transcription(Base):
#     __tablename__ = "transcriptions"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     title = Column(String(255), nullable=False)
#     original_filename = Column(String(255))
#     file_url = Column(String(500))
#     file_type = Column(String(50))
#     file_size = Column(Integer)  # in bytes
#     duration_seconds = Column(Integer)
    
#     # Content
#     transcription_text = Column(Text)
#     summary_text = Column(Text)
    
#     # Processing
#     status = Column(String(50), default="pending")  # pending, processing, completed, failed
#     language = Column(String(10), default="auto")
#     confidence_score = Column(Float)
    
#     # Vector storage
#     qdrant_point_ids = Column(ARRAY(String))
#     qdrant_collection = Column(String(255))
    
#     # Settings
#     generate_summary = Column(Boolean, default=True)
#     speaker_diarization = Column(Boolean, default=False)
#     add_to_knowledge_base = Column(Boolean, default=True)
    
#     # Metadata
#     processing_time_seconds = Column(Integer)
#     error_message = Column(Text)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
#     completed_at = Column(DateTime)
    
#     # Relationships
#     user = relationship("User", back_populates="transcriptions")

# class KnowledgeQuery(Base):
#     __tablename__ = "knowledge_queries"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     query_text = Column(Text, nullable=False)
#     response_text = Column(Text)
#     transcription_ids = Column(ARRAY(UUID))  # Source transcriptions
#     confidence_score = Column(Float)
#     response_time_ms = Column(Integer)
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     # Relationships
#     user = relationship("User", back_populates="knowledge_queries")

# class APIKey(Base):
#     __tablename__ = "api_keys"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     name = Column(String(255), nullable=False)
#     key_hash = Column(String(255), nullable=False, unique=True)
#     is_active = Column(Boolean, default=True)
#     last_used = Column(DateTime)
#     usage_count = Column(Integer, default=0)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     expires_at = Column(DateTime)

# class UserUsage(Base):
#     __tablename__ = "user_usage"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     year = Column(Integer, nullable=False)
#     month = Column(Integer, nullable=False)
#     transcriptions_count = Column(Integer, default=0)
#     total_duration_seconds = Column(Integer, default=0)
#     total_file_size_bytes = Column(Integer, default=0)
#     api_calls_count = Column(Integer, default=0)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)