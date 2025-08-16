# backend/app/services/groq_service.py (Fixed Groq Client)
import os
import tempfile
import logging
from groq import Groq

logger = logging.getLogger(__name__)

class GroqTranscriptionService:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
    
    async def transcribe_audio(self, audio_path: str, language: str = "auto") -> str:
        """
        Transcribe audio using Groq Whisper API
        """
        try:
            with open(audio_path, 'rb') as audio_file:
                # Use the correct Groq API structure
                transcript = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language=None if language == "auto" else language,
                    response_format="text"
                )
                
                # Handle response - could be string or object
                if hasattr(transcript, 'text'):
                    return transcript.text
                else:
                    return str(transcript)
                    
        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            
            # Fallback: try alternative API call
            try:
                import requests
                
                with open(audio_path, 'rb') as audio_file:
                    files = {'file': audio_file}
                    data = {
                        'model': 'whisper-large-v3',
                        'response_format': 'text'
                    }
                    
                    response = requests.post(
                        'https://api.groq.com/openai/v1/audio/transcriptions',
                        headers={'Authorization': f'Bearer {api_key}'},
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        return response.text
                    else:
                        raise Exception(f"API request failed: {response.status_code}")
                        
            except Exception as fallback_error:
                logger.error(f"Fallback transcription also failed: {fallback_error}")
                raise Exception(f"Transcription failed: {str(e)}")
