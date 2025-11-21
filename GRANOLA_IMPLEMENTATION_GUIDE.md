# Granola AI Features - Implementation Guide
## TranscribeAI Platform Enhancement

**Status:** Phase 1 Complete (Backend Foundation) ✅
**Date:** 2025-11-19
**Version:** 1.0

---

## 📋 Table of Contents
1. [What's Been Implemented](#whats-been-implemented)
2. [Database Schema](#database-schema)
3. [Services Created](#services-created)
4. [Next Steps](#next-steps)
5. [Setup Instructions](#setup-instructions)
6. [API Endpoints (To Be Created)](#api-endpoints-to-be-created)
7. [Frontend Components (To Be Created)](#frontend-components-to-be-created)

---

## ✅ What's Been Implemented

### Phase 1: Backend Foundation (COMPLETE)

#### 1. Database Models & Migration
- **File:** `backend/alembic/versions/003_add_granola_features.py`
- **Models Added:** `backend/app/models.py` (lines 156-369)
  - `CalendarConnection` - OAuth connections (Google/Microsoft/Apple)
  - `MeetingTemplate` - Pre-defined and custom templates
  - `Meeting` - Calendar meetings with transcription
  - `MeetingNote` - Hybrid notes (manual + AI)
  - `ActionItem` - Tasks extracted from meetings
  - `TranscriptionTag` - Junction table for tags
  - `Integration` - Third-party integrations (Slack, webhooks)

#### 2. Services

##### **CalendarService** (`backend/app/services/calendar_service.py`)
Full Google Calendar OAuth integration:
- ✅ OAuth URL generation
- ✅ Token exchange and storage
- ✅ Automatic token refresh
- ✅ Calendar event syncing
- ✅ Meeting platform detection (Zoom, Meet, Teams)
- ✅ Participant extraction
- ✅ Incremental sync support
- ✅ Auto-preparation of meetings

**Key Methods:**
```python
CalendarService.get_google_oauth_url(state)
CalendarService.exchange_google_code(code, db, user_id)
CalendarService.sync_calendar_events(connection, db)
CalendarService.get_upcoming_meetings(user_id, db)
CalendarService.prepare_meeting_for_recording(meeting, db)
```

##### **MeetingService** (`backend/app/services/meeting_service.py`)
Complete meeting management:
- ✅ Meeting creation and quick-start (one-tap)
- ✅ Hybrid note-taking (manual + AI)
- ✅ Combined notes retrieval
- ✅ AI-powered action item extraction
- ✅ Meeting summary generation
- ✅ Chat with meeting feature
- ✅ Action item management

**Key Methods:**
```python
MeetingService.quick_start_meeting(user_id, title, db)
MeetingService.add_manual_note(meeting_id, user_id, content, db)
MeetingService.add_ai_note(meeting_id, user_id, content, db)
MeetingService.extract_action_items_with_ai(meeting_id, transcript, db, user_id)
MeetingService.generate_meeting_summary(meeting_id, db)
MeetingService.chat_with_meeting(meeting_id, question, db)
```

##### **TemplateService** (`backend/app/services/template_service.py`)
Meeting templates system:
- ✅ 7 pre-defined system templates:
  - 1-on-1 Meeting
  - Customer Discovery
  - Team Standup
  - Sales Call
  - User Interview
  - Brainstorming Session
  - Project Kickoff
- ✅ Custom template creation
- ✅ Template application to meetings
- ✅ Usage tracking

**Key Methods:**
```python
TemplateService.initialize_system_templates(db)
TemplateService.create_custom_template(user_id, name, description, db)
TemplateService.get_templates(user_id, db)
TemplateService.apply_template_to_meeting(template, meeting_id, db)
```

#### 3. Configuration Updates
**File:** `backend/app/config.py` (lines 86-103)

Added settings:
```python
# Calendar Integration
GOOGLE_CLIENT_ID: str
GOOGLE_CLIENT_SECRET: str
GOOGLE_REDIRECT_URI: str

# Microsoft/Apple (for future)
MICROSOFT_CLIENT_ID: str
APPLE_CLIENT_ID: str

# Sync Settings
CALENDAR_SYNC_INTERVAL_MINUTES: int = 15
MEETING_PREP_MINUTES_BEFORE: int = 15

# WebSocket Settings
WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
WEBSOCKET_MAX_CONNECTIONS: int = 100
```

---

## 🗄️ Database Schema

### New Tables

#### `calendar_connections`
Stores user calendar OAuth connections
```sql
- id (UUID, PK)
- user_id (FK → users)
- provider (google/microsoft/apple)
- calendar_id, calendar_name
- access_token, refresh_token, token_expires_at
- is_active, sync_enabled, auto_record_meetings
- default_template_id (FK → meeting_templates)
- last_synced_at, sync_token
- created_at, updated_at
```

#### `meeting_templates`
Pre-defined and custom templates
```sql
- id (UUID, PK)
- user_id (FK → users, NULL for system templates)
- name, description
- is_system_template, is_public
- structure (JSON: sections, fields)
- summary_prompt (custom AI prompt)
- auto_extract_action_items, auto_extract_decisions
- icon, color
- usage_count
- created_at, updated_at
```

#### `meetings`
Calendar meetings with transcription
```sql
- id (UUID, PK)
- user_id (FK → users)
- calendar_connection_id (FK)
- transcription_id (FK → transcriptions)
- template_id (FK → meeting_templates)
- title, description, calendar_event_id
- start_time, end_time, timezone
- actual_start_time, actual_end_time
- meeting_url, platform
- participants (JSON), organizer_email
- status (scheduled/in_progress/completed/cancelled)
- recording_status (not_started/recording/processing/completed/failed)
- is_recurring, recurrence_pattern, parent_meeting_id
- summary, key_points
- created_at, updated_at
```

#### `meeting_notes`
Hybrid notes (manual + AI)
```sql
- id (UUID, PK)
- meeting_id (FK → meetings)
- user_id (FK → users)
- content
- note_type (manual/ai/hybrid)
- section (agenda/discussion/action_items/decisions/notes)
- timestamp_in_meeting (seconds)
- speaker (for AI notes)
- created_at, updated_at
```

#### `action_items`
Tasks from meetings
```sql
- id (UUID, PK)
- meeting_id (FK → meetings)
- user_id (FK → users)
- title, description
- assigned_to_email, assigned_to_name
- priority (low/medium/high)
- due_date
- status (pending/in_progress/completed/cancelled)
- completed_at
- created_from_ai (boolean)
- related_transcript_chunk
- created_at, updated_at
```

#### `transcription_tags`
Many-to-many junction table
```sql
- transcription_id (FK → transcriptions, PK)
- tag_id (FK → tags, PK)
- created_at
```

#### `integrations`
Third-party integrations
```sql
- id (UUID, PK)
- user_id (FK → users)
- provider (slack/webhook/zapier/notion)
- name
- access_token, refresh_token, webhook_url
- config (JSON)
- is_active, last_used_at
- created_at, updated_at
```

---

## 🚀 Next Steps

### Phase 2: API Endpoints (IN PROGRESS)

Need to create routes in `backend/app/routes/`:

#### `calendar_routes.py`
```python
POST   /api/calendar/google/auth
GET    /api/calendar/google/callback
POST   /api/calendar/sync
GET    /api/calendar/events
POST   /api/calendar/events/{id}/prepare
DELETE /api/calendar/disconnect/{id}
GET    /api/calendar/connections
```

#### `meeting_routes.py`
```python
POST   /api/meetings/quick-start
GET    /api/meetings
GET    /api/meetings/{id}
POST   /api/meetings
PATCH  /api/meetings/{id}
DELETE /api/meetings/{id}
POST   /api/meetings/{id}/start
POST   /api/meetings/{id}/stop
GET    /api/meetings/{id}/notes
POST   /api/meetings/{id}/notes
PATCH  /api/meetings/{id}/notes/{note_id}
DELETE /api/meetings/{id}/notes/{note_id}
GET    /api/meetings/{id}/export
POST   /api/meetings/{id}/chat
```

#### `action_items_routes.py`
```python
GET    /api/action-items
GET    /api/action-items/mine
POST   /api/meetings/{id}/action-items
PATCH  /api/action-items/{id}/status
PATCH  /api/action-items/{id}
DELETE /api/action-items/{id}
```

#### `template_routes.py`
```python
GET    /api/templates
POST   /api/templates
GET    /api/templates/{id}
PUT    /api/templates/{id}
DELETE /api/templates/{id}
POST   /api/templates/{id}/apply/{meeting_id}
```

### Phase 3: WebSocket for Real-time Transcription

Create `backend/app/websocket/`:
- `meeting_websocket.py` - Real-time audio streaming
- `connection_manager.py` - WebSocket connection management

### Phase 4: Frontend Components

Need to create in `frontend/src/`:

#### Pages
- `app/calendar/page.tsx` - Calendar view with meetings
- `app/meetings/page.tsx` - Meetings list
- `app/meetings/[id]/page.tsx` - Meeting detail with hybrid notes
- `app/meetings/live/page.tsx` - Live recording interface
- `app/templates/page.tsx` - Template management
- `app/settings/calendar/page.tsx` - Calendar settings
- `app/settings/integrations/page.tsx` - Integrations

#### Components
- `components/calendar/CalendarView.tsx`
- `components/meetings/MeetingCard.tsx`
- `components/meetings/HybridNoteEditor.tsx`
- `components/meetings/QuickCaptureButton.tsx`
- `components/meetings/MeetingTimeline.tsx`
- `components/meetings/ActionItemList.tsx`
- `components/meetings/ChatWithMeeting.tsx`
- `components/templates/TemplateSelector.tsx`

### Phase 5: Integration & Testing
- Slack integration
- Microsoft/Apple calendar support
- End-to-end testing
- Performance optimization

---

## 🛠️ Setup Instructions

### 1. Install Dependencies

Add to `backend/requirements.txt`:
```txt
google-api-python-client==2.100.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
websockets==12.0
```

Install:
```bash
cd backend
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib websockets
```

### 2. Set Up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Google Calendar API"
4. Create OAuth 2.0 Credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/api/calendar/google/callback`
5. Download credentials and add to `.env`:

```bash
# Add to backend/.env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback
```

### 3. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This will create all new tables.

### 4. Initialize System Templates

Add to your startup script or run once:
```python
from app.services.template_service import TemplateService
from app.database import SessionLocal

db = SessionLocal()
TemplateService.initialize_system_templates(db)
db.close()
```

---

## 🔌 API Endpoints (To Be Created)

### Calendar Integration Flow

1. **User initiates connection**
   ```
   GET /api/calendar/google/auth
   → Returns: { "auth_url": "https://accounts.google.com/..." }
   ```

2. **Google redirects back**
   ```
   GET /api/calendar/google/callback?code=xxx
   → Creates CalendarConnection
   → Returns: { "connection_id": "...", "calendar_name": "..." }
   ```

3. **Manual sync**
   ```
   POST /api/calendar/sync
   Body: { "connection_id": "..." }
   → Syncs events
   → Returns: { "meetings_synced": 15, "last_sync": "..." }
   ```

4. **View upcoming meetings**
   ```
   GET /api/meetings?upcoming=true
   → Returns: [ { meeting objects } ]
   ```

### Meeting Recording Flow

1. **Quick start (one-tap)**
   ```
   POST /api/meetings/quick-start
   Body: { "title": "Quick Meeting" }
   → Returns: { meeting object with status='in_progress' }
   ```

2. **Add manual note**
   ```
   POST /api/meetings/{id}/notes
   Body: {
     "content": "User typed note",
     "timestamp_in_meeting": 120
   }
   → Returns: { note object }
   ```

3. **WebSocket for real-time AI transcription**
   ```
   WS /ws/meetings/{meeting_id}
   Send: audio chunks
   Receive: { "transcript": "...", "speaker": "...", "timestamp": 120 }
   ```

4. **Stop recording**
   ```
   POST /api/meetings/{id}/stop
   → Generates summary
   → Extracts action items
   → Returns: { meeting object with summary }
   ```

5. **Chat with meeting**
   ```
   POST /api/meetings/{id}/chat
   Body: { "question": "What were the main action items?" }
   → Returns: { "answer": "...", "sources": [...] }
   ```

---

## 🎨 Frontend Components (To Be Created)

### HybridNoteEditor Component
```tsx
<HybridNoteEditor meetingId={meetingId}>
  {/* Manual notes in BLACK */}
  <ManualNote timestamp="00:05:23">User typed note</ManualNote>

  {/* AI notes in GRAY */}
  <AINote speaker="John" timestamp="00:05:45">
    AI transcribed speech
  </AINote>
</HybridNoteEditor>
```

### QuickCaptureButton
```tsx
<QuickCaptureButton
  onStart={handleStart}
  onStop={handleStop}
/>
// One-tap to start recording, shows in Lock Screen
```

### CalendarView
```tsx
<CalendarView
  events={meetings}
  onMeetingClick={handleMeetingClick}
  onPrepareRecording={handlePrepare}
/>
```

---

## 📊 Current Implementation Status

| Feature | Status | Progress |
|---------|--------|----------|
| Database Models | ✅ Complete | 100% |
| Calendar OAuth Service | ✅ Complete | 100% |
| Meeting Service | ✅ Complete | 100% |
| Template Service | ✅ Complete | 100% |
| API Routes | ⏳ Pending | 0% |
| WebSocket Real-time | ⏳ Pending | 0% |
| Frontend Components | ⏳ Pending | 0% |
| Slack Integration | ⏳ Pending | 0% |
| Microsoft/Apple Calendar | ⏳ Pending | 0% |
| Testing | ⏳ Pending | 0% |

**Overall Progress: 40%**

---

## 🔐 Security Considerations

1. **OAuth Tokens:** Should be encrypted in production
   - Use `cryptography` library for token encryption
   - Store encryption key in environment variable

2. **WebSocket Authentication:** Verify JWT tokens
   - Include token in WebSocket connection
   - Validate user has access to meeting

3. **Rate Limiting:** Protect calendar sync endpoint
   - Limit sync frequency per user
   - Use existing rate_limiter service

4. **Data Privacy:** Row-level security for meetings
   - Users can only access their own meetings
   - Shared meetings require explicit permissions

---

## 📝 Environment Variables Checklist

Add to `backend/.env`:
```bash
# Existing (keep as-is)
DATABASE_URL=postgresql://...
GROQ_API_KEY=gsk_...
SECRET_KEY=...

# NEW - Calendar Integration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/google/callback

# NEW - Microsoft (future)
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=

# NEW - Apple (future)
APPLE_CLIENT_ID=
APPLE_CLIENT_SECRET=
```

---

## 🐛 Known Issues & TODOs

1. **Token Encryption:** Currently storing tokens in plain text
   - TODO: Implement encryption for production

2. **Background Sync:** Calendar sync is manual
   - TODO: Set up background task scheduler (Celery/APScheduler)

3. **WebSocket Scaling:** Need to handle multiple concurrent connections
   - TODO: Implement connection pooling

4. **Error Handling:** Some edge cases not covered
   - TODO: Add comprehensive error handling

---

## 🎯 Next Immediate Actions

1. ✅ Create database migration (DONE)
2. ✅ Create calendar service (DONE)
3. ✅ Create meeting service (DONE)
4. ✅ Create template service (DONE)
5. ⏳ Create API routes (NEXT)
6. ⏳ Set up WebSocket infrastructure
7. ⏳ Build frontend components
8. ⏳ End-to-end testing

---

## 📞 Support

If you encounter issues:
1. Check logs: `backend/logs/`
2. Verify database migration: `alembic current`
3. Test Google OAuth setup: Visit auth URL manually
4. Check environment variables are loaded

---

**Implementation Guide Version 1.0**
**Last Updated:** 2025-11-19
**Maintained by:** Claude AI Assistant
