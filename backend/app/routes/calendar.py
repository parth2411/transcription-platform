# backend/app/routes/calendar.py
"""
Calendar OAuth Integration Routes
Handles Google Calendar authentication and synchronization
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, CalendarConnection, Meeting
from ..services.auth_service import get_current_user
from ..services.calendar_service import CalendarService
from ..services.microsoft_calendar_service import MicrosoftCalendarService
from ..services.apple_calendar_service import AppleCalendarService
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
google_calendar_service = CalendarService()
microsoft_calendar_service = MicrosoftCalendarService()
apple_calendar_service = AppleCalendarService()

# Pydantic models for request/response
class CalendarConnectionResponse(BaseModel):
    id: str
    provider: str
    calendar_name: str
    is_active: bool
    sync_enabled: bool
    auto_record_meetings: bool
    last_synced_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class OAuthInitResponse(BaseModel):
    auth_url: str
    provider: str
    message: str

class SyncResponse(BaseModel):
    success: bool
    meetings_synced: int
    last_sync: Optional[str]

class UpcomingMeetingsResponse(BaseModel):
    id: str
    title: str
    start_time: str
    end_time: str
    platform: Optional[str]
    meeting_url: Optional[str]
    status: str
    recording_status: str

    class Config:
        from_attributes = True


# ==========================================
# OAUTH FLOW ENDPOINTS
# ==========================================

@router.post("/google/auth", response_model=OAuthInitResponse)
async def initiate_google_calendar_auth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Initiate Google Calendar OAuth flow

    Returns OAuth URL that user should be redirected to.
    User will authorize on Google's website, then be redirected back.

    Example:
        POST /api/calendar/google/auth
        Response: { "auth_url": "https://accounts.google.com/...", ... }
    """
    try:
        # Generate state token for security (includes user_id)
        state = f"{current_user.id}"

        # Get OAuth URL
        auth_url = CalendarService.get_google_oauth_url(state=state)

        logger.info(f"Generated Google OAuth URL for user {current_user.id}")

        return OAuthInitResponse(
            auth_url=auth_url,
            provider="google",
            message="Redirect user to this URL to authorize Google Calendar access"
        )

    except Exception as e:
        logger.error(f"Error generating Google OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.get("/google/callback")
async def google_calendar_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for security"),
    error: Optional[str] = Query(None, description="Error from Google"),
    db: Session = Depends(get_db)
):
    """
    Step 2: OAuth callback endpoint

    Google redirects here after user authorizes.
    This endpoint is called automatically - user doesn't interact with it.

    Exchanges authorization code for access tokens and saves connection.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/calendar?error=oauth_failed&message={error}",
            status_code=302
        )

    try:
        # Extract user_id from state
        user_id = state

        # Exchange code for tokens and create connection
        connection = CalendarService.exchange_google_code(
            code=code,
            db=db,
            user_id=user_id
        )

        # Initial sync of calendar events
        try:
            CalendarService.sync_calendar_events(connection, db)
        except Exception as sync_error:
            logger.warning(f"Initial sync failed but connection created: {sync_error}")

        logger.info(f"Successfully connected Google Calendar for user {user_id}")

        # Redirect to success page
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/settings/calendar?success=true&provider=google",
            status_code=302
        )

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/settings/calendar?error=true&message=connection_failed",
            status_code=302
        )


# ==========================================
# MICROSOFT OAUTH FLOW ENDPOINTS
# ==========================================

@router.post("/microsoft/auth", response_model=OAuthInitResponse)
async def initiate_microsoft_calendar_auth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Initiate Microsoft Calendar OAuth flow

    Returns OAuth URL that user should be redirected to.
    User will authorize on Microsoft's website, then be redirected back.

    Example:
        POST /api/calendar/microsoft/auth
        Response: { "auth_url": "https://login.microsoftonline.com/...", ... }
    """
    try:
        # Generate state token for security (includes user_id)
        state = f"{current_user.id}"

        # Get OAuth URL
        auth_url = microsoft_calendar_service.get_auth_url(state=state)

        logger.info(f"Generated Microsoft OAuth URL for user {current_user.id}")

        return OAuthInitResponse(
            auth_url=auth_url,
            provider="microsoft",
            message="Redirect user to this URL to authorize Microsoft Calendar access"
        )

    except Exception as e:
        logger.error(f"Error generating Microsoft OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.get("/microsoft/callback")
async def microsoft_calendar_callback(
    code: str = Query(..., description="Authorization code from Microsoft"),
    state: str = Query(..., description="State token for security"),
    error: Optional[str] = Query(None, description="Error from Microsoft"),
    db: Session = Depends(get_db)
):
    """
    Step 2: OAuth callback endpoint for Microsoft

    Microsoft redirects here after user authorizes.
    This endpoint is called automatically - user doesn't interact with it.

    Exchanges authorization code for access tokens and saves connection.
    """
    # Handle OAuth errors
    if error:
        logger.error(f"Microsoft OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/calendar?error=oauth_failed&message={error}",
            status_code=302
        )

    try:
        # Extract user_id from state
        user_id = state

        # Exchange code for tokens
        token_data = microsoft_calendar_service.exchange_code_for_token(code)

        # Get user info
        user_info = microsoft_calendar_service.get_user_info(token_data["access_token"])

        # Get calendars
        calendars = microsoft_calendar_service.list_calendars(token_data["access_token"])
        primary_calendar = calendars[0] if calendars else None

        # Create or update calendar connection
        connection = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == user_id,
            CalendarConnection.provider == "microsoft"
        ).first()

        if connection:
            # Update existing connection
            connection.access_token = token_data["access_token"]
            connection.refresh_token = token_data.get("refresh_token")
            connection.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
            connection.is_active = True
        else:
            # Create new connection
            connection = CalendarConnection(
                user_id=user_id,
                provider="microsoft",
                calendar_id=primary_calendar.get("id") if primary_calendar else "primary",
                calendar_name=primary_calendar.get("name", "Primary") if primary_calendar else "Primary",
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
                is_active=True,
                sync_enabled=True,
                auto_record_meetings=False
            )
            db.add(connection)

        db.commit()
        db.refresh(connection)

        # Initial sync of calendar events
        try:
            microsoft_calendar_service.sync_calendar_events(db, connection, user_id)
        except Exception as sync_error:
            logger.warning(f"Initial sync failed but connection created: {sync_error}")

        logger.info(f"Successfully connected Microsoft Calendar for user {user_id}")

        # Redirect to success page
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/settings/calendar?success=true&provider=microsoft",
            status_code=302
        )

    except Exception as e:
        logger.error(f"Microsoft OAuth callback error: {e}")
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/settings/calendar?error=true&message=connection_failed",
            status_code=302
        )


