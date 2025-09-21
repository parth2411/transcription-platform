# backend/app/services/speaker_diarization_service.py - CREATE NEW FILE
import logging
import re
from typing import List, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

class SpeakerDiarizationService:
    """Speaker Diarization Service with rule-based approach"""
    
    def __init__(self):
        self.use_advanced = False  # Set to True when you have PyAnnote setup
        
    async def apply_speaker_diarization(
        self, 
        audio_path: str, 
        transcription_text: str,
        method: str = "rule_based"
    ) -> str:
        """Apply speaker diarization using available method"""
        
        try:
            if method == "rule_based" or not self.use_advanced:
                return await self._diarize_rule_based(transcription_text)
            else:
                # Future: Add advanced methods here
                return await self._diarize_rule_based(transcription_text)
                
        except Exception as e:
            logger.error(f"Speaker diarization failed: {e}")
            return f"[Speaker 1]: {transcription_text}"

    async def _diarize_rule_based(self, transcription_text: str) -> str:
        """Simple rule-based speaker diarization"""
        try:
            # Split text into sentences
            sentences = re.split(r'[.!?]+', transcription_text)
            
            diarized_text = ""
            current_speaker = 1
            
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if sentence:
                    # Simple rules for speaker changes
                    if i > 0:
                        # Look for dialogue indicators
                        if any(word in sentence.lower() for word in ['yes', 'no', 'right', 'okay', 'well']):
                            if i % 3 == 0:  # Change speaker occasionally
                                current_speaker = 2 if current_speaker == 1 else 1
                        
                        # Change speaker every 3-4 sentences
                        elif i % 4 == 0:
                            current_speaker = 2 if current_speaker == 1 else 1
                    
                    diarized_text += f"[Speaker {current_speaker}]: {sentence}. "
            
            return diarized_text.strip()
            
        except Exception as e:
            logger.error(f"Rule-based diarization failed: {e}")
            return f"[Speaker 1]: {transcription_text}"
    
    def get_speaker_count(self, diarized_text: str) -> int:
        """Count number of speakers in diarized text"""
        try:
            speakers = set()
            matches = re.findall(r'\[Speaker (\d+)\]:', diarized_text)
            for match in matches:
                speakers.add(int(match))
            return len(speakers)
        except:
            return 1