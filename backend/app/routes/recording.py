# backend/app/routes/recording.py
"""
Recording Routes - Real-time Meeting Recording
Handles starting/stopping recording sessions and WebSocket connections
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime
import logging
import json
import asyncio

from ..database import get_db
from ..models import User, Meeting, Transcription
from ..services.auth_service import get_current_user
from ..services.realtime_transcription_service import RealtimeTranscriptionService
from ..config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize real-time transcription service
transcription_service = RealtimeTranscriptionService(
    api_key=settings.GROQ_API_KEY,
    buffer_duration=5  # Process every 5 seconds of audio
)


# ========================================
# Pydantic Schemas
# ========================================

class StartRecordingRequest(BaseModel):
    meeting_id: str
    audio_settings: Optional[dict] = None  # Sample rate, channels, etc.

class StartRecordingResponse(BaseModel):
    session_id: str
    meeting_id: str
    websocket_url: str
    status: str

class StopRecordingRequest(BaseModel):
    meeting_id: str

class StopRecordingResponse(BaseModel):
    meeting_id: str
    transcription_id: Optional[str]
    duration_seconds: int
    status: str


# ========================================
# Recording Session Management
# ========================================

# In-memory store for active recording sessions
# In production, use Redis for distributed systems
active_sessions = {}


@router.post("/recording/start", response_model=StartRecordingResponse)
async def start_recording(
    request: StartRecordingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new recording session for a meeting

    - Creates a Transcription record
    - Updates Meeting status to 'recording'
    - Returns WebSocket URL for audio streaming
    """
    try:
        # Get the meeting
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == request.meeting_id,
                Meeting.user_id == current_user.id
            )
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        # Check if already recording
        if meeting.recording_status == "recording":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting is already being recorded"
            )

        # Create a new transcription record
        transcription = Transcription(
            user_id=current_user.id,
            title=f"{meeting.title} - Recording",
            status="processing",
            source_type="meeting",
            language="auto",
            generate_summary=True,
            speaker_diarization=True,
            add_to_knowledge_base=True
        )
        db.add(transcription)
        db.flush()  # Get the ID without committing

        # Update meeting
        meeting.recording_status = "recording"
        meeting.actual_start_time = datetime.utcnow()
        meeting.transcription_id = transcription.id
        meeting.status = "in_progress"

        db.commit()
        db.refresh(transcription)

        # Create session
        session_id = str(transcription.id)
        active_sessions[session_id] = {
            "meeting_id": str(meeting.id),
            "transcription_id": str(transcription.id),
            "user_id": str(current_user.id),
            "started_at": datetime.utcnow(),
            "audio_buffer": [],
            "transcript_chunks": []
        }

        logger.info(f"Started recording session {session_id} for meeting {meeting.id}")

        return StartRecordingResponse(
            session_id=session_id,
            meeting_id=str(meeting.id),
            websocket_url=f"/api/recording/ws/{session_id}",
            status="recording"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recording: {str(e)}"
        )


