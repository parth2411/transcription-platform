# backend/app/services/calendar_service.py
"""
Google Calendar Integration Service
Handles OAuth authentication and calendar synchronization for Granola-like features
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import re

from ..models import CalendarConnection, Meeting, User, MeetingTemplate
from ..config import settings

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for managing calendar integrations (Google, Microsoft, Apple)"""

    # Google Calendar OAuth Scopes
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly'
    ]

    @staticmethod
    def get_google_oauth_url(state: str = None) -> str:
        """
        Generate Google OAuth authorization URL

        Args:
            state: Optional state parameter for security

        Returns:
            Authorization URL
        """
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=CalendarService.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )

        return authorization_url

    @staticmethod
    def exchange_google_code(code: str, db: Session, user_id: str) -> CalendarConnection:
        """
        Exchange authorization code for tokens and save calendar connection

        Args:
            code: Authorization code from Google
            db: Database session
            user_id: User ID

        Returns:
            CalendarConnection object
        """
        from google_auth_oauthlib.flow import Flow

        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=CalendarService.GOOGLE_SCOPES,
                redirect_uri=settings.GOOGLE_REDIRECT_URI
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Get calendar info
            service = build('calendar', 'v3', credentials=credentials)
            calendar = service.calendars().get(calendarId='primary').execute()

            # Create or update calendar connection
            connection = db.query(CalendarConnection).filter(
                CalendarConnection.user_id == user_id,
                CalendarConnection.provider == 'google',
                CalendarConnection.calendar_id == calendar['id']
            ).first()

            if not connection:
                connection = CalendarConnection(
                    user_id=user_id,
                    provider='google',
                    calendar_id=calendar['id'],
                    calendar_name=calendar.get('summary', 'Primary Calendar'),
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expires_at=credentials.expiry,
                    is_active=True,
                    sync_enabled=True
                )
                db.add(connection)
            else:
                connection.access_token = credentials.token
                connection.refresh_token = credentials.refresh_token
                connection.token_expires_at = credentials.expiry
                connection.is_active = True
                connection.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(connection)

            logger.info(f"Successfully connected Google Calendar for user {user_id}")
            return connection

        except Exception as e:
            logger.error(f"Error exchanging Google code: {e}")
            db.rollback()
            raise

    @staticmethod
    def refresh_google_token(connection: CalendarConnection, db: Session) -> CalendarConnection:
        """
        Refresh expired Google OAuth token

        Args:
            connection: CalendarConnection object
            db: Database session

        Returns:
            Updated CalendarConnection
        """
        try:
            credentials = Credentials(
                token=connection.access_token,
                refresh_token=connection.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )

            credentials.refresh(Request())

            connection.access_token = credentials.token
            connection.token_expires_at = credentials.expiry
            connection.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(connection)

            logger.info(f"Refreshed Google token for connection {connection.id}")
            return connection

        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")
            raise

    @staticmethod
    def get_google_service(connection: CalendarConnection, db: Session):
        """
        Get authenticated Google Calendar service

        Args:
            connection: CalendarConnection object
            db: Database session

        Returns:
            Google Calendar service object
        """
        # Check if token is expired
        if connection.token_expires_at and connection.token_expires_at < datetime.utcnow():
            connection = CalendarService.refresh_google_token(connection, db)

        credentials = Credentials(
            token=connection.access_token,
            refresh_token=connection.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )

        return build('calendar', 'v3', credentials=credentials)

    @staticmethod
    def extract_meeting_platform(event: Dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extract meeting platform and URL from Google Calendar event

        Args:
            event: Google Calendar event object

        Returns:
            Tuple of (platform, meeting_url)
        """
        # Check for conference data (Google Meet)
        if 'conferenceData' in event:
            entry_points = event['conferenceData'].get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    uri = entry.get('uri')
                    if 'meet.google.com' in uri:
                        return ('google_meet', uri)

        # Check description and location for Zoom/Teams links
        text_to_search = f"{event.get('description', '')} {event.get('location', '')}"

        # Zoom pattern
        zoom_match = re.search(r'https?://[\w-]*\.?zoom\.us/j/[\d\w?=-]+', text_to_search)
        if zoom_match:
            return ('zoom', zoom_match.group(0))

        # Microsoft Teams pattern
        teams_match = re.search(r'https?://teams\.microsoft\.com/[\w\d/\-?=&]+', text_to_search)
        if teams_match:
            return ('teams', teams_match.group(0))

        # Generic meeting link check
        meet_match = re.search(r'https?://meet\.[\w.]+/[\w\d/\-?=&]+', text_to_search)
        if meet_match:
            return ('other', meet_match.group(0))

        return (None, None)

    @staticmethod
    def sync_calendar_events(
        connection: CalendarConnection,
        db: Session,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None
    ) -> List[Meeting]:
        """
        Sync calendar events from Google Calendar and create Meeting records

        Args:
            connection: CalendarConnection object
            db: Database session
            time_min: Start time for events (default: now)
            time_max: End time for events (default: 30 days from now)

        Returns:
            List of created/updated Meeting objects
        """
        try:
            service = CalendarService.get_google_service(connection, db)

            # Default time range: now to 30 days ahead
            if not time_min:
                time_min = datetime.utcnow()
            if not time_max:
                time_max = datetime.utcnow() + timedelta(days=30)

            # Fetch events
            events_result = service.events().list(
                calendarId=connection.calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                syncToken=connection.sync_token if connection.sync_token else None
            ).execute()

            events = events_result.get('items', [])
            new_sync_token = events_result.get('nextSyncToken')

            created_meetings = []

            for event in events:
                # Skip all-day events and events without start time
                if 'dateTime' not in event.get('start', {}):
                    continue

                # Parse event details
                event_id = event['id']
                title = event.get('summary', 'Untitled Meeting')
                description = event.get('description', '')
                start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))

                # Extract meeting platform and URL
                platform, meeting_url = CalendarService.extract_meeting_platform(event)

                # Parse participants
                attendees = event.get('attendees', [])
                participants = json.dumps([
                    {
                        'email': a.get('email'),
                        'name': a.get('displayName', a.get('email')),
                        'status': a.get('responseStatus', 'needsAction')
                    }
                    for a in attendees
                ])

                organizer_email = event.get('organizer', {}).get('email')

                # Check if meeting already exists
                meeting = db.query(Meeting).filter(
                    Meeting.calendar_event_id == event_id,
                    Meeting.user_id == connection.user_id
                ).first()

                if not meeting:
                    # Create new meeting
                    meeting = Meeting(
                        user_id=connection.user_id,
                        calendar_connection_id=connection.id,
                        calendar_event_id=event_id,
                        title=title,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        meeting_url=meeting_url,
                        platform=platform,
                        participants=participants,
                        organizer_email=organizer_email,
                        status='scheduled'
                    )
                    db.add(meeting)
                    created_meetings.append(meeting)
                    logger.info(f"Created meeting: {title} at {start_time}")
                else:
                    # Update existing meeting
                    meeting.title = title
                    meeting.description = description
                    meeting.start_time = start_time
                    meeting.end_time = end_time
                    meeting.meeting_url = meeting_url
                    meeting.platform = platform
                    meeting.participants = participants
                    meeting.organizer_email = organizer_email
                    meeting.updated_at = datetime.utcnow()
                    created_meetings.append(meeting)
                    logger.info(f"Updated meeting: {title} at {start_time}")

            # Update sync token
            if new_sync_token:
                connection.sync_token = new_sync_token
            connection.last_synced_at = datetime.utcnow()

            db.commit()

            logger.info(f"Synced {len(created_meetings)} meetings for user {connection.user_id}")
            return created_meetings

        except HttpError as e:
            logger.error(f"Google API error during sync: {e}")
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Error syncing calendar events: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_upcoming_meetings(
        user_id: str,
        db: Session,
        hours_ahead: int = 24
    ) -> List[Meeting]:
        """
        Get upcoming meetings for a user

        Args:
            user_id: User ID
            db: Database session
            hours_ahead: How many hours ahead to look (default: 24)

        Returns:
            List of upcoming Meeting objects
        """
        now = datetime.utcnow()
        future = now + timedelta(hours=hours_ahead)

        meetings = db.query(Meeting).filter(
            Meeting.user_id == user_id,
            Meeting.start_time >= now,
            Meeting.start_time <= future,
            Meeting.status.in_(['scheduled', 'in_progress'])
        ).order_by(Meeting.start_time).all()

        return meetings

    @staticmethod
    def prepare_meeting_for_recording(meeting: Meeting, db: Session) -> Meeting:
        """
        Prepare a meeting for recording (auto-applied N minutes before start)

        Args:
            meeting: Meeting object
            db: Database session

        Returns:
            Updated Meeting object
        """
        # Apply default template if connection has one
        if meeting.calendar_connection_id and not meeting.template_id:
            connection = db.query(CalendarConnection).get(meeting.calendar_connection_id)
            if connection and connection.default_template_id:
                meeting.template_id = connection.default_template_id

        # Update status
        meeting.recording_status = 'ready'
        meeting.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(meeting)

        logger.info(f"Prepared meeting {meeting.id} for recording")
        return meeting

    @staticmethod
    def disconnect_calendar(connection_id: str, db: Session) -> bool:
        """
        Disconnect a calendar integration

        Args:
            connection_id: CalendarConnection ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            connection = db.query(CalendarConnection).get(connection_id)
            if not connection:
                return False

            connection.is_active = False
            connection.sync_enabled = False
            connection.updated_at = datetime.utcnow()

            db.commit()

            logger.info(f"Disconnected calendar connection {connection_id}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting calendar: {e}")
            db.rollback()
            return False


# Helper function to auto-sync calendars (can be called by background task)
async def auto_sync_all_calendars(db: Session):
    """
    Background task to automatically sync all active calendar connections
    Should be called every CALENDAR_SYNC_INTERVAL_MINUTES
    """
    try:
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.is_active == True,
            CalendarConnection.sync_enabled == True
        ).all()

        for connection in connections:
            try:
                CalendarService.sync_calendar_events(connection, db)
            except Exception as e:
                logger.error(f"Error syncing calendar {connection.id}: {e}")
                continue

        logger.info(f"Auto-synced {len(connections)} calendars")

    except Exception as e:
        logger.error(f"Error in auto_sync_all_calendars: {e}")
