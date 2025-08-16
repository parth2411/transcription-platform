# backend/app/routes/transcriptions.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import logging
import uuid
from datetime import datetime

from ..database import get_db
from ..models import User, Transcription
from ..services.auth_service import get_current_user
from ..services.transcription_service import TranscriptionService
from ..services.file_service import FileService
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class TranscriptionCreate(BaseModel):
    title: str
    language: str = "auto"
    generate_summary: bool = True
    speaker_diarization: bool = False
    add_to_knowledge_base: bool = True

class TranscriptionURL(BaseModel):
    url: HttpUrl
    title: str
    language: str = "auto"
    generate_summary: bool = True
    speaker_diarization: bool = False
    add_to_knowledge_base: bool = True

class TranscriptionText(BaseModel):
    text: str
    title: str
    generate_summary: bool = True
    add_to_knowledge_base: bool = True

class TranscriptionResponse(BaseModel):
    id: str
    title: str
    status: str
    file_type: Optional[str]
    file_size: Optional[int]
    duration_seconds: Optional[int]
    transcription_text: Optional[str]
    summary_text: Optional[str]
    language: str
    created_at: str
    completed_at: Optional[str]
    processing_time_seconds: Optional[int]
    error_message: Optional[str]

class TranscriptionList(BaseModel):
    transcriptions: List[TranscriptionResponse]
    total: int
    page: int
    per_page: int

# Initialize services
transcription_service = TranscriptionService()
file_service = FileService()

def check_usage_limits(user: User, db: Session):
    """Check if user has exceeded usage limits"""
    if user.subscription_tier == "business":
        return  # Unlimited for business tier
    if user.subscription_tier == "free" and user.monthly_usage >= settings.FREE_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly limit exceeded. Upgrade to Pro for more transcriptions."
        )
    elif user.subscription_tier == "pro" and user.monthly_usage >= settings.PRO_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly limit exceeded. Contact support for higher limits."
        )

def increment_usage(user: User, db: Session):
    """Increment user's monthly usage counter"""
    user.monthly_usage += 1
    db.commit()

async def process_transcription_background(
    transcription_id: str,
    processing_type: str,
    file_path_or_url_or_text: str
):
    """Background task to process transcription"""
    try:
        from ..database import SessionLocal
        db = SessionLocal()
        
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return
        
        if processing_type == "file":
            await transcription_service.process_file_transcription(
                db, transcription, file_path_or_url_or_text
            )
        elif processing_type == "url":
            await transcription_service.process_url_transcription(
                db, transcription, file_path_or_url_or_text
            )
        elif processing_type == "text":
            await transcription_service.process_text_transcription(
                db, transcription, file_path_or_url_or_text
            )
        
        db.close()
        logger.info(f"Background processing completed for {transcription_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {transcription_id}: {e}")

