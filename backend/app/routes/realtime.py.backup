# backend/app/routes/realtime.py - Enhanced version
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import tempfile
import os
import logging
from datetime import datetime
from typing import Optional
import uuid
import asyncio
from collections import defaultdict
import time

from ..database import get_db
from ..models import User, Transcription
from ..services.auth_service import get_current_user
from ..services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)
router = APIRouter()

transcription_service = TranscriptionService()

# Store partial transcription contexts for continuous streaming
transcription_contexts = defaultdict(dict)

@router.post("/realtime-chunk")
async def realtime_transcription_chunk(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process real-time audio chunks for live transcription (legacy endpoint)
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

@router.post("/realtime-stream")
async def realtime_transcription_stream(
    audio: UploadFile = File(...),
    continuous: bool = Form(False),
    timestamp: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced real-time transcription with continuous streaming support
    """
    try:
        # Check usage limits
        from ..routes.transcriptions import check_usage_limits
        check_usage_limits(current_user, db)
        
        user_id = str(current_user.id)
        session_timestamp = timestamp
        
        # Initialize or get existing context for this user session
        if user_id not in transcription_contexts:
            transcription_contexts[user_id] = {
                'session_start': time.time(),
                'accumulated_text': '',
                'last_final_text': '',
                'chunk_count': 0,
                'last_update': time.time()
            }
        
        context = transcription_contexts[user_id]
        context['chunk_count'] += 1
        context['last_update'] = time.time()
        
        # Save uploaded chunk to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Skip very small chunks (less than 2KB)
        if len(content) < 2048:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {
                "text": "",
                "is_final": False,
                "status": "success",
                "message": "Chunk too small"
            }
        
        try:
            # Convert webm to wav if needed
            wav_path = await transcription_service._convert_to_wav(temp_path)
            
            # Enhanced transcription with context awareness
            transcription = await transcription_service._transcribe_with_groq_streaming(
                wav_path, 
                context=context.get('accumulated_text', ''),
                chunk_number=context['chunk_count']
            )
            
            # Determine if this is a final transcription or partial
            is_final = False
            clean_transcription = transcription.strip()
            
            if clean_transcription:
                # Simple heuristic: if transcription ends with punctuation and is substantial, 
                # consider it more "final"
                if (clean_transcription.endswith(('.', '!', '?')) and 
                    len(clean_transcription.split()) > 3 and
                    context['chunk_count'] % 4 == 0):  # Every 4th chunk can be "final"
                    is_final = True
                    context['last_final_text'] = context['accumulated_text'] + ' ' + clean_transcription
                    context['accumulated_text'] = context['last_final_text']
                
                # Filter out repetitive transcriptions
                if clean_transcription.lower() not in context.get('accumulated_text', '').lower():
                    return {
                        "text": clean_transcription,
                        "is_final": is_final,
                        "status": "success",
                        "chunk_number": context['chunk_count'],
                        "session_duration": time.time() - context['session_start']
                    }
                else:
                    # Return empty if repetitive
                    return {
                        "text": "",
                        "is_final": False,
                        "status": "success", 
                        "message": "Filtered repetitive content"
                    }
            
            return {
                "text": clean_transcription,
                "is_final": is_final,
                "status": "success",
                "chunk_number": context['chunk_count']
            }
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
                
    except Exception as e:
        logger.error(f"Real-time streaming transcription failed: {e}")
        return {
            "text": "", 
            "is_final": False,
            "status": "error", 
            "error": str(e)
        }

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
        
        # Clean up user's transcription context
        user_id = str(current_user.id)
        if user_id in transcription_contexts:
            del transcription_contexts[user_id]
        
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
        db.refresh(transcription)
        
        # Process the complete recording
        result = await transcription_service.process_complete_realtime_recording(
            transcription, audio, db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Complete real-time transcription failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/realtime-session")
async def clear_realtime_session(
    current_user: User = Depends(get_current_user)
):
    """
    Clear the real-time transcription session context for a user
    """
    user_id = str(current_user.id)
    if user_id in transcription_contexts:
        del transcription_contexts[user_id]
        return {"status": "success", "message": "Session context cleared"}
    
    return {"status": "success", "message": "No active session found"}

# Background task to clean up old contexts (prevent memory leaks)
async def cleanup_old_contexts():
    """
    Clean up transcription contexts older than 30 minutes
    """
    current_time = time.time()
    expired_users = []
    
    for user_id, context in transcription_contexts.items():
        if current_time - context.get('last_update', 0) > 1800:  # 30 minutes
            expired_users.append(user_id)
    
    for user_id in expired_users:
        del transcription_contexts[user_id]
        logger.info(f"Cleaned up expired transcription context for user {user_id}")

# Initialize cleanup task on startup
import atexit
cleanup_task = None

def start_cleanup_task():
    global cleanup_task
    if cleanup_task is None:
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(600)  # Run every 10 minutes
                await cleanup_old_contexts()
        
        cleanup_task = asyncio.create_task(periodic_cleanup())

def stop_cleanup_task():
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()

# Register cleanup on exit
atexit.register(stop_cleanup_task)
# # backend/app/routes/realtime.py
# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
# from sqlalchemy.orm import Session
# import tempfile
# import os
# import logging
# from datetime import datetime
# from typing import Optional
# import uuid

# from ..database import get_db
# from ..models import User, Transcription
# from ..services.auth_service import get_current_user
# from ..services.transcription_service import TranscriptionService

# logger = logging.getLogger(__name__)
# router = APIRouter()

# transcription_service = TranscriptionService()

# @router.post("/realtime-chunk")
# async def realtime_transcription_chunk(
#     audio: UploadFile = File(...),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Process real-time audio chunks for live transcription (no storage)
#     """
#     try:
#         # Check usage limits
#         from ..routes.transcriptions import check_usage_limits
#         check_usage_limits(current_user, db)
        
#         # Save uploaded chunk to temporary file
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
#             content = await audio.read()
#             temp_file.write(content)
#             temp_path = temp_file.name
        
#         try:
#             # Convert webm to wav if needed
#             wav_path = await transcription_service._convert_to_wav(temp_path)
            
#             # Transcribe the chunk
#             transcription = await transcription_service._transcribe_with_groq(wav_path)
            
#             return {"text": transcription, "status": "success"}
            
#         finally:
#             # Clean up
#             if os.path.exists(temp_path):
#                 os.remove(temp_path)
#             if 'wav_path' in locals() and os.path.exists(wav_path):
#                 os.remove(wav_path)
                
#     except Exception as e:
#         logger.error(f"Real-time transcription failed: {e}")
#         return {"text": "", "status": "error", "error": str(e)}

# @router.post("/realtime-complete")
# async def complete_realtime_transcription(
#     audio: UploadFile = File(...),
#     title: str = Form(...),
#     add_to_knowledge_base: bool = Form(True),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Process complete real-time recording with summary and knowledge base storage
#     """
#     try:
#         # Check usage limits
#         from ..routes.transcriptions import check_usage_limits
#         check_usage_limits(current_user, db)
        
#         # Create transcription record
#         transcription = Transcription(
#             id=str(uuid.uuid4()),
#             user_id=current_user.id,
#             title=title,
#             file_type="webm",
#             file_size=len(await audio.read()),
#             language="auto",
#             status="processing",
#             generate_summary=True,
#             add_to_knowledge_base=add_to_knowledge_base,
#             created_at=datetime.utcnow()
#         )
        
#         # Reset file pointer
#         await audio.seek(0)
        
#         db.add(transcription)
#         db.commit()
        
#         # Save uploaded file to temporary location
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
#             content = await audio.read()
#             temp_file.write(content)
#             temp_path = temp_file.name
        
#         try:
#             # Convert webm to wav
#             wav_path = await transcription_service._convert_to_wav(temp_path)
            
#             # Get duration
#             duration = transcription_service._get_audio_duration(wav_path)
#             transcription.duration_seconds = duration
            
#             # Transcribe the complete audio
#             transcription_text = await transcription_service._transcribe_with_groq(wav_path)
#             transcription.transcription_text = transcription_text
            
#             # Generate summary
#             summary = await transcription_service._generate_summary(transcription_text)
#             transcription.summary_text = summary
            
#             # Store in knowledge base if requested
#             stored = False
#             if add_to_knowledge_base and transcription_text:
#                 point_ids = await transcription_service._store_in_qdrant(
#                     transcription_text, 
#                     summary, 
#                     str(current_user.id),
#                     str(transcription.id),
#                     {
#                         "title": title,
#                         "created_at": datetime.utcnow().isoformat(),
#                         "type": "realtime_recording",
#                         "duration_seconds": duration
#                     }
#                 )
#                 transcription.qdrant_point_ids = point_ids
#                 transcription.qdrant_collection = f"user_{current_user.id}_transcriptions"
#                 stored = len(point_ids) > 0
            
#             # Update transcription status
#             transcription.status = "completed"
#             transcription.completed_at = datetime.utcnow()
            
#             # Update user usage
#             current_user.monthly_usage += 1
            
#             db.commit()
            
#             return {
#                 "id": str(transcription.id),
#                 "text": transcription_text,
#                 "summary": summary,
#                 "status": "success",
#                 "stored_in_knowledge_base": stored,
#                 "duration_seconds": duration,
#                 "title": title,
#                 "created_at": transcription.created_at.isoformat()
#             }
            
#         finally:
#             # Clean up
#             if os.path.exists(temp_path):
#                 os.remove(temp_path)
#             if 'wav_path' in locals() and os.path.exists(wav_path):
#                 os.remove(wav_path)
                
#     except Exception as e:
#         logger.error(f"Complete realtime transcription failed: {e}")
#         if 'transcription' in locals():
#             transcription.status = "failed"
#             transcription.error_message = str(e)
#             db.commit()
#         return {"text": "", "status": "error", "error": str(e)}