"""
Speaker Diarization Service
Uses pyannote.audio for speaker identification and segmentation
"""
import os
import logging
import tempfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """Represents a segment of speech by a speaker"""
    start: float  # Start time in seconds
    end: float  # End time in seconds
    speaker: str  # Speaker label (e.g., "SPEAKER_00")
    text: Optional[str] = None  # Transcribed text for this segment
    confidence: float = 1.0


class DiarizationService:
    """
    Speaker diarization service using pyannote.audio
    Identifies and segments different speakers in audio
    """

    def __init__(self, huggingface_token: Optional[str] = None, enabled: bool = False):
        self.enabled = enabled
        self.huggingface_token = huggingface_token
        self.pipeline = None

        if self.enabled and self.huggingface_token:
            try:
                self._initialize_pipeline()
            except Exception as e:
                logger.error(f"Failed to initialize diarization pipeline: {e}")
                self.enabled = False
        else:
            logger.info("Diarization service disabled or no HuggingFace token provided")

    def _initialize_pipeline(self):
        """Initialize the pyannote diarization pipeline"""
        try:
            from pyannote.audio import Pipeline

            # Load pre-trained speaker diarization pipeline
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.huggingface_token
            )

            # Move to GPU if available
            import torch
            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
                logger.info("Diarization pipeline initialized on GPU")
            else:
                logger.info("Diarization pipeline initialized on CPU")

        except ImportError as e:
            logger.error(
                "pyannote.audio not installed. Install with: "
                "pip install pyannote.audio"
            )
            raise RuntimeError(
                "Diarization dependencies not installed. "
                "Please install: pip install pyannote.audio torch torchaudio"
            )
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            raise

    async def diarize_audio(
        self,
        audio_path: str,
        min_speakers: int = 1,
        max_speakers: int = 10
    ) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to audio file
            min_speakers: Minimum number of speakers to detect
            max_speakers: Maximum number of speakers to detect

        Returns:
            List of speaker segments with timing information
        """
        if not self.enabled or not self.pipeline:
            logger.warning("Diarization not enabled or pipeline not initialized")
            return []

        try:
            logger.info(f"Starting diarization for: {audio_path}")

            # Run diarization
            diarization = self.pipeline(
                audio_path,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )

            # Convert to speaker segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = SpeakerSegment(
                    start=turn.start,
                    end=turn.end,
                    speaker=speaker
                )
                segments.append(segment)

            logger.info(
                f"Diarization completed: Found {len(set(s.speaker for s in segments))} speakers "
                f"across {len(segments)} segments"
            )

            return segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []

    def align_transcription_with_speakers(
        self,
        transcription: str,
        speaker_segments: List[SpeakerSegment],
        word_timestamps: Optional[List[Dict]] = None
    ) -> List[SpeakerSegment]:
        """
        Align transcription text with speaker segments

        Args:
            transcription: Full transcription text
            speaker_segments: List of speaker timing segments
            word_timestamps: Optional word-level timestamps from Whisper

        Returns:
            Speaker segments with aligned text
        """
        if not speaker_segments:
            return []

        try:
            if word_timestamps:
                # Use word-level timestamps for precise alignment
                return self._align_with_word_timestamps(
                    word_timestamps,
                    speaker_segments
                )
            else:
                # Simple alignment by splitting text proportionally
                return self._align_simple(transcription, speaker_segments)

        except Exception as e:
            logger.error(f"Transcription alignment failed: {e}")
            return speaker_segments

    def _align_with_word_timestamps(
        self,
        word_timestamps: List[Dict],
        speaker_segments: List[SpeakerSegment]
    ) -> List[SpeakerSegment]:
        """Align using word-level timestamps"""
        aligned_segments = []

        for segment in speaker_segments:
            # Find words that fall within this speaker's time range
            segment_words = [
                word['word']
                for word in word_timestamps
                if segment.start <= word['start'] < segment.end
            ]

            segment.text = ' '.join(segment_words).strip()
            aligned_segments.append(segment)

        return aligned_segments

    def _align_simple(
        self,
        transcription: str,
        speaker_segments: List[SpeakerSegment]
    ) -> List[SpeakerSegment]:
        """Simple proportional text alignment"""
        words = transcription.split()
        total_duration = speaker_segments[-1].end if speaker_segments else 0

        if total_duration == 0:
            return speaker_segments

        aligned_segments = []
        word_index = 0

        for segment in speaker_segments:
            # Calculate proportion of total time
            segment_duration = segment.end - segment.start
            proportion = segment_duration / total_duration

            # Assign proportional number of words
            num_words = max(1, int(len(words) * proportion))
            segment_words = words[word_index:word_index + num_words]

            segment.text = ' '.join(segment_words).strip()
            aligned_segments.append(segment)

            word_index += num_words

        return aligned_segments

    def format_transcript_with_speakers(
        self,
        speaker_segments: List[SpeakerSegment],
        format_type: str = "simple"
    ) -> str:
        """
        Format transcript with speaker labels

        Args:
            speaker_segments: List of speaker segments with text
            format_type: Format type ("simple", "detailed", "json")

        Returns:
            Formatted transcript string
        """
        if not speaker_segments:
            return ""

        if format_type == "json":
            return json.dumps(
                [
                    {
                        "speaker": seg.speaker,
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": seg.text or "",
                        "duration": round(seg.end - seg.start, 2)
                    }
                    for seg in speaker_segments
                ],
                indent=2
            )

        elif format_type == "detailed":
            lines = []
            for seg in speaker_segments:
                timestamp = f"[{self._format_time(seg.start)} --> {self._format_time(seg.end)}]"
                lines.append(f"{seg.speaker} {timestamp}")
                lines.append(f"  {seg.text or '(no text)'}")
                lines.append("")
            return "\n".join(lines)

        else:  # simple format
            lines = []
            current_speaker = None

            for seg in speaker_segments:
                if seg.speaker != current_speaker:
                    if current_speaker is not None:
                        lines.append("")  # Add blank line between speakers
                    lines.append(f"**{seg.speaker}:**")
                    current_speaker = seg.speaker

                if seg.text:
                    lines.append(seg.text)

            return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_speaker_statistics(
        self,
        speaker_segments: List[SpeakerSegment]
    ) -> Dict[str, Dict]:
        """
        Get statistics about speaker participation

        Returns:
            Dictionary with speaker statistics
        """
        if not speaker_segments:
            return {}

        stats = {}

        for segment in speaker_segments:
            if segment.speaker not in stats:
                stats[segment.speaker] = {
                    "total_time": 0.0,
                    "num_segments": 0,
                    "word_count": 0
                }

            duration = segment.end - segment.start
            stats[segment.speaker]["total_time"] += duration
            stats[segment.speaker]["num_segments"] += 1

            if segment.text:
                stats[segment.speaker]["word_count"] += len(segment.text.split())

        # Add percentages
        total_time = sum(s["total_time"] for s in stats.values())
        for speaker_stats in stats.values():
            speaker_stats["percentage"] = round(
                (speaker_stats["total_time"] / total_time * 100) if total_time > 0 else 0,
                2
            )
            speaker_stats["total_time"] = round(speaker_stats["total_time"], 2)

        return stats


# Global diarization service instance
_diarization_service: Optional[DiarizationService] = None


def get_diarization_service() -> DiarizationService:
    """Get or create the global diarization service"""
    global _diarization_service

    if _diarization_service is None:
        from ..config import settings

        _diarization_service = DiarizationService(
            huggingface_token=settings.HUGGINGFACE_TOKEN,
            enabled=settings.DIARIZATION_ENABLED
        )
        logger.info("Global diarization service created")

    return _diarization_service
