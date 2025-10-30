# backend/app/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Dict, List
import logging
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Transcription, KnowledgeQuery, UserUsage
from ..services.auth_service import get_current_user
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class UserStatsResponse(BaseModel):
    total_transcriptions: int
    completed_transcriptions: int
    total_duration_hours: float
    total_queries: int
    monthly_usage: int
    subscription_tier: str
    usage_limit: int
    storage_used_mb: float

class UsageHistoryResponse(BaseModel):
    month: str
    transcriptions_count: int
    total_duration_seconds: int
    api_calls_count: int

class SubscriptionUpdate(BaseModel):
    tier: str  # "free", "pro", "business"

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive user statistics
    """
    try:
        # Count transcriptions
        total_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id
        ).count()
        
        completed_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "completed"
        ).count()
        
        # Calculate total duration
        total_duration = db.query(
            func.sum(Transcription.duration_seconds)
        ).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "completed"
        ).scalar() or 0
        
        # Count queries
        total_queries = db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == current_user.id
        ).count()
        
        # Calculate storage used
        total_file_size = db.query(
            func.sum(Transcription.file_size)
        ).filter(
            Transcription.user_id == current_user.id
        ).scalar() or 0
        
        # Get usage limit based on subscription
        usage_limits = {
            "free": settings.FREE_TIER_LIMIT,
            "pro": settings.PRO_TIER_LIMIT,
            "business": settings.BUSINESS_TIER_LIMIT
        }
        
        usage_limit = usage_limits.get(current_user.subscription_tier, settings.FREE_TIER_LIMIT)
        if usage_limit == -1:
            usage_limit = 999999  # Unlimited
        
        return UserStatsResponse(
            total_transcriptions=total_transcriptions,
            completed_transcriptions=completed_transcriptions,
            total_duration_hours=round(total_duration / 3600, 2),
            total_queries=total_queries,
            monthly_usage=current_user.monthly_transcription_count,
            subscription_tier=current_user.subscription_tier,
            usage_limit=usage_limit,
            storage_used_mb=round(total_file_size / 1024 / 1024, 2)
        )
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )

@router.get("/usage-history", response_model=List[UsageHistoryResponse])
async def get_usage_history(
    months: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's usage history for the past N months
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Get usage data
        usage_data = db.query(UserUsage).filter(
            UserUsage.user_id == current_user.id,
            UserUsage.year >= start_date.year
        ).order_by(UserUsage.year.desc(), UserUsage.month.desc()).all()
        
        # Convert to response format
        history = []
        for usage in usage_data:
            history.append(UsageHistoryResponse(
                month=f"{usage.year}-{usage.month:02d}",
                transcriptions_count=usage.transcriptions_count,
                total_duration_seconds=usage.total_duration_seconds,
                api_calls_count=usage.api_calls_count
            ))
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to get usage history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage history"
        )

@router.put("/subscription", response_model=Dict[str, str])
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user subscription tier
    Note: In production, this should integrate with payment processing
    """
    try:
        valid_tiers = ["free", "pro", "business"]
        
        if subscription_data.tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subscription tier. Valid options: {valid_tiers}"
            )
        
        # In production, you would:
        # 1. Verify payment with Stripe/PayPal
        # 2. Check if user can downgrade (based on current usage)
        # 3. Handle proration and billing
        
        current_user.subscription_tier = subscription_data.tier
        db.commit()
        
        logger.info(f"Subscription updated for user {current_user.id}: {subscription_data.tier}")
        
        return {
            "message": f"Subscription updated to {subscription_data.tier}",
            "tier": subscription_data.tier
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )

@router.post("/reset-monthly-usage")
async def reset_monthly_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset monthly usage counter (admin function or scheduled task)
    """
    try:
        current_user.monthly_transcription_count = 0
        db.commit()
        
        logger.info(f"Monthly usage reset for user {current_user.id}")
        
        return {"message": "Monthly usage reset successfully"}
        
    except Exception as e:
        logger.error(f"Failed to reset monthly usage: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset monthly usage"
        )

@router.get("/export-data")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data (GDPR compliance)
    """
    try:
        # Get all user data
        transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id
        ).all()
        
        queries = db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == current_user.id
        ).all()
        
        # Format data for export
        export_data = {
            "user_info": {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "subscription_tier": current_user.subscription_tier,
                "created_at": current_user.created_at.isoformat(),
                "monthly_usage": current_user.monthly_transcription_count
            },
            "transcriptions": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "transcription_text": t.transcription_text,
                    "summary_text": t.summary_text,
                    "created_at": t.created_at.isoformat(),
                    "duration_seconds": t.duration_seconds
                }
                for t in transcriptions
            ],
            "knowledge_queries": [
                {
                    "id": str(q.id),
                    "query_text": q.query_text,
                    "response_text": q.response_text,
                    "created_at": q.created_at.isoformat()
                }
                for q in queries
            ]
        }
        
        return export_data
        
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )