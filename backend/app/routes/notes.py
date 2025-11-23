# backend/app/routes/notes.py
"""
Meeting Notes Routes
Handles CRUD operations for meeting notes (manual, AI, and hybrid)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
import logging

from ..database import get_db
from ..models import User, Meeting, MeetingNote
from ..services.auth_service import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ========================================
# Pydantic Schemas
# ========================================

class NoteCreate(BaseModel):
    meeting_id: str
    content: str
    note_type: str = "manual"  # manual, ai, hybrid
    section: Optional[str] = None  # agenda, discussion, action_items, decisions, notes
    timestamp_in_meeting: Optional[int] = None  # Seconds from meeting start

class NoteUpdate(BaseModel):
    content: Optional[str] = None
    section: Optional[str] = None

class NoteResponse(BaseModel):
    id: str
    meeting_id: str
    user_id: str
    content: str
    note_type: str
    section: Optional[str]
    timestamp_in_meeting: Optional[int]
    speaker: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=str(obj.id),
            meeting_id=str(obj.meeting_id),
            user_id=str(obj.user_id),
            content=obj.content,
            note_type=obj.note_type,
            section=obj.section,
            timestamp_in_meeting=obj.timestamp_in_meeting,
            speaker=obj.speaker,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


# ========================================
# Notes CRUD Operations
# ========================================

@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new meeting note

    - **meeting_id**: ID of the meeting
    - **content**: Note content (markdown supported)
    - **note_type**: manual, ai, or hybrid
    - **section**: Optional section (agenda, discussion, etc.)
    """
    try:
        # Verify meeting exists and user has access
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == note_data.meeting_id,
                Meeting.user_id == current_user.id
            )
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        # Create note
        note = MeetingNote(
            meeting_id=note_data.meeting_id,
            user_id=current_user.id,
            content=note_data.content,
            note_type=note_data.note_type,
            section=note_data.section,
            timestamp_in_meeting=note_data.timestamp_in_meeting
        )

        db.add(note)
        db.commit()
        db.refresh(note)

        logger.info(f"Created note {note.id} for meeting {note_data.meeting_id}")

        return NoteResponse.from_orm(note)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(e)}"
        )


@router.get("/meetings/{meeting_id}/notes", response_model=List[NoteResponse])
async def get_meeting_notes(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    note_type: Optional[str] = None,
    section: Optional[str] = None
):
    """
    Get all notes for a meeting

    - **meeting_id**: ID of the meeting
    - **note_type**: Filter by note type (manual, ai, hybrid)
    - **section**: Filter by section
    """
    try:
        # Verify meeting access
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

        # Build query
        query = db.query(MeetingNote).filter(
            MeetingNote.meeting_id == meeting_id
        )

        # Apply filters
        if note_type:
            query = query.filter(MeetingNote.note_type == note_type)
        if section:
            query = query.filter(MeetingNote.section == section)

        # Order by creation time
        notes = query.order_by(MeetingNote.created_at.asc()).all()

        return [NoteResponse.from_orm(note) for note in notes]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notes for meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notes"
        )


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific note by ID
    """
    try:
        note = db.query(MeetingNote).filter(
            and_(
                MeetingNote.id == note_id,
                MeetingNote.user_id == current_user.id
            )
        ).first()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )

        return NoteResponse.from_orm(note)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve note"
        )


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a note
    """
    try:
        note = db.query(MeetingNote).filter(
            and_(
                MeetingNote.id == note_id,
                MeetingNote.user_id == current_user.id
            )
        ).first()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )

        # Update fields
        if note_data.content is not None:
            note.content = note_data.content
        if note_data.section is not None:
            note.section = note_data.section

        note.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(note)

        logger.info(f"Updated note {note_id}")

        return NoteResponse.from_orm(note)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update note"
        )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a note
    """
    try:
        note = db.query(MeetingNote).filter(
            and_(
                MeetingNote.id == note_id,
                MeetingNote.user_id == current_user.id
            )
        ).first()

        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found"
            )

        db.delete(note)
        db.commit()

        logger.info(f"Deleted note {note_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete note"
        )