@router.post("/upload", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def upload_file_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    language: str = Form("auto"),
    generate_summary: bool = Form(True),
    speaker_diarization: bool = Form(False),
    add_to_knowledge_base: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process audio/video file for transcription
    """
    try:
        # Check usage limits
        check_usage_limits(current_user, db)
        
        # Validate file
        file_service.validate_file(file.filename, file.size, file.content_type)
        
        # Upload file to storage
        file_url = await file_service.upload_file(
            file.file, file.filename, file.content_type, str(current_user.id)
        )
        
        # Create transcription record
        transcription = Transcription(
            user_id=current_user.id,
            title=title,
            original_filename=file.filename,
            file_url=file_url,
            file_type=file.content_type,
            file_size=file.size,
            language=language,
            generate_summary=generate_summary,
            speaker_diarization=speaker_diarization,
            add_to_knowledge_base=add_to_knowledge_base,
            status="pending"
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Increment usage
        increment_usage(current_user, db)
        
        # Download file for processing
        local_file_path = await file_service.download_file(file_url)
        
        # Start background processing
        background_tasks.add_task(
            process_transcription_background,
            str(transcription.id),
            "file",
            local_file_path
        )
        
        logger.info(f"File transcription started: {transcription.id}")
        
        return TranscriptionResponse(
            id=str(transcription.id),
            title=transcription.title,
            status=transcription.status,
            file_type=transcription.file_type,
            file_size=transcription.file_size,
            duration_seconds=transcription.duration_seconds,
            transcription_text=transcription.transcription_text,
            summary_text=transcription.summary_text,
            language=transcription.language,
            created_at=transcription.created_at.isoformat(),
            completed_at=transcription.completed_at.isoformat() if transcription.completed_at else None,
            processing_time_seconds=transcription.processing_time_seconds,
            error_message=transcription.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@router.post("/url", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_url_transcription(
    background_tasks: BackgroundTasks,
    transcription_data: TranscriptionURL,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process URL (YouTube, podcast) for transcription
    """
    try:
        # Check usage limits
        check_usage_limits(current_user, db)
        
        # Create transcription record
        transcription = Transcription(
            user_id=current_user.id,
            title=transcription_data.title,
            file_url=str(transcription_data.url),
            file_type="url",
            language=transcription_data.language,
            generate_summary=transcription_data.generate_summary,
            speaker_diarization=transcription_data.speaker_diarization,
            add_to_knowledge_base=transcription_data.add_to_knowledge_base,
            status="pending"
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Increment usage
        increment_usage(current_user, db)
        
        # Start background processing
        background_tasks.add_task(
            process_transcription_background,
            str(transcription.id),
            "url",
            str(transcription_data.url)
        )
        
        logger.info(f"URL transcription started: {transcription.id}")
        
        return TranscriptionResponse(
            id=str(transcription.id),
            title=transcription.title,
            status=transcription.status,
            file_type=transcription.file_type,
            file_size=transcription.file_size,
            duration_seconds=transcription.duration_seconds,
            transcription_text=transcription.transcription_text,
            summary_text=transcription.summary_text,
            language=transcription.language,
            created_at=transcription.created_at.isoformat(),
            completed_at=transcription.completed_at.isoformat() if transcription.completed_at else None,
            processing_time_seconds=transcription.processing_time_seconds,
            error_message=transcription.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL transcription failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="URL transcription failed"
        )
@router.get("/{transcription_id}/export")
async def export_transcription(
    transcription_id: str,
    format: str = "txt",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export transcription in various formats
    """
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        if format == "txt":
            content = transcription.transcription_text or ""
            media_type = "text/plain"
            filename = f"{transcription.title}.txt"
            
        elif format == "pdf":
            # Generate PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add content to PDF
            text = transcription.transcription_text or ""
            lines = text.split('\n')
            y = 750
            
            p.drawString(50, 800, transcription.title)
            p.drawString(50, 780, f"Created: {transcription.created_at}")
            
            for line in lines:
                if y < 50:  # New page
                    p.showPage()
                    y = 750
                p.drawString(50, y, line[:80])  # Wrap long lines
                y -= 20
            
            p.save()
            content = buffer.getvalue()
            media_type = "application/pdf"
            filename = f"{transcription.title}.pdf"
            
        elif format == "srt":
            # Generate SRT subtitle format
            content = generate_srt_format(transcription.transcription_text or "")
            media_type = "text/plain"
            filename = f"{transcription.title}.srt"
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

def generate_srt_format(text: str) -> str:
    """Generate SRT subtitle format from transcription text"""
    if not text:
        return ""
    
    # Split text into chunks (roughly 10-15 words per subtitle)
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 12:  # 12 words per subtitle
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Generate SRT format
    srt_content = ""
    for i, chunk in enumerate(chunks, 1):
        start_time = (i - 1) * 4  # 4 seconds per subtitle
        end_time = i * 4
        
        start_formatted = format_srt_time(start_time)
        end_formatted = format_srt_time(end_time)
        
        srt_content += f"{i}\n"
        srt_content += f"{start_formatted} --> {end_formatted}\n"
        srt_content += f"{chunk}\n\n"
    
    return srt_content

def format_srt_time(seconds: int) -> str:
    """Format seconds into SRT time format (HH:MM:SS,mmm)"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"

@router.post("/{transcription_id}/share")
async def create_shareable_link(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a shareable public link for transcription
    """
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        # Generate a unique share token
        import secrets
        share_token = secrets.token_urlsafe(32)
        
        # Store share token in database (you might want to add a shares table)
        # For now, we'll use a simple approach
        share_url = f"{settings.FRONTEND_URL}/share/{share_token}"
        
        # You could store this in Redis or a shares table
        # For demo purposes, we'll return a basic share URL
        
        return {
            "share_url": share_url,
            "expires_at": "7 days"  # You can implement expiration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Share link creation failed: {e}")
        raise HTTPException(status_code=500, detail="Share link creation failed")

@router.post("/text", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_text_transcription(
    background_tasks: BackgroundTasks,
    transcription_data: TranscriptionText,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process uploaded text for summary and knowledge base
    """
    try:
        # Check usage limits
        check_usage_limits(current_user, db)
        
        # Create transcription record
        transcription = Transcription(
            user_id=current_user.id,
            title=transcription_data.title,
            file_type="text",
            generate_summary=transcription_data.generate_summary,
            add_to_knowledge_base=transcription_data.add_to_knowledge_base,
            status="pending"
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Increment usage
        increment_usage(current_user, db)
        
        # Start background processing
        background_tasks.add_task(
            process_transcription_background,
            str(transcription.id),
            "text",
            transcription_data.text
        )
        
        logger.info(f"Text processing started: {transcription.id}")
        
        return TranscriptionResponse(
            id=str(transcription.id),
            title=transcription.title,
            status=transcription.status,
            file_type=transcription.file_type,
            file_size=transcription.file_size,
            duration_seconds=transcription.duration_seconds,
            transcription_text=transcription.transcription_text,
            summary_text=transcription.summary_text,
            language=transcription.language,
            created_at=transcription.created_at.isoformat(),
            completed_at=transcription.completed_at.isoformat() if transcription.completed_at else None,
            processing_time_seconds=transcription.processing_time_seconds,
            error_message=transcription.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text processing failed"
        )

@router.get("/", response_model=TranscriptionList)
async def list_transcriptions(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's transcriptions with pagination
    """
    try:
        # Build query
        query = db.query(Transcription).filter(Transcription.user_id == current_user.id)
        
        if status_filter:
            query = query.filter(Transcription.status == status_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        transcriptions = query.order_by(
            Transcription.created_at.desc()
        ).offset(offset).limit(per_page).all()
        
        # Convert to response format
        transcription_list = []
        for t in transcriptions:
            transcription_list.append(TranscriptionResponse(
                id=str(t.id),
                title=t.title,
                status=t.status,
                file_type=t.file_type,
                file_size=t.file_size,
                duration_seconds=t.duration_seconds,
                transcription_text=t.transcription_text,
                summary_text=t.summary_text,
                language=t.language,
                created_at=t.created_at.isoformat(),
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
                processing_time_seconds=t.processing_time_seconds,
                error_message=t.error_message
            ))
        
        return TranscriptionList(
            transcriptions=transcription_list,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to list transcriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcriptions"
        )

@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific transcription details
    """
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if not transcription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcription not found"
            )
        
        return TranscriptionResponse(
            id=str(transcription.id),
            title=transcription.title,
            status=transcription.status,
            file_type=transcription.file_type,
            file_size=transcription.file_size,
            duration_seconds=transcription.duration_seconds,
            transcription_text=transcription.transcription_text,
            summary_text=transcription.summary_text,
            language=transcription.language,
            created_at=transcription.created_at.isoformat(),
            completed_at=transcription.completed_at.isoformat() if transcription.completed_at else None,
            processing_time_seconds=transcription.processing_time_seconds,
            error_message=transcription.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transcription {transcription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transcription"
        )

@router.delete("/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete transcription and associated data
    """
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if not transcription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcription not found"
            )
        
        # Delete from vector database if exists
        if transcription.qdrant_point_ids:
            await transcription_service.delete_from_qdrant(
                str(current_user.id),
                transcription.qdrant_point_ids
            )
        
        # Delete file from storage if exists
        if transcription.file_url and not transcription.file_url.startswith('http'):
            await file_service.delete_file(transcription.file_url)
        
        # Delete transcription record
        db.delete(transcription)
        db.commit()
        
        logger.info(f"Transcription deleted: {transcription_id}")
        return {"message": "Transcription deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete transcription {transcription_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transcription"
        )