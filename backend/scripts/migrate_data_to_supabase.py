"""
Migrate data from local PostgreSQL to Supabase
Handles schema differences (removes qdrant columns, adds embedding column)
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Source database (local)
SOURCE_DB = "postgresql://parthbhalodiya@localhost:5432/transcription_db"

# Target database (Supabase) - fixed format for SQLAlchemy
TARGET_DB = "postgresql://postgres:Yg8ifcVKKCLdra9I@db.kqwjqvbifrmpvwqkrijs.supabase.co:5432/postgres"

print("=" * 60)
print("DATA MIGRATION TO SUPABASE")
print("=" * 60)

# Connect to both databases
print("\n1. Connecting to databases...")
source_engine = create_engine(SOURCE_DB)
target_engine = create_engine(TARGET_DB)
print("✓ Connected to source and target")

# Migrate users
print("\n2. Migrating users...")
with source_engine.connect() as source, target_engine.begin() as target:
    users = source.execute(text("SELECT * FROM users")).fetchall()
    columns = source.execute(text("SELECT * FROM users LIMIT 0")).keys()

    for user in users:
        user_dict = dict(zip(columns, user))
        target.execute(text("""
            INSERT INTO users (id, email, password_hash, first_name, last_name,
                subscription_tier, is_active, is_verified, monthly_transcription_count,
                created_at, updated_at)
            VALUES (:id, :email, :password_hash, :first_name, :last_name,
                :subscription_tier, :is_active, :is_verified, :monthly_transcription_count,
                :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": str(user_dict["id"]),
            "email": user_dict["email"],
            "password_hash": user_dict["password_hash"],
            "first_name": user_dict.get("first_name"),
            "last_name": user_dict.get("last_name"),
            "subscription_tier": user_dict.get("subscription_tier", "free"),
            "is_active": user_dict.get("is_active", True),
            "is_verified": user_dict.get("is_verified", False),
            "monthly_transcription_count": user_dict.get("monthly_transcription_count", 0),
            "created_at": user_dict.get("created_at"),
            "updated_at": user_dict.get("updated_at")
        })

    print(f"✓ Migrated {len(users)} users")

