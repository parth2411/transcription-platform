# backend/app/services/apple_calendar_service.py
"""
Apple Calendar Service (iCloud CalDAV)
Handles iCloud calendar sync using CalDAV protocol
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import caldav
from caldav.elements import dav, cdav
from icalendar import Calendar as iCalendar
from sqlalchemy.orm import Session

from ..models import Meeting, CalendarConnection
from ..config import settings

logger = logging.getLogger(__name__)


class AppleCalendarService:
    """Service for Apple iCloud Calendar sync via CalDAV"""

    def __init__(self):
        self.caldav_url = "https://caldav.icloud.com"

    def verify_credentials(self, email: str, app_password: str) -> bool:
        """
        Verify iCloud credentials by attempting to connect

        Args:
            email: iCloud email address
            app_password: App-specific password from iCloud

        Returns:
            True if credentials are valid
        """
        try:
            client = caldav.DAVClient(
                url=self.caldav_url,
                username=email,
                password=app_password
            )

            # Try to access the principal
            principal = client.principal()
            calendars = principal.calendars()

            logger.info(f"Successfully verified iCloud credentials for {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to verify iCloud credentials: {e}")
            return False

    def get_calendars(self, email: str, app_password: str) -> List[Dict]:
        """
        List all calendars for the user

        Args:
            email: iCloud email address
            app_password: App-specific password

        Returns:
            List of calendar objects
        """
        try:
            client = caldav.DAVClient(
                url=self.caldav_url,
                username=email,
                password=app_password
            )

            principal = client.principal()
            calendars = principal.calendars()

            calendar_list = []
            for calendar in calendars:
                try:
                    calendar_list.append({
                        "id": calendar.url,
                        "name": calendar.name or "Unnamed Calendar",
                        "url": str(calendar.url)
                    })
                except Exception as e:
                    logger.warning(f"Error processing calendar: {e}")
                    continue

            logger.info(f"Found {len(calendar_list)} calendars for {email}")
            return calendar_list

        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            raise

    def get_events(
        self,
        email: str,
        app_password: str,
        calendar_url: Optional[str] = None,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fetch calendar events from iCloud Calendar

        Args:
            email: iCloud email address
            app_password: App-specific password
            calendar_url: Specific calendar URL (optional, uses all calendars if not specified)
            time_min: Start time filter
            time_max: End time filter

        Returns:
            List of event objects
        """
        if not time_min:
            time_min = datetime.utcnow()
        if not time_max:
            time_max = time_min + timedelta(days=30)

        try:
            client = caldav.DAVClient(
                url=self.caldav_url,
                username=email,
                password=app_password
            )

            principal = client.principal()

            # Get specific calendar or all calendars
            if calendar_url:
                calendars = [client.calendar(url=calendar_url)]
            else:
                calendars = principal.calendars()

            all_events = []

            for calendar in calendars:
                try:
                    # Search for events in date range
                    events = calendar.date_search(
                        start=time_min,
                        end=time_max,
                        expand=True
                    )

                    for event in events:
                        try:
                            # Parse the iCalendar data
                            ical = iCalendar.from_ical(event.data)

                            for component in ical.walk():
                                if component.name == "VEVENT":
                                    event_data = self._parse_event(component, calendar.name)
                                    if event_data:
                                        all_events.append(event_data)

                        except Exception as e:
                            logger.warning(f"Error parsing event: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Error fetching events from calendar: {e}")
                    continue

            logger.info(f"Fetched {len(all_events)} events from iCloud")
            return all_events

        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            raise

    def _parse_event(self, component, calendar_name: str) -> Optional[Dict]:
        """
        Parse iCalendar VEVENT component into our event format

        Args:
            component: iCalendar VEVENT component
            calendar_name: Name of the calendar

        Returns:
            Parsed event dictionary
        """
        try:
            # Extract basic info
            event_id = str(component.get('uid', ''))
            title = str(component.get('summary', 'Untitled Event'))
            description = str(component.get('description', ''))

            # Parse start and end times
            dtstart = component.get('dtstart')
            dtend = component.get('dtend')

            if not dtstart:
                return None

            start_time = dtstart.dt
            end_time = dtend.dt if dtend else start_time + timedelta(hours=1)

            # Convert date to datetime if needed
            if isinstance(start_time, datetime):
                start_datetime = start_time
            else:
                start_datetime = datetime.combine(start_time, datetime.min.time())

            if isinstance(end_time, datetime):
                end_datetime = end_time
            else:
                end_datetime = datetime.combine(end_time, datetime.min.time())

            # Extract location and URL
            location = str(component.get('location', ''))
            url = str(component.get('url', ''))

            # Try to detect meeting platform from URL or location
            platform = None
            meeting_url = None

            # Check for video conference URLs in description or location
            text_to_check = f"{description} {location} {url}".lower()

            if 'zoom.us' in text_to_check:
                platform = 'Zoom'
                # Try to extract Zoom URL
                if 'zoom.us' in url:
                    meeting_url = url
                elif 'zoom.us' in description:
                    # Simple URL extraction
                    import re
                    zoom_match = re.search(r'https://[^\s]*zoom\.us[^\s]*', description)
                    if zoom_match:
                        meeting_url = zoom_match.group(0)

            elif 'teams.microsoft.com' in text_to_check:
                platform = 'Microsoft Teams'
                if 'teams.microsoft.com' in url:
                    meeting_url = url
                elif 'teams.microsoft.com' in description:
                    import re
                    teams_match = re.search(r'https://[^\s]*teams\.microsoft\.com[^\s]*', description)
                    if teams_match:
                        meeting_url = teams_match.group(0)

            elif 'meet.google.com' in text_to_check:
                platform = 'Google Meet'
                if 'meet.google.com' in url:
                    meeting_url = url
                elif 'meet.google.com' in description:
                    import re
                    meet_match = re.search(r'https://meet\.google\.com/[^\s]*', description)
                    if meet_match:
                        meeting_url = meet_match.group(0)

            # Extract attendees
            attendees = component.get('attendee', [])
            if not isinstance(attendees, list):
                attendees = [attendees]

            participants_list = []
            for attendee in attendees:
                if hasattr(attendee, 'params') and 'CN' in attendee.params:
                    participants_list.append(attendee.params['CN'])

            participants = ','.join(participants_list) if participants_list else None

            # Get organizer
            organizer = component.get('organizer')
            organizer_email = None
            if organizer:
                if hasattr(organizer, 'params') and 'CN' in organizer.params:
                    organizer_email = organizer.params['CN']

            return {
                'id': event_id,
                'title': title,
                'description': description,
                'start': start_datetime,
                'end': end_datetime,
                'location': location,
                'meeting_url': meeting_url,
                'platform': platform,
                'participants': participants,
                'organizer_email': organizer_email,
                'calendar_name': calendar_name
            }

        except Exception as e:
            logger.error(f"Error parsing event component: {e}")
            return None

    def sync_calendar_events(
        self,
        db: Session,
        calendar_connection: CalendarConnection,
        user_id: str
    ) -> int:
        """
        Sync events from iCloud Calendar to database

        Args:
            db: Database session
            calendar_connection: CalendarConnection record
            user_id: User ID

        Returns:
            Number of events synced
        """
        try:
            # Get the stored credentials
            # Email is stored in sync_token as JSON metadata
            import json
            metadata = json.loads(calendar_connection.sync_token) if calendar_connection.sync_token else {}
            email = metadata.get("email")

            if not email:
                raise ValueError("Email not found in calendar connection metadata")

            app_password = calendar_connection.access_token  # We store app password as access_token
            calendar_url = calendar_connection.calendar_id if calendar_connection.calendar_id != "all" else None

            # Get events from iCloud
            events = self.get_events(
                email=email,
                app_password=app_password,
                calendar_url=calendar_url,
                time_min=datetime.utcnow() - timedelta(days=7),  # Past week
                time_max=datetime.utcnow() + timedelta(days=90)  # Next 3 months
            )

            synced_count = 0

            for event in events:
                # Check if meeting already exists
                existing_meeting = db.query(Meeting).filter(
                    Meeting.calendar_event_id == event['id'],
                    Meeting.user_id == user_id
                ).first()

                if existing_meeting:
                    # Update existing meeting
                    existing_meeting.title = event['title']
                    existing_meeting.description = event['description']
                    existing_meeting.start_time = event['start']
                    existing_meeting.end_time = event['end']
                    existing_meeting.meeting_url = event['meeting_url']
                    existing_meeting.platform = event['platform']
                    existing_meeting.participants = event['participants']
                    existing_meeting.organizer_email = event['organizer_email']
                else:
                    # Create new meeting
                    new_meeting = Meeting(
                        user_id=user_id,
                        calendar_connection_id=calendar_connection.id,
                        calendar_event_id=event['id'],
                        title=event['title'],
                        description=event['description'],
                        start_time=event['start'],
                        end_time=event['end'],
                        timezone="UTC",
                        meeting_url=event['meeting_url'],
                        platform=event['platform'],
                        participants=event['participants'],
                        organizer_email=event['organizer_email'],
                        status="scheduled",
                        recording_status="not_started"
                    )
                    db.add(new_meeting)

                synced_count += 1

            # Update last synced time
            calendar_connection.last_synced_at = datetime.utcnow()
            db.commit()

            logger.info(f"Synced {synced_count} events from iCloud Calendar")
            return synced_count

        except Exception as e:
            logger.error(f"Error syncing iCloud calendar: {e}")
            db.rollback()
            raise
