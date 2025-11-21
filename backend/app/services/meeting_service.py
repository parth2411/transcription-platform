# backend/app/services/meeting_service.py
"""
Meeting Service for Granola-like Features
Handles meetings, hybrid notes, action items, and AI-powered features
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import re

from ..models import (
    Meeting, MeetingNote, ActionItem, MeetingTemplate,
    Transcription, User
)
from ..config import settings

logger = logging.getLogger(__name__)


class MeetingService:
    """Service for managing meetings, notes, and action items"""

    @staticmethod
    def create_meeting(
        user_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        db: Session,
        description: Optional[str] = None,
        meeting_url: Optional[str] = None,
        template_id: Optional[str] = None,
        **kwargs
    ) -> Meeting:
        """
        Create a new meeting

        Args:
            user_id: User ID
            title: Meeting title
            start_time: Start time
            end_time: End time
            db: Database session
            description: Optional description
            meeting_url: Optional meeting URL
            template_id: Optional template ID
            **kwargs: Additional meeting fields

        Returns:
            Meeting object
        """
        try:
            meeting = Meeting(
                user_id=user_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                meeting_url=meeting_url,
                template_id=template_id,
                **kwargs
            )

            db.add(meeting)
            db.commit()
            db.refresh(meeting)

            logger.info(f"Created meeting: {title} for user {user_id}")
            return meeting

        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            db.rollback()
            raise

    @staticmethod
    def quick_start_meeting(
        user_id: str,
        title: str,
        db: Session
    ) -> Meeting:
        """
        Quick start a meeting (one-tap capture)

        Args:
            user_id: User ID
            title: Meeting title
            db: Database session

        Returns:
            Meeting object
        """
        now = datetime.utcnow()

        meeting = MeetingService.create_meeting(
            user_id=user_id,
            title=title,
            start_time=now,
            end_time=now + timedelta(hours=1),  # Default 1 hour
            db=db,
            status='in_progress',
            recording_status='recording',
            actual_start_time=now
        )

        logger.info(f"Quick-started meeting {meeting.id}")
        return meeting

    @staticmethod
    def add_manual_note(
        meeting_id: str,
        user_id: str,
        content: str,
        db: Session,
        section: Optional[str] = None,
        timestamp_in_meeting: Optional[int] = None
    ) -> MeetingNote:
        """
        Add a manual note to a meeting (user-typed)

        Args:
            meeting_id: Meeting ID
            user_id: User ID
            content: Note content
            db: Database session
            section: Optional section (agenda, discussion, etc.)
            timestamp_in_meeting: Seconds from meeting start

        Returns:
            MeetingNote object
        """
        try:
            note = MeetingNote(
                meeting_id=meeting_id,
                user_id=user_id,
                content=content,
                note_type='manual',
                section=section,
                timestamp_in_meeting=timestamp_in_meeting
            )

            db.add(note)
            db.commit()
            db.refresh(note)

            logger.info(f"Added manual note to meeting {meeting_id}")
            return note

        except Exception as e:
            logger.error(f"Error adding manual note: {e}")
            db.rollback()
            raise

    @staticmethod
    def add_ai_note(
        meeting_id: str,
        user_id: str,
        content: str,
        db: Session,
        speaker: Optional[str] = None,
        timestamp_in_meeting: Optional[int] = None
    ) -> MeetingNote:
        """
        Add an AI-generated note from transcription

        Args:
            meeting_id: Meeting ID
            user_id: User ID
            content: Transcribed content
            db: Database session
            speaker: Speaker name/identifier
            timestamp_in_meeting: Seconds from meeting start

        Returns:
            MeetingNote object
        """
        try:
            note = MeetingNote(
                meeting_id=meeting_id,
                user_id=user_id,
                content=content,
                note_type='ai',
                speaker=speaker,
                timestamp_in_meeting=timestamp_in_meeting
            )

            db.add(note)
            db.commit()
            db.refresh(note)

            logger.debug(f"Added AI note to meeting {meeting_id}")
            return note

        except Exception as e:
            logger.error(f"Error adding AI note: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_combined_notes(meeting_id: str, db: Session) -> List[Dict]:
        """
        Get combined notes (manual + AI) for a meeting, sorted by timestamp

        Args:
            meeting_id: Meeting ID
            db: Database session

        Returns:
            List of notes with type indicator
        """
        notes = db.query(MeetingNote).filter(
            MeetingNote.meeting_id == meeting_id
        ).order_by(MeetingNote.timestamp_in_meeting, MeetingNote.created_at).all()

        return [
            {
                'id': str(note.id),
                'content': note.content,
                'type': note.note_type,  # 'manual' or 'ai'
                'speaker': note.speaker,
                'section': note.section,
                'timestamp': note.timestamp_in_meeting,
                'created_at': note.created_at.isoformat()
            }
            for note in notes
        ]

    @staticmethod
    async def extract_action_items_with_ai(
        meeting_id: str,
        transcript: str,
        db: Session,
        user_id: str
    ) -> List[ActionItem]:
        """
        Extract action items from meeting transcript using AI

        Args:
            meeting_id: Meeting ID
            transcript: Full meeting transcript
            db: Database session
            user_id: User ID

        Returns:
            List of extracted ActionItem objects
        """
        try:
            # Import Groq service for AI extraction
            from .groq_service import GroqService

            groq_service = GroqService()

            # Prompt for action item extraction
            prompt = f"""
