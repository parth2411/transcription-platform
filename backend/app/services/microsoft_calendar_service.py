# backend/app/services/microsoft_calendar_service.py
"""
Microsoft Calendar Service
Handles Microsoft OAuth and calendar sync for Outlook/Office 365
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import msal
from sqlalchemy.orm import Session

from ..models import Meeting, CalendarConnection
from ..config import settings

logger = logging.getLogger(__name__)


class MicrosoftCalendarService:
    """Service for Microsoft Calendar OAuth and sync"""

    def __init__(self):
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.redirect_uri = settings.MICROSOFT_REDIRECT_URI
        self.tenant_id = settings.MICROSOFT_TENANT_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Microsoft Graph API scopes
        # Note: offline_access is handled automatically by MSAL
        self.scopes = [
            "Calendars.Read",
            "User.Read"
        ]

    def get_auth_url(self, state: str) -> str:
        """
        Generate Microsoft OAuth authorization URL

        Args:
            state: State parameter for security

        Returns:
            Authorization URL for user to visit
        """
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

        auth_url = app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri
        )

        logger.info(f"Generated Microsoft auth URL with state: {state}")
        return auth_url

    def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from callback

        Returns:
            Token data including access_token and refresh_token
        """
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

        result = app.acquire_token_by_authorization_code(
            code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

        if "error" in result:
            logger.error(f"Microsoft token exchange error: {result.get('error_description')}")
            raise Exception(f"Token exchange failed: {result.get('error_description')}")

        logger.info("Successfully exchanged code for Microsoft token")
        return result

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token from database

        Returns:
            New token data
        """
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

        result = app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=self.scopes
        )

        if "error" in result:
            logger.error(f"Microsoft token refresh error: {result.get('error_description')}")
            raise Exception(f"Token refresh failed: {result.get('error_description')}")

        return result

    def get_user_info(self, access_token: str) -> Dict:
        """
        Get user profile information from Microsoft Graph

        Args:
            access_token: Valid access token

        Returns:
            User profile data
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def list_calendars(self, access_token: str) -> List[Dict]:
        """
        List all calendars for the user

        Args:
            access_token: Valid access token

        Returns:
            List of calendar objects
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/calendars",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data.get("value", [])

    def get_events(
        self,
        access_token: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Fetch calendar events from Microsoft Calendar

        Args:
            access_token: Valid access token
            calendar_id: Calendar ID or 'primary' for default
            time_min: Start time filter
            time_max: End time filter
            max_results: Maximum number of events to return

        Returns:
            List of event objects
        """
        if not time_min:
            time_min = datetime.utcnow()
        if not time_max:
            time_max = time_min + timedelta(days=30)

        headers = {"Authorization": f"Bearer {access_token}"}

        # Use primary calendar if calendar_id is 'primary'
        calendar_path = f"/me/calendar" if calendar_id == "primary" else f"/me/calendars/{calendar_id}"

        params = {
            "$filter": f"start/dateTime ge '{time_min.isoformat()}' and end/dateTime le '{time_max.isoformat()}'",
            "$top": max_results,
            "$orderby": "start/dateTime"
        }

        response = requests.get(
            f"https://graph.microsoft.com/v1.0{calendar_path}/events",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        data = response.json()
        return data.get("value", [])

    def sync_calendar_events(
        self,
        db: Session,
        calendar_connection: CalendarConnection,
        user_id: str
    ) -> int:
        """
        Sync events from Microsoft Calendar to database

        Args:
            db: Database session
            calendar_connection: CalendarConnection record
            user_id: User ID

        Returns:
            Number of events synced
        """
        try:
            # Get events from Microsoft Calendar
            events = self.get_events(
                access_token=calendar_connection.access_token,
                calendar_id=calendar_connection.calendar_id,
                time_min=datetime.utcnow() - timedelta(days=7),  # Past week
                time_max=datetime.utcnow() + timedelta(days=90)  # Next 3 months
            )

            synced_count = 0

            for event in events:
                # Extract event details
                event_id = event.get("id")
                title = event.get("subject", "Untitled Meeting")
                description = event.get("bodyPreview", "")

                # Parse start and end times
                start = event.get("start", {})
                end = event.get("end", {})

                start_time = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
                timezone_str = start.get("timeZone", "UTC")

                # Extract meeting details
                meeting_url = None
                platform = None

                # Check for online meeting info
                if event.get("isOnlineMeeting"):
                    meeting_url = event.get("onlineMeeting", {}).get("joinUrl")
                    provider = event.get("onlineMeetingProvider", "").lower()
                    if "teams" in provider:
                        platform = "Microsoft Teams"
                    elif "zoom" in provider:
                        platform = "Zoom"
                    elif "webex" in provider:
                        platform = "Webex"

                # If no platform detected but has URL, try to detect from URL
                if not platform and meeting_url:
                    url_lower = meeting_url.lower()
                    if "teams" in url_lower:
                        platform = "Microsoft Teams"
                    elif "zoom" in url_lower:
                        platform = "Zoom"
                    elif "meet.google" in url_lower:
                        platform = "Google Meet"

                # Extract participants
                attendees = event.get("attendees", [])
                participants_list = [
                    attendee.get("emailAddress", {}).get("address", "")
                    for attendee in attendees
                    if attendee.get("emailAddress", {}).get("address")
                ]
                participants = ",".join(participants_list) if participants_list else None

                organizer_email = event.get("organizer", {}).get("emailAddress", {}).get("address")

                # Check if meeting already exists
                existing_meeting = db.query(Meeting).filter(
                    Meeting.calendar_event_id == event_id,
                    Meeting.user_id == user_id
                ).first()

                if existing_meeting:
                    # Update existing meeting
                    existing_meeting.title = title
                    existing_meeting.description = description
                    existing_meeting.start_time = start_time
                    existing_meeting.end_time = end_time
                    existing_meeting.timezone = timezone_str
                    existing_meeting.meeting_url = meeting_url
                    existing_meeting.platform = platform
                    existing_meeting.participants = participants
                    existing_meeting.organizer_email = organizer_email
                else:
                    # Create new meeting
                    new_meeting = Meeting(
                        user_id=user_id,
                        calendar_connection_id=calendar_connection.id,
                        calendar_event_id=event_id,
                        title=title,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        timezone=timezone_str,
                        meeting_url=meeting_url,
                        platform=platform,
                        participants=participants,
                        organizer_email=organizer_email,
                        status="scheduled",
                        recording_status="not_started"
                    )
                    db.add(new_meeting)

                synced_count += 1

            # Update last synced time
            calendar_connection.last_synced_at = datetime.utcnow()
            db.commit()

            logger.info(f"Synced {synced_count} events from Microsoft Calendar")
            return synced_count

        except Exception as e:
            logger.error(f"Error syncing Microsoft calendar: {e}")
            db.rollback()
            raise
