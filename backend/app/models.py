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

class Folder(Base):
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    color = Column(String(7), default="#3B82F6")
    icon = Column(String(50), default="folder")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#6B7280")
    created_at = Column(DateTime, default=datetime.utcnow)

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

    # Organization
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    is_favorite = Column(Boolean, default=False)

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

# ========================================
# NEW MODELS FOR GRANOLA-LIKE FEATURES
# ========================================

class CalendarConnection(Base):
    """Stores user's calendar OAuth connections (Google, Microsoft, Apple)"""
    __tablename__ = "calendar_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # google, microsoft, apple
    calendar_id = Column(String(255), nullable=False)  # External calendar ID
    calendar_name = Column(String(255))

    # OAuth tokens (encrypted in production)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)

    # Settings
    is_active = Column(Boolean, default=True)
    sync_enabled = Column(Boolean, default=True)
    auto_record_meetings = Column(Boolean, default=False)
    default_template_id = Column(UUID(as_uuid=True), ForeignKey("meeting_templates.id", ondelete="SET NULL"), nullable=True)

    # Sync metadata
    last_synced_at = Column(DateTime)
    sync_token = Column(Text)  # For incremental sync

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meetings = relationship("Meeting", back_populates="calendar_connection", cascade="all, delete-orphan")

class MeetingTemplate(Base):
    """Pre-defined and custom meeting templates (1-on-1s, Customer Discovery, etc.)"""
    __tablename__ = "meeting_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL for system templates
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Template type
    is_system_template = Column(Boolean, default=False)  # Pre-defined templates
    is_public = Column(Boolean, default=False)  # Share with team

    # Structure (JSON): sections, fields, prompts
    # Example: {"sections": ["Agenda", "Discussion", "Action Items", "Decisions"]}
    structure = Column(Text)  # JSON string

    # AI prompt customization
    summary_prompt = Column(Text)  # Custom prompt for summary generation
    auto_extract_action_items = Column(Boolean, default=True)
    auto_extract_decisions = Column(Boolean, default=True)

    # Icon and color
    icon = Column(String(50), default="document")
    color = Column(String(7), default="#3B82F6")

    # Usage stats
    usage_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Meeting(Base):
    """Represents a calendar meeting/event with transcription capabilities"""
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    calendar_connection_id = Column(UUID(as_uuid=True), ForeignKey("calendar_connections.id", ondelete="SET NULL"), nullable=True)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="SET NULL"), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("meeting_templates.id", ondelete="SET NULL"), nullable=True)

    # Meeting details
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # External IDs
    calendar_event_id = Column(String(255))  # Google/Microsoft event ID

    # Time
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    timezone = Column(String(50), default="UTC")
    actual_start_time = Column(DateTime)  # When recording actually started
    actual_end_time = Column(DateTime)  # When recording actually ended

    # Meeting platform
    meeting_url = Column(Text)  # Zoom, Google Meet, Teams link
    platform = Column(String(50))  # zoom, google_meet, teams, slack, phone, in_person

    # Participants (JSON array of objects: [{email, name, role}])
    participants = Column(Text)  # JSON string
    organizer_email = Column(String(255))

    # Status
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    recording_status = Column(String(50), default="not_started")  # not_started, recording, processing, completed, failed

    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(Text)  # JSON: {frequency, interval, until}
    parent_meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)

    # Content summary
    summary = Column(Text)  # AI-generated summary
    key_points = Column(Text)  # JSON array of key discussion points

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calendar_connection = relationship("CalendarConnection", back_populates="meetings")
    notes = relationship("MeetingNote", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")

class MeetingNote(Base):
    """Hybrid notes: manual (user-typed) + AI-generated (transcription)"""
    __tablename__ = "meeting_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    content = Column(Text, nullable=False)
    note_type = Column(String(20), nullable=False)  # manual, ai, hybrid
    section = Column(String(100))  # agenda, discussion, action_items, decisions, notes

    # Timing
    timestamp_in_meeting = Column(Integer)  # Seconds from meeting start
    speaker = Column(String(255))  # For AI notes: who was speaking

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="notes")

class ActionItem(Base):
    """Action items extracted from meetings or manually created"""
    __tablename__ = "action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Details
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Assignment
    assigned_to_email = Column(String(255))
    assigned_to_name = Column(String(255))

    # Priority and deadline
    priority = Column(String(20), default="medium")  # low, medium, high
    due_date = Column(DateTime)

    # Status
    status = Column(String(50), default="pending")  # pending, in_progress, completed, cancelled
    completed_at = Column(DateTime)

    # Origin
    created_from_ai = Column(Boolean, default=False)
    related_transcript_chunk = Column(Text)  # Context from transcript

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")

class TranscriptionTag(Base):
    """Junction table for many-to-many relationship between transcriptions and tags"""
    __tablename__ = "transcription_tags"

    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Integration(Base):
    """Third-party integrations (Slack, webhooks, etc.)"""
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Integration type
    provider = Column(String(50), nullable=False)  # slack, webhook, zapier, notion
    name = Column(String(255), nullable=False)

    # OAuth/API credentials (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    webhook_url = Column(Text)

    # Configuration (JSON)
    # Example: {"channel": "#meetings", "auto_post": true, "include_action_items": true}
    config = Column(Text)  # JSON string

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)