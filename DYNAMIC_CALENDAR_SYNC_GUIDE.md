# Dynamic Multi-Calendar OAuth Integration Guide
## Secure, User-Friendly Calendar Sync for All Platforms

**Key Principle:** Users never enter passwords. They click "Connect Calendar" → Authorize on provider's website → Done! ✅

---

## 🔐 How OAuth Calendar Sync Works (No Credentials Needed!)

### User Experience Flow:

```
User clicks "Connect Google Calendar"
    ↓
Redirected to Google's authorization page
    ↓
User clicks "Allow" on Google's page (Google handles authentication)
    ↓
Redirected back to your app with authorization code
    ↓
Your app exchanges code for access token (happens in backend)
    ↓
Calendar synced! No passwords ever stored! ✅
```

**This is exactly how "Sign in with Google/Apple/Microsoft" works - industry standard!**

---

## 🎯 Smart Platform Detection

### Detect User's Operating System & Suggest Calendar

```typescript
// frontend/src/utils/platform-detection.ts
export function detectUserPlatform() {
  const userAgent = window.navigator.userAgent;
  const platform = window.navigator.platform;

  // Detect macOS/iOS (Apple users)
  if (/Mac|iPhone|iPad|iPod/.test(platform) || /Mac OS X/.test(userAgent)) {
    return {
      os: 'apple',
      suggestedCalendars: ['icloud', 'google', 'microsoft'],
      primarySuggestion: 'icloud'
    };
  }

  // Detect Windows
  if (/Win/.test(platform)) {
    return {
      os: 'windows',
      suggestedCalendars: ['microsoft', 'google'],
      primarySuggestion: 'microsoft'
    };
  }

  // Detect Android
  if (/Android/.test(userAgent)) {
    return {
      os: 'android',
      suggestedCalendars: ['google'],
      primarySuggestion: 'google'
    };
  }

  // Default
  return {
    os: 'other',
    suggestedCalendars: ['google', 'microsoft', 'icloud'],
    primarySuggestion: 'google'
  };
}
```

---

## 🔗 Multi-Provider OAuth Implementation

### Backend: Universal Calendar Service

Let me update the calendar service to support all providers:

```python
# backend/app/services/calendar_service_multi.py

class UniversalCalendarService:
    """
    Unified service for Google, Microsoft, and Apple calendar integration
    """

    PROVIDERS = {
        'google': {
            'name': 'Google Calendar',
            'scopes': [
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events.readonly'
            ],
            'auth_url': 'https://accounts.google.com/o/oauth2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'api_base': 'https://www.googleapis.com/calendar/v3'
        },
        'microsoft': {
            'name': 'Outlook Calendar',
            'scopes': [
                'Calendars.Read',
                'Calendars.Read.Shared'
            ],
            'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            'api_base': 'https://graph.microsoft.com/v1.0'
        },
        'icloud': {
            'name': 'iCloud Calendar',
            'scopes': ['calendar'],
            'auth_url': 'https://appleid.apple.com/auth/authorize',
            'token_url': 'https://appleid.apple.com/auth/token',
            'api_base': 'https://caldav.icloud.com'  # CalDAV
        }
    }

    @staticmethod
    def get_oauth_url(provider: str, user_id: str, state: str = None):
        """
        Generate OAuth URL for any calendar provider

        Args:
            provider: 'google', 'microsoft', or 'icloud'
            user_id: User ID (included in state)
            state: Security state token

        Returns:
            Authorization URL
        """
        if provider not in UniversalCalendarService.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        config = UniversalCalendarService.PROVIDERS[provider]

        if not state:
            state = f"{user_id}:{secrets.token_urlsafe(32)}"

        if provider == 'google':
            return UniversalCalendarService._google_oauth_url(state)
        elif provider == 'microsoft':
            return UniversalCalendarService._microsoft_oauth_url(state)
        elif provider == 'icloud':
            return UniversalCalendarService._apple_oauth_url(state)

    @staticmethod
    def _google_oauth_url(state: str) -> str:
        """Generate Google OAuth URL"""
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
            scopes=UniversalCalendarService.PROVIDERS['google']['scopes'],
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )

        return authorization_url

    @staticmethod
    def _microsoft_oauth_url(state: str) -> str:
        """Generate Microsoft OAuth URL"""
        params = {
            'client_id': settings.MICROSOFT_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.MICROSOFT_REDIRECT_URI,
            'scope': ' '.join(UniversalCalendarService.PROVIDERS['microsoft']['scopes']),
            'state': state,
            'response_mode': 'query'
        }

        return f"{UniversalCalendarService.PROVIDERS['microsoft']['auth_url']}?{urlencode(params)}"

    @staticmethod
    def _apple_oauth_url(state: str) -> str:
        """Generate Apple Sign In OAuth URL"""
        params = {
            'client_id': settings.APPLE_CLIENT_ID,
            'redirect_uri': settings.APPLE_REDIRECT_URI,
            'response_type': 'code',
            'state': state,
            'scope': 'email name',
            'response_mode': 'form_post'
        }

        return f"{UniversalCalendarService.PROVIDERS['icloud']['auth_url']}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(
        provider: str,
        code: str,
        db: Session,
        user_id: str
    ) -> CalendarConnection:
        """
        Exchange authorization code for tokens (any provider)
        """
        if provider == 'google':
            return await UniversalCalendarService._exchange_google_code(code, db, user_id)
        elif provider == 'microsoft':
            return await UniversalCalendarService._exchange_microsoft_code(code, db, user_id)
        elif provider == 'icloud':
            return await UniversalCalendarService._exchange_apple_code(code, db, user_id)

    @staticmethod
    async def sync_events(connection: CalendarConnection, db: Session):
        """
        Sync calendar events (universal method)
        """
        if connection.provider == 'google':
            return await UniversalCalendarService._sync_google_events(connection, db)
        elif connection.provider == 'microsoft':
            return await UniversalCalendarService._sync_microsoft_events(connection, db)
        elif connection.provider == 'icloud':
            return await UniversalCalendarService._sync_apple_events(connection, db)
```

