"""
Import Valid Vectors to Supabase
Only imports vectors that have valid transcription IDs
"""

import os
import json
from sqlalchemy import create_engine, text

print("=" * 60)
print("SUPABASE VECTOR IMPORT (FIXED)")
print("=" * 60)

# Load exported data
print("\n1. Loading export file...")
with open("qdrant_export.json", "r") as f:
    export_data = json.load(f)
print(f"✓ Loaded {len(export_data)} total vectors")

# Filter only vectors with valid transcription_ids
valid_vectors = [v for v in export_data if v.get("transcription_id") is not None]
print(f"✓ Found {len(valid_vectors)} vectors with valid transcription IDs")

# Connect to Supabase
print("\n2. Connecting to Supabase...")
database_url = "postgresql://postgres:Yg8ifcVKKCLdra9I@db.kqwjqvbifrmpvwqkrijs.supabase.co:5432/postgres"
engine = create_engine(database_url)
print("✓ Connected")

# Get list of transcription IDs that exist in Supabase
print("\n3. Verifying transcription IDs...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT id FROM transcriptions"))
    existing_ids = {str(row[0]) for row in result.fetchall()}
    print(f"✓ Found {len(existing_ids)} transcriptions in Supabase")

# Filter vectors to only those with existing transcription IDs
importable_vectors = [v for v in valid_vectors if v.get("transcription_id") in existing_ids]
print(f"✓ {len(importable_vectors)} vectors match existing transcriptions")

if len(importable_vectors) == 0:
    print("\n⚠ No vectors to import. Exiting.")
    exit(0)

# Group vectors by transcription_id (for chunks)
from collections import defaultdict
vectors_by_transcription = defaultdict(list)
for v in importable_vectors:
    vectors_by_transcription[v["transcription_id"]].append(v)

print(f"\n4. Importing {len(importable_vectors)} vectors...")
print(f"   Spread across {len(vectors_by_transcription)} transcriptions")

imported_chunks = 0
imported_transcriptions = 0
errors = 0

with engine.begin() as conn:
    for trans_id, vectors in vectors_by_transcription.items():
        try:
            # Sort vectors by chunk_index
            vectors_sorted = sorted(vectors, key=lambda x: x.get("chunk_index", 0))

            for v in vectors_sorted:
                vector_list = v["vector"]
                vector_str = "[" + ",".join(str(x) for x in vector_list) + "]"
                chunk_index = v.get("chunk_index", 0)
                chunk_text = v.get("text", "")

                if chunk_index > 0 or len(vectors_sorted) > 1:
                    # Multiple chunks - insert into transcription_chunks
                    conn.execute(text("""
                        INSERT INTO transcription_chunks
                        (transcription_id, chunk_index, text, embedding)
                        VALUES (:transcription_id, :chunk_index, :chunk_text, CAST(:embedding AS vector))
                        ON CONFLICT (transcription_id, chunk_index) DO UPDATE
                        SET embedding = EXCLUDED.embedding, text = EXCLUDED.text
                    """), {
                        "transcription_id": trans_id,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk_text,
                        "embedding": vector_str
                    })
                    imported_chunks += 1
                else:
                    # Single vector - update main transcription
                    conn.execute(text("""
                        UPDATE transcriptions
                        SET embedding = CAST(:embedding AS vector)
                        WHERE id = :transcription_id
                    """), {
                        "transcription_id": trans_id,
                        "embedding": vector_str
                    })
                    imported_transcriptions += 1

            if (imported_chunks + imported_transcriptions) % 10 == 0:
                print(f"   → Processed {imported_chunks + imported_transcriptions} vectors...")

        except Exception as e:
            errors += 1
            print(f"   ✗ Error importing vectors for transcription {trans_id[:8]}: {e}")
            continue

print(f"\n✓ Import completed!")
print(f"   Chunks inserted: {imported_chunks}")
print(f"   Transcriptions updated: {imported_transcriptions}")
print(f"   Errors: {errors}")

# Verify import
print("\n5. Verifying import...")
with engine.connect() as conn:
    chunk_count = conn.execute(text(
        "SELECT COUNT(*) FROM transcription_chunks WHERE embedding IS NOT NULL"
    )).scalar()

    trans_count = conn.execute(text(
        "SELECT COUNT(*) FROM transcriptions WHERE embedding IS NOT NULL"
    )).scalar()

    print(f"✓ Verification:")
    print(f"   Transcriptions with embeddings: {trans_count}")
    print(f"   Total chunks with embeddings: {chunk_count}")

# Create indexes if they don't exist
print("\n6. Creating vector indexes...")
try:
    with engine.begin() as conn:
        # Check if indexes exist
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'transcription_chunks'
            AND indexname = 'idx_chunks_embedding'
        """))

        if not result.fetchone():
            print("   → Creating HNSW index on transcription_chunks...")
            conn.execute(text("""
                CREATE INDEX idx_chunks_embedding
                ON transcription_chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            print("   ✓ Created index")
        else:
            print("   ✓ Index already exists")

except Exception as e:
    print(f"   ⚠ Could not create index: {e}")

# Test vector search
print("\n7. Testing vector search...")
try:
    with engine.connect() as conn:
        # Get a random embedding to test
        result = conn.execute(text("""
            SELECT embedding FROM transcription_chunks
            WHERE embedding IS NOT NULL
            LIMIT 1
        """)).fetchone()

        if result:
            test_embedding = result[0]

            # Test similarity search
            search_result = conn.execute(text("""
                SELECT tc.transcription_id, tc.text,
                       1 - (tc.embedding <=> :query_embedding) as similarity
                FROM transcription_chunks tc
                WHERE tc.embedding IS NOT NULL
                ORDER BY tc.embedding <=> :query_embedding
                LIMIT 3
            """), {"query_embedding": test_embedding}).fetchall()

            if search_result:
                print("   ✓ Vector search working!")
                print(f"   Found {len(search_result)} similar results")
                print(f"   Top similarity: {search_result[0][2]:.4f}")
            else:
                print("   ⚠ No search results")
        else:
            print("   ⚠ No embeddings to test")

except Exception as e:
    print(f"   ✗ Error testing search: {e}")

print("\n" + "=" * 60)
print("✓ VECTOR IMPORT COMPLETE!")
print("=" * 60)
print("\nYour vectors are now in Supabase pgvector!")
print("Next steps:")
print("1. Update backend code to use pgvector queries")
print("2. Update .env to use Supabase DATABASE_URL")
print("3. Test the application")
print("=" * 60)
