# backend/app/models.py
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ARRAY, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    subscription_tier = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    monthly_transcription_count = Column(Integer, default=0)  # Updated to match Supabase schema
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transcriptions = relationship("Transcription", back_populates="user", cascade="all, delete-orphan")
    knowledge_queries = relationship("KnowledgeQuery", back_populates="user", cascade="all, delete-orphan")

class Transcription(Base):
    __tablename__ = "transcriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    original_filename = Column("filename", String(255))  # Maps to 'filename' column in Supabase
    file_url = Column(Text)  # Changed to Text to match Supabase
    file_type = Column(String(50))
    file_size = Column(Integer)  # in bytes
    duration_seconds = Column(Integer)
    
    # Content
    transcription_text = Column(Text)
    summary_text = Column(Text)
    diarization_data = Column(Text)  # JSON string with speaker segments
    speaker_count = Column(Integer)  # Number of detected speakers

    # Processing
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    language = Column(String(10), default="auto")
    confidence_score = Column(Float)
    
    # Vector storage (pgvector - replaces Qdrant)
    embedding = Column(Vector(384), nullable=True)
    
    # Settings
    generate_summary = Column(Boolean, default=True)
    speaker_diarization = Column(Boolean, default=False)
    add_to_knowledge_base = Column(Boolean, default=True)
    
    # Metadata
    processing_time_seconds = Column(Float)  # Changed to Float to match Supabase DOUBLE PRECISION
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="transcriptions")
    chunks = relationship("TranscriptionChunk", back_populates="transcription", cascade="all, delete-orphan")

class TranscriptionChunk(Base):
    """
    Stores text chunks with embeddings for long transcriptions.
    Enables granular semantic search across transcription segments.
    """
    __tablename__ = "transcription_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transcription = relationship("Transcription", back_populates="chunks")

class KnowledgeQuery(Base):
    __tablename__ = "knowledge_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    transcription_ids = Column(ARRAY(UUID))  # Source transcriptions
    confidence_score = Column(Float)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="knowledge_queries")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class UserUsage(Base):
    __tablename__ = "user_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    transcriptions_count = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    total_file_size_bytes = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)