---

## 🎨 Frontend: Dynamic Calendar Connection UI

### Calendar Settings Page with Smart Detection

```tsx
// frontend/src/app/settings/calendar/page.tsx

'use client';

import { useState, useEffect } from 'react';
import { detectUserPlatform } from '@/utils/platform-detection';

export default function CalendarSettingsPage() {
  const [platform, setPlatform] = useState(null);
  const [connections, setConnections] = useState([]);

  useEffect(() => {
    const detected = detectUserPlatform();
    setPlatform(detected);
    loadConnections();
  }, []);

  const handleConnectCalendar = async (provider: string) => {
    // Call backend to get OAuth URL
    const response = await fetch(`/api/calendar/${provider}/auth`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const { auth_url } = await response.json();

    // Redirect user to provider's OAuth page
    // They authorize there (no credentials in your app!)
    window.location.href = auth_url;
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Calendar Connections</h1>

      {/* Smart Suggestion Based on OS */}
      {platform && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-blue-900 mb-2">
            📱 We detected you're using {platform.os === 'apple' ? 'macOS/iOS' : platform.os}
          </h3>
          <p className="text-blue-700 mb-3">
            We recommend connecting your {
              platform.os === 'apple' ? 'iCloud Calendar' :
              platform.os === 'windows' ? 'Outlook Calendar' :
              'Google Calendar'
            } for the best experience.
          </p>
        </div>
      )}

      {/* Calendar Provider Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">

        {/* Google Calendar */}
        <CalendarProviderCard
          provider="google"
          name="Google Calendar"
          icon="🇬"
          description="Gmail, Google Workspace"
          connected={connections.some(c => c.provider === 'google')}
          isPrimary={platform?.primarySuggestion === 'google'}
          onConnect={() => handleConnectCalendar('google')}
          onDisconnect={() => handleDisconnect('google')}
        />

        {/* Microsoft Outlook */}
        <CalendarProviderCard
          provider="microsoft"
          name="Outlook Calendar"
          icon="📧"
          description="Outlook, Microsoft 365"
          connected={connections.some(c => c.provider === 'microsoft')}
          isPrimary={platform?.primarySuggestion === 'microsoft'}
          onConnect={() => handleConnectCalendar('microsoft')}
          onDisconnect={() => handleDisconnect('microsoft')}
        />

        {/* Apple iCloud */}
        <CalendarProviderCard
          provider="icloud"
          name="iCloud Calendar"
          icon="🍎"
          description="Apple Calendar, iCloud"
          connected={connections.some(c => c.provider === 'icloud')}
          isPrimary={platform?.primarySuggestion === 'icloud'}
          onConnect={() => handleConnectCalendar('icloud')}
          onDisconnect={() => handleDisconnect('icloud')}
        />

      </div>

      {/* Connected Calendars List */}
      {connections.length > 0 && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Connected Calendars</h2>
          {connections.map(conn => (
            <ConnectedCalendarItem
              key={conn.id}
              connection={conn}
              onSync={() => handleSync(conn.id)}
              onDisconnect={() => handleDisconnect(conn.provider)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Calendar Provider Card Component
function CalendarProviderCard({
  provider, name, icon, description, connected, isPrimary, onConnect, onDisconnect
}) {
  return (
    <div className={`
      border rounded-lg p-6 hover:shadow-lg transition-shadow
      ${isPrimary ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}
    `}>
      <div className="text-4xl mb-3">{icon}</div>

      {isPrimary && (
        <span className="inline-block bg-blue-500 text-white text-xs px-2 py-1 rounded mb-2">
          Recommended for you
        </span>
      )}

      <h3 className="font-semibold text-lg mb-1">{name}</h3>
      <p className="text-sm text-gray-600 mb-4">{description}</p>

      {!connected ? (
        <button
          onClick={onConnect}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
        >
          Connect {name}
        </button>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center text-green-600 text-sm">
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
            </svg>
            Connected
          </div>
          <button
            onClick={onDisconnect}
            className="w-full bg-gray-200 text-gray-700 py-2 px-4 rounded hover:bg-gray-300 transition text-sm"
          >
            Disconnect
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 🔄 API Endpoints for Multi-Provider OAuth

### Backend Routes

```python
# backend/app/routes/calendar_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.auth_service import get_current_user
from ..services.calendar_service_multi import UniversalCalendarService
from ..models import User

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

