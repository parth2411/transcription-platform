# backend/app/routes/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from ..database import get_db
from ..models import User, Transcription, KnowledgeQuery
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard statistics"""
    try:
        user_id = str(current_user.id)

        # Total transcriptions by status
        total_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id
        ).count()

        completed_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "completed"
        ).count()

        processing_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "processing"
        ).count()

        # Total duration and usage
        duration_stats = db.execute(text("""
            SELECT
                COALESCE(SUM(duration_seconds), 0) as total_seconds,
                COALESCE(AVG(duration_seconds), 0) as avg_seconds,
                COUNT(*) as count
            FROM transcriptions
            WHERE user_id = :user_id
              AND status = 'completed'
              AND duration_seconds IS NOT NULL
        """), {"user_id": user_id}).fetchone()

        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_activity = db.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as count,
                COALESCE(SUM(duration_seconds), 0) as total_duration
            FROM transcriptions
            WHERE user_id = :user_id
              AND created_at >= :start_date
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """), {"user_id": user_id, "start_date": thirty_days_ago}).fetchall()

        # Knowledge base queries
        total_queries = db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == current_user.id
        ).count()

        # File type distribution
        file_types = db.execute(text("""
            SELECT
                file_type,
                COUNT(*) as count
            FROM transcriptions
            WHERE user_id = :user_id
              AND file_type IS NOT NULL
            GROUP BY file_type
        """), {"user_id": user_id}).fetchall()

        failed_count = total_transcriptions - completed_transcriptions - processing_transcriptions
        success_rate = (completed_transcriptions / total_transcriptions * 100) if total_transcriptions > 0 else 0

        return {
            "total_transcriptions": total_transcriptions,
            "completed_transcriptions": completed_transcriptions,
            "processing_transcriptions": processing_transcriptions,
            "failed_transcriptions": failed_count,
            "success_rate": round(success_rate, 1),
            "total_duration_hours": round(duration_stats[0] / 3600, 2),
            "avg_duration_minutes": round(duration_stats[1] / 60, 2),
            "total_queries": total_queries,
            "monthly_usage": current_user.monthly_transcription_count,
            "usage_limit": 100,  # TODO: Get from settings based on subscription_tier
            "storage_used_mb": 0,  # TODO: Calculate actual storage
            "recent_activity": [
                {
                    "date": row[0].isoformat(),
                    "count": row[1],
                    "duration_hours": round(row[2] / 3600, 2)
                }
                for row in recent_activity
            ],
            "file_types": [
                {"type": row[0], "count": row[1]}
                for row in file_types
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard statistics"
        )

@router.get("/trends")
async def get_trends(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage trends over time"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        trends = db.execute(text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as transcriptions,
                COALESCE(SUM(duration_seconds), 0) as total_duration,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
            FROM transcriptions
            WHERE user_id = :user_id
              AND created_at >= :start_date
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """), {
            "user_id": str(current_user.id),
            "start_date": start_date
        }).fetchall()

        return {
            "trends": [
                {
                    "date": row[0].isoformat(),
                    "transcriptions": row[1],
                    "duration_hours": round(row[2] / 3600, 2),
                    "completed": row[3],
                    "failed": row[4],
                    "success_rate": round((row[3] / row[1] * 100) if row[1] > 0 else 0, 1)
                }
                for row in trends
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trends")

@router.get("/top-keywords")
async def get_top_keywords(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get most common keywords from transcriptions"""
    try:
        # Get top query keywords
        keywords = db.execute(text("""
            SELECT
                query_text,
                COUNT(*) as frequency,
                AVG(confidence_score) as avg_confidence
            FROM knowledge_queries
            WHERE user_id = :user_id
            GROUP BY query_text
            ORDER BY frequency DESC
            LIMIT :limit
        """), {
            "user_id": str(current_user.id),
            "limit": limit
        }).fetchall()

        return {
            "keywords": [
                {
                    "text": row[0][:50],  # Truncate long queries
                    "frequency": row[1],
                    "avg_confidence": round(row[2], 2) if row[2] else 0
                }
                for row in keywords
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get keywords: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve keywords")
