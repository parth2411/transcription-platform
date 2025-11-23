# backend/app/services/realtime_transcription_service.py
"""
Real-time Transcription Service
Handles streaming audio transcription using Groq Whisper API
"""

import os
import tempfile
import asyncio
import logging
from typing import Optional
from groq import Groq
from .rate_limiter import get_groq_rate_limiter

logger = logging.getLogger(__name__)


class RealtimeTranscriptionService:
    """
    Service for real-time audio transcription using Groq Whisper
    Buffers audio chunks and processes them periodically
    """

    def __init__(self, api_key: str, buffer_duration: int = 5):
        """
        Initialize the real-time transcription service

        Args:
            api_key: Groq API key
            buffer_duration: Seconds of audio to buffer before transcribing
        """
        self.client = Groq(api_key=api_key)
        self.rate_limiter = get_groq_rate_limiter()
        self.buffer_duration = buffer_duration
        logger.info(f"Real-time transcription service initialized (buffer: {buffer_duration}s)")

    async def transcribe_chunk(
        self,
        audio_data: bytes,
        language: str = "en",
        previous_context: Optional[str] = None
    ) -> dict:
        """
        Transcribe a single audio chunk

        Args:
            audio_data: Raw audio bytes (WebM format from browser)
            language: Language code
            previous_context: Previous transcript for context (improves accuracy)

        Returns:
            dict: {
                "text": str,
                "is_final": bool,
                "confidence": float,
                "language": str
            }
        """

        async def _transcribe():
            """Inner function for actual transcription"""
            temp_file = None
            try:
                # Save audio chunk to temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    suffix='.webm',
                    delete=False
                )
                temp_file.write(audio_data)
                temp_file.flush()
                temp_file.close()

                # Transcribe with Groq Whisper
                with open(temp_file.name, 'rb') as audio_file:
                    # Use whisper-large-v3-turbo for faster real-time processing
                    # Note: Groq's API doesn't support streaming, so we process chunks
                    transcript_response = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        language=language if language != "auto" else None,
                        response_format="verbose_json",  # Get detailed response
                        temperature=0.0  # More deterministic for real-time
                    )

                    # Extract text
                    text = ""
                    if hasattr(transcript_response, 'text'):
                        text = transcript_response.text
                    else:
                        text = str(transcript_response)

                    # Calculate confidence (if available)
                    confidence = 1.0
                    if hasattr(transcript_response, 'segments') and transcript_response.segments:
                        # Average confidence from segments
                        confidences = [
                            seg.get('avg_logprob', 0)
                            for seg in transcript_response.segments
                        ]
                        if confidences:
                            # Convert log probability to confidence (rough approximation)
                            avg_logprob = sum(confidences) / len(confidences)
                            confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))

                    # Detect language
                    detected_language = language
                    if hasattr(transcript_response, 'language'):
                        detected_language = transcript_response.language

                    return {
                        "text": text.strip(),
                        "is_final": True,  # Each chunk is final
                        "confidence": confidence,
                        "language": detected_language
                    }

            except Exception as e:
                error_msg = str(e).lower()

                # Handle rate limit errors
                if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
                    logger.warning(f"Groq rate limit hit during real-time transcription: {e}")
                    raise  # Let rate_limiter handle retry

                # Handle empty audio
                if 'invalid' in error_msg or 'empty' in error_msg:
                    logger.debug(f"Empty or invalid audio chunk")
                    return {
                        "text": "",
                        "is_final": False,
                        "confidence": 0.0,
                        "language": language
                    }

                # Log and raise other errors
                logger.error(f"Real-time transcription failed: {e}")
                return {
                    "text": "",
                    "is_final": False,
                    "confidence": 0.0,
                    "language": language,
                    "error": str(e)
                }

            finally:
                # Clean up temporary file
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass

        # Execute with rate limiting
        try:
            result = await self.rate_limiter.execute_with_retry(_transcribe)
            return result

        except Exception as e:
            logger.error(f"Real-time transcription attempt failed: {e}")
            return {
                "text": "",
                "is_final": False,
                "confidence": 0.0,
                "language": language,
                "error": str(e)
            }

    async def transcribe_buffer(
        self,
        audio_chunks: list,
        language: str = "en"
    ) -> dict:
        """
        Transcribe a buffer of audio chunks

        Args:
            audio_chunks: List of audio bytes
            language: Language code

        Returns:
            dict with transcription result
        """
        # Combine chunks into single audio data
        combined_audio = b''.join(audio_chunks)

        # Transcribe combined audio
        return await self.transcribe_chunk(combined_audio, language)

    def get_rate_limit_stats(self) -> dict:
        """Get current rate limit statistics"""
        return self.rate_limiter.get_stats()
