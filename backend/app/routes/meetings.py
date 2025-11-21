# backend/app/routes/meetings.py
"""
Meeting Routes - Granola Features
Handles viewing and managing synced calendar meetings
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import User, Meeting, CalendarConnection
from ..services.auth_service import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic schemas
class MeetingResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    timezone: str
    platform: Optional[str]
    meeting_url: Optional[str]
    participants: Optional[str]
    status: str
    recording_status: str
    calendar_connection_id: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Convert UUID fields to strings
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            start_time=obj.start_time,
            end_time=obj.end_time,
            timezone=obj.timezone,
            platform=obj.platform,
            meeting_url=obj.meeting_url,
            participants=obj.participants,
            status=obj.status,
            recording_status=obj.recording_status,
            calendar_connection_id=str(obj.calendar_connection_id) if obj.calendar_connection_id else None
        )


class MeetingListResponse(BaseModel):
    meetings: List[MeetingResponse]
    total: int
    upcoming_count: int
    past_count: int


@router.get("/meetings", response_model=MeetingListResponse)
async def list_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status: upcoming, past, all"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List all meetings for the current user

    - **status_filter**: upcoming, past, or all (default: all)
    - **limit**: Maximum number of meetings to return
    - **offset**: Number of meetings to skip
    """
    try:
        # Base query
        query = db.query(Meeting).filter(Meeting.user_id == current_user.id)

        # Apply status filter
        now = datetime.utcnow()
        if status_filter == "upcoming":
            query = query.filter(Meeting.start_time >= now)
            query = query.order_by(Meeting.start_time.asc())
        elif status_filter == "past":
            query = query.filter(Meeting.start_time < now)
            query = query.order_by(Meeting.start_time.desc())
        else:
            # Default: all meetings, sorted by start time descending
            query = query.order_by(Meeting.start_time.desc())

        # Get total count
        total = query.count()

        # Get upcoming and past counts
        upcoming_count = db.query(Meeting).filter(
            and_(
                Meeting.user_id == current_user.id,
                Meeting.start_time >= now
            )
        ).count()

        past_count = db.query(Meeting).filter(
            and_(
                Meeting.user_id == current_user.id,
                Meeting.start_time < now
            )
        ).count()

        # Apply pagination
        meetings = query.limit(limit).offset(offset).all()

        return MeetingListResponse(
            meetings=[MeetingResponse.from_orm(m) for m in meetings],
            total=total,
            upcoming_count=upcoming_count,
            past_count=past_count
        )

    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve meetings"
        )


@router.get("/meetings/upcoming", response_model=List[MeetingResponse])
async def get_upcoming_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours ahead to look")
):
    """
    Get upcoming meetings within the next N hours

    - **hours_ahead**: How many hours ahead to look (default: 24, max: 168/1 week)
    """
    try:
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours_ahead)

        meetings = db.query(Meeting).filter(
            and_(
                Meeting.user_id == current_user.id,
                Meeting.start_time >= now,
                Meeting.start_time <= end_time
            )
        ).order_by(Meeting.start_time.asc()).all()

        return [MeetingResponse.from_orm(m) for m in meetings]

    except Exception as e:
        logger.error(f"Error getting upcoming meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upcoming meetings"
        )


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific meeting by ID
    """
    try:
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == current_user.id
            )
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        return MeetingResponse.from_orm(meeting)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve meeting"
        )


@router.get("/meetings/today")
async def get_todays_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all meetings for today
    """
    try:
        # Get start and end of today in UTC
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        meetings = db.query(Meeting).filter(
            and_(
                Meeting.user_id == current_user.id,
                Meeting.start_time >= today_start,
                Meeting.start_time <= today_end
            )
        ).order_by(Meeting.start_time.asc()).all()

        return [MeetingResponse.from_orm(m) for m in meetings]

    except Exception as e:
        logger.error(f"Error getting today's meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve today's meetings"
        )
