# backend/app/services/transcription_service.py
import os
import subprocess
import uuid
import time
import json
import math
from typing import Optional, List, Tuple, Dict, Any
from groq import Groq
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import tempfile
import shutil
import re
import asyncio
from fastapi import UploadFile

from ..config import settings
from ..models import Transcription, User
from .file_service import FileService
from .rate_limiter import get_groq_rate_limiter
from .diarization_service import get_diarization_service

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self):
        # Fix tokenizers warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        # Initialize Groq client with rate limiting
        try:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            self.rate_limiter = get_groq_rate_limiter()
            logger.info("✅ Groq client initialized with rate limiting")
            self.groq_available = True
        except Exception as e:
            logger.error(f"❌ Groq initialization failed: {e}")
            self.groq_client = None
            self.groq_available = False

        # Initialize diarization service
        try:
            self.diarization_service = get_diarization_service()
            if self.diarization_service.enabled:
                logger.info("✅ Diarization service enabled")
            else:
                logger.info("ℹ️ Diarization service disabled")
        except Exception as e:
            logger.error(f"❌ Diarization initialization failed: {e}")
            self.diarization_service = None

        # Vector database now uses pgvector through KnowledgeService
        logger.info("ℹ️ Using Supabase pgvector for embeddings (via KnowledgeService)")
        self.qdrant_available = False  # Kept for backward compatibility checks

        # Initialize embedder
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedder initialized")
            self.embedder_available = True
        except Exception as e:
            logger.error(f"❌ Embedder initialization failed: {e}")
            self.embedder = None
            self.embedder_available = False

        # Initialize file service
        self.file_service = FileService()

        # Enhanced limits and settings for large video support
        self.MAX_FILE_SIZE = 24 * 1024 * 1024  # 24MB (safely under Groq's 25MB limit)
        self.CHUNK_SIZE_MINUTES = 8  # Process in 8-minute chunks
        self.MAX_DURATION_MINUTES = 120  # 2 hour limit
        self.DOWNLOAD_TIMEOUT = 600  # 10 minutes
        self.PROCESSING_TIMEOUT = 300  # 5 minutes per chunk

    def _check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            # Check yt-dlp
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("yt-dlp not found. Please install: pip install yt-dlp")
            
            # Check ffmpeg
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not found. Please install FFmpeg")
                
            logger.info("All dependencies verified successfully")
            
        except FileNotFoundError as e:
            if 'yt-dlp' in str(e):
                raise RuntimeError("yt-dlp not found. Install with: pip install yt-dlp")
            elif 'ffmpeg' in str(e):
                raise RuntimeError("FFmpeg not found. Please install FFmpeg")
            else:
                raise RuntimeError(f"Dependency check failed: {e}")

    async def _get_video_duration(self, url: str) -> int:
        """Get video duration before downloading"""
        try:
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                str(url)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = info.get('duration', 0)
                return int(duration) if duration else 0
            
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")
        
        return 0

    async def _extract_video_info(self, url: str) -> Dict[str, str]:
        """Extract video information including title using yt-dlp"""
        try:
            self._check_dependencies()
            
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "--no-playlist",
                # Bot protection bypass
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--extractor-args", "youtube:player_client=android", "--extractor-retries", "5",
                str(url)
            ]
            
            logger.info(f"Extracting video info for: {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Could not extract video info: {result.stderr}")
                return self._generate_fallback_info(url)
            
            try:
                video_info = json.loads(result.stdout)
                
                # Extract relevant information
                title = video_info.get('title', '').strip()
                uploader = video_info.get('uploader', '').strip()
                duration = video_info.get('duration', 0)
                upload_date = video_info.get('upload_date', '')
                description = video_info.get('description', '')[:200]  # First 200 chars
                
                # Clean and format title
                if title:
                    title = self._clean_title(title)
                else:
                    title = self._generate_fallback_title(url)
                
                return {
                    'title': title,
                    'uploader': uploader,
                    'duration': str(duration) if duration else '0',
                    'upload_date': upload_date,
                    'description': description,
                    'url': url
                }
                
            except json.JSONDecodeError:
                logger.warning("Could not parse video info JSON")
                return self._generate_fallback_info(url)
                
        except subprocess.TimeoutExpired:
            logger.warning("Video info extraction timeout")
            return self._generate_fallback_info(url)
        except Exception as e:
            logger.warning(f"Video info extraction failed: {e}")
            return self._generate_fallback_info(url)

    def _clean_title(self, title: str) -> str:
        """Clean and format video title"""
        # Remove common unwanted patterns
        title = re.sub(r'\s*\|\s*.*$', '', title)  # Remove "| Channel Name" suffix
        title = re.sub(r'\s*-\s*YouTube\s*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\s*\[.*?\]\s*', '', title)  # Remove [tags] at start
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)  # Remove (info) at end
        
        # Clean up whitespace and special characters
        title = re.sub(r'\s+', ' ', title).strip()
        title = title[:100]  # Limit length
        
        return title if title else "Untitled Video"

    def _generate_fallback_info(self, url: str) -> Dict[str, str]:
        """Generate fallback info when video info extraction fails"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Try to extract domain for better fallback title
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            title = f"Content from {domain} - {timestamp}"
        except:
            title = f"Audio/Video Content - {timestamp}"
        
        return {
            'title': title,
            'uploader': 'Unknown',
            'duration': '0',
            'upload_date': '',
            'description': '',
            'url': url
        }

    def _generate_fallback_title(self, url: str) -> str:
        """Generate a fallback title from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            
            # Extract meaningful part from path
            path_parts = [p for p in parsed.path.split('/') if p and p != 'watch']
            if path_parts:
                last_part = path_parts[-1]
                # Remove file extensions
                last_part = re.sub(r'\.[a-zA-Z0-9]+$', '', last_part)
                # Replace hyphens and underscores with spaces
                last_part = re.sub(r'[-_]+', ' ', last_part)
                if len(last_part) > 3:  # If meaningful content
                    return f"{last_part.title()} - {domain}"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"Content from {domain} - {timestamp}"
            
        except:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"Audio/Video Content - {timestamp}"

    def generate_auto_title(self, transcription_text: str = None, file_name: str = None) -> str:
        """Generate automatic title from transcription text or file name"""
        try:
            # If we have transcription text, try to generate a smart title
            if transcription_text and len(transcription_text.strip()) > 50:
                # Take first meaningful sentence
                sentences = transcription_text.split('.')
                for sentence in sentences[:3]:  # Check first 3 sentences
                    clean_sentence = sentence.strip()
                    if len(clean_sentence) > 10 and len(clean_sentence) < 80:
                        # Remove common filler words from start
                        clean_sentence = re.sub(r'^(um|uh|so|well|okay|alright|now)\s+', '', clean_sentence, flags=re.IGNORECASE)
                        return clean_sentence.capitalize()
            
            # If we have a filename, use it
            if file_name:
                name = os.path.splitext(os.path.basename(file_name))[0]
                name = re.sub(r'[-_]+', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 3:
                    return name.title()
            
            # Default timestamp-based title
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"Transcription - {timestamp}"
            
        except Exception as e:
            logger.warning(f"Auto title generation failed: {e}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            return f"Transcription - {timestamp}"

    async def _download_audio_from_url(self, url: str, output_dir: str) -> Tuple[str, Dict[str, str]]:
        """Enhanced download with large video support"""
        try:
            self._check_dependencies()
            
            # Check video duration first
            duration_seconds = await self._get_video_duration(url)
            duration_minutes = duration_seconds / 60 if duration_seconds else 0
            
            logger.info(f"Video duration: {duration_minutes:.1f} minutes")
            
            # Check if video is too long
            if duration_minutes > self.MAX_DURATION_MINUTES:
                raise RuntimeError(
                    f"Video too long ({duration_minutes:.1f} minutes). "
                    f"Maximum supported duration: {self.MAX_DURATION_MINUTES} minutes"
                )
            
            # First extract video info
            video_info = await self._extract_video_info(url)
            
            output_template = os.path.join(output_dir, "downloaded_audio.%(ext)s")
            
            # Enhanced yt-dlp command with bot protection bypass
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",  # Use MP3 for better compression
                "--audio-quality", "5",   # Medium quality for size balance
                "--no-playlist",
                "--prefer-free-formats",
                "--format", "bestaudio[filesize<50M]/bestaudio/best[filesize<50M]",  # Prefer smaller files
                "--max-filesize", "50M",  # Hard limit on source file size
                # Bot protection bypass
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "--add-header", "Accept-Language:en-us,en;q=0.5",
                "--add-header", "Sec-Fetch-Mode:navigate",
                "--extractor-args", "youtube:player_client=android", "--extractor-retries", "5",
                "--retries", "3",
                "-o", output_template,
                str(url)
            ]
            
            logger.info(f"Starting download: {video_info.get('title', 'Unknown')}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.DOWNLOAD_TIMEOUT)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp failed: {result.stderr}")
                if "File is larger than max-filesize" in result.stderr:
                    raise RuntimeError("Video file is too large. Try a shorter video or different quality.")
                elif "Unsupported URL" in result.stderr:
                    raise RuntimeError("This URL is not supported. Please try a different link.")
                elif "Video unavailable" in result.stderr:
                    raise RuntimeError("Video is unavailable or private. Please check the URL.")
                elif "Sign in to confirm" in result.stderr or "bot" in result.stderr.lower():
                    raise RuntimeError(
                        "YouTube is blocking this video due to bot protection. "
                        "Please try a different video or wait a few minutes and try again. "
                        "Some videos with strict protection cannot be downloaded."
                    )
                else:
                    raise RuntimeError(f"Download failed: {result.stderr}")
            
            # Find downloaded file
            downloaded_files = [f for f in os.listdir(output_dir) if f.startswith("downloaded_audio")]
            if not downloaded_files:
                raise RuntimeError("No audio file was downloaded")
            
            audio_path = os.path.join(output_dir, downloaded_files[0])
            
            # Convert to WAV for processing
            wav_path = await self._convert_to_wav_optimized(audio_path)
            
            logger.info(f"Successfully downloaded and converted: {wav_path}")
            return wav_path, video_info
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Download timeout. The video might be too large or connection is slow.")
        except Exception as e:
            logger.error(f"URL download failed: {e}")
            raise RuntimeError(f"Download failed: {str(e)}")

    async def _convert_to_wav_optimized(self, input_path: str) -> str:
        """Convert to optimized WAV format"""
        try:
            wav_path = input_path.replace(os.path.splitext(input_path)[1], '.wav')
            
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000",      # 16kHz sample rate (optimized for speech)
                "-ac", "1",          # Mono
                "-c:a", "pcm_s16le", # 16-bit PCM
                wav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.PROCESSING_TIMEOUT)
            if result.returncode != 0:
                raise RuntimeError(f"Audio conversion failed: {result.stderr}")
            
            # Remove original file to save space
            if os.path.exists(input_path) and input_path != wav_path:
                os.remove(input_path)
                
            file_size = os.path.getsize(wav_path)
            logger.info(f"Converted to WAV: {file_size / (1024*1024):.1f} MB")
                
            return wav_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio conversion timeout")

    async def _split_audio_into_chunks(self, audio_path: str, chunk_minutes: int = None) -> List[str]:
        """Split large audio files into smaller chunks for processing"""
        if chunk_minutes is None:
            chunk_minutes = self.CHUNK_SIZE_MINUTES
            
        try:
            # Get total duration
            duration = await self._get_audio_duration(audio_path)
            if duration <= chunk_minutes * 60:
                return [audio_path]  # No need to split
            
            chunk_duration = chunk_minutes * 60  # Convert to seconds
            num_chunks = math.ceil(duration / chunk_duration)
            
            logger.info(f"Splitting {duration/60:.1f} minute audio into {num_chunks} chunks")
            
            chunks = []
            base_path = os.path.splitext(audio_path)[0]
            
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = f"{base_path}_chunk_{i+1:03d}.wav"
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", audio_path,
                    "-ss", str(start_time),
                    "-t", str(chunk_duration),
                    "-ar", "16000", "-ac", "1",
                    chunk_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and os.path.exists(chunk_path):
                    # Check if chunk has audio content
                    chunk_size = os.path.getsize(chunk_path)
                    if chunk_size > 1000:  # At least 1KB
                        chunks.append(chunk_path)
                        logger.info(f"Created chunk {i+1}/{num_chunks}: {chunk_size/(1024*1024):.1f}MB")
                    else:
                        os.remove(chunk_path)  # Remove empty chunks
                else:
                    logger.warning(f"Failed to create chunk {i+1}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Audio splitting failed: {e}")
            return [audio_path]  # Fall back to original file

    async def _transcribe_with_groq_chunked(self, audio_path: str, language: str = "auto") -> str:
        """Enhanced transcription with chunking support for large files"""
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Transcribing audio file: {file_size/(1024*1024):.1f}MB")
            
            # If file is small enough, transcribe directly
            if file_size <= self.MAX_FILE_SIZE:
                return await self._transcribe_single_file(audio_path, language)
            
            # Split into chunks and transcribe each
            logger.info("File too large, splitting into chunks...")
            chunks = await self._split_audio_into_chunks(audio_path)
            
            if len(chunks) == 1:
                return await self._transcribe_single_file(chunks[0], language)
            
            # Transcribe each chunk
            transcriptions = []
            total_chunks = len(chunks)
            
            for i, chunk_path in enumerate(chunks):
                try:
                    logger.info(f"Transcribing chunk {i+1}/{total_chunks}")
                    chunk_transcription = await self._transcribe_single_file(chunk_path, language)
                    
                    if chunk_transcription.strip():
                        transcriptions.append(f"[Segment {i+1}] {chunk_transcription}")
                    
                    # Clean up chunk file
                    if os.path.exists(chunk_path) and chunk_path != audio_path:
                        os.remove(chunk_path)
                        
                except Exception as e:
                    logger.error(f"Failed to transcribe chunk {i+1}: {e}")
                    transcriptions.append(f"[Segment {i+1}] [Transcription failed: {str(e)}]")
            
            # Combine all transcriptions
            full_transcription = "\n\n".join(transcriptions)
            logger.info(f"Combined transcription completed, total length: {len(full_transcription)} characters")
            
            return full_transcription
            
        except Exception as e:
            logger.error(f"Chunked transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    async def _transcribe_single_file(self, audio_path: str, language: str = "auto") -> str:
        """Transcribe a single audio file with rate limiting"""
        try:
            file_size = os.path.getsize(audio_path)

            # Final check for file size
            if file_size > self.MAX_FILE_SIZE:
                # Try to compress further
                compressed_path = await self._compress_audio_aggressive(audio_path)
                if os.path.getsize(compressed_path) <= self.MAX_FILE_SIZE:
                    audio_path = compressed_path
                else:
                    raise RuntimeError(f"File still too large after compression: {file_size/(1024*1024):.1f}MB")

            async def _do_transcription():
                """Inner function for actual API call"""
                with open(audio_path, 'rb') as audio_file:
                    response = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3",
                        language=None if language == "auto" else language,
                        response_format="text"
                    )

                    if hasattr(response, 'text'):
                        transcription = response.text
                    else:
                        transcription = str(response)

                    if not transcription or transcription.strip() == "":
                        raise RuntimeError("Empty transcription received")

                    return transcription

            # Execute with rate limiting
            result = await self.rate_limiter.execute_with_retry(_do_transcription)
            return result

        except Exception as e:
            logger.error(f"Single file transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    async def _compress_audio_aggressive(self, audio_path: str) -> str:
        """Aggressively compress audio for very large files"""
        try:
            compressed_path = audio_path.replace('.wav', '_compressed.wav')
            
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000",    # Lower sample rate
                "-ac", "1",        # Mono
                "-b:a", "32k",     # Very low bitrate
                compressed_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"Aggressive compression failed: {result.stderr}")
                return audio_path
            
            compressed_size = os.path.getsize(compressed_path)
            original_size = os.path.getsize(audio_path)
            
            logger.info(f"Compressed from {original_size/(1024*1024):.1f}MB to {compressed_size/(1024*1024):.1f}MB")
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Aggressive compression error: {e}")
            return audio_path
    # Fixed real-time transcription handling

    async def _convert_to_wav_safe(self, input_path: str, output_path: str = None):
        """Safe audio conversion with better WebM handling"""
        try:
            if output_path is None:
                output_path = input_path.replace(os.path.splitext(input_path)[1], '.wav')
            
            # First, try to probe the file to see if it's valid
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-show_format", "-show_streams", 
                "-print_format", "json", input_path
            ]
            
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            
            if probe_result.returncode != 0:
                # File is corrupted or invalid
                logger.error(f"Invalid audio file detected: {input_path}")
                logger.error(f"FFprobe error: {probe_result.stderr}")
                raise RuntimeError("Invalid or corrupted audio file")
            
            # Try to parse the probe result
            try:
                probe_data = json.loads(probe_result.stdout)
                if not probe_data.get('streams'):
                    raise RuntimeError("No audio streams found in file")
            except json.JSONDecodeError:
                logger.warning("Could not parse probe data, continuing with conversion attempt")
            
            # Enhanced conversion command with error recovery
            cmd = [
                "ffmpeg", "-y", 
                "-i", input_path,
                "-vn",  # No video
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",      # Mono
                "-c:a", "pcm_s16le",  # PCM format
                "-f", "wav",     # Force WAV format
                "-avoid_negative_ts", "make_zero",  # Handle timing issues
                "-fflags", "+genpts",  # Generate presentation timestamps
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Audio conversion failed: {result.stderr}")
                raise RuntimeError(f"Audio conversion failed: {result.stderr}")
            
            # Verify the output file exists and has content
            if not os.path.exists(output_path):
                raise RuntimeError("Conversion completed but output file not found")
            
            file_size = os.path.getsize(output_path)
            if file_size < 1000:  # Less than 1KB indicates likely empty/corrupt file
                raise RuntimeError(f"Output file too small ({file_size} bytes), likely corrupted")
            
            logger.info(f"Successfully converted audio: {file_size} bytes")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio conversion timeout - file may be corrupted")
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            raise RuntimeError(f"Audio conversion failed: {str(e)}")

    # Add this method to handle real-time audio better
    async def _handle_realtime_audio(self, audio_data: bytes, temp_dir: str) -> str:
        """Handle real-time audio data with validation"""
        try:
            # Save the audio data
            temp_path = os.path.join(temp_dir, f"realtime_audio_{int(time.time())}.webm")
            
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            
            # Check file size
            file_size = os.path.getsize(temp_path)
            logger.info(f"Received audio file: {file_size} bytes")
            
            if file_size < 1000:  # Less than 1KB
                raise RuntimeError(f"Audio file too small ({file_size} bytes), likely empty or corrupted")
            
            # Try to convert to WAV
            wav_path = os.path.join(temp_dir, f"converted_audio_{int(time.time())}.wav")
            converted_path = await self._convert_to_wav_safe(temp_path, wav_path)
            
            # Clean up original
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return converted_path
            
        except Exception as e:
            logger.error(f"Real-time audio handling failed: {e}")
            raise RuntimeError(f"Real-time audio processing failed: {str(e)}")
    
    async def _convert_to_wav_detailed(self, input_path: str, output_path: str):
        """Convert audio with detailed error handling"""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"Audio conversion failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio conversion timeout")

    async def _transcribe_with_groq(self, audio_path: str, language: str = "auto") -> str:
        """
        Enhanced Groq transcription with English translation
        Always translates to English regardless of source language
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")

            # Check file size
            file_size = os.path.getsize(audio_path)
            if file_size > self.MAX_FILE_SIZE:
                raise RuntimeError(f"File too large: {file_size/(1024*1024):.1f}MB")

            # Skip very small files
            if file_size < 1024:
                logger.warning("File too small, skipping transcription")
                return ""

            # Determine file type
            file_ext = os.path.splitext(audio_path)[1].lower()
            logger.info(f"Processing {file_ext} file of size {file_size} bytes")

            async def _do_transcription():
                with open(audio_path, "rb") as audio_file:
                    # Use translations endpoint to ALWAYS get English output
                    # This automatically translates any language to English
                    response = self.groq_client.audio.translations.create(
                        file=audio_file,
                        model="whisper-large-v3",
                        response_format="text",
                        temperature=0.0,
                        prompt="Translate and transcribe the following audio to clear English."
                    )

                transcription = response.strip() if isinstance(response, str) else (response.text.strip() if hasattr(response, 'text') else str(response))

                if transcription:
                    logger.info(f"English transcription successful: {len(transcription)} characters")
                else:
                    logger.warning("Empty transcription result")

                return transcription

            # Execute with rate limiting
            return await self.rate_limiter.execute_with_retry(_do_transcription)

        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            return ""

    async def _compress_audio(self, audio_path: str) -> str:
        """Compress audio file to reduce size"""
        try:
            compressed_path = audio_path.replace('.wav', '_compressed.wav')
            
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000",
                "-ac", "1",
                "-b:a", "64k",
                compressed_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Audio compression failed: {result.stderr}")
                return audio_path
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Audio compression error: {e}")
            return audio_path

    async def _generate_summary(self, text: str) -> str:
        """Generate summary using Groq with rate limiting"""
        try:
            # Don't generate summary for very short texts
            if len(text.split()) < 50:
                return "Text too short for meaningful summary."

            async def _do_summary():
                """Inner function for actual API call"""
                prompt = f"""You are an expert at creating clear, concise, and actionable summaries of transcribed conversations.

