#!/usr/bin/env python3
"""
Run Granola Features Migration
This script creates the new tables for calendar integration and meetings
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings

def run_migration():
    """Run the Granola features migration"""
    print("🚀 Starting Granola Features Migration...")
    print(f"📊 Database: {settings.DATABASE_URL.split('@')[1]}")  # Hide password

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'add_granola_tables.sql')
    with open(sql_file, 'r') as f:
        sql = f.read()

    # Execute SQL
    try:
        with engine.connect() as conn:
            # Execute as a single transaction
            print(f"📝 Executing SQL script...")
            conn.execute(text(sql))
            conn.commit()

            print("✅ Migration completed successfully!")
            print("\n📋 Created tables:")
            print("  - meeting_templates")
            print("  - calendar_connections")
            print("  - meetings")
            print("  - meeting_notes")
            print("  - action_items")
            print("  - integrations")
            print("\n✨ Your database is now ready for Granola features!")

            return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