# ==========================================
# APPLE CALENDAR (iCloud) - CalDAV
# ==========================================

class AppleCalendarSetupRequest(BaseModel):
    email: str
    app_password: str
    calendar_id: Optional[str] = "all"  # "all" or specific calendar URL

@router.post("/apple/setup")
async def setup_apple_calendar(
    setup_data: AppleCalendarSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Setup Apple iCloud Calendar connection using CalDAV

    User must provide:
    - iCloud email
    - App-specific password (generated from appleid.apple.com)

    Steps for users:
    1. Go to https://appleid.apple.com
    2. Sign in → Security → App-Specific Passwords
    3. Generate password for "TranscribeAI"
    4. Enter email and password here
    """
    try:
        # Verify credentials
        is_valid = apple_calendar_service.verify_credentials(
            email=setup_data.email,
            app_password=setup_data.app_password
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid iCloud credentials. Please check your email and app-specific password."
            )

        # Get list of calendars
        calendars = apple_calendar_service.get_calendars(
            email=setup_data.email,
            app_password=setup_data.app_password
        )

        # Determine calendar name (include email for Apple)
        import json as json_lib
        calendar_name = f"{setup_data.email} - All Calendars"
        if setup_data.calendar_id and setup_data.calendar_id != "all":
            matching_cal = next((c for c in calendars if c["url"] == setup_data.calendar_id), None)
            if matching_cal:
                calendar_name = f"{setup_data.email} - {matching_cal['name']}"

        # Check if connection already exists
        existing_connection = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == current_user.id,
            CalendarConnection.provider == "apple"
        ).first()

        if existing_connection:
            # Update existing connection
            # Store email in sync_token as JSON metadata
            existing_connection.sync_token = json_lib.dumps({"email": setup_data.email})
            existing_connection.access_token = setup_data.app_password  # Store app password securely
            existing_connection.calendar_id = setup_data.calendar_id
            existing_connection.calendar_name = calendar_name
            existing_connection.is_active = True
            existing_connection.sync_enabled = True
            connection = existing_connection
        else:
            # Create new connection
            # Store email in sync_token as JSON metadata
            connection = CalendarConnection(
                user_id=current_user.id,
                provider="apple",
                access_token=setup_data.app_password,  # Store app password
                calendar_id=setup_data.calendar_id,
                calendar_name=calendar_name,
                sync_token=json_lib.dumps({"email": setup_data.email}),
                is_active=True,
                sync_enabled=True
            )
            db.add(connection)

        db.commit()
        db.refresh(connection)

        # Initial sync
        try:
            synced_count = apple_calendar_service.sync_calendar_events(
                db=db,
                calendar_connection=connection,
                user_id=str(current_user.id)
            )
            logger.info(f"Initial sync completed: {synced_count} events")
        except Exception as sync_error:
            logger.warning(f"Initial sync failed: {sync_error}")

        logger.info(f"Apple Calendar connected for user {current_user.id}")

        return {
            "success": True,
            "connection_id": str(connection.id),
            "calendar_name": calendar_name,
            "calendars": calendars,
            "message": "Apple Calendar connected successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up Apple Calendar: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup Apple Calendar: {str(e)}"
        )


@router.get("/apple/calendars")
async def list_apple_calendars(
    email: str = Query(...),
    app_password: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    """
    List all available iCloud calendars for the user

    Used to let user choose which calendar to sync
    """
    try:
        # Verify credentials first
        is_valid = apple_calendar_service.verify_credentials(
            email=email,
            app_password=app_password
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Get calendars
        calendars = apple_calendar_service.get_calendars(
            email=email,
            app_password=app_password
        )

        return {
            "success": True,
            "calendars": calendars
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Apple calendars: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list calendars: {str(e)}"
        )


# ==========================================
# CALENDAR CONNECTION MANAGEMENT
# ==========================================

@router.get("/connections", response_model=List[CalendarConnectionResponse])
async def list_calendar_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all calendar connections for current user

    Returns list of connected calendars (Google, Microsoft, Apple)
    """
    try:
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == current_user.id
        ).order_by(CalendarConnection.created_at.desc()).all()

        return [
            CalendarConnectionResponse(
                id=str(conn.id),
                provider=conn.provider,
                calendar_name=conn.calendar_name or f"{conn.provider.title()} Calendar",
                is_active=conn.is_active,
                sync_enabled=conn.sync_enabled,
                auto_record_meetings=conn.auto_record_meetings,
                last_synced_at=conn.last_synced_at.isoformat() if conn.last_synced_at else None,
                created_at=conn.created_at.isoformat()
            )
            for conn in connections
        ]

    except Exception as e:
        logger.error(f"Error listing calendar connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar connections"
        )


