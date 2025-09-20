-- Add new columns to existing transcriptions table
ALTER TABLE transcriptions 
ADD COLUMN IF NOT EXISTS source_language VARCHAR(10),
ADD COLUMN IF NOT EXISTS target_language VARCHAR(10),
ADD COLUMN IF NOT EXISTS is_translated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
ADD COLUMN IF NOT EXISTS speaker_count INTEGER,
ADD COLUMN IF NOT EXISTS diarization_method VARCHAR(50),
ADD COLUMN IF NOT EXISTS real_time_chunks JSON,
ADD COLUMN IF NOT EXISTS audio_quality_score FLOAT,
ADD COLUMN IF NOT EXISTS processing_metadata JSON;

-- Add new columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS preferred_source_language VARCHAR(10) DEFAULT 'auto',
ADD COLUMN IF NOT EXISTS auto_translate_to_english BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS enable_speaker_diarization BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS default_add_to_knowledge BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transcriptions_source_language ON transcriptions(source_language);
CREATE INDEX IF NOT EXISTS idx_transcriptions_is_translated ON transcriptions(is_translated);
CREATE INDEX IF NOT EXISTS idx_transcriptions_speaker_count ON transcriptions(speaker_count);

-- Create new tables
CREATE TABLE IF NOT EXISTS realtime_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    accumulated_text TEXT,
    chunk_count INTEGER DEFAULT 0,
    source_language VARCHAR(10) DEFAULT 'auto',
    translate_to_english BOOLEAN DEFAULT FALSE,
    speaker_diarization_enabled BOOLEAN DEFAULT FALSE,
    session_metadata JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS language_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10),
    usage_count INTEGER DEFAULT 1,
    total_duration_seconds INTEGER DEFAULT 0,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_realtime_sessions_user_id ON realtime_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_realtime_sessions_session_token ON realtime_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_language_usage_user_source ON language_usage_stats(user_id, source_language);