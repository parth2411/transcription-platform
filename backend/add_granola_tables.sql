-- Add Granola Features Tables
-- Run this SQL script directly on your database

-- meeting_templates table
CREATE TABLE IF NOT EXISTS meeting_templates (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_system_template BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT FALSE,
    structure TEXT,
    summary_prompt TEXT,
    auto_extract_action_items BOOLEAN DEFAULT TRUE,
    auto_extract_decisions BOOLEAN DEFAULT TRUE,
    icon VARCHAR(50) DEFAULT 'document',
    color VARCHAR(7) DEFAULT '#3B82F6',
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- calendar_connections table
CREATE TABLE IF NOT EXISTS calendar_connections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    calendar_id VARCHAR(255) NOT NULL,
    calendar_name VARCHAR(255),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    sync_enabled BOOLEAN DEFAULT TRUE,
    auto_record_meetings BOOLEAN DEFAULT FALSE,
    default_template_id UUID REFERENCES meeting_templates(id) ON DELETE SET NULL,
    last_synced_at TIMESTAMP,
    sync_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    calendar_connection_id UUID REFERENCES calendar_connections(id) ON DELETE SET NULL,
    transcription_id UUID REFERENCES transcriptions(id) ON DELETE SET NULL,
    template_id UUID REFERENCES meeting_templates(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    calendar_event_id VARCHAR(255),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    actual_start_time TIMESTAMP,
    actual_end_time TIMESTAMP,
    meeting_url TEXT,
    platform VARCHAR(50),
    participants TEXT,
    organizer_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'scheduled',
    recording_status VARCHAR(50) DEFAULT 'not_started',
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern TEXT,
    parent_meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
    summary TEXT,
    key_points TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- meeting_notes table
CREATE TABLE IF NOT EXISTS meeting_notes (
    id UUID PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    note_type VARCHAR(20) NOT NULL,
    section VARCHAR(100),
    timestamp_in_meeting INTEGER,
    speaker VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- action_items table
CREATE TABLE IF NOT EXISTS action_items (
    id UUID PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    assigned_to_email VARCHAR(255),
    assigned_to_name VARCHAR(255),
    priority VARCHAR(20) DEFAULT 'medium',
    due_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    completed_at TIMESTAMP,
    created_from_ai BOOLEAN DEFAULT FALSE,
    related_transcript_chunk TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- integrations table
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    webhook_url TEXT,
    config TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS ix_calendar_connections_user_id ON calendar_connections(user_id);
CREATE INDEX IF NOT EXISTS ix_meetings_user_id ON meetings(user_id);
CREATE INDEX IF NOT EXISTS ix_meetings_start_time ON meetings(start_time);
CREATE INDEX IF NOT EXISTS ix_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS ix_meetings_calendar_event_id ON meetings(calendar_event_id);
CREATE INDEX IF NOT EXISTS ix_meeting_notes_meeting_id ON meeting_notes(meeting_id);
CREATE INDEX IF NOT EXISTS ix_action_items_meeting_id ON action_items(meeting_id);
CREATE INDEX IF NOT EXISTS ix_action_items_user_id ON action_items(user_id);
CREATE INDEX IF NOT EXISTS ix_action_items_status ON action_items(status);
CREATE INDEX IF NOT EXISTS ix_action_items_assigned_to_email ON action_items(assigned_to_email);

-- Mark migration as complete
INSERT INTO alembic_version (version_num) VALUES ('003_add_granola_features')
ON CONFLICT (version_num) DO NOTHING;
