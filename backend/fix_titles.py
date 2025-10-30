#!/usr/bin/env python3
"""Fix transcription titles by generating them from content"""

from sqlalchemy import create_engine, text
import re
from datetime import datetime

db_url = 'postgresql://postgres:Yg8ifcVKKCLdra9I@db.kqwjqvbifrmpvwqkrijs.supabase.co:5432/postgres'
engine = create_engine(db_url)

def generate_title_from_text(text, created_at):
    if not text or len(text.strip()) < 20:
        # Use date as fallback
        return f'Transcription {created_at.strftime("%Y-%m-%d %H:%M")}'

    # Remove segment markers
    text = re.sub(r'\[Segment \d+\]', '', text)
    text = text.strip()

    # Get first meaningful sentence
    sentences = text.split('.')
    for sentence in sentences[:3]:
        clean = sentence.strip()
        # Skip very short or filler
        if len(clean) > 15 and len(clean) < 100:
            # Remove common filler words from start
            clean = re.sub(r'^(um|uh|so|well|okay|alright|now|the)\s+', '', clean, flags=re.IGNORECASE)
            if clean:
                return clean[:80]  # Limit to 80 chars

    # Fallback: first 80 chars
    return text[:80].strip()

with engine.connect() as conn:
    # Get all transcriptions with 'Untitled'
    result = conn.execute(text("""
        SELECT id, transcription_text, created_at
        FROM transcriptions
        WHERE title = 'Untitled'
    """))

    rows = result.fetchall()
    print(f'Updating {len(rows)} transcriptions...\n')

    updated = 0
    for row in rows:
        trans_id, trans_text, created_at = row
        new_title = generate_title_from_text(trans_text, created_at)

        conn.execute(
            text('UPDATE transcriptions SET title = :title WHERE id = :id'),
            {'title': new_title, 'id': trans_id}
        )
        updated += 1
        if updated <= 10:  # Show first 10
            print(f'  ✓ {new_title}')

    conn.commit()
    print(f'\n✅ Updated {updated} transcription titles!')
