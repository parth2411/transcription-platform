"""
Import Vector Data to Supabase
This script imports exported Qdrant vector data into Supabase PostgreSQL with pgvector.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def import_to_supabase():
    """Import Qdrant export data to Supabase pgvector"""

    print("=" * 60)
    print("SUPABASE DATA IMPORT")
    print("=" * 60)

    # Load exported data
    print("\n1. Loading export file...")
    export_file = "qdrant_export.json"

    if not os.path.exists(export_file):
        print(f"✗ Export file not found: {export_file}")
        print("  Please run export_qdrant_data.py first")
        return False

    try:
        with open(export_file, "r") as f:
            export_data = json.load(f)
        print(f"✓ Loaded {len(export_data)} vectors")
    except Exception as e:
        print(f"✗ Failed to load export file: {e}")
        return False

    # Connect to Supabase PostgreSQL
    print("\n2. Connecting to Supabase...")
    try:
        database_url = "postgresql://postgres:Yg8ifcVKKCLdra9I@db.kqwjqvbifrmpvwqkrijs.supabase.co:5432/postgres"
        engine = create_engine(database_url)
        print("✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        return False

    # Verify pgvector extension
    print("\n3. Verifying pgvector extension...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT * FROM pg_extension WHERE extname = 'vector'"
            ))
            if result.fetchone():
                print("✓ pgvector extension enabled")
            else:
                print("✗ pgvector extension not found")
                print("  Please enable it in Supabase dashboard")
                return False
    except Exception as e:
        print(f"✗ Failed to verify pgvector: {e}")
        return False

    # Import data
    print("\n4. Importing vectors...")

    imported_chunks = 0
    imported_transcriptions = 0
    skipped = 0
    errors = 0

    with engine.begin() as conn:
        for i, item in enumerate(export_data):
            try:
                # Convert vector list to pgvector format
                vector_str = "[" + ",".join(str(v) for v in item["vector"]) + "]"

                if item["content_type"] == "transcription_chunk" or item.get("chunk_index", 0) > 0:
                    # Insert into transcription_chunks table
                    conn.execute(text("""
                        INSERT INTO transcription_chunks
                        (id, transcription_id, chunk_index, text, embedding, created_at)
                        VALUES (:id, :transcription_id, :chunk_index, :text, :embedding::vector, :created_at)
                        ON CONFLICT (id) DO UPDATE SET
                          embedding = EXCLUDED.embedding,
                          text = EXCLUDED.text
                    """), {
                        "id": item["point_id"],
                        "transcription_id": item["transcription_id"],
                        "chunk_index": item["chunk_index"],
                        "text": item["text"],
                        "embedding": vector_str,
                        "created_at": item.get("created_at") or datetime.utcnow()
                    })
                    imported_chunks += 1

                else:
                    # Update main transcription with embedding
                    result = conn.execute(text("""
                        UPDATE transcriptions
                        SET embedding = :embedding::vector
                        WHERE id = :transcription_id
                    """), {
                        "transcription_id": item["transcription_id"],
                        "embedding": vector_str
                    })

                    if result.rowcount > 0:
                        imported_transcriptions += 1
                    else:
                        skipped += 1

                # Progress update every 100 items
                if (i + 1) % 100 == 0:
                    print(f"  → Processed {i + 1}/{len(export_data)} vectors...")

            except Exception as e:
                errors += 1
                print(f"  ✗ Error importing vector {i + 1}: {e}")
                continue

    print(f"\n✓ Import completed")

    # Create indexes if they don't exist
    print("\n5. Creating vector indexes...")
    try:
        with engine.begin() as conn:
            # Check if indexes exist
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename IN ('transcriptions', 'transcription_chunks')
                AND indexname LIKE '%embedding%'
            """))
            existing_indexes = [row[0] for row in result.fetchall()]

            # Create transcriptions index if needed
            if 'idx_transcriptions_embedding' not in existing_indexes:
                print("  → Creating HNSW index on transcriptions.embedding...")
                conn.execute(text("""
                    CREATE INDEX idx_transcriptions_embedding
                    ON transcriptions
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                print("  ✓ Created transcriptions embedding index")
            else:
                print("  ✓ Transcriptions embedding index exists")

            # Create chunks index if needed
            if 'idx_chunks_embedding' not in existing_indexes:
                print("  → Creating HNSW index on transcription_chunks.embedding...")
                conn.execute(text("""
                    CREATE INDEX idx_chunks_embedding
                    ON transcription_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                print("  ✓ Created chunks embedding index")
            else:
                print("  ✓ Chunks embedding index exists")

    except Exception as e:
        print(f"  ⚠ Warning: Could not create indexes: {e}")
        print("  You may need to create them manually")

    # Test vector search
    print("\n6. Testing vector search...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM transcription_chunks WHERE embedding IS NOT NULL
            """))
            chunk_count = result.scalar()

            result = conn.execute(text("""
                SELECT COUNT(*) FROM transcriptions WHERE embedding IS NOT NULL
            """))
            transcription_count = result.scalar()

            print(f"✓ Vector search ready")
            print(f"  Transcriptions with vectors: {transcription_count}")
            print(f"  Chunks with vectors: {chunk_count}")

    except Exception as e:
        print(f"✗ Failed to verify vector search: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Total vectors processed: {len(export_data)}")
    print(f"Transcriptions updated: {imported_transcriptions}")
    print(f"Chunks created: {imported_chunks}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print("\nNext steps:")
    print("1. Test vector search in your application")
    print("2. Update backend code to use pgvector queries")
    print("3. Run integration tests")
    print("4. Deploy updated backend")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = import_to_supabase()
    sys.exit(0 if success else 1)
