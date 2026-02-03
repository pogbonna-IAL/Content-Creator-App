"""
Text-to-Speech (TTS) Provider Interface and Implementations
Adapter pattern for supporting multiple TTS engines
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import logging
import os
import sys

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        format: str = "wav"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier (provider-specific)
            speed: Speech speed multiplier (0.5-2.0, default 1.0)
            format: Output format ('wav', 'mp3', etc.)
        
        Returns:
            Tuple of (audio_bytes, metadata_dict)
            metadata_dict should contain:
            - duration_sec: float
            - format: str
            - sample_rate: int
            - voice_id: str
            - text_hash: str (hash of input text for deduplication)
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> list[str]:
        """Get list of available voice IDs"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS provider is available/configured"""
        pass


class PiperTTSProvider(TTSProvider):
    """Piper TTS provider (open-source, local runtime)"""
    
    def __init__(self, model_path: Optional[str] = None, piper_binary: Optional[str] = None):
        """
        Initialize Piper TTS provider
        
        Args:
            model_path: Path to Piper model directory or file
            piper_binary: Path to piper binary (default: 'piper' in PATH)
        """
        self.model_path = model_path or os.getenv("PIPER_MODEL_PATH", "models/piper")
        self.piper_binary = piper_binary or os.getenv("PIPER_BINARY", "piper")
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Piper is available"""
        # First try Python API
        try:
            from piper import PiperVoice
            return True
        except ImportError:
            pass
        
        # Fallback to binary check
        try:
            import subprocess
            result = subprocess.run(
                [self.piper_binary, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning(f"Piper TTS not available: {self.piper_binary} not found")
            return False
    
    def is_available(self) -> bool:
        """Check if Piper is available"""
        return self._available
    
    def get_available_voices(self) -> list[str]:
        """Get list of available voices"""
        # Default Piper voices (can be extended)
        return [
            "en_US-lessac-medium",
            "en_US-lessac-high",
            "en_US-amy-medium",
            "en_US-amy-high",
            "en_GB-alba-medium",
            "en_GB-alba-high",
        ]
    
    def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        format: str = "wav"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Synthesize speech using Piper
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier (defaults to first available voice)
            speed: Speech speed (0.5-2.0)
            format: Output format ('wav' supported)
        
        Returns:
            Tuple of (audio_bytes, metadata_dict)
        """
        if not self._available:
            raise RuntimeError("Piper TTS is not available. Install piper-tts or set PIPER_BINARY.")
        
        if format != "wav":
            raise ValueError(f"Piper only supports 'wav' format, got '{format}'")
        
        import hashlib
        import tempfile
        import wave
        import io
        
        # Hash text for metadata
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        # Try Python API first
        try:
            from piper import PiperVoice
            
            # Resolve "default" to actual voice ID first
            actual_voice_id = voice_id
            if voice_id == "default":
                available_voices = self.get_available_voices()
                if available_voices:
                    actual_voice_id = available_voices[0]
                    logger.info(f"[TTS_SYNTHESIS] Resolved 'default' to voice_id: {actual_voice_id}")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Resolved 'default' to voice_id: {actual_voice_id}", file=sys.stdout, flush=True)
                else:
                    logger.error("[TTS_SYNTHESIS] No available voices found")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] ERROR: No available voices found", file=sys.stderr, flush=True)
                    raise RuntimeError("No Piper voices available. Check piper-tts installation.")
            
            # Resolve voice model path (will download if needed)
            logger.info(f"[TTS_SYNTHESIS] Resolving voice model for voice_id: {actual_voice_id}")
            print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Resolving voice model for voice_id: {actual_voice_id}", file=sys.stdout, flush=True)
            
            voice_model = None
            try:
                voice_model = self._resolve_voice_model(actual_voice_id)
                logger.info(f"[TTS_SYNTHESIS] Resolved voice model path: {voice_model}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Resolved voice model path: {voice_model}", file=sys.stdout, flush=True)
                
                # Verify file exists
                if voice_model and os.path.exists(voice_model):
                    file_size = os.path.getsize(voice_model)
                    logger.info(f"[TTS_SYNTHESIS] Voice model file exists, size: {file_size} bytes")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Voice model file exists, size: {file_size} bytes", file=sys.stdout, flush=True)
                else:
                    logger.warning(f"[TTS_SYNTHESIS] Voice model file not found at resolved path: {voice_model}")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Voice model file not found at resolved path: {voice_model}", file=sys.stderr, flush=True)
                    # Don't raise error yet - try loading by voice_id directly (PiperVoice might auto-download)
                    logger.info(f"[TTS_SYNTHESIS] Will try loading by voice_id directly (PiperVoice may auto-download)")
                    voice_model = None  # Signal to try direct loading
            except FileNotFoundError as resolve_error:
                logger.warning(f"[TTS_SYNTHESIS] Voice model not found, will try direct loading: {resolve_error}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Voice model not found, will try direct loading: {resolve_error}", file=sys.stderr, flush=True)
                voice_model = None  # Signal to try direct loading
            except Exception as resolve_error:
                logger.warning(f"[TTS_SYNTHESIS] Failed to resolve voice model, will try direct loading: {resolve_error}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Failed to resolve voice model, will try direct loading: {resolve_error}", file=sys.stderr, flush=True)
                voice_model = None  # Try direct loading as fallback
            
            # Load voice - PiperVoice.load can also accept voice_id directly
            # Try loading by path first, then by voice_id (which may auto-download)
            voice = None
            
            if voice_model and os.path.exists(voice_model):
                logger.info(f"[TTS_SYNTHESIS] Loading PiperVoice from path: {voice_model}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Loading PiperVoice from path: {voice_model}", file=sys.stdout, flush=True)
                
                try:
                    voice = PiperVoice.load(voice_model, config_path=None)
                    logger.info(f"[TTS_SYNTHESIS] Successfully loaded PiperVoice from file")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Successfully loaded PiperVoice from file", file=sys.stdout, flush=True)
                except Exception as load_error:
                    logger.warning(f"[TTS_SYNTHESIS] Failed to load voice from path {voice_model}: {load_error}")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Failed to load from path, will try voice_id: {load_error}", file=sys.stderr, flush=True)
                    voice = None  # Will try voice_id next
            
            # If path loading failed or no path, try loading by actual_voice_id directly
            # PiperVoice.load(voice_id) may auto-download the model
            if voice is None:
                logger.info(f"[TTS_SYNTHESIS] Loading PiperVoice by voice_id (may auto-download): {actual_voice_id}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Loading PiperVoice by voice_id (may auto-download): {actual_voice_id}", file=sys.stdout, flush=True)
                try:
                    voice = PiperVoice.load(actual_voice_id)
                    logger.info(f"[TTS_SYNTHESIS] Successfully loaded PiperVoice by voice_id (auto-download may have occurred)")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Successfully loaded PiperVoice by voice_id", file=sys.stdout, flush=True)
                except Exception as voice_id_error:
                    logger.warning(f"[TTS_SYNTHESIS] Failed to load by voice_id {actual_voice_id}, trying hyphen version: {voice_id_error}")
                    print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Failed to load by voice_id {actual_voice_id}, trying hyphen version: {voice_id_error}", file=sys.stderr, flush=True)
                    # Try with hyphen version as fallback
                    try:
                        voice_id_hyphen = actual_voice_id.replace('_', '-')
                        logger.info(f"[TTS_SYNTHESIS] Trying hyphen version: {voice_id_hyphen}")
                        print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Trying hyphen version: {voice_id_hyphen}", file=sys.stdout, flush=True)
                        voice = PiperVoice.load(voice_id_hyphen)
                        logger.info(f"[TTS_SYNTHESIS] Successfully loaded PiperVoice with hyphen version")
                        print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Successfully loaded PiperVoice with hyphen version", file=sys.stdout, flush=True)
                    except Exception as hyphen_error:
                        logger.error(f"[TTS_SYNTHESIS] All loading methods failed for voice_id {actual_voice_id}", exc_info=True)
                        print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] All loading methods failed. Original: {voice_id_error}, Hyphen: {hyphen_error}", file=sys.stderr, flush=True)
                        # Don't raise error here - let it be caught by the outer exception handler
                        raise FileNotFoundError(
                            f"Piper model not found and could not be auto-downloaded. "
                            f"Voice ID: {actual_voice_id} (resolved from '{voice_id}'). "
                            f"Tried paths: {voice_model if voice_model else 'N/A'}. "
                            f"Set PIPER_MODEL_PATH or install piper models. "
                            f"To download models automatically, ensure piper-tts package is installed with download support."
                        )
            
            if voice is None:
                raise FileNotFoundError(f"Failed to load Piper voice model for {actual_voice_id} (resolved from '{voice_id}')")
            
            # Synthesize (PiperVoice.synthesize returns generator of AudioChunk objects)
            # Speed control may not be available in Python API, synthesize as-is
            # Note: Speed parameter is ignored for Python API (would need SynthesisConfig)
            audio_generator = voice.synthesize(text)
            # Extract audio data from chunks (AudioChunk has audio_int16_bytes attribute)
            audio_chunks = []
            sample_rate = None
            sample_width = None
            sample_channels = None
            for chunk in audio_generator:
                # AudioChunk has audio_int16_bytes attribute (raw PCM data)
                audio_chunks.append(chunk.audio_int16_bytes)
                if sample_rate is None:
                    sample_rate = chunk.sample_rate
                    sample_width = chunk.sample_width
                    sample_channels = chunk.sample_channels
            
            # Convert raw PCM to WAV format
            raw_audio = b''.join(audio_chunks)
            num_frames = len(raw_audio) // (sample_width * sample_channels)
            duration_sec = num_frames / float(sample_rate)
            
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(sample_channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(raw_audio)
            audio_bytes = wav_buffer.getvalue()
            
            metadata = {
                "duration_sec": duration_sec,
                "format": "wav",
                "sample_rate": sample_rate,
                "voice_id": voice_id,
                "text_hash": text_hash,
                "provider": "piper"
            }
            
            return audio_bytes, metadata
            
        except ImportError:
            # Fallback to binary subprocess
            import subprocess
            
            # Resolve voice model path
            voice_model = self._resolve_voice_model(voice_id)
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                output_path = tmp_file.name
            
            try:
                # Build piper command
                cmd = [
                    self.piper_binary,
                    "--model", voice_model,
                    "--output_file", output_path,
                ]
                
                # Add speed control (length_scale = 1/speed)
                if speed != 1.0:
                    length_scale = 1.0 / speed
                    cmd.extend(["--length_scale", str(length_scale)])
                
                # Run piper
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate(input=text, timeout=300)  # 5 min timeout
                
                if process.returncode != 0:
                    raise RuntimeError(f"Piper TTS failed: {stderr}")
                
                # Read generated audio file
                with open(output_path, 'rb') as f:
                    audio_bytes = f.read()
                
                # Extract metadata from WAV file
                with wave.open(output_path, 'rb') as wav_file:
                    sample_rate = wav_file.getframerate()
                    frames = wav_file.getnframes()
                    duration_sec = frames / float(sample_rate)
                
                metadata = {
                    "duration_sec": duration_sec,
                    "format": "wav",
                    "sample_rate": sample_rate,
                    "voice_id": voice_id,
                    "text_hash": text_hash,
                    "provider": "piper"
                }
                
                return audio_bytes, metadata
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(output_path)
                except Exception:
                    pass
    
    def _download_model_if_needed(self, voice_id: str) -> str:
        """Download Piper model if not present from HuggingFace"""
        import urllib.request
        import urllib.error
        
        # Ensure model directory exists
        os.makedirs(self.model_path, exist_ok=True)
        
        # Piper voices are hosted on HuggingFace at rhasspy/piper-voices
        # Voice models are typically in format: {voice_id}/model.onnx
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        
        # Try different possible paths for the voice model
        # HuggingFace Piper voices repository structure:
        # - Some voices are in directories: en-US-lessac-medium/model.onnx
        # - Some are direct files: en-US-lessac-medium.onnx
        # - Voice IDs use underscores: en_US-lessac-medium
        # - URLs use hyphens: en-US-lessac-medium
        voice_id_hyphen = voice_id.replace('_', '-')
        possible_paths = [
            f"{voice_id_hyphen}/model.onnx",  # Directory format with hyphens (most common)
            f"{voice_id_hyphen}.onnx",  # Direct file format with hyphens
            f"{voice_id}/model.onnx",  # Directory format with underscores
            f"{voice_id}.onnx",  # Direct file format with underscores
        ]
        
        # Normalize local path to use voice_id format (underscores) for consistency
        # This ensures downloaded files match what _resolve_voice_model expects
        local_path_normalized = os.path.join(self.model_path, f"{voice_id}.onnx")
        
        for model_path in possible_paths:
            model_url = f"{base_url}/{model_path}"
            
            # Determine local path based on format
            if '/' in model_path:
                # Directory format: create voice directory
                voice_dir = os.path.join(self.model_path, voice_id)
                os.makedirs(voice_dir, exist_ok=True)
                local_path = os.path.join(voice_dir, "model.onnx")
            else:
                # Direct file format - always use normalized path (voice_id format)
                local_path = local_path_normalized
            
            # Skip if already exists
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                logger.info(f"Model already exists at {local_path}")
                return local_path
            
            try:
                logger.info(f"Attempting to download Piper model from {model_url} to {local_path}")
                print(f"[RAILWAY_DEBUG] Downloading Piper model: {model_url}", file=sys.stdout, flush=True)
                logger.info(f"Download target path: {local_path}")
                print(f"[RAILWAY_DEBUG] Download target path: {local_path}", file=sys.stdout, flush=True)
                
                # Download with progress tracking
                def show_progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, (block_num * block_size * 100) // total_size)
                        if block_num % 10 == 0:  # Log every 10 blocks
                            logger.debug(f"Download progress: {percent}%")
                            print(f"[RAILWAY_DEBUG] Download progress: {percent}%", file=sys.stdout, flush=True)
                
                # Download to temporary path first, then rename to consistent format
                temp_path = local_path + '.tmp'
                logger.info(f"Downloading to temporary path: {temp_path}")
                print(f"[RAILWAY_DEBUG] Downloading to temporary path: {temp_path}", file=sys.stdout, flush=True)
                
                urllib.request.urlretrieve(model_url, temp_path, show_progress)
                
                # Verify download succeeded
                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    logger.info(f"Downloaded file size: {file_size} bytes")
                    print(f"[RAILWAY_DEBUG] Downloaded file size: {file_size} bytes", file=sys.stdout, flush=True)
                    
                    if file_size > 1000:  # At least 1KB
                        # Move to final location (normalized to voice_id format)
                        if os.path.exists(local_path):
                            logger.info(f"Removing existing file at {local_path}")
                            os.remove(local_path)  # Remove old file if exists
                        
                        logger.info(f"Moving temp file to final location: {local_path}")
                        print(f"[RAILWAY_DEBUG] Moving temp file to final location: {local_path}", file=sys.stdout, flush=True)
                        os.rename(temp_path, local_path)
                        
                        # Verify final file exists
                        if os.path.exists(local_path):
                            final_size = os.path.getsize(local_path)
                            logger.info(f"Successfully downloaded Piper model to {local_path} ({final_size} bytes)")
                            print(f"[RAILWAY_DEBUG] Successfully downloaded {final_size} bytes to {local_path}", file=sys.stdout, flush=True)
                            return local_path
                        else:
                            logger.error(f"File rename succeeded but final file not found at {local_path}")
                            print(f"[RAILWAY_DEBUG] ERROR: File rename succeeded but final file not found at {local_path}", file=sys.stderr, flush=True)
                    else:
                        logger.warning(f"Downloaded file too small: {file_size} bytes (expected > 1KB)")
                        print(f"[RAILWAY_DEBUG] WARNING: Downloaded file too small: {file_size} bytes", file=sys.stderr, flush=True)
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    logger.error(f"Download completed but file not found at {temp_path}")
                    print(f"[RAILWAY_DEBUG] ERROR: Download completed but file not found at {temp_path}", file=sys.stderr, flush=True)
            except urllib.error.HTTPError as e:
                error_msg = f"HTTP error downloading {model_url}: {e.code} - {e.reason}"
                if e.code == 404:
                    logger.warning(f"Model not found at {model_url} (404)")
                    print(f"[RAILWAY_DEBUG] Model not found at {model_url} (404)", file=sys.stderr, flush=True)
                else:
                    logger.error(error_msg)
                    print(f"[RAILWAY_DEBUG] {error_msg}", file=sys.stderr, flush=True)
            except urllib.error.URLError as e:
                error_msg = f"URL error downloading {model_url}: {str(e)}"
                logger.error(error_msg)
                print(f"[RAILWAY_DEBUG] {error_msg}", file=sys.stderr, flush=True)
            except Exception as e:
                error_msg = f"Failed to download {model_url}: {type(e).__name__} - {str(e)}"
                logger.error(error_msg, exc_info=True)
                print(f"[RAILWAY_DEBUG] {error_msg}", file=sys.stderr, flush=True)
                # Clean up partial download
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except:
                        pass
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
        
        # Try using piper-tts download utility if available (fallback)
        # This is often more reliable than manual HuggingFace downloads
        try:
            from piper import download_voice, get_voices
            logger.info(f"Attempting to download voice {voice_id} using piper-tts library...")
            print(f"[RAILWAY_DEBUG] Attempting to download voice {voice_id} using piper-tts library...", file=sys.stdout, flush=True)
            
            try:
                # Try downloading with the voice_id as-is
                voice_path = download_voice(voice_id, self.model_path)
                if voice_path and os.path.exists(voice_path):
                    file_size = os.path.getsize(voice_path)
                    logger.info(f"Downloaded Piper voice model {voice_id} via piper-tts to {voice_path} ({file_size} bytes)")
                    print(f"[RAILWAY_DEBUG] Downloaded Piper voice model via piper-tts to {voice_path} ({file_size} bytes)", file=sys.stdout, flush=True)
                    # If downloaded to a different location, copy/symlink to expected location
                    if voice_path != local_path_normalized and os.path.exists(voice_path):
                        # Check if we should copy it to the normalized location
                        if not os.path.exists(local_path_normalized):
                            try:
                                import shutil
                                shutil.copy2(voice_path, local_path_normalized)
                                logger.info(f"Copied model to normalized location: {local_path_normalized}")
                                return local_path_normalized
                            except Exception as copy_error:
                                logger.warning(f"Failed to copy to normalized location, using original: {copy_error}")
                    return voice_path
            except Exception as download_error:
                logger.warning(f"download_voice failed: {download_error}")
                print(f"[RAILWAY_DEBUG] download_voice failed: {download_error}", file=sys.stderr, flush=True)
                
                # Try with hyphen version
                try:
                    voice_id_hyphen = voice_id.replace('_', '-')
                    logger.info(f"Trying download with hyphen version: {voice_id_hyphen}")
                    voice_path = download_voice(voice_id_hyphen, self.model_path)
                    if voice_path and os.path.exists(voice_path):
                        file_size = os.path.getsize(voice_path)
                        logger.info(f"Downloaded Piper voice model {voice_id_hyphen} via piper-tts to {voice_path} ({file_size} bytes)")
                        print(f"[RAILWAY_DEBUG] Downloaded Piper voice model {voice_id_hyphen} via piper-tts to {voice_path} ({file_size} bytes)", file=sys.stdout, flush=True)
                        # Copy to normalized location if needed
                        if voice_path != local_path_normalized and os.path.exists(voice_path):
                            if not os.path.exists(local_path_normalized):
                                try:
                                    import shutil
                                    shutil.copy2(voice_path, local_path_normalized)
                                    logger.info(f"Copied model to normalized location: {local_path_normalized}")
                                    return local_path_normalized
                                except Exception as copy_error:
                                    logger.warning(f"Failed to copy to normalized location, using original: {copy_error}")
                        return voice_path
                except Exception as hyphen_error:
                    logger.debug(f"download_voice with hyphen also failed: {hyphen_error}")
            
            try:
                voices = get_voices()
                if voice_id in voices:
                    voice_info = voices[voice_id]
                    if hasattr(voice_info, 'path') and os.path.exists(voice_info.path):
                        logger.info(f"Found voice {voice_id} in piper-tts voices list: {voice_info.path}")
                        return voice_info.path
            except Exception as find_error:
                logger.debug(f"get_voices failed: {find_error}")
        except ImportError:
            logger.warning("piper download utilities not available - install piper-tts package")
            print(f"[RAILWAY_DEBUG] piper download utilities not available", file=sys.stderr, flush=True)
        except Exception as e:
            logger.error(f"Failed to use piper download utilities: {e}", exc_info=True)
            print(f"[RAILWAY_DEBUG] Failed to use piper download utilities: {e}", file=sys.stderr, flush=True)
        
        logger.error(f"Failed to download Piper model {voice_id} from all attempted sources")
        print(f"[RAILWAY_DEBUG] ERROR: Failed to download Piper model {voice_id} from all attempted sources", file=sys.stderr, flush=True)
        return None
    
    def _resolve_voice_model(self, voice_id: str) -> str:
        """Resolve voice ID to model file path"""
        # Default voice
        if voice_id == "default":
            voice_id = self.get_available_voices()[0]
        
        # Check if voice_id is a full path
        if os.path.exists(voice_id):
            return voice_id
        
        # Check in model directory - try both underscore and hyphen versions
        # Voice IDs might use underscores (en_US) but downloads use hyphens (en-US)
        model_file_underscore = os.path.join(self.model_path, f"{voice_id}.onnx")
        model_file_hyphen = os.path.join(self.model_path, f"{voice_id.replace('_', '-')}.onnx")
        
        if os.path.exists(model_file_underscore):
            return model_file_underscore
        if os.path.exists(model_file_hyphen):
            logger.info(f"Found model file with hyphen format: {model_file_hyphen}")
            return model_file_hyphen
        
        # Try to download model if not found
        logger.info(f"Voice model {voice_id} not found locally, attempting to download...")
        print(f"[RAILWAY_DEBUG] Voice model {voice_id} not found, attempting download...", file=sys.stdout, flush=True)
        
        try:
            downloaded_path = self._download_model_if_needed(voice_id)
            if downloaded_path and os.path.exists(downloaded_path):
                logger.info(f"Successfully downloaded model to {downloaded_path}")
                print(f"[RAILWAY_DEBUG] Successfully downloaded model to {downloaded_path}", file=sys.stdout, flush=True)
                return downloaded_path
        except Exception as download_error:
            logger.error(f"Error during model download: {download_error}", exc_info=True)
            print(f"[RAILWAY_DEBUG] Model download error: {download_error}", file=sys.stderr, flush=True)
        
        # Check if downloaded to model directory (might have been downloaded with different name)
        # Check both underscore and hyphen versions
        if os.path.exists(model_file_underscore):
            logger.info(f"Found model file at {model_file_underscore}")
            return model_file_underscore
        if os.path.exists(model_file_hyphen):
            logger.info(f"Found model file at {model_file_hyphen}")
            return model_file_hyphen
        
        # Also check for directory format (both underscore and hyphen)
        voice_dir_model_underscore = os.path.join(self.model_path, voice_id, "model.onnx")
        voice_dir_model_hyphen = os.path.join(self.model_path, voice_id.replace('_', '-'), "model.onnx")
        
        if os.path.exists(voice_dir_model_underscore):
            logger.info(f"Found model file at {voice_dir_model_underscore}")
            return voice_dir_model_underscore
        if os.path.exists(voice_dir_model_hyphen):
            logger.info(f"Found model file at {voice_dir_model_hyphen}")
            return voice_dir_model_hyphen
        
        # Fallback: use first available voice
        logger.warning(f"Voice {voice_id} not found, using default")
        default_voice = self.get_available_voices()[0]
        model_file = os.path.join(self.model_path, f"{default_voice}.onnx")
        
        # Try downloading default voice
        if not os.path.exists(model_file):
            logger.info(f"Default voice model {default_voice} not found, attempting to download...")
            downloaded_path = self._download_model_if_needed(default_voice)
            if downloaded_path and os.path.exists(downloaded_path):
                return downloaded_path
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(
                f"Piper model not found. Expected at: {model_file}. "
                f"Set PIPER_MODEL_PATH or install piper models. "
                f"To download models automatically, ensure piper-tts package is installed with download support."
            )
        
        return model_file


class CoquiXTTSProvider(TTSProvider):
    """Coqui XTTS v2 provider (optional, behind config flag)"""
    
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        """
        Initialize Coqui XTTS provider
        
        Args:
            model_name: Coqui model name
        """
        self.model_name = model_name
        self._model = None
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Coqui TTS is available"""
        try:
            import TTS
            return True
        except ImportError:
            logger.warning("Coqui TTS not available: TTS package not installed")
            return False
    
    def is_available(self) -> bool:
        """Check if Coqui TTS is available"""
        return self._available
    
    def get_available_voices(self) -> list[str]:
        """Get list of available voices"""
        # Coqui XTTS supports cloning voices, but we can list some defaults
        return [
            "default",
            "female_1",
            "male_1",
        ]
    
    def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        format: str = "wav"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Synthesize speech using Coqui XTTS
        
        Note: This is a placeholder implementation.
        Full implementation would require TTS library setup.
        """
        if not self._available:
            raise RuntimeError("Coqui TTS is not available. Install TTS package.")
        
        raise NotImplementedError(
            "Coqui XTTS implementation requires TTS library setup. "
            "Use PiperTTSProvider for now."
        )


class GoogleTTSProvider(TTSProvider):
    """Google Text-to-Speech (gTTS) provider - Free, no API key required"""
    
    def __init__(self):
        """Initialize Google TTS provider"""
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if gTTS is available"""
        try:
            from gtts import gTTS
            return True
        except ImportError:
            logger.warning("Google TTS (gTTS) not available: gTTS package not installed")
            return False
    
    def is_available(self) -> bool:
        """Check if gTTS is available"""
        return self._available
    
    def get_available_voices(self) -> list[str]:
        """Get list of available language codes"""
        # gTTS supports many languages via language codes
        # Common ones: 'en' (English), 'es' (Spanish), 'fr' (French), etc.
        return [
            "en",      # English
            "en-us",   # English (US)
            "en-gb",   # English (UK)
            "es",      # Spanish
            "fr",      # French
            "de",      # German
            "it",      # Italian
            "pt",      # Portuguese
            "ru",      # Russian
            "ja",      # Japanese
            "ko",      # Korean
            "zh",      # Chinese
            "ar",      # Arabic
            "hi",      # Hindi
        ]
    
    def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        format: str = "wav"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Synthesize speech using Google TTS (gTTS)
        
        Args:
            text: Text to synthesize
            voice_id: Language code (e.g., 'en', 'en-us', 'es') or 'default' for English
            speed: Speech speed (0.5-2.0) - Note: gTTS doesn't support speed control directly
            format: Output format ('mp3' supported, 'wav' will be converted)
        
        Returns:
            Tuple of (audio_bytes, metadata_dict)
        """
        if not self._available:
            raise RuntimeError("Google TTS (gTTS) is not available. Install gTTS package.")
        
        from gtts import gTTS
        import io
        import hashlib
        import tempfile
        
        # Hash text for metadata
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        # Resolve language code
        lang = "en"  # Default to English
        if voice_id and voice_id != "default":
            # Extract language code from voice_id
            # Handle formats like "en", "en-us", "en_US", etc.
            lang = voice_id.lower().replace("_", "-").split("-")[0]
            # Validate it's a 2-letter code (gTTS requirement)
            if len(lang) != 2:
                logger.warning(f"Invalid language code '{lang}', defaulting to 'en'")
                lang = "en"
        
        try:
            # Create gTTS object
            # Note: gTTS doesn't support speed control, so we ignore the speed parameter
            tts = gTTS(text=text, lang=lang, slow=False)
            
            # Generate audio to BytesIO buffer
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_bytes = audio_buffer.getvalue()
            
            # gTTS outputs MP3 format
            # If WAV format is requested, convert using pydub (requires ffmpeg)
            output_format = "mp3"  # gTTS default output
            
            if format == "wav":
                logger.info(f"gTTS outputs MP3 format. Converting to WAV...")
                try:
                    from pydub import AudioSegment
                    # Convert MP3 to WAV
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                    wav_buffer = io.BytesIO()
                    audio_segment.export(wav_buffer, format="wav")
                    audio_bytes = wav_buffer.getvalue()
                    output_format = "wav"
                    logger.info("Successfully converted MP3 to WAV")
                except ImportError:
                    logger.warning("pydub not available, returning MP3 format instead of WAV")
                    output_format = "mp3"
                except Exception as conv_error:
                    logger.warning(f"Failed to convert MP3 to WAV: {conv_error}. Returning MP3 format.")
                    output_format = "mp3"
            
            # Estimate duration (rough calculation for MP3)
            # MP3 files: ~1KB per second at 128kbps
            # This is approximate
            estimated_duration = len(audio_bytes) / 16000.0  # Rough estimate
            
            metadata = {
                "duration_sec": estimated_duration,
                "format": output_format,
                "sample_rate": 22050 if output_format == "mp3" else 22050,  # gTTS default
                "voice_id": voice_id,
                "language": lang,
                "text_hash": text_hash,
                "provider": "gtts"
            }
            
            return audio_bytes, metadata
            
        except Exception as e:
            logger.error(f"Google TTS synthesis failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to synthesize speech with Google TTS: {str(e)}")


def get_tts_provider(provider_name: str = None) -> TTSProvider:
    """
    Factory function to get TTS provider
    
    Args:
        provider_name: Provider name ('piper', 'gtts', 'coqui', or None for auto-detect)
    
    Returns:
        TTSProvider instance
    """
    from ..config import config
    
    # Auto-detect if not specified
    if provider_name is None:
        provider_name = os.getenv("TTS_PROVIDER", "piper")
    
    provider_name_lower = provider_name.lower()
    
    if provider_name_lower == "piper":
        return PiperTTSProvider()
    elif provider_name_lower == "gtts" or provider_name_lower == "google":
        return GoogleTTSProvider()
    elif provider_name_lower == "coqui":
        # Check if enabled via config
        if os.getenv("ENABLE_COQUI_TTS", "false").lower() == "true":
            return CoquiXTTSProvider()
        else:
            logger.warning("Coqui TTS requested but not enabled. Using Piper.")
            return PiperTTSProvider()
    else:
        raise ValueError(f"Unknown TTS provider: {provider_name}. Supported: 'piper', 'gtts', 'coqui'")