Please analyze the following transcription and create a well-structured summary in markdown format.

**TRANSCRIPTION:**
{text}

**INSTRUCTIONS:**
1. Create clear section headers using ## markdown syntax
2. Use bullet points for key information
3. Extract main topics, decisions, and action items
4. Identify speakers' key points (if multiple speakers)
5. Highlight any important dates, numbers, or deadlines
6. Keep language professional and clear

**REQUIRED SECTIONS:**
## 📋 Overview
Brief 2-3 sentence summary of the entire conversation

## 💡 Key Points
- Main topics discussed (bullet points)
- Important insights or revelations

## ✅ Decisions Made
- Any decisions, agreements, or conclusions reached

## 📌 Action Items
- Tasks to be completed
- Responsibilities assigned
- Deadlines mentioned

## 🔍 Additional Notes
- Any other relevant information

Keep the summary concise yet comprehensive. Focus on what matters most."""

                response = self.groq_client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[
                        {"role": "system", "content": "You are a professional transcription analyst who creates clear, actionable summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=8000,
                    temperature=0.2
                )

                return response.choices[0].message.content

            # Execute with rate limiting
            summary = await self.rate_limiter.execute_with_retry(_do_summary)
            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return "Summary generation failed"

    async def _convert_to_wav(self, audio_path: str) -> str:
        """
        Enhanced audio conversion with WebM support for real-time chunks
        """
        try:
            # Check if input is already WAV
            if audio_path.lower().endswith('.wav'):
                return audio_path
            
            # Generate output path
            base_path = os.path.splitext(audio_path)[0]
            wav_path = f"{base_path}.wav"
            
            # Get file size to determine processing approach
            file_size = os.path.getsize(audio_path)
            logger.info(f"Converting audio file: {file_size} bytes")
            
            # For very small files (< 1KB), skip conversion - likely invalid
            if file_size < 1024:
                logger.warning(f"Audio file too small ({file_size} bytes), skipping conversion")
                raise RuntimeError("Audio file too small to process")
            
            # Enhanced FFmpeg command for WebM chunks
            if audio_path.lower().endswith('.webm'):
                # Special handling for WebM real-time chunks
                cmd = [
                    "ffmpeg", "-y", "-v", "error",  # Suppress verbose output
                    "-f", "webm",  # Force WebM input format
                    "-i", audio_path,
                    "-vn",  # No video
                    "-ar", "16000",  # 16kHz sample rate
                    "-ac", "1",  # Mono
                    "-acodec", "pcm_s16le",  # PCM 16-bit
                    "-f", "wav",  # Force WAV output
                    wav_path
                ]
            else:
                # Standard conversion for other formats
                cmd = [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", audio_path,
                    "-vn",
                    "-ar", "16000",
                    "-ac", "1", 
                    "-acodec", "pcm_s16le",
                    wav_path
                ]
            
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            
            # Run conversion with timeout
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=os.path.dirname(audio_path) if os.path.dirname(audio_path) else None
            )
            
            if result.returncode == 0 and os.path.exists(wav_path):
                output_size = os.path.getsize(wav_path)
                logger.info(f"Conversion successful: {file_size} → {output_size} bytes")
                return wav_path
            else:
                # If standard conversion fails, try alternative approach
                logger.warning(f"Standard conversion failed, trying alternative method")
                return await self._convert_webm_alternative(audio_path)
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timed out")
            raise RuntimeError("Audio conversion timed out")
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise RuntimeError(f"Audio conversion failed: {str(e)}")
        
    async def _convert_webm_alternative(self, audio_path: str) -> str:
        """
        Alternative WebM conversion method for problematic chunks
        """
        try:
            base_path = os.path.splitext(audio_path)[0]
            wav_path = f"{base_path}_alt.wav"
            
            # Try with different WebM handling
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-fflags", "+genpts",  # Generate presentation timestamps
                "-avoid_negative_ts", "make_zero",  # Handle timing issues
                "-i", audio_path,
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                "-f", "wav",
                wav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(wav_path):
                logger.info("Alternative WebM conversion successful")
                return wav_path
            else:
                # If all conversions fail, try to send WebM directly to Groq
                logger.warning("All conversions failed, attempting direct WebM transcription")
                return await self._handle_webm_direct(audio_path)
                
        except Exception as e:
            logger.error(f"Alternative conversion failed: {e}")
            raise RuntimeError(f"Could not convert audio: {str(e)}")
    async def _handle_webm_direct(self, audio_path: str) -> str:
        """
        Handle WebM files directly without conversion (Groq supports WebM)
        """
        try:
            # Check if Groq can handle the WebM directly
            file_size = os.path.getsize(audio_path)
            
            if file_size > self.MAX_FILE_SIZE:
                raise RuntimeError(f"WebM file too large: {file_size} bytes")
            
            # Return original path for direct Groq processing
            logger.info("Using WebM file directly for transcription")
            return audio_path
            
        except Exception as e:
            logger.error(f"Direct WebM handling failed: {e}")
            raise RuntimeError("Cannot process WebM file")
    
    def _extract_audio_if_needed(self, input_path: str) -> str:
        """Extract audio from video files if needed"""
        try:
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
                logger.error(f"Audio extraction failed: {result.stderr}")
                raise RuntimeError(f"Audio extraction failed: {result.stderr}")
            
            logger.info(f"Successfully extracted audio: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return input_path
    
    def _get_audio_duration(self, audio_path: str) -> int:
        """Get audio duration in seconds using ffprobe"""
        try:
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
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0
    
    async def _store_in_knowledge_base(
        self,
        db: Session,
        transcription: str,
        summary: str = None,
        user_id: str = None,
        transcription_id: str = None,
        metadata: Dict = None
    ) -> bool:
        """Store transcription and summary in pgvector knowledge base"""

        if not self.embedder_available:
            logger.warning("Embedder not available, skipping vector storage")
            return False

        try:
            from .knowledge_service import KnowledgeService

            knowledge_service = KnowledgeService(db)

            # Store the transcription with chunks
            await knowledge_service.store_transcription_with_chunks(
                transcription_id=transcription_id,
                user_id=user_id,
                transcription_text=transcription,
                summary_text=summary,
                title=metadata.get('title') if metadata else None
            )

            logger.info(f"Successfully stored transcription in pgvector knowledge base")
            return True

        except Exception as e:
            logger.error(f"Failed to store in knowledge base: {e}")
            return False

    async def delete_from_knowledge_base(self, db: Session, transcription_id: str) -> bool:
        """Delete transcription from pgvector knowledge base"""
        try:
            from .knowledge_service import KnowledgeService

            knowledge_service = KnowledgeService(db)
            await knowledge_service.delete_transcription(transcription_id)

            logger.info(f"Deleted transcription {transcription_id} from knowledge base")
            return True

        except Exception as e:
            logger.error(f"Failed to delete from knowledge base: {e}")
            return False
    
    async def process_file_transcription(
        self, 
        db: Session, 
        transcription: Transcription, 
        file_path: str
    ) -> Transcription:
        """
        Process uploaded file for transcription with enhanced large file support
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
            duration = await self._get_audio_duration(audio_path)
            transcription.duration_seconds = duration

            # Enhanced transcription with chunking support
            transcription_text = await self._transcribe_with_groq_chunked(audio_path, transcription.language)
            transcription.transcription_text = transcription_text

            # Generate smart AI-powered title from content (or use timestamp fallback)
            if not transcription.title or transcription.title.strip() == "":
                file_name_fallback = self.generate_auto_title(file_name=file_path)
                transcription.title = await self._generate_smart_title(
                    transcription_text,
                    fallback=file_name_fallback
                )
                logger.info(f"Generated smart title: {transcription.title}")
            
            # Generate summary if requested
            if transcription.generate_summary and transcription_text:
                summary = await self._generate_summary(transcription_text)
                transcription.summary_text = summary
            
            # Store in knowledge base if requested
            if transcription.add_to_knowledge_base and transcription_text:
                await self._store_in_knowledge_base(
                    db=db,
                    transcription=transcription_text,
                    summary=transcription.summary_text,
                    user_id=str(transcription.user_id),
                    transcription_id=str(transcription.id),
                    metadata={
                        "title": transcription.title,
                        "created_at": transcription.created_at.isoformat(),
                        "type": "file_upload",
                        "duration_seconds": duration
                    }
                )
            
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
        Process URL with enhanced large video support and auto title extraction
        """
        try:
            logger.info(f"Starting URL transcription for {transcription.id}: {url}")
            
            # Update status
            transcription.status = "processing"
            db.commit()
            
            # Download audio from URL using enhanced method with video info
            temp_dir = tempfile.mkdtemp()
            try:
                audio_path, video_info = await self._download_audio_from_url(url, temp_dir)

                # Update file info
                transcription.file_size = os.path.getsize(audio_path)
                transcription.duration_seconds = await self._get_audio_duration(audio_path)

                # Enhanced transcription with chunking support
                transcription_text = await self._transcribe_with_groq_chunked(audio_path, transcription.language)
                transcription.transcription_text = transcription_text

                # Generate smart title from content (fallback to video title or timestamp)
                if not transcription.title or transcription.title.strip() == "":
                    video_title_fallback = video_info.get('title', self.generate_auto_title())
                    transcription.title = await self._generate_smart_title(
                        transcription_text,
                        fallback=video_title_fallback
                    )
                    logger.info(f"Generated smart title: {transcription.title}")
                
                # Generate summary if requested
                if transcription.generate_summary and transcription_text:
                    summary = await self._generate_summary(transcription_text)
                    transcription.summary_text = summary
                
                # Store in knowledge base if requested
                if transcription.add_to_knowledge_base and transcription_text:
                    await self._store_in_knowledge_base(
                        db=db,
                        transcription=transcription_text,
                        summary=transcription.summary_text,
                        user_id=str(transcription.user_id),
                        transcription_id=str(transcription.id),
                        metadata={
                            "title": transcription.title,
                            "created_at": transcription.created_at.isoformat(),
                            "type": "url_download",
                            "source_url": str(url),
                            "uploader": video_info.get('uploader', ''),
                            "duration_seconds": transcription.duration_seconds
                        }
                    )
                
                # Mark as completed
                transcription.status = "completed"
                transcription.completed_at = datetime.utcnow()
                processing_time = int(time.time() - time.time())
                transcription.processing_time_seconds = processing_time
                
                db.commit()
                logger.info(f"URL transcription completed for {transcription.id}")
                
                return transcription
                
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

            # Generate smart AI-powered title from content (or use timestamp fallback)
            if not transcription.title or transcription.title.strip() == "":
                transcription.title = await self._generate_smart_title(text)
                logger.info(f"Generated smart title: {transcription.title}")
            
            # Generate summary
            if transcription.generate_summary:
                summary = await self._generate_summary(text)
                transcription.summary_text = summary
            
            # Store in knowledge base
            if transcription.add_to_knowledge_base:
                await self._store_in_knowledge_base(
                    db=db,
                    transcription=text,
                    summary=transcription.summary_text,
                    user_id=str(transcription.user_id),
                    transcription_id=str(transcription.id),
                    metadata={
                        "title": transcription.title,
                        "created_at": transcription.created_at.isoformat(),
                        "type": "text_input"
                    }
                )
            
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
    # Add these debug methods to your TranscriptionService class

    
    async def _transcribe_with_groq_streaming(
        self, 
        audio_path: str, 
        language: str = "auto",
        context: str = "",
        chunk_number: int = 1
    ) -> str:
        """
        Enhanced transcription for real-time streaming with context awareness
        """
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Transcribing streaming chunk {chunk_number}: {file_size/(1024):.1f}KB")
            
            # Skip very small files
            if file_size < 1024:  # Less than 1KB
                return ""
            
            # Ensure file is not too large for streaming
            if file_size > self.MAX_FILE_SIZE:
                # Try to compress for streaming
                compressed_path = await self._compress_audio_for_streaming(audio_path)
                if os.path.getsize(compressed_path) <= self.MAX_FILE_SIZE:
                    audio_path = compressed_path
                else:
                    logger.warning(f"Streaming chunk too large: {file_size/(1024*1024):.1f}MB")
                    return ""
            
            # Enhanced transcription with streaming optimizations
            with open(audio_path, "rb") as audio_file:
                # Build prompt for better context continuity
                prompt = self._build_streaming_prompt(context, chunk_number)
                
                # Use Groq Whisper with streaming-optimized parameters
                response = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language=language if language != "auto" else None,
                    prompt=prompt,
                    response_format="text",
                    temperature=0.1,  # Lower temperature for more consistent results
                )
                
                # Clean and filter the transcription
                transcription = self._clean_streaming_transcription(
                    response.strip(), 
                    context,
                    chunk_number
                )
                
                if transcription:
                    logger.info(f"Streaming transcription {chunk_number}: {len(transcription)} chars")
                
                return transcription
                
        except Exception as e:
            logger.error(f"Streaming transcription failed for chunk {chunk_number}: {e}")
            return ""

    def _build_streaming_prompt(self, context: str, chunk_number: int) -> str:
        """
        Build context-aware prompt for better transcription continuity
        """
        if not context or chunk_number == 1:
            return "Transcribe the following audio clearly and accurately."
        
        # Get last few words from context for continuity
        context_words = context.split()
        if len(context_words) > 10:
            recent_context = " ".join(context_words[-10:])
            return f"Continue transcribing. Previous context: ...{recent_context}"
        else:
            return f"Continue transcribing. Previous: {context}"

    def _clean_streaming_transcription(
        self, 
        transcription: str, 
        context: str, 
        chunk_number: int
    ) -> str:
        """
        Clean and filter transcription for streaming with duplicate detection
        """
        if not transcription:
            return ""
        
        # Remove common transcription artifacts
        cleaned = transcription.strip()
        
        # Remove leading/trailing whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Filter out very short or meaningless transcriptions
        if len(cleaned) < 3:
            return ""
        
        # Filter out common false positives
        false_positives = [
            "thank you", "thanks", "bye", "hello", "hi", "um", "uh", "ah",
            "you know", "like", "so", "well", "yeah", "yes", "no", "okay"
        ]
        
        if cleaned.lower().strip() in false_positives:
            return ""
        
        # Check for repetition with recent context
        if context and len(context) > 10:
            # Get last 50 characters of context
            recent_context = context[-50:].lower()
            if cleaned.lower() in recent_context:
                return ""  # Skip if already transcribed recently
        
        # Remove obvious repetitions within the same transcription
        words = cleaned.split()
        if len(words) > 2:
            # Check for immediate word repetition (e.g., "the the the")
            filtered_words = []
            prev_word = ""
            repeat_count = 0
            
            for word in words:
                if word.lower() == prev_word.lower():
                    repeat_count += 1
                    if repeat_count < 2:  # Allow one repetition
                        filtered_words.append(word)
                else:
                    filtered_words.append(word)
                    repeat_count = 0
                    prev_word = word
            
            cleaned = " ".join(filtered_words)
        
        return cleaned

    async def _compress_audio_for_streaming(self, audio_path: str) -> str:
        """
        Compress audio specifically for streaming transcription
        """
        try:
            base_path = os.path.splitext(audio_path)[0]
            compressed_path = f"{base_path}_stream_compressed.wav"
            
            # More aggressive compression for streaming
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ar", "8000",  # Lower sample rate for streaming
                "-ac", "1",     # Mono
                "-ab", "32k",   # Lower bitrate
                "-f", "wav",
                compressed_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(compressed_path):
                new_size = os.path.getsize(compressed_path)
                original_size = os.path.getsize(audio_path)
                
                logger.info(f"Compressed streaming audio: {original_size/(1024):.1f}KB → {new_size/(1024):.1f}KB")
                return compressed_path
            else:
                logger.warning("Streaming compression failed, using original")
                return audio_path
                
        except Exception as e:
            logger.error(f"Streaming compression error: {e}")
            return audio_path

    async def process_complete_realtime_recording(
        self, 
        transcription: Transcription, 
        audio_file: UploadFile,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process complete real-time recording with enhanced final transcription
        """
        try:
            # Save audio file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_path = temp_file.name

            # Convert to WAV
            wav_path = await self._convert_to_wav(temp_path)
            
            # Get duration
            duration = await self._get_audio_duration(wav_path)
            transcription.duration_seconds = int(duration)
            
            # Enhanced final transcription (not chunked for better quality)
            start_time = time.time()
            final_text = await self._transcribe_with_groq(wav_path, transcription.language)
            processing_time = time.time() - start_time

            transcription.transcription_text = final_text
            transcription.processing_time_seconds = int(processing_time)

            # Generate smart AI-powered title from content (or use timestamp fallback)
            if not transcription.title or transcription.title.strip() == "" or transcription.title == "Real-time Recording":
                transcription.title = await self._generate_smart_title(
                    final_text,
                    fallback=f"Recording - {datetime.now().strftime('%b %d, %Y at %I:%M %p')}"
                )
                logger.info(f"Generated smart title for real-time recording: {transcription.title}")
            
            # Generate summary if requested
            summary_text = ""
            if transcription.generate_summary and final_text:
                try:
                    summary_text = await self._generate_summary(final_text)
                    transcription.summary_text = summary_text
                except Exception as e:
                    logger.error(f"Summary generation failed: {e}")
            
            # Store in knowledge base if requested
            stored_in_kb = False
            if transcription.add_to_knowledge_base and final_text:
                try:
                    from ..services.knowledge_service import KnowledgeService
                    knowledge_service = KnowledgeService()
                    
                    await knowledge_service.store_transcription(
                        transcription_id=transcription.id,
                        title=transcription.title,
                        content=final_text,
                        summary=summary_text,
                        user_id=transcription.user_id
                    )
                    stored_in_kb = True
                except Exception as e:
                    logger.error(f"Knowledge base storage failed: {e}")
            
            # Update transcription status
            transcription.status = "completed"
            transcription.completed_at = datetime.utcnow()
            
            # Update user usage
            user = db.query(User).filter(User.id == transcription.user_id).first()
            if user:
                user.monthly_transcription_count += 1
            
            db.commit()
            
            # Clean up temporary files
            for path in [temp_path, wav_path]:
                if os.path.exists(path):
                    os.remove(path)
            
            logger.info(f"Real-time recording processed successfully: {transcription.id}")
            
            return {
                "id": transcription.id,
                "text": final_text,
                "summary": summary_text,
                "status": "completed",
                "stored_in_knowledge_base": stored_in_kb,
                "duration_seconds": transcription.duration_seconds,
                "processing_time_seconds": transcription.processing_time_seconds,
                "title": transcription.title,
                "created_at": transcription.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Real-time recording processing failed: {e}")
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            raise RuntimeError(f"Processing failed: {str(e)}")

    async def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get audio duration using ffprobe
        """
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.warning("Could not determine audio duration")
                return 0.0
                
        except Exception as e:
            logger.error(f"Duration detection failed: {e}")
            return 0.0
    async def _transcribe_live_chunk(self, audio_path: str) -> str:
        """
        Transcribe live audio chunks (for real-time recording)
        Uses transcriptions API (faster, works with small WebM files)
        Returns text in original language - translation happens on final complete
        """
        try:
            logger.info(f"Transcribing live chunk: {audio_path}")

            # Check file size
            file_size = os.path.getsize(audio_path)

            # Skip very small files (less than 10KB)
            if file_size < 10240:
                logger.warning(f"Chunk too small ({file_size} bytes), skipping")
                return ""

            # Determine file type
            file_ext = os.path.splitext(audio_path)[1].lower()
            logger.info(f"Processing live {file_ext} chunk of size {file_size} bytes")

            async def _do_transcription():
                with open(audio_path, "rb") as audio_file:
                    # Use transcriptions API for live chunks (works better with WebM)
                    response = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",  # Turbo for speed
                        response_format="text",
                        temperature=0.0,
                        language="en"  # Hint that we expect English, but accepts any language
                    )

                transcription = response.strip() if isinstance(response, str) else (response.text.strip() if hasattr(response, 'text') else str(response))

                if transcription:
                    logger.info(f"Live chunk transcribed: {len(transcription)} characters")
                else:
                    logger.debug("Empty transcription from chunk")

                return transcription

            # Execute with rate limiting
            return await self.rate_limiter.execute_with_retry(_do_transcription)

        except Exception as e:
            logger.error(f"Live chunk transcription failed: {e}")
            return ""  # Return empty string, don't fail the whole stream

    async def _generate_smart_title(self, text: str, fallback: str = None) -> str:
        """
        Generate a smart, concise title from transcription content using AI
        Falls back to timestamp-based title if AI fails
        
        Args:
            text: Transcription text to analyze
            fallback: Optional fallback title
            
        Returns:
            Generated title (max 100 characters)
        """
        try:
            # If text is too short, use timestamp
            if len(text.split()) < 10:
                return fallback or f"Transcription - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Use first 500 words for title generation (faster)
            sample_text = " ".join(text.split()[:500])
            
            async def _do_title_generation():
                """Inner function for AI title generation"""
                prompt = f"""Generate a short, descriptive title (maximum 10 words) for this transcription.

The title should:
- Be clear and specific about the content
- Be concise (under 10 words)
- Use title case
- NOT include quotes or special characters
- Focus on the main topic or theme

Transcription excerpt:
{sample_text}

Respond with ONLY the title, nothing else."""

                response = self.groq_client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[
                        {"role": "system", "content": "You are a title generator. Generate short, clear titles."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.3
                )
                
                title = response.choices[0].message.content.strip()
                
                # Clean up the title
                title = title.strip('"\'')  # Remove quotes
                title = ' '.join(title.split())  # Normalize whitespace
                
                # Limit length
                if len(title) > 100:
                    title = title[:97] + "..."
                
                return title
            
            # Execute with rate limiting
            title = await self.rate_limiter.execute_with_retry(_do_title_generation)
            
            # Validate title
            if title and len(title) > 5 and len(title) < 150:
                logger.info(f"Generated smart title: {title}")
                return title
            else:
                raise ValueError("Generated title is invalid")
                
        except Exception as e:
            logger.warning(f"Smart title generation failed: {e}, using fallback")
            # Fallback to timestamp-based title
            return fallback or f"Transcription - {datetime.now().strftime('%b %d, %Y at %I:%M %p')}"