@router.get("/connections/{connection_id}", response_model=CalendarConnectionResponse)
async def get_calendar_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific calendar connection
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar connection not found"
        )

    return CalendarConnectionResponse(
        id=str(connection.id),
        provider=connection.provider,
        calendar_name=connection.calendar_name or f"{connection.provider.title()} Calendar",
        is_active=connection.is_active,
        sync_enabled=connection.sync_enabled,
        auto_record_meetings=connection.auto_record_meetings,
        last_synced_at=connection.last_synced_at.isoformat() if connection.last_synced_at else None,
        created_at=connection.created_at.isoformat()
    )


@router.patch("/connections/{connection_id}")
async def update_calendar_connection(
    connection_id: str,
    sync_enabled: Optional[bool] = None,
    auto_record_meetings: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update calendar connection settings

    Body:
        - sync_enabled: Enable/disable automatic syncing
        - auto_record_meetings: Auto-start recording for calendar meetings
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar connection not found"
        )

    if sync_enabled is not None:
        connection.sync_enabled = sync_enabled

    if auto_record_meetings is not None:
        connection.auto_record_meetings = auto_record_meetings

    connection.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(connection)

    return {
        "success": True,
        "message": "Connection settings updated",
        "connection": CalendarConnectionResponse(
            id=str(connection.id),
            provider=connection.provider,
            calendar_name=connection.calendar_name,
            is_active=connection.is_active,
            sync_enabled=connection.sync_enabled,
            auto_record_meetings=connection.auto_record_meetings,
            last_synced_at=connection.last_synced_at.isoformat() if connection.last_synced_at else None,
            created_at=connection.created_at.isoformat()
        )
    }


