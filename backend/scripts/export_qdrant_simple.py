"""
Simple Qdrant Export - Works around client version issues
"""

import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import requests

load_dotenv()

# Get credentials
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

print("=" * 60)
print("SIMPLE QDRANT EXPORT")
print("=" * 60)

# Connect to Qdrant
print("\nConnecting to Qdrant...")
client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=60)
print("✓ Connected")

# List collections
print("\nListing collections...")
collections = client.get_collections().collections
print(f"Found {len(collections)} collections:")

export_data = []
total_points = 0

for collection in collections:
    collection_name = collection.name
    print(f"\n  → {collection_name}")

    try:
        # Use REST API directly to avoid client version issues
        url = f"{qdrant_url}/collections/{collection_name}/points/scroll"
        headers = {"api-key": qdrant_api_key}

        offset = None
        batch_count = 0

        while True:
            payload = {"limit": 100, "with_vector": True, "with_payload": True}
            if offset:
                payload["offset"] = offset

            response = requests.post(url, json=payload, headers=headers)
            data = response.json()

            if "result" not in data or "points" not in data["result"]:
                break

            points = data["result"]["points"]
            if not points:
                break

            for point in points:
                export_data.append({
                    "point_id": point["id"],
                    "transcription_id": point.get("payload", {}).get("transcription_id"),
                    "user_id": collection_name.split("_")[1] if "_" in collection_name else None,
                    "vector": point["vector"],
                    "text": point.get("payload", {}).get("full_text", ""),
                    "chunk_index": point.get("payload", {}).get("chunk_index", 0),
                    "content_type": point.get("payload", {}).get("content_type", "transcription"),
                    "title": point.get("payload", {}).get("title", ""),
                    "created_at": point.get("payload", {}).get("created_at", "")
                })

            batch_count += len(points)
            offset = data["result"].get("next_page_offset")

            if offset is None:
                break

        print(f"    ✓ Exported {batch_count} points")
        total_points += batch_count

    except Exception as e:
        print(f"    ✗ Error: {e}")
        continue

# Save to file
output_file = "qdrant_export.json"
with open(output_file, "w") as f:
    json.dump(export_data, f, indent=2)

file_size = os.path.getsize(output_file) / (1024 * 1024)

print("\n" + "=" * 60)
print(f"✓ Export complete!")
print(f"  Total points: {total_points}")
print(f"  Output file: {output_file}")
print(f"  File size: {file_size:.2f} MB")
print("=" * 60)