Analyze this meeting transcript and extract all action items.

For each action item, identify:
1. What needs to be done (title)
2. Any details or context (description)
3. Who it's assigned to (if mentioned)
4. Any mentioned deadline
5. Priority (high/medium/low based on urgency)

Return a JSON array with this structure:
[
  {{
    "title": "Brief description of the action",
    "description": "Additional context",
    "assigned_to": "Person's name or email if mentioned",
    "due_date": "ISO date string if mentioned, otherwise null",
    "priority": "high/medium/low",
    "context": "Relevant quote from transcript"
  }}
]

Transcript:
{transcript}

Return ONLY the JSON array, no other text.
"""

            # Call Groq API
            response = await groq_service.generate_completion(
                prompt=prompt,
                model="llama-3.3-70b-versatile",  # Good for extraction tasks
                temperature=0.1,  # Low temperature for consistency
                max_tokens=2000
            )

            # Parse JSON response
            try:
                action_items_data = json.loads(response.strip())
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    action_items_data = json.loads(json_match.group(0))
                else:
                    logger.error("Failed to parse action items from AI response")
                    return []

            # Create ActionItem objects
            action_items = []
            for item_data in action_items_data:
                # Parse due date if present
                due_date = None
                if item_data.get('due_date'):
                    try:
                        due_date = datetime.fromisoformat(item_data['due_date'])
                    except (ValueError, TypeError):
                        pass

                action_item = ActionItem(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    title=item_data.get('title', 'Untitled action'),
                    description=item_data.get('description'),
                    assigned_to_name=item_data.get('assigned_to'),
                    priority=item_data.get('priority', 'medium'),
                    due_date=due_date,
                    created_from_ai=True,
                    related_transcript_chunk=item_data.get('context')
                )

                db.add(action_item)
                action_items.append(action_item)

            db.commit()

            logger.info(f"Extracted {len(action_items)} action items from meeting {meeting_id}")
            return action_items

        except Exception as e:
            logger.error(f"Error extracting action items with AI: {e}")
            db.rollback()
            return []

    @staticmethod
    async def generate_meeting_summary(
        meeting_id: str,
        db: Session,
        template: Optional[MeetingTemplate] = None
    ) -> str:
        """
        Generate AI-powered meeting summary

        Args:
            meeting_id: Meeting ID
            db: Database session
            template: Optional template for custom summary format

        Returns:
            Summary text
        """
        try:
            from .groq_service import GroqService

            meeting = db.query(Meeting).get(meeting_id)
            if not meeting:
                raise ValueError("Meeting not found")

            # Get all notes
            notes = MeetingService.get_combined_notes(meeting_id, db)

            # Combine notes into full transcript
            transcript_parts = []
            for note in notes:
                if note['type'] == 'ai' and note['speaker']:
                    transcript_parts.append(f"[{note['speaker']}]: {note['content']}")
                else:
                    transcript_parts.append(note['content'])

            full_transcript = "\n".join(transcript_parts)

            # Build prompt based on template
            if template and template.summary_prompt:
                prompt = template.summary_prompt.format(
                    title=meeting.title,
                    transcript=full_transcript
                )
            else:
                # Default summary prompt
                prompt = f"""
Summarize this meeting in a structured format.

Meeting: {meeting.title}

Create a summary with these sections:
1. Overview (2-3 sentences)
2. Key Discussion Points (bullet points)
3. Decisions Made (bullet points)
4. Next Steps (bullet points)