@router.post("/{provider}/auth")
async def initiate_calendar_auth(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Get OAuth URL for any calendar provider

    Usage:
        POST /api/calendar/google/auth
        POST /api/calendar/microsoft/auth
        POST /api/calendar/icloud/auth

    Returns: { "auth_url": "https://..." }

    User clicks this URL → Redirected to provider → Authorizes → Redirected back
    """
    try:
        auth_url = UniversalCalendarService.get_oauth_url(
            provider=provider,
            user_id=str(current_user.id)
        )

        return {
            "auth_url": auth_url,
            "provider": provider,
            "message": f"Redirect user to this URL to authorize {provider} calendar"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{provider}/callback")
async def calendar_oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Step 2: OAuth callback (provider redirects here after user authorizes)

    This endpoint receives the authorization code and exchanges it for tokens
    User never sees this - happens automatically in background
    """
    try:
        # Extract user_id from state
        user_id = state.split(':')[0]

        # Exchange code for tokens and save connection
        connection = await UniversalCalendarService.exchange_code(
            provider=provider,
            code=code,
            db=db,
            user_id=user_id
        )

        # Redirect to success page
        return RedirectResponse(
            url=f"/settings/calendar?success=true&provider={provider}",
            status_code=302
        )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"/settings/calendar?error=true&message={str(e)}",
            status_code=302
        )

