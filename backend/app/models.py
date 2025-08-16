# backend/app/models.py
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ARRAY, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
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
    monthly_usage = Column(Integer, default=0)
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
    original_filename = Column(String(255))
    file_url = Column(String(500))
    file_type = Column(String(50))
    file_size = Column(Integer)  # in bytes
    duration_seconds = Column(Integer)
    
    # Content
    transcription_text = Column(Text)
    summary_text = Column(Text)
    
    # Processing
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    language = Column(String(10), default="auto")
    confidence_score = Column(Float)
    
    # Vector storage
    qdrant_point_ids = Column(ARRAY(String))
    qdrant_collection = Column(String(255))
    
    # Settings
    generate_summary = Column(Boolean, default=True)
    speaker_diarization = Column(Boolean, default=False)
    add_to_knowledge_base = Column(Boolean, default=True)
    
    # Metadata
    processing_time_seconds = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="transcriptions")

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