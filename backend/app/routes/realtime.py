# backend/app/routes/realtime.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import tempfile
import os
import logging

from ..database import get_db
from ..models import User
from ..services.auth_service import get_current_user
from ..services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()

transcription_service = TranscriptionService()

@router.post("/realtime")
async def realtime_transcription(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process real-time audio chunks for live transcription
    """
    try:
        # Save uploaded chunk to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Convert webm to wav if needed
            if temp_path.endswith('.webm'):
                wav_path = temp_path.replace('.webm', '.wav')
                import subprocess
                cmd = [
                    "ffmpeg", "-y", "-i", temp_path,
                    "-ar", "16000", "-ac", "1", wav_path
                ]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0:
                    os.remove(temp_path)
                    temp_path = wav_path
            
            # Transcribe the chunk
            transcription = await transcription_service._transcribe_with_groq(temp_path)
            
            return {"text": transcription, "status": "success"}
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Real-time transcription failed: {e}")
        return {"text": "", "status": "error", "error": str(e)}

@router.post("/complete")
async def complete_transcription(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process complete recording for final transcription
    """
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Convert webm to wav
            if temp_path.endswith('.webm'):
                wav_path = temp_path.replace('.webm', '.wav')
                import subprocess
                cmd = [
                    "ffmpeg", "-y", "-i", temp_path,
                    "-ar", "16000", "-ac", "1", wav_path
                ]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode == 0:
                    os.remove(temp_path)
                    temp_path = wav_path
            
            # Transcribe the complete audio
            transcription = await transcription_service._transcribe_with_groq(temp_path)
            
            # Generate summary
            summary = await transcription_service._generate_summary(transcription)
            
            # Store in knowledge base
            point_ids = await transcription_service._store_in_qdrant(
                transcription, 
                summary, 
                str(current_user.id),
                f"realtime_{current_user.id}_{len(transcription)}"
            )
            
            return {
                "text": transcription,
                "summary": summary,
                "status": "success",
                "stored": len(point_ids) > 0
            }
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Complete transcription failed: {e}")
        return {"text": "", "status": "error", "error": str(e)}