-- Migration: Initial Schema for Supabase with pgvector
-- Date: 2025-10-30
-- Description: Creates all tables with pgvector support, replacing Qdrant

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    subscription_tier VARCHAR(50) DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'business')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    monthly_transcription_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================
-- TRANSCRIPTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- File metadata
    filename VARCHAR(255),
    file_url TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    duration_seconds INTEGER,

    -- Transcription content
    transcription_text TEXT,
    summary_text TEXT,
    language VARCHAR(10) DEFAULT 'auto',

    -- Vector embedding (replaces Qdrant)
    embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2

    -- Speaker diarization
    diarization_data TEXT,  -- JSON string
    speaker_count INTEGER DEFAULT 0,

    -- Processing info
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    confidence_score FLOAT,
    processing_time_seconds FLOAT,
    error_message TEXT,

    -- Configuration
    generate_summary BOOLEAN DEFAULT false,
    speaker_diarization BOOLEAN DEFAULT false,
    add_to_knowledge_base BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at DESC);

-- HNSW index for fast vector similarity search
-- This replaces Qdrant's vector indexing
CREATE INDEX IF NOT EXISTS idx_transcriptions_embedding
ON transcriptions
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_transcriptions_embedding IS 'HNSW index for fast cosine similarity search on transcription embeddings';

-- ============================================
-- TRANSCRIPTION CHUNKS TABLE
-- ============================================
-- For long transcriptions, split into chunks
CREATE TABLE IF NOT EXISTS transcription_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(384),  -- Vector embedding for this chunk
    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique chunks per transcription
    UNIQUE(transcription_id, chunk_index)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_transcription_id ON transcription_chunks(transcription_id);

-- HNSW index for chunk-level vector search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON transcription_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON TABLE transcription_chunks IS 'Stores text chunks with embeddings for long transcriptions, enabling granular semantic search';

-- ============================================
-- KNOWLEDGE QUERIES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    transcription_ids UUID[],  -- Array of source transcription IDs
    confidence_score FLOAT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON knowledge_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON knowledge_queries(created_at DESC);

-- ============================================
-- API KEYS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- ============================================
-- USER USAGE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    transcriptions_count INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    total_file_size_bytes BIGINT DEFAULT 0,
    api_calls_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique tracking per user per month
    UNIQUE(user_id, year, month)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_usage_user_id ON user_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_year_month ON user_usage(year, month);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transcriptions_updated_at BEFORE UPDATE ON transcriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_usage_updated_at BEFORE UPDATE ON user_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VECTOR SEARCH HELPER FUNCTIONS
-- ============================================

-- Function to search transcriptions by similarity
CREATE OR REPLACE FUNCTION search_transcriptions(
    query_embedding vector(384),
    user_uuid UUID,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    transcription_id UUID,
    text TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id AS transcription_id,
        t.transcription_text AS text,
        1 - (t.embedding <=> query_embedding) AS similarity
    FROM transcriptions t
    WHERE t.user_id = user_uuid
      AND t.embedding IS NOT NULL
      AND 1 - (t.embedding <=> query_embedding) > match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_transcriptions IS 'Semantic search across full transcriptions using cosine similarity';

-- Function to search transcription chunks by similarity
CREATE OR REPLACE FUNCTION search_transcription_chunks(
    query_embedding vector(384),
    user_uuid UUID,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    transcription_id UUID,
    chunk_index INT,
    text TEXT,
    similarity FLOAT,
    title VARCHAR,
    filename VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tc.id AS chunk_id,
        tc.transcription_id,
        tc.chunk_index,
        tc.text,
        1 - (tc.embedding <=> query_embedding) AS similarity,
        t.filename AS title,
        t.filename
    FROM transcription_chunks tc
    JOIN transcriptions t ON t.id = tc.transcription_id
    WHERE t.user_id = user_uuid
      AND tc.embedding IS NOT NULL
      AND 1 - (tc.embedding <=> query_embedding) > match_threshold
    ORDER BY tc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_transcription_chunks IS 'Semantic search across transcription chunks for granular results';

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
-- Note: We'll use service_role key in backend, so RLS is optional
-- But we set it up for future frontend integration

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcription_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;

-- Policies for users table
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- Policies for transcriptions table
CREATE POLICY "Users can view own transcriptions"
    ON transcriptions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own transcriptions"
    ON transcriptions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own transcriptions"
    ON transcriptions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own transcriptions"
    ON transcriptions FOR DELETE
    USING (auth.uid() = user_id);

-- Policies for transcription_chunks table
CREATE POLICY "Users can view own chunks"
    ON transcription_chunks FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM transcriptions
            WHERE transcriptions.id = transcription_chunks.transcription_id
            AND transcriptions.user_id = auth.uid()
        )
    );

-- Policies for knowledge_queries table
CREATE POLICY "Users can view own queries"
    ON knowledge_queries FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own queries"
    ON knowledge_queries FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policies for api_keys table
CREATE POLICY "Users can manage own API keys"
    ON api_keys FOR ALL
    USING (auth.uid() = user_id);

-- Policies for user_usage table
CREATE POLICY "Users can view own usage"
    ON user_usage FOR SELECT
    USING (auth.uid() = user_id);

-- ============================================
-- INITIAL DATA (Optional)
-- ============================================

-- You can add a test user here if needed
-- INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier)
-- VALUES ('test@example.com', 'hashed_password', 'Test', 'User', 'free');

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

-- Grant necessary permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant permissions to service role (for backend)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ============================================
-- COMPLETION
-- ============================================

-- Verify vector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test vector operations
SELECT '[1,2,3]'::vector(3);
SELECT '[1,2,3]'::vector(3) <=> '[4,5,6]'::vector(3) AS cosine_distance;

COMMENT ON DATABASE postgres IS 'Transcription Platform Database with pgvector support';

-- Migration completed successfully
