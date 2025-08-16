# backend/app/services/transcription_service.py
import os
import subprocess
import uuid
import time
from typing import Optional, List, Tuple
from groq import Groq
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import tempfile
import shutil

from ..config import settings
from ..models import Transcription, User
from .file_service import FileService
from .groq_service import GroqTranscriptionService


logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.groq_service = GroqTranscriptionService(settings.GROQ_API_KEY)
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.file_service = FileService()
    
    async def _transcribe_with_groq(self, audio_path: str, language: str = "auto") -> str:
        """Use the new Groq service"""
        return await self.groq_service.transcribe_audio(audio_path, language)
    
    async def process_file_transcription(
        self, 
        db: Session, 
        transcription: Transcription, 
        file_path: str
    ) -> Transcription:
        """
        Process uploaded file for transcription
        """
        try:
            logger.info(f"Starting transcription processing for {transcription.id}")
            start_time = time.time()
            
            # Update status to processing
            transcription.status = "processing"
            db.commit()
            
            # Extract audio if needed
            audio_path = self._extract_audio_if_needed(file_path)
            
            # Get file duration
            duration = self._get_audio_duration(audio_path)
            transcription.duration_seconds = duration
            
            # Transcribe with Groq
            transcription_text = await self._transcribe_with_groq(audio_path, transcription.language)
            transcription.transcription_text = transcription_text
            
            # Generate summary if requested
            if transcription.generate_summary and transcription_text:
                summary = await self._generate_summary(transcription_text)
                transcription.summary_text = summary
            
            # Store in vector database if requested
            if transcription.add_to_knowledge_base and transcription_text:
                point_ids = await self._store_in_qdrant(
                    transcription_text, 
                    transcription.summary_text,
                    str(transcription.user_id),
                    str(transcription.id)
                )
                transcription.qdrant_point_ids = point_ids
                transcription.qdrant_collection = f"user_{transcription.user_id}_transcriptions"
            
            # Clean up temporary files
            if audio_path != file_path:
                os.remove(audio_path)
            
            # Update transcription record
            processing_time = int(time.time() - start_time)
            transcription.processing_time_seconds = processing_time
            transcription.status = "completed"
            transcription.completed_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Transcription {transcription.id} completed in {processing_time}s")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Transcription processing failed for {transcription.id}: {e}")
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            raise
    
    async def process_url_transcription(
        self, 
        db: Session, 
        transcription: Transcription, 
        url: str
    ) -> Transcription:
        """
        Process URL (YouTube, podcast) for transcription
        """
        try:
            logger.info(f"Starting URL transcription for {transcription.id}: {url}")
            
            # Update status
            transcription.status = "processing"
            db.commit()
            
            # Download audio from URL using yt-dlp
            temp_dir = tempfile.mkdtemp()
            try:
                audio_path = await self._download_audio_from_url(url, temp_dir)
                
                # Update file info
                transcription.file_size = os.path.getsize(audio_path)
                transcription.duration_seconds = self._get_audio_duration(audio_path)
                
                # Process like a regular file
                return await self.process_file_transcription(db, transcription, audio_path)
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"URL transcription failed for {transcription.id}: {e}")
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            raise
    
    async def process_text_transcription(
        self, 
        db: Session, 
        transcription: Transcription, 
        text: str
    ) -> Transcription:
        """
        Process uploaded text for summary and knowledge base
        """
        try:
            logger.info(f"Starting text processing for {transcription.id}")
            
            transcription.status = "processing"
            transcription.transcription_text = text
            db.commit()
            
            # Generate summary
            if transcription.generate_summary:
                summary = await self._generate_summary(text)
                transcription.summary_text = summary
            
            # Store in knowledge base
            if transcription.add_to_knowledge_base:
                point_ids = await self._store_in_qdrant(
                    text,
                    transcription.summary_text,
                    str(transcription.user_id),
                    str(transcription.id)
                )
                transcription.qdrant_point_ids = point_ids
                transcription.qdrant_collection = f"user_{transcription.user_id}_transcriptions"
            
            transcription.status = "completed"
            transcription.completed_at = datetime.utcnow()
            db.commit()
            
            return transcription
            
        except Exception as e:
            logger.error(f"Text processing failed for {transcription.id}: {e}")
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            raise
    
    def _extract_audio_if_needed(self, input_path: str) -> str:
        """Extract audio from video files if needed"""
        video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv')
        
        if not input_path.lower().endswith(video_extensions):
            return input_path
        
        # Create output path
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_audio.wav"
        
        # Extract audio using ffmpeg
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")
        
        return output_path
    
    def _get_audio_duration(self, audio_path: str) -> int:
        """Get audio duration in seconds using ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "csv=p=0", audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                return int(float(result.stdout.strip()))
            except ValueError:
                pass
        
        return 0
    
    async def _transcribe_with_groq(self, audio_path: str, language: str = "auto") -> str:
        """Transcribe audio using Groq Whisper"""
        try:
            with open(audio_path, 'rb') as audio_file:
                # Updated Groq API usage
                response = self.groq_client.audio.transcriptions.create(
                    file=("audio.wav", audio_file, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    language=None if language == "auto" else language,
                    response_format="text"
                )
                
                # Handle different response formats
                if hasattr(response, 'text'):
                    transcription = response.text
                else:
                    transcription = str(response)
                    
                logger.info(f"Transcription completed, length: {len(transcription)} characters")
                return transcription
                
        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    async def _generate_summary(self, text: str) -> str:
        """Generate summary using Groq"""
        try:
            prompt = f"""
            Generate a comprehensive summary of the following transcription organized into clear sections.
            Use markdown formatting with headers (##) for main sections and bullet points for key details.
            
            Transcription:
            {text}
            
            Please provide the summary with sections like:
            ## Overview
            ## Key Discussion Points  
            ## Important Decisions/Actions
            ## Conclusion
            
            Keep it concise but comprehensive.
            """
            
            response = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            logger.info("Summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return "Summary generation failed"
    
    async def _store_in_qdrant(
        self, 
        transcription: str, 
        summary: Optional[str], 
        user_id: str,
        transcription_id: str
    ) -> List[str]:
        """Store transcription and summary in Qdrant vector database"""
        try:
            collection_name = f"user_{user_id}_transcriptions"
            
            # Ensure collection exists
            try:
                self.qdrant_client.get_collection(collection_name)
            except:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={"size": 384, "distance": "Cosine"}
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
            
            point_ids = []
            
            # Store transcription
            transcription_vector = self.embedder.encode(transcription).tolist()
            transcription_point_id = str(uuid.uuid4())
            
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[{
                    "id": transcription_point_id,
                    "vector": transcription_vector,
                    "payload": {
                        "text": transcription,
                        "type": "transcription",
                        "user_id": user_id,
                        "transcription_id": transcription_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }]
            )
            point_ids.append(transcription_point_id)
            
            # Store summary if available
            if summary:
                summary_vector = self.embedder.encode(summary).tolist()
                summary_point_id = str(uuid.uuid4())
                
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[{
                        "id": summary_point_id,
                        "vector": summary_vector,
                        "payload": {
                            "text": summary,
                            "type": "summary",
                            "user_id": user_id,
                            "transcription_id": transcription_id,
                            "created_at": datetime.utcnow().isoformat()
                        }
                    }]
                )
                point_ids.append(summary_point_id)
            
            logger.info(f"Stored {len(point_ids)} points in Qdrant collection {collection_name}")
            return point_ids
            
        except Exception as e:
            logger.error(f"Qdrant storage failed: {e}")
            return []
    
    async def _download_audio_from_url(self, url: str, output_dir: str) -> str:
        """Download audio from URL using yt-dlp"""
        output_path = os.path.join(output_dir, "downloaded_audio.wav")
        
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", output_path.replace('.wav', '.%(ext)s'),
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"URL download failed: {result.stderr}")
        
        # Find the actual output file (yt-dlp might change the extension)
        for file in os.listdir(output_dir):
            if file.startswith("downloaded_audio"):
                actual_path = os.path.join(output_dir, file)
                if not file.endswith('.wav'):
                    # Convert to wav if needed
                    wav_path = output_path
                    subprocess.run([
                        "ffmpeg", "-y", "-i", actual_path,
                        "-ar", "16000", "-ac", "1", wav_path
                    ], capture_output=True)
                    os.remove(actual_path)
                    return wav_path
                return actual_path
        
        raise RuntimeError("Downloaded file not found")
    
    async def delete_from_qdrant(self, user_id: str, point_ids: List[str]) -> bool:
        """Delete points from Qdrant collection"""
        try:
            collection_name = f"user_{user_id}_transcriptions"
            
            self.qdrant_client.delete(
                collection_name=collection_name,
                points_selector=point_ids
            )
            
            logger.info(f"Deleted {len(point_ids)} points from Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")
            return False