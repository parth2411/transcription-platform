# Migration Plan: PostgreSQL + Qdrant → Supabase + pgvector

## Overview

This document outlines the complete migration from your current setup (PostgreSQL + Qdrant) to Supabase with pgvector.

**Migration Timeline:** 2-3 hours (for experienced developer)

---

## Table of Contents

1. [Pre-Migration Checklist](#pre-migration-checklist)
2. [Phase 1: Backup Current Data](#phase-1-backup-current-data)
3. [Phase 2: Schema Migration](#phase-2-schema-migration)
4. [Phase 3: Data Migration](#phase-3-data-migration)
5. [Phase 4: Backend Code Updates](#phase-4-backend-code-updates)
6. [Phase 5: Testing](#phase-5-testing)
7. [Phase 6: Deployment](#phase-6-deployment)
8. [Phase 7: Cleanup](#phase-7-cleanup)
9. [Rollback Plan](#rollback-plan)

---

## Pre-Migration Checklist

Before starting migration:

- [ ] Supabase account created and configured (see [SUPABASE_SETUP.md](SUPABASE_SETUP.md))
- [ ] `vector` extension enabled in Supabase
- [ ] Current database backed up
- [ ] All environment variables documented
- [ ] Development environment ready for testing
- [ ] No active users (or plan for zero-downtime migration)
- [ ] Estimated data size calculated

### Check Current Data Size

```bash
# Connect to your current PostgreSQL
psql $DATABASE_URL

# Run these queries
SELECT pg_size_pretty(pg_database_size('transcription_db'));
SELECT count(*) FROM users;
SELECT count(*) FROM transcriptions;
SELECT count(*) FROM knowledge_queries;
```

---

## Phase 1: Backup Current Data

### 1.1 Backup PostgreSQL Database

```bash
# Backup current PostgreSQL database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql

# Optional: Compress backup
gzip backup_*.sql
```

### 1.2 Export Qdrant Collections

Create a backup script for Qdrant data:

```bash
cd backend
source .venv/bin/activate
python scripts/export_qdrant_data.py
```

We'll create this script next.

---

## Phase 2: Schema Migration

### 2.1 Create New Schema in Supabase

You have two options:

#### Option A: Use SQL Editor in Supabase Dashboard

1. Go to Supabase Dashboard → SQL Editor
2. Create new query
3. Copy the SQL from `migrations/supabase_schema.sql` (we'll create this)
4. Run the query

#### Option B: Use Supabase CLI (Recommended)

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref xxxxxxxxxxxxx

# Run migration
supabase db push
```

### 2.2 Schema Changes from Current Setup

**Key differences:**

1. **Add vector column to transcriptions table**
   ```sql
   ALTER TABLE transcriptions
   ADD COLUMN embedding vector(384);
   ```

2. **Remove Qdrant-specific columns**
   ```sql
   ALTER TABLE transcriptions
   DROP COLUMN qdrant_point_ids,
   DROP COLUMN qdrant_collection;
   ```

3. **Add vector index for fast similarity search**
   ```sql
   CREATE INDEX transcriptions_embedding_idx
   ON transcriptions
   USING hnsw (embedding vector_cosine_ops);
   ```

4. **Create chunks table for long transcriptions**
   ```sql
   CREATE TABLE transcription_chunks (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     transcription_id UUID REFERENCES transcriptions(id) ON DELETE CASCADE,
     chunk_index INT NOT NULL,
     text TEXT NOT NULL,
     embedding vector(384),
     created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE INDEX transcription_chunks_embedding_idx
   ON transcription_chunks
   USING hnsw (embedding vector_cosine_ops);
   ```

---

## Phase 3: Data Migration

### 3.1 Export Existing Qdrant Vectors

Create script to export vectors from Qdrant:

**File:** `backend/scripts/export_qdrant_data.py`

```python
import os
import json
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Connect to Qdrant
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

# Connect to PostgreSQL
engine = create_engine(os.getenv("DATABASE_URL"))

# Export data
export_data = []

with engine.connect() as conn:
    # Get all users
    users = conn.execute(text("SELECT id FROM users")).fetchall()

    for user in users:
        user_id = str(user[0])
        collection_name = f"user_{user_id}_transcriptions"

        try:
            # Get all points from Qdrant
            points, _ = qdrant.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=True
            )

            for point in points:
                export_data.append({
                    "point_id": str(point.id),
                    "transcription_id": point.payload.get("transcription_id"),
                    "user_id": user_id,
                    "vector": point.vector,
                    "text": point.payload.get("full_text", ""),
                    "chunk_index": point.payload.get("chunk_index", 0),
                    "content_type": point.payload.get("content_type", "transcription")
                })

            print(f"Exported {len(points)} points for user {user_id}")

        except Exception as e:
            print(f"No collection for user {user_id}: {e}")
            continue

# Save to file
with open("qdrant_export.json", "w") as f:
    json.dump(export_data, f, indent=2)

print(f"Total exported: {len(export_data)} vectors")
```

Run the export:

```bash
cd backend
python scripts/export_qdrant_data.py
```

### 3.2 Migrate Data to Supabase

**Step 1: Migrate PostgreSQL tables**

```bash
# Dump data from current PostgreSQL
pg_dump $DATABASE_URL \
  --data-only \
  --table=users \
  --table=transcriptions \
  --table=knowledge_queries \
  --table=api_keys \
  --table=user_usage \
  > data_export.sql

# Import to Supabase
psql "$SUPABASE_DATABASE_URL" < data_export.sql
```

**Step 2: Import vectors to Supabase**

Create import script:

**File:** `backend/scripts/import_to_supabase.py`

```python
import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Connect to Supabase PostgreSQL
engine = create_engine(os.getenv("DATABASE_URL"))

# Load exported data
with open("qdrant_export.json", "r") as f:
    export_data = json.load(f)

print(f"Importing {len(export_data)} vectors...")

with engine.connect() as conn:
    for i, item in enumerate(export_data):
        if item["content_type"] == "transcription_chunk":
            # Insert into transcription_chunks table
            conn.execute(text("""
                INSERT INTO transcription_chunks
                (id, transcription_id, chunk_index, text, embedding)
                VALUES (:id, :transcription_id, :chunk_index, :text, :embedding::vector)
                ON CONFLICT (id) DO UPDATE SET
                  embedding = EXCLUDED.embedding
            """), {
                "id": item["point_id"],
                "transcription_id": item["transcription_id"],
                "chunk_index": item["chunk_index"],
                "text": item["text"],
                "embedding": str(item["vector"])
            })
        else:
            # Update main transcription with embedding
            conn.execute(text("""
                UPDATE transcriptions
                SET embedding = :embedding::vector
                WHERE id = :transcription_id
            """), {
                "transcription_id": item["transcription_id"],
                "embedding": str(item["vector"])
            })

        if (i + 1) % 100 == 0:
            print(f"Imported {i + 1} vectors...")
            conn.commit()

    conn.commit()

print("Import complete!")
```

Run the import:

```bash
cd backend
python scripts/import_to_supabase.py
```

---

## Phase 4: Backend Code Updates

### 4.1 Update Dependencies

**File:** `backend/requirements.txt`

```diff
- qdrant-client==1.7.3
+ supabase==2.3.4
+ vecs==0.4.0  # Optional: Supabase vector client
```

Install:
```bash
pip install supabase vecs
```

### 4.2 Update Database Configuration

**File:** `backend/app/database.py`

No changes needed! SQLAlchemy will work the same with Supabase PostgreSQL.

Just update the `DATABASE_URL` in `.env` to Supabase connection string.

### 4.3 Update Models

**File:** `backend/app/models.py`

```diff
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, UUID, ForeignKey, Text, ARRAY
+ from pgvector.sqlalchemy import Vector

class Transcription(Base):
    __tablename__ = "transcriptions"

    # ... existing fields ...

-   qdrant_point_ids = Column(ARRAY(String), nullable=True)
-   qdrant_collection = Column(String(255), nullable=True)
+   embedding = Column(Vector(384), nullable=True)  # pgvector column

+ class TranscriptionChunk(Base):
+     __tablename__ = "transcription_chunks"
+
+     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
+     transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"))
+     chunk_index = Column(Integer, nullable=False)
+     text = Column(Text, nullable=False)
+     embedding = Column(Vector(384), nullable=True)
+     created_at = Column(DateTime, default=datetime.utcnow)
+
+     transcription = relationship("Transcription", back_populates="chunks")

+ Transcription.chunks = relationship("TranscriptionChunk", back_populates="transcription", cascade="all, delete-orphan")
```

### 4.4 Replace Knowledge Service (Qdrant → pgvector)

**File:** `backend/app/services/knowledge_service.py`

This is the main change. Replace Qdrant client with pgvector queries:

```python
from sqlalchemy import text, func
from pgvector.sqlalchemy import Vector
import numpy as np

class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Keep same model

    async def query_knowledge_base(
        self,
        user_id: UUID,
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ):
        """Query using pgvector similarity search"""

        # Generate query embedding (same as before)
        query_embedding = self.model.encode(query_text).tolist()

        # Vector similarity search with pgvector
        results = self.db.execute(text("""
            SELECT
                tc.transcription_id,
                tc.text,
                tc.chunk_index,
                t.title,
                t.filename,
                1 - (tc.embedding <=> :query_embedding::vector) as similarity
            FROM transcription_chunks tc
            JOIN transcriptions t ON t.id = tc.transcription_id
            WHERE t.user_id = :user_id
              AND 1 - (tc.embedding <=> :query_embedding::vector) > :threshold
            ORDER BY tc.embedding <=> :query_embedding::vector
            LIMIT :limit
        """), {
            "query_embedding": str(query_embedding),
            "user_id": str(user_id),
            "threshold": similarity_threshold,
            "limit": limit
        }).fetchall()

        # Format results (same as before)
        contexts = []
        for row in results:
            contexts.append({
                "transcription_id": str(row[0]),
                "text": row[1],
                "chunk_index": row[2],
                "title": row[3],
                "filename": row[4],
                "similarity": float(row[5])
            })

        # Generate answer with Groq (same as before)
        if contexts:
            context_text = "\n\n".join([c["text"] for c in contexts])
            answer = await self._generate_answer(query_text, context_text)
        else:
            answer = "No relevant information found in your transcriptions."

        # Save query (same as before)
        query_record = KnowledgeQuery(
            user_id=user_id,
            query_text=query_text,
            response_text=answer,
            transcription_ids=[c["transcription_id"] for c in contexts],
            confidence_score=contexts[0]["similarity"] if contexts else 0.0
        )
        self.db.add(query_record)
        self.db.commit()

        return {
            "answer": answer,
            "sources": contexts,
            "query_id": query_record.id
        }

    async def store_transcription(
        self,
        transcription_id: UUID,
        text: str,
        user_id: UUID
    ):
        """Store transcription with vector embeddings"""

        # Split into chunks (same logic as before)
        chunks = self._split_text(text, chunk_size=1000)

        for i, chunk_text in enumerate(chunks):
            # Generate embedding
            embedding = self.model.encode(chunk_text).tolist()

            # Store in database with pgvector
            chunk = TranscriptionChunk(
                transcription_id=transcription_id,
                chunk_index=i,
                text=chunk_text,
                embedding=embedding
            )
            self.db.add(chunk)

        self.db.commit()

        return len(chunks)

    async def delete_transcription_vectors(self, transcription_id: UUID):
        """Delete all chunks for a transcription"""
        self.db.query(TranscriptionChunk).filter(
            TranscriptionChunk.transcription_id == transcription_id
        ).delete()
        self.db.commit()

    async def get_knowledge_base_stats(self, user_id: UUID):
        """Get statistics about user's knowledge base"""
        stats = self.db.execute(text("""
            SELECT
                COUNT(DISTINCT tc.transcription_id) as transcription_count,
                COUNT(tc.id) as chunk_count,
                AVG(length(tc.text)) as avg_chunk_length
            FROM transcription_chunks tc
            JOIN transcriptions t ON t.id = tc.transcription_id
            WHERE t.user_id = :user_id
        """), {"user_id": str(user_id)}).fetchone()

        query_count = self.db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == user_id
        ).count()

        return {
            "transcription_count": stats[0] or 0,
            "chunk_count": stats[1] or 0,
            "query_count": query_count,
            "avg_chunk_length": int(stats[2]) if stats[2] else 0
        }

    async def clear_knowledge_base(self, user_id: UUID):
        """Clear all vectors for a user"""
        self.db.execute(text("""
            DELETE FROM transcription_chunks
            WHERE transcription_id IN (
                SELECT id FROM transcriptions WHERE user_id = :user_id
            )
        """), {"user_id": str(user_id)})
        self.db.commit()

    def _split_text(self, text: str, chunk_size: int = 1000) -> list:
        """Split text into chunks (same as before)"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using Groq (same as before)"""
        # Keep existing Groq implementation
        pass
```

### 4.5 Update Config

**File:** `backend/app/config.py`

```diff
- QDRANT_URL: str = os.getenv("QDRANT_URL", "")
- QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
+ SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
+ SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
+ SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
```

### 4.6 Optional: Add Supabase Storage (Replace S3)

If you want to use Supabase Storage instead of S3:

```python
from supabase import create_client, Client

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Upload file
with open("audio.mp3", "rb") as f:
    res = supabase.storage.from_("transcriptions").upload(
        f"user_{user_id}/{filename}",
        f
    )

# Get public URL
url = supabase.storage.from_("transcriptions").get_public_url(
    f"user_{user_id}/{filename}"
)
```

---

## Phase 5: Testing

### 5.1 Unit Tests

Test vector operations:

```bash
cd backend
pytest tests/test_knowledge_service.py -v
```

### 5.2 Integration Tests

Create test script:

**File:** `backend/tests/test_migration.py`

```python
import pytest
from app.services.knowledge_service import KnowledgeService

def test_vector_similarity_search(db_session, test_user):
    """Test pgvector similarity search works"""
    service = KnowledgeService(db_session)

    # Store a test transcription
    transcription = create_test_transcription(test_user.id)
    service.store_transcription(
        transcription.id,
        "This is a test about machine learning and AI",
        test_user.id
    )

    # Query
    result = service.query_knowledge_base(
        test_user.id,
        "What did I learn about AI?",
        limit=5
    )

    assert len(result["sources"]) > 0
    assert "machine learning" in result["sources"][0]["text"].lower()

def test_performance(db_session, test_user):
    """Test query performance"""
    import time
    service = KnowledgeService(db_session)

    start = time.time()
    result = service.query_knowledge_base(
        test_user.id,
        "test query",
        limit=10
    )
    elapsed = time.time() - start

    # Should be under 200ms for pgvector
    assert elapsed < 0.2, f"Query took {elapsed}s, too slow!"
```

Run tests:
```bash
pytest tests/test_migration.py -v
```

### 5.3 Manual Testing

1. **Upload a file** → Check it transcribes
2. **Query knowledge base** → Check it returns relevant results
3. **Generate summary** → Check it works
4. **Check stats** → Verify counts are correct
5. **Delete transcription** → Verify vectors are deleted

---

## Phase 6: Deployment

### 6.1 Update Environment Variables

Production `.env`:

```env
# Supabase (Production)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres.xxxxxxxxxxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Remove these
# QDRANT_URL=...
# QDRANT_API_KEY=...
```

### 6.2 Deploy Backend

```bash
# Pull latest code
git pull origin main

# Install new dependencies
pip install -r requirements.txt

# Restart backend
systemctl restart transcription-backend

# Or with Docker
docker-compose up -d --build backend
```

### 6.3 Verify Production

```bash
# Health check
curl https://api.yourdomain.com/health

# Test query
curl -X POST https://api.yourdomain.com/api/knowledge/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

---

## Phase 7: Cleanup

After confirming everything works:

### 7.1 Remove Qdrant

```bash
# Remove from requirements.txt
pip uninstall qdrant-client

# Remove environment variables
# Delete QDRANT_URL and QDRANT_API_KEY from .env

# Cancel Qdrant subscription (if paid)
# Delete collections from Qdrant dashboard
```

### 7.2 Remove Old Code

```bash
# Remove old Qdrant integration code
rm backend/app/services/qdrant_client.py  # if exists

# Update documentation
# Remove Qdrant references from README, DEPLOYMENT.md
```

### 7.3 Archive Backups

```bash
# Move backups to archive
mkdir -p backups/migration_$(date +%Y%m%d)
mv backup_*.sql backups/migration_$(date +%Y%m%d)/
mv qdrant_export.json backups/migration_$(date +%Y%m%d)/
```

---

## Rollback Plan

If something goes wrong:

### Immediate Rollback (< 1 hour after migration)

```bash
# 1. Switch back to old DATABASE_URL and Qdrant
cp .env.backup .env

# 2. Restart backend
systemctl restart transcription-backend

# 3. Verify old system works
curl http://localhost:8000/health
```

### Data Recovery (if needed)

```bash
# Restore PostgreSQL backup
psql $OLD_DATABASE_URL < backup_YYYYMMDD.sql

# Qdrant data should still be intact
# Just reconnect with old credentials
```

---

## Timeline Estimate

| Phase | Time | Can Run in Background? |
|-------|------|----------------------|
| 1. Backup | 10 min | No |
| 2. Schema Migration | 15 min | No |
| 3. Data Migration | 30-60 min | Yes (depends on data size) |
| 4. Code Updates | 45 min | Yes |
| 5. Testing | 30 min | No |
| 6. Deployment | 15 min | No |
| **Total** | **2-3 hours** | |

---

## Success Criteria

Migration is successful when:

- [ ] All existing data visible in Supabase dashboard
- [ ] Vector similarity search returns relevant results
- [ ] Query performance < 200ms (acceptable)
- [ ] No errors in production logs for 24 hours
- [ ] All tests passing
- [ ] Users can upload and transcribe successfully
- [ ] Knowledge base queries work correctly

---

## Post-Migration Monitoring

### Week 1:
- Check error logs daily
- Monitor query performance
- Verify backup automation
- Check Supabase dashboard for issues

### Week 2-4:
- Review performance metrics
- Optimize slow queries if needed
- Consider upgrading to Pro plan if needed
- Remove Qdrant backups after 30 days

---

## Getting Help

**Issues during migration:**
- Supabase Discord: [discord.supabase.com](https://discord.supabase.com)
- Supabase Support: support@supabase.io (Pro/Team plans)
- pgvector GitHub: [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)

**Common Issues:**
- Vector dimension mismatch → Check embedding model (384 dims)
- Slow queries → Add HNSW index, check connection pooling
- Import errors → Check PostgreSQL version (14+), vector extension enabled

---

Ready to start? Begin with [Phase 1: Backup Current Data](#phase-1-backup-current-data)