@router.delete("/connections/{connection_id}")
async def disconnect_calendar(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a calendar

    This doesn't delete the connection but deactivates it.
    Existing meetings remain but no new events will be synced.
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar connection not found"
        )

    success = CalendarService.disconnect_calendar(connection_id, db)

    if success:
        return {
            "success": True,
            "message": f"{connection.provider.title()} calendar disconnected successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect calendar"
        )


# ==========================================
# CALENDAR SYNC OPERATIONS
# ==========================================

@router.post("/sync", response_model=SyncResponse)
async def sync_all_calendars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger sync for all active calendar connections

    This syncs all connected calendars and creates/updates meeting records.
    """
    try:
        connections = db.query(CalendarConnection).filter(
            CalendarConnection.user_id == current_user.id,
            CalendarConnection.is_active == True,
            CalendarConnection.sync_enabled == True
        ).all()

        if not connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active calendar connections found"
            )

        total_meetings = 0

        for connection in connections:
            try:
                meetings = CalendarService.sync_calendar_events(connection, db)
                total_meetings += len(meetings)
            except Exception as e:
                logger.error(f"Error syncing calendar {connection.id}: {e}")
                continue

        last_sync = max(
            (c.last_synced_at for c in connections if c.last_synced_at),
            default=None
        )

        return SyncResponse(
            success=True,
            meetings_synced=total_meetings,
            last_sync=last_sync.isoformat() if last_sync else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing calendars: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync calendars"
        )


@router.post("/sync/{connection_id}", response_model=SyncResponse)
async def sync_specific_calendar(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger sync for a specific calendar connection
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar connection not found"
        )

    if not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calendar connection is not active"
        )

    try:
        # Use appropriate service based on provider
        if connection.provider == "google":
            meetings = CalendarService.sync_calendar_events(connection, db)
            synced_count = len(meetings)
        elif connection.provider == "microsoft":
            synced_count = microsoft_calendar_service.sync_calendar_events(
                db=db,
                calendar_connection=connection,
                user_id=str(current_user.id)
            )
        elif connection.provider == "apple":
            synced_count = apple_calendar_service.sync_calendar_events(
                db=db,
                calendar_connection=connection,
                user_id=str(current_user.id)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported calendar provider: {connection.provider}"
            )

        return SyncResponse(
            success=True,
            meetings_synced=synced_count,
            last_sync=connection.last_synced_at.isoformat() if connection.last_synced_at else None
        )

    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync calendar: {str(e)}"
        )


# ==========================================
# UPCOMING MEETINGS
# ==========================================

@router.get("/upcoming", response_model=List[UpcomingMeetingsResponse])
async def get_upcoming_meetings(
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours to look ahead (1-168)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upcoming meetings from synced calendars

    Query params:
        - hours_ahead: How many hours ahead to look (default: 24, max: 168 = 1 week)

    Returns meetings sorted by start time.
    """
    try:
        meetings = CalendarService.get_upcoming_meetings(
            user_id=str(current_user.id),
            db=db,
            hours_ahead=hours_ahead
        )

        return [
            UpcomingMeetingsResponse(
                id=str(meeting.id),
                title=meeting.title,
                start_time=meeting.start_time.isoformat(),
                end_time=meeting.end_time.isoformat(),
                platform=meeting.platform,
                meeting_url=meeting.meeting_url,
                status=meeting.status,
                recording_status=meeting.recording_status
            )
            for meeting in meetings
        ]

    except Exception as e:
        logger.error(f"Error fetching upcoming meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch upcoming meetings"
        )


@router.post("/meetings/{meeting_id}/prepare")
async def prepare_meeting_for_recording(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Prepare a calendar meeting for recording

    This applies default template, sets up recording settings, etc.
    Usually called automatically 15 minutes before meeting starts.
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    try:
        prepared_meeting = CalendarService.prepare_meeting_for_recording(meeting, db)

        return {
            "success": True,
            "message": "Meeting prepared for recording",
            "meeting_id": str(prepared_meeting.id),
            "recording_status": prepared_meeting.recording_status
        }

    except Exception as e:
        logger.error(f"Error preparing meeting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare meeting"
        )