@router.get("/connections")
async def list_calendar_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all connected calendars for current user
    """
    connections = db.query(CalendarConnection).filter(
        CalendarConnection.user_id == current_user.id,
        CalendarConnection.is_active == True
    ).all()

    return {
        "connections": [
            {
                "id": str(conn.id),
                "provider": conn.provider,
                "calendar_name": conn.calendar_name,
                "connected_at": conn.created_at,
                "last_synced": conn.last_synced_at,
                "sync_enabled": conn.sync_enabled
            }
            for conn in connections
        ]
    }

@router.post("/sync/{connection_id}")
async def sync_calendar(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger calendar sync
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.id == connection_id,
        CalendarConnection.user_id == current_user.id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Calendar connection not found")

    meetings = await UniversalCalendarService.sync_events(connection, db)

    return {
        "success": True,
        "meetings_synced": len(meetings),
        "last_sync": connection.last_synced_at
    }

@router.delete("/{provider}/disconnect")
async def disconnect_calendar(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a calendar provider
    """
    connection = db.query(CalendarConnection).filter(
        CalendarConnection.user_id == current_user.id,
        CalendarConnection.provider == provider,
        CalendarConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No active connection found")

    connection.is_active = False
    connection.sync_enabled = False
    db.commit()

    return {"success": True, "message": f"{provider} calendar disconnected"}
```

---

## 🔐 Security & Privacy (Why OAuth is Safe)

### What OAuth Does:
1. ✅ User never enters password in your app
2. ✅ User authorizes on **provider's official website** (Google/Microsoft/Apple)
3. ✅ Provider gives your app a **temporary token** (not the user's password)
4. ✅ Token can be revoked anytime by user
5. ✅ Token only has permissions user approved (read calendars, not delete)

### What You Store:
- ❌ NO passwords
- ❌ NO credit card info
- ✅ Only OAuth tokens (encrypted)
- ✅ Calendar metadata (event titles, times)

---

## 📱 User Journey Example

### Scenario: User on MacBook Pro

**Step 1:** User opens "Settings > Calendar"
```
App detects: macOS
Suggests: "Connect iCloud Calendar" (primary)
Also shows: Google, Outlook
```

**Step 2:** User clicks "Connect iCloud Calendar"
```
→ Redirected to https://appleid.apple.com
→ User logs in with their Apple ID (on Apple's website!)
→ Apple asks: "Allow TranscribeAI to read your calendar?"
→ User clicks "Allow"
```

**Step 3:** User redirected back to your app
```
→ Callback endpoint receives authorization code
→ Exchange code for access token (in backend)
→ Save connection to database
→ Start syncing calendar events
→ Show success: "iCloud Calendar connected! 🎉"
```

**Step 4:** Calendar auto-syncs
```
→ Every 15 minutes, sync new events
→ User sees upcoming meetings in dashboard
→ Can start recording with one click
```

---

## 🛠️ Setup Required for Each Provider

### Google Calendar (Already Configured!)
✅ You already have setup instructions in the main guide

### Microsoft Outlook Calendar
1. Go to: https://portal.azure.com/
2. Register application
3. Add redirect URI: `http://localhost:8000/api/calendar/microsoft/callback`
4. Add permissions: `Calendars.Read`, `Calendars.Read.Shared`
5. Copy Client ID and Secret to `.env`

### Apple iCloud Calendar
1. Go to: https://developer.apple.com/
2. Register App ID
3. Enable "Sign in with Apple"
4. Add redirect URI: `http://localhost:8000/api/calendar/icloud/callback`
5. Copy Client ID and Secret to `.env`

---

## 🎯 Implementation Priority

**Phase 1: Google Only (Already Built!)**
- Most users have Google Calendar
- OAuth service already created
- Focus on perfecting one provider first

**Phase 2: Add Microsoft Outlook (2-3 hours)**
- Similar to Google implementation
- Reuse UniversalCalendarService structure

**Phase 3: Add Apple iCloud (3-4 hours)**
- Slightly different (uses CalDAV)
- Need additional library for CalDAV protocol

---

## 📝 Updated Environment Variables

```bash
# .env - Add these for multi-provider support

# Google Calendar (PRIORITY 1)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback

# Microsoft Outlook (PRIORITY 2)
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/api/calendar/microsoft/callback

# Apple iCloud (PRIORITY 3)
APPLE_CLIENT_ID=com.yourapp.service
APPLE_CLIENT_SECRET=your-apple-secret
APPLE_REDIRECT_URI=http://localhost:8000/api/calendar/icloud/callback
```

---

## ✅ Summary: Zero Credentials Needed!

**User Experience:**
1. Click "Connect Google Calendar" button
2. Authorize on Google's official page
3. Done! Calendar synced automatically
4. **NEVER entered password in your app** ✅

**Same flow for:**
- Microsoft Outlook
- Apple iCloud
- Any OAuth-compatible calendar

**This is the industry standard** used by:
- Zoom, Google Meet, Calendly
- Notion, Slack, Asana
- Every major app with calendar integration

---

## 🚀 Want Me to Implement This?

I can create:
1. **Universal Calendar Service** - Support all 3 providers
2. **Multi-provider OAuth routes** - Handle all callbacks
3. **Smart platform detection** - Suggest right calendar
4. **Frontend UI** - Calendar connection page with smart suggestions

**Just say:** "Create the multi-provider calendar system" and I'll build it! 🎨

Or ask any questions about how OAuth works, security, or implementation details.
