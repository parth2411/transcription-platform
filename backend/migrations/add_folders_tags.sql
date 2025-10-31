-- Add folders and tags tables for better organization

-- Folders table
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(7) DEFAULT '#3B82F6',
    icon VARCHAR(50) DEFAULT 'folder',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_tags_user_id ON tags(user_id);

-- Transcription-Tags many-to-many relationship
CREATE TABLE IF NOT EXISTS transcription_tags (
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (transcription_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_transcription_tags_transcription ON transcription_tags(transcription_id);
CREATE INDEX IF NOT EXISTS idx_transcription_tags_tag ON transcription_tags(tag_id);

-- Add folder_id to transcriptions table
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES folders(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_transcriptions_folder_id ON transcriptions(folder_id);

-- Add favorites flag
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_transcriptions_is_favorite ON transcriptions(is_favorite);

COMMENT ON TABLE folders IS 'User-created folders for organizing transcriptions';
COMMENT ON TABLE tags IS 'User-created tags for categorizing transcriptions';
COMMENT ON TABLE transcription_tags IS 'Many-to-many relationship between transcriptions and tags';
