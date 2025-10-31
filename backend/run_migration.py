#!/usr/bin/env python3
"""Run database migrations for folders and tags"""

import psycopg2
import os

# Database connection
DATABASE_URL = "postgresql://postgres:Yg8ifcVKKCLdra9I@db.kqwjqvbifrmpvwqkrijs.supabase.co:5432/postgres"

def run_migration():
    """Execute the migration SQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Read migration file
        with open('migrations/add_folders_tags.sql', 'r') as f:
            sql = f.read()

        # Execute migration
        cur.execute(sql)
        conn.commit()

        print("✅ Migration completed successfully!")
        print("   - Created folders table")
        print("   - Created tags table")
        print("   - Created transcription_tags table")
        print("   - Added folder_id column to transcriptions")
        print("   - Added is_favorite column to transcriptions")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_migration()
