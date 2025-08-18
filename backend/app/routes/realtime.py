# backend/app/routes/realtime.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import tempfile
import os
import logging
from datetime import datetime
from typing import Optional
import uuid

from ..database import get_db
from ..models import User, Transcription
from ..services.auth_service import get_current_user
from ..services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()

transcription_service = TranscriptionService()

@router.post("/realtime-chunk")
async def realtime_transcription_chunk(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process real-time audio chunks for live transcription (no storage)
    """
    try:
        # Check usage limits
        from ..routes.transcriptions import check_usage_limits
        check_usage_limits(current_user, db)
        
        # Save uploaded chunk to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Convert webm to wav if needed
            wav_path = await transcription_service._convert_to_wav(temp_path)
            
            # Transcribe the chunk
            transcription = await transcription_service._transcribe_with_groq(wav_path)
            
            return {"text": transcription, "status": "success"}
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
                
    except Exception as e:
        logger.error(f"Real-time transcription failed: {e}")
        return {"text": "", "status": "error", "error": str(e)}

@router.post("/realtime-complete")
async def complete_realtime_transcription(
    audio: UploadFile = File(...),
    title: str = Form(...),
    add_to_knowledge_base: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process complete real-time recording with summary and knowledge base storage
    """
    try:
        # Check usage limits
        from ..routes.transcriptions import check_usage_limits
        check_usage_limits(current_user, db)
        
        # Create transcription record
        transcription = Transcription(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title=title,
            file_type="webm",
            file_size=len(await audio.read()),
            language="auto",
            status="processing",
            generate_summary=True,
            add_to_knowledge_base=add_to_knowledge_base,
            created_at=datetime.utcnow()
        )
        
        # Reset file pointer
        await audio.seek(0)
        
        db.add(transcription)
        db.commit()
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Convert webm to wav
            wav_path = await transcription_service._convert_to_wav(temp_path)
            
            # Get duration
            duration = transcription_service._get_audio_duration(wav_path)
            transcription.duration_seconds = duration
            
            # Transcribe the complete audio
            transcription_text = await transcription_service._transcribe_with_groq(wav_path)
            transcription.transcription_text = transcription_text
            
            # Generate summary
            summary = await transcription_service._generate_summary(transcription_text)
            transcription.summary_text = summary
            
            # Store in knowledge base if requested
            stored = False
            if add_to_knowledge_base and transcription_text:
                point_ids = await transcription_service._store_in_qdrant(
                    transcription_text, 
                    summary, 
                    str(current_user.id),
                    str(transcription.id),
                    {
                        "title": title,
                        "created_at": datetime.utcnow().isoformat(),
                        "type": "realtime_recording",
                        "duration_seconds": duration
                    }
                )
                transcription.qdrant_point_ids = point_ids
                transcription.qdrant_collection = f"user_{current_user.id}_transcriptions"
                stored = len(point_ids) > 0
            
            # Update transcription status
            transcription.status = "completed"
            transcription.completed_at = datetime.utcnow()
            
            # Update user usage
            current_user.monthly_usage += 1
            
            db.commit()
            
            return {
                "id": str(transcription.id),
                "text": transcription_text,
                "summary": summary,
                "status": "success",
                "stored_in_knowledge_base": stored,
                "duration_seconds": duration,
                "title": title,
                "created_at": transcription.created_at.isoformat()
            }
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
                
    except Exception as e:
        logger.error(f"Complete realtime transcription failed: {e}")
        if 'transcription' in locals():
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
        return {"text": "", "status": "error", "error": str(e)}