# Migrate transcriptions (excluding qdrant columns)
print("\n3. Migrating transcriptions...")
with source_engine.connect() as source, target_engine.begin() as target:
    transcriptions = source.execute(text("SELECT * FROM transcriptions")).fetchall()
    columns = source.execute(text("SELECT * FROM transcriptions LIMIT 0")).keys()

    for trans in transcriptions:
        trans_dict = dict(zip(columns, trans))

        # Skip qdrant_point_ids and qdrant_collection columns
        target.execute(text("""
            INSERT INTO transcriptions (
                id, user_id, filename, file_url, file_type, file_size,
                duration_seconds, transcription_text, summary_text, language,
                diarization_data, speaker_count, status, confidence_score,
                processing_time_seconds, error_message, generate_summary,
                speaker_diarization, add_to_knowledge_base, created_at,
                updated_at, completed_at
            ) VALUES (
                :id, :user_id, :filename, :file_url, :file_type, :file_size,
                :duration_seconds, :transcription_text, :summary_text, :language,
                :diarization_data, :speaker_count, :status, :confidence_score,
                :processing_time_seconds, :error_message, :generate_summary,
                :speaker_diarization, :add_to_knowledge_base, :created_at,
                :updated_at, :completed_at
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": str(trans_dict["id"]),
            "user_id": str(trans_dict["user_id"]),
            "filename": trans_dict.get("filename"),
            "file_url": trans_dict.get("file_url"),
            "file_type": trans_dict.get("file_type"),
            "file_size": trans_dict.get("file_size"),
            "duration_seconds": trans_dict.get("duration_seconds"),
            "transcription_text": trans_dict.get("transcription_text"),
            "summary_text": trans_dict.get("summary_text"),
            "language": trans_dict.get("language", "auto"),
            "diarization_data": trans_dict.get("diarization_data"),
            "speaker_count": trans_dict.get("speaker_count", 0),
            "status": trans_dict.get("status", "completed"),
            "confidence_score": trans_dict.get("confidence_score"),
            "processing_time_seconds": trans_dict.get("processing_time_seconds"),
            "error_message": trans_dict.get("error_message"),
            "generate_summary": trans_dict.get("generate_summary", False),
            "speaker_diarization": trans_dict.get("speaker_diarization", False),
            "add_to_knowledge_base": trans_dict.get("add_to_knowledge_base", True),
            "created_at": trans_dict.get("created_at"),
            "updated_at": trans_dict.get("updated_at"),
            "completed_at": trans_dict.get("completed_at")
        })

    print(f"✓ Migrated {len(transcriptions)} transcriptions")

# Migrate knowledge_queries
print("\n4. Migrating knowledge queries...")
with source_engine.connect() as source, target_engine.begin() as target:
    queries = source.execute(text("SELECT * FROM knowledge_queries")).fetchall()
    columns = source.execute(text("SELECT * FROM knowledge_queries LIMIT 0")).keys()

    for query in queries:
        query_dict = dict(zip(columns, query))
        target.execute(text("""
            INSERT INTO knowledge_queries (
                id, user_id, query_text, response_text, transcription_ids,
                confidence_score, response_time_ms, created_at
            ) VALUES (
                :id, :user_id, :query_text, :response_text, :transcription_ids,
                :confidence_score, :response_time_ms, :created_at
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": str(query_dict["id"]),
            "user_id": str(query_dict["user_id"]),
            "query_text": query_dict.get("query_text"),
            "response_text": query_dict.get("response_text"),
            "transcription_ids": query_dict.get("transcription_ids"),
            "confidence_score": query_dict.get("confidence_score"),
            "response_time_ms": query_dict.get("response_time_ms"),
            "created_at": query_dict.get("created_at")
        })

    print(f"✓ Migrated {len(queries)} knowledge queries")

# Migrate api_keys (if exists)
print("\n5. Migrating API keys...")
try:
    with source_engine.connect() as source, target_engine.begin() as target:
        api_keys = source.execute(text("SELECT * FROM api_keys")).fetchall()
        if api_keys:
            columns = source.execute(text("SELECT * FROM api_keys LIMIT 0")).keys()

            for key in api_keys:
                key_dict = dict(zip(columns, key))
                target.execute(text("""
                    INSERT INTO api_keys (
                        id, user_id, name, key_hash, is_active, last_used,
                        usage_count, expires_at, created_at
                    ) VALUES (
                        :id, :user_id, :name, :key_hash, :is_active, :last_used,
                        :usage_count, :expires_at, :created_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": str(key_dict["id"]),
                    "user_id": str(key_dict["user_id"]),
                    "name": key_dict.get("name"),
                    "key_hash": key_dict.get("key_hash"),
                    "is_active": key_dict.get("is_active", True),
                    "last_used": key_dict.get("last_used"),
                    "usage_count": key_dict.get("usage_count", 0),
                    "expires_at": key_dict.get("expires_at"),
                    "created_at": key_dict.get("created_at")
                })

            print(f"✓ Migrated {len(api_keys)} API keys")
        else:
            print("⊘ No API keys to migrate")
except Exception as e:
    print(f"⊘ No API keys table: {e}")

# Migrate user_usage (if exists)
print("\n6. Migrating user usage...")
try:
    with source_engine.connect() as source, target_engine.begin() as target:
        usage = source.execute(text("SELECT * FROM user_usage")).fetchall()
        if usage:
            columns = source.execute(text("SELECT * FROM user_usage LIMIT 0")).keys()

            for u in usage:
                u_dict = dict(zip(columns, u))
                target.execute(text("""
                    INSERT INTO user_usage (
                        id, user_id, year, month, transcriptions_count,
                        total_duration_seconds, total_file_size_bytes,
                        api_calls_count, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :year, :month, :transcriptions_count,
                        :total_duration_seconds, :total_file_size_bytes,
                        :api_calls_count, :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": str(u_dict["id"]),
                    "user_id": str(u_dict["user_id"]),
                    "year": u_dict.get("year"),
                    "month": u_dict.get("month"),
                    "transcriptions_count": u_dict.get("transcriptions_count", 0),
                    "total_duration_seconds": u_dict.get("total_duration_seconds", 0),
                    "total_file_size_bytes": u_dict.get("total_file_size_bytes", 0),
                    "api_calls_count": u_dict.get("api_calls_count", 0),
                    "created_at": u_dict.get("created_at"),
                    "updated_at": u_dict.get("updated_at")
                })

            print(f"✓ Migrated {len(usage)} usage records")
        else:
            print("⊘ No usage records to migrate")
except Exception as e:
    print(f"⊘ No user_usage table: {e}")

# Verify migration
print("\n7. Verifying migration...")
with target_engine.connect() as target:
    user_count = target.execute(text("SELECT COUNT(*) FROM users")).scalar()
    trans_count = target.execute(text("SELECT COUNT(*) FROM transcriptions")).scalar()
    query_count = target.execute(text("SELECT COUNT(*) FROM knowledge_queries")).scalar()

    print(f"✓ Users: {user_count}")
    print(f"✓ Transcriptions: {trans_count}")
    print(f"✓ Knowledge queries: {query_count}")

print("\n" + "=" * 60)
print("✓ DATA MIGRATION COMPLETE!")
print("=" * 60)
print("\nNext step: Import vectors with import_to_supabase.py")