Transcript:
{full_transcript}
"""

            groq_service = GroqService()
            summary = await groq_service.generate_completion(
                prompt=prompt,
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=1500
            )

            # Update meeting with summary
            meeting.summary = summary
            meeting.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Generated summary for meeting {meeting_id}")
            return summary

        except Exception as e:
            logger.error(f"Error generating meeting summary: {e}")
            raise

    @staticmethod
    def stop_meeting_recording(
        meeting_id: str,
        db: Session,
        generate_summary: bool = True
    ) -> Meeting:
        """
        Stop recording a meeting

        Args:
            meeting_id: Meeting ID
            db: Database session
            generate_summary: Whether to auto-generate summary

        Returns:
            Updated Meeting object
        """
        meeting = db.query(Meeting).get(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")

        meeting.status = 'completed'
        meeting.recording_status = 'processing'
        meeting.actual_end_time = datetime.utcnow()
        meeting.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(meeting)

        logger.info(f"Stopped recording for meeting {meeting_id}")

        # Trigger summary generation (can be done async)
        if generate_summary:
            # This would typically be queued as a background task
            # For now, we'll just mark it for processing
            meeting.recording_status = 'processing'
            db.commit()

        return meeting

    @staticmethod
    def create_action_item(
        meeting_id: str,
        user_id: str,
        title: str,
        db: Session,
        **kwargs
    ) -> ActionItem:
        """
        Create a manual action item

        Args:
            meeting_id: Meeting ID
            user_id: User ID
            title: Action item title
            db: Database session
            **kwargs: Additional fields

        Returns:
            ActionItem object
        """
        try:
            action_item = ActionItem(
                meeting_id=meeting_id,
                user_id=user_id,
                title=title,
                created_from_ai=False,
                **kwargs
            )

            db.add(action_item)
            db.commit()
            db.refresh(action_item)

            logger.info(f"Created action item for meeting {meeting_id}")
            return action_item

        except Exception as e:
            logger.error(f"Error creating action item: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_action_item_status(
        action_item_id: str,
        status: str,
        db: Session
    ) -> ActionItem:
        """
        Update action item status

        Args:
            action_item_id: ActionItem ID
            status: New status
            db: Database session

        Returns:
            Updated ActionItem
        """
        action_item = db.query(ActionItem).get(action_item_id)
        if not action_item:
            raise ValueError("Action item not found")

        action_item.status = status
        if status == 'completed':
            action_item.completed_at = datetime.utcnow()

        action_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(action_item)

        logger.info(f"Updated action item {action_item_id} to {status}")
        return action_item

    @staticmethod
    def get_user_action_items(
        user_id: str,
        db: Session,
        status: Optional[str] = None,
        assigned_to_me: bool = False
    ) -> List[ActionItem]:
        """
        Get action items for a user (across all meetings)

        Args:
            user_id: User ID
            db: Database session
            status: Filter by status (optional)
            assigned_to_me: Filter by items assigned to user email

        Returns:
            List of ActionItem objects
        """
        query = db.query(ActionItem).filter(ActionItem.user_id == user_id)

        if status:
            query = query.filter(ActionItem.status == status)

        if assigned_to_me:
            user = db.query(User).get(user_id)
            if user:
                query = query.filter(ActionItem.assigned_to_email == user.email)

        return query.order_by(ActionItem.due_date.asc().nullslast()).all()

    @staticmethod
    async def chat_with_meeting(
        meeting_id: str,
        question: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Chat with meeting notes using AI

        Args:
            meeting_id: Meeting ID
            question: User's question
            db: Database session

        Returns:
            Dict with answer and sources
        """
        try:
            from .groq_service import GroqService

            meeting = db.query(Meeting).get(meeting_id)
            if not meeting:
                raise ValueError("Meeting not found")

            # Get all meeting content
            notes = MeetingService.get_combined_notes(meeting_id, db)
            action_items = db.query(ActionItem).filter(
                ActionItem.meeting_id == meeting_id
            ).all()

            # Build context
            context_parts = [
                f"Meeting: {meeting.title}",
                f"Date: {meeting.start_time.strftime('%Y-%m-%d %H:%M')}",
                "\nNotes:"
            ]

            for note in notes:
                prefix = f"[{note['speaker']}]" if note.get('speaker') else "[User Note]"
                context_parts.append(f"{prefix}: {note['content']}")

            if action_items:
                context_parts.append("\nAction Items:")
                for item in action_items:
                    context_parts.append(f"- {item.title} (Status: {item.status})")

            context = "\n".join(context_parts)

            # Generate answer
            prompt = f"""
Based on the meeting information below, answer the following question.
Provide specific references to the meeting content when possible.

{context}

Question: {question}

Answer the question clearly and concisely, referencing specific parts of the meeting.
"""

            groq_service = GroqService()
            answer = await groq_service.generate_completion(
                prompt=prompt,
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                max_tokens=800
            )

            return {
                'answer': answer,
                'meeting_id': meeting_id,
                'meeting_title': meeting.title,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in chat_with_meeting: {e}")
            raise
