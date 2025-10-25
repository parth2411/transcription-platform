# backend/app/services/groq_service.py (Rate-Limited Groq Client)
import os
import tempfile
import logging
from groq import Groq
from .rate_limiter import get_groq_rate_limiter

logger = logging.getLogger(__name__)


class GroqTranscriptionService:
    """
    Groq API client with built-in rate limiting for free tier protection
    """

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.rate_limiter = get_groq_rate_limiter()
        logger.info("Groq service initialized with rate limiting")

    async def transcribe_audio(self, audio_path: str, language: str = "auto") -> str:
        """
        Transcribe audio using Groq Whisper API with rate limiting

        Args:
            audio_path: Path to audio file
            language: Language code or "auto" for automatic detection

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails after retries
        """

        async def _transcribe():
            """Inner function for actual transcription"""
            try:
                with open(audio_path, 'rb') as audio_file:
                    # Use whisper-large-v3-turbo for faster processing
                    transcript = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        language=None if language == "auto" else language,
                        response_format="text"
                    )

                    # Handle response - could be string or object
                    if hasattr(transcript, 'text'):
                        return transcript.text
                    else:
                        return str(transcript)

            except Exception as e:
                error_msg = str(e).lower()

                # Handle rate limit errors
                if any(term in error_msg for term in ['rate limit', 'too many requests', '429']):
                    logger.warning(f"Groq rate limit hit: {e}")
                    raise  # Let rate_limiter handle retry

                # Log and raise other errors
                logger.error(f"Groq transcription failed: {e}")
                raise Exception(f"Transcription failed: {str(e)}")

        # Execute with rate limiting and retry logic
        try:
            result = await self.rate_limiter.execute_with_retry(_transcribe)
            return result

        except Exception as e:
            logger.error(f"All transcription attempts failed: {e}")
            raise

    async def generate_summary(self, text: str, max_tokens: int = 8000) -> str:
        """
        Generate summary using Groq LLM with rate limiting

        Args:
            text: Text to summarize
            max_tokens: Maximum tokens in response

        Returns:
            Generated summary
        """

        async def _generate():
            """Inner function for summary generation"""
            try:
                # Don't generate summary for very short texts
                if len(text.split()) < 50:
                    return "Text too short for meaningful summary."

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

                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3
                )

                return response.choices[0].message.content

            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                raise

        # Execute with rate limiting
        try:
            result = await self.rate_limiter.execute_with_retry(_generate)
            logger.info("Summary generated successfully")
            return result

        except Exception as e:
            logger.error(f"All summary generation attempts failed: {e}")
            return "Summary generation failed"

    def get_rate_limit_stats(self) -> dict:
        """Get current rate limit statistics"""
        return self.rate_limiter.get_stats()