@router.post("/recording/stop", response_model=StopRecordingResponse)
async def stop_recording(
    request: StopRecordingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stop an active recording session

    - Closes WebSocket connection
    - Updates Meeting status to 'completed'
    - Triggers transcription processing
    """
    try:
        # Get the meeting
        meeting = db.query(Meeting).filter(
            and_(
                Meeting.id == request.meeting_id,
                Meeting.user_id == current_user.id
            )
        ).first()

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        if meeting.recording_status != "recording":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting is not currently recording"
            )

        # Update meeting
        meeting.recording_status = "processing"
        meeting.actual_end_time = datetime.utcnow()
        meeting.status = "completed"

        # Calculate duration
        duration_seconds = 0
        if meeting.actual_start_time and meeting.actual_end_time:
            duration_seconds = int((meeting.actual_end_time - meeting.actual_start_time).total_seconds())

        # Get transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == meeting.transcription_id
        ).first()

        # Get session data before removing it
        session_id = str(meeting.transcription_id)
        transcript_chunks = []
        if session_id in active_sessions:
            transcript_chunks = active_sessions[session_id].get("transcript_chunks", [])

        if transcription:
            transcription.duration_seconds = duration_seconds

            # Combine all transcript chunks into final transcript
            if transcript_chunks:
                full_transcript = "\n".join([chunk["text"] for chunk in transcript_chunks])
                transcription.transcription_text = full_transcript
                transcription.status = "completed"

                # Calculate average confidence
                if transcript_chunks:
                    avg_confidence = sum(chunk.get("confidence", 0) for chunk in transcript_chunks) / len(transcript_chunks)
                    transcription.confidence_score = avg_confidence

                logger.info(f"Saved transcript for meeting {meeting.id}: {len(full_transcript)} characters")
            else:
                # No transcript generated
                transcription.status = "completed"
                transcription.transcription_text = ""

        # Generate AI summary if we have transcript
        if transcript_chunks and transcription and transcription.transcription_text:
            try:
                from app.services.groq_service import GroqService
                groq_service = GroqService()

                # Generate summary
                summary_prompt = f"""Generate a concise meeting summary from this transcript. Include:
1. Key Discussion Points (3-5 bullet points)
2. Decisions Made
3. Next Steps

Transcript:
{transcription.transcription_text[:4000]}  # Limit to avoid token limits
"""

                summary = await groq_service.generate_summary(summary_prompt)

                # Update transcription with summary
                if summary:
                    transcription.summary_text = summary
                    meeting.summary = summary  # Also save to meeting
                    logger.info(f"Generated AI summary for meeting {meeting.id}")

            except Exception as e:
                logger.error(f"Failed to generate summary: {e}")
                # Don't fail the whole request if summary generation fails

        # Update meeting summary status
        meeting.recording_status = "completed"

        db.commit()

        # Remove from active sessions
        if session_id in active_sessions:
            del active_sessions[session_id]

        logger.info(f"Stopped recording for meeting {meeting.id}")

        return StopRecordingResponse(
            meeting_id=str(meeting.id),
            transcription_id=str(meeting.transcription_id) if meeting.transcription_id else None,
            duration_seconds=duration_seconds,
            status="completed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop recording: {str(e)}"
        )


@router.get("/recording/status/{meeting_id}")
async def get_recording_status(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current recording status for a meeting
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

        # Check if there's an active session
        session_id = str(meeting.transcription_id) if meeting.transcription_id else None
        is_active = session_id in active_sessions if session_id else False

        response = {
            "meeting_id": str(meeting.id),
            "recording_status": meeting.recording_status,
            "status": meeting.status,
            "is_active_session": is_active,
            "transcription_id": str(meeting.transcription_id) if meeting.transcription_id else None,
            "actual_start_time": meeting.actual_start_time.isoformat() if meeting.actual_start_time else None,
            "actual_end_time": meeting.actual_end_time.isoformat() if meeting.actual_end_time else None
        }

        # Add duration if recording
        if is_active and session_id:
            session = active_sessions[session_id]
            duration = (datetime.utcnow() - session["started_at"]).total_seconds()
            response["duration_seconds"] = int(duration)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recording status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recording status"
        )


# ========================================
# WebSocket for Real-time Audio Streaming
# ========================================

@router.websocket("/recording/ws/{session_id}")
async def recording_websocket(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time audio streaming and transcription

    Accepts audio chunks from the client and processes them for transcription
    Sends back real-time transcript updates
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")

    # Verify session exists
    if session_id not in active_sessions:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid session ID"
        })
        await websocket.close()
        return

    session = active_sessions[session_id]

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Recording session started"
        })

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive()

            # Handle different message types
            if "text" in data:
                # JSON message (control messages)
                message = json.loads(data["text"])
                message_type = message.get("type")

                if message_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})

                elif message_type == "stop":
                    # Client requested stop
                    await websocket.send_json({
                        "type": "stopped",
                        "message": "Recording stopped"
                    })
                    break

            elif "bytes" in data:
                # Binary audio data
                audio_chunk = data["bytes"]

                # Store audio chunk
                session["audio_buffer"].append(audio_chunk)

                # Acknowledge receipt
                await websocket.send_json({
                    "type": "audio_received",
                    "chunk_size": len(audio_chunk),
                    "total_chunks": len(session["audio_buffer"])
                })

                # Process audio buffer every 5 chunks (~5 seconds of audio)
                if len(session["audio_buffer"]) >= 5:
                    # Get buffer to process
                    buffer_to_process = session["audio_buffer"].copy()
                    session["audio_buffer"] = []  # Clear buffer

                    try:
                        # Transcribe the audio buffer
                        result = await transcription_service.transcribe_buffer(
                            buffer_to_process,
                            language="en"  # TODO: Get from meeting settings
                        )

                        # Only send if we got actual text
                        if result.get("text"):
                            # Send transcript to client
                            await websocket.send_json({
                                "type": "transcript",
                                "text": result["text"],
                                "is_final": result.get("is_final", True),
                                "confidence": result.get("confidence", 1.0),
                                "language": result.get("language", "en")
                            })

                            # Store transcript chunk for final save
                            session["transcript_chunks"].append({
                                "text": result["text"],
                                "timestamp": datetime.utcnow().isoformat(),
                                "confidence": result.get("confidence", 1.0)
                            })

                            logger.info(f"Transcribed chunk for session {session_id}: {len(result['text'])} chars")

                    except Exception as e:
                        logger.error(f"Error transcribing audio buffer: {e}")
                        # Don't stop the recording, just log the error
                        await websocket.send_json({
                            "type": "transcription_error",
                            "message": "Temporary transcription error, continuing recording..."
                        })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        # Only log real errors, not normal close codes (1005, 1000)
        error_str = str(e)
        if "1005" not in error_str and "1000" not in error_str:
            logger.error(f"WebSocket error for session {session_id}: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except:
                pass
        else:
            logger.info(f"WebSocket closed normally for session {session_id}")
    finally:
        # Cleanup
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"WebSocket session {session_id} ended")
