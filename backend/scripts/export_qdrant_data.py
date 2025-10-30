"""
Export Qdrant Vector Data
This script exports all vector data from Qdrant collections to a JSON file
for migration to Supabase pgvector.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def export_qdrant_data():
    """Export all Qdrant collections to JSON file"""

    print("=" * 60)
    print("QDRANT DATA EXPORT")
    print("=" * 60)

    # Connect to Qdrant
    print("\n1. Connecting to Qdrant...")
    try:
        qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=60
        )
        print("✓ Connected to Qdrant")
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        return False

    # Connect to PostgreSQL
    print("\n2. Connecting to PostgreSQL...")
    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return False

    # Export data
    export_data = []
    total_users = 0
    total_vectors = 0

    print("\n3. Exporting vector data...")

    with engine.connect() as conn:
        # Get all users
        result = conn.execute(text("SELECT id, email FROM users"))
        users = result.fetchall()
        total_users = len(users)

        print(f"\nFound {total_users} users")

        for idx, user in enumerate(users, 1):
            user_id = str(user[0])
            user_email = user[1]
            collection_name = f"user_{user_id}_transcriptions"

            print(f"\n[{idx}/{total_users}] Processing user: {user_email}")
            print(f"  Collection: {collection_name}")

            try:
                # Check if collection exists
                collections = qdrant.get_collections().collections
                collection_names = [c.name for c in collections]

                if collection_name not in collection_names:
                    print(f"  ⊘ No collection found, skipping")
                    continue

                # Get collection info
                collection_info = qdrant.get_collection(collection_name)
                vector_count = collection_info.points_count
                print(f"  → Found {vector_count} vectors")

                # Scroll through all points
                offset = None
                batch_count = 0

                while True:
                    points, offset = qdrant.scroll(
                        collection_name=collection_name,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=True
                    )

                    if not points:
                        break

                    batch_count += len(points)

                    for point in points:
                        export_data.append({
                            "point_id": str(point.id),
                            "transcription_id": point.payload.get("transcription_id"),
                            "user_id": user_id,
                            "vector": point.vector,
                            "text": point.payload.get("full_text", ""),
                            "chunk_index": point.payload.get("chunk_index", 0),
                            "content_type": point.payload.get("content_type", "transcription"),
                            "title": point.payload.get("title", ""),
                            "created_at": point.payload.get("created_at", "")
                        })

                    if offset is None:
                        break

                total_vectors += batch_count
                print(f"  ✓ Exported {batch_count} vectors")

            except Exception as e:
                print(f"  ✗ Error processing collection: {e}")
                continue

    # Save to file
    print(f"\n4. Saving to file...")
    output_file = "qdrant_export.json"

    try:
        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)

        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"✓ Saved to {output_file}")
        print(f"  File size: {file_size:.2f} MB")
    except Exception as e:
        print(f"✗ Failed to save file: {e}")
        return False

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"Total users processed: {total_users}")
    print(f"Total vectors exported: {total_vectors}")
    print(f"Output file: {output_file}")
    print(f"File size: {file_size:.2f} MB")
    print("\nNext steps:")
    print("1. Review qdrant_export.json")
    print("2. Run import_to_supabase.py to import data")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = export_qdrant_data()
    sys.exit(0 if success else 1)
