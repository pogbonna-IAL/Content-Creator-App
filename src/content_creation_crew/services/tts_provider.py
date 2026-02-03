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
            
            # Resolve voice model path (will download if needed)
            logger.info(f"[TTS_SYNTHESIS] Resolving voice model for voice_id: {voice_id}")
            print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Resolving voice model for voice_id: {voice_id}", file=sys.stdout, flush=True)
            
            try:
                voice_model = self._resolve_voice_model(voice_id)
                logger.info(f"[TTS_SYNTHESIS] Resolved voice model path: {voice_model}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Resolved voice model path: {voice_model}", file=sys.stdout, flush=True)
                
                # Verify file exists
                if not os.path.exists(voice_model):
                    raise FileNotFoundError(f"Voice model file not found at resolved path: {voice_model}")
                
                file_size = os.path.getsize(voice_model)
                logger.info(f"[TTS_SYNTHESIS] Voice model file exists, size: {file_size} bytes")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Voice model file exists, size: {file_size} bytes", file=sys.stdout, flush=True)
            except Exception as resolve_error:
                logger.error(f"[TTS_SYNTHESIS] Failed to resolve voice model: {resolve_error}", exc_info=True)
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Failed to resolve voice model: {resolve_error}", file=sys.stderr, flush=True)
                raise
            
            # Load voice - PiperVoice.load can also accept voice_id directly
            # Try loading by path first, then by voice_id
            logger.info(f"[TTS_SYNTHESIS] Loading PiperVoice from path: {voice_model}")
            print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Loading PiperVoice from path: {voice_model}", file=sys.stdout, flush=True)
            
            try:
                voice = PiperVoice.load(voice_model, config_path=None)
                logger.info(f"[TTS_SYNTHESIS] Successfully loaded PiperVoice")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Successfully loaded PiperVoice", file=sys.stdout, flush=True)
            except Exception as load_error:
                # If path loading fails, try loading by voice_id directly
                # PiperVoice might download automatically
                logger.warning(f"[TTS_SYNTHESIS] Failed to load voice from path {voice_model}, trying voice_id {voice_id}: {load_error}")
                print(f"[RAILWAY_DEBUG] [TTS_SYNTHESIS] Trying to load by voice_id: {voice_id}", file=sys.stdout, flush=True)
                try:
                    voice = PiperVoice.load(voice_id)
                    logger.info(f"[TTS_SYNTHESIS] Successfully loaded PiperVoice by voice_id")
                except Exception as voice_id_error:
                    logger.error(f"[TTS_SYNTHESIS] Failed to load by voice_id: {voice_id_error}", exc_info=True)
                    # Last resort: try with model path again
                    raise load_error
            
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
        # Common formats: en_US-lessac-medium/model.onnx or en_US-lessac-medium.onnx
        possible_paths = [
            f"{voice_id}/model.onnx",  # Directory format
            f"{voice_id}.onnx",  # Direct file format
            f"{voice_id.replace('_', '-')}/model.onnx",  # With hyphens
            f"{voice_id.replace('_', '-')}.onnx",  # With hyphens, direct file
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
                
                # Download with progress tracking
                def show_progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, (block_num * block_size * 100) // total_size)
                        if block_num % 10 == 0:  # Log every 10 blocks
                            logger.debug(f"Download progress: {percent}%")
                
                # Download to temporary path first, then rename to consistent format
                temp_path = local_path + '.tmp'
                urllib.request.urlretrieve(model_url, temp_path, show_progress)
                
                # Verify download succeeded
                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    if file_size > 1000:  # At least 1KB
                        # Move to final location (normalized to voice_id format)
                        if os.path.exists(local_path):
                            os.remove(local_path)  # Remove old file if exists
                        os.rename(temp_path, local_path)
                        logger.info(f"Successfully downloaded Piper model to {local_path} ({file_size} bytes)")
                        print(f"[RAILWAY_DEBUG] Successfully downloaded {file_size} bytes to {local_path}", file=sys.stdout, flush=True)
                        return local_path
                    else:
                        logger.warning(f"Downloaded file too small: {file_size} bytes")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    logger.warning(f"Download completed but file not found at {temp_path}")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.debug(f"Model not found at {model_url} (404)")
                else:
                    logger.warning(f"HTTP error downloading {model_url}: {e.code} - {e.reason}")
            except Exception as e:
                logger.warning(f"Failed to download {model_url}: {type(e).__name__} - {str(e)}")
                # Clean up partial download
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except:
                        pass
        
        # Try using piper-tts download utility if available (fallback)
        try:
            from piper import download_voice, get_voices
            try:
                voice_path = download_voice(voice_id, self.model_path)
                if voice_path and os.path.exists(voice_path):
                    logger.info(f"Downloaded Piper voice model {voice_id} via piper-tts to {voice_path}")
                    return voice_path
            except Exception as download_error:
                logger.debug(f"download_voice failed: {download_error}")
            
            try:
                voices = get_voices()
                if voice_id in voices:
                    voice_info = voices[voice_id]
                    if hasattr(voice_info, 'path') and os.path.exists(voice_info.path):
                        return voice_info.path
            except Exception as find_error:
                logger.debug(f"get_voices failed: {find_error}")
        except ImportError:
            logger.debug("piper download utilities not available")
        except Exception as e:
            logger.debug(f"Failed to use piper download utilities: {e}")
        
        logger.error(f"Failed to download Piper model {voice_id} from all attempted sources")
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


def get_tts_provider(provider_name: str = None) -> TTSProvider:
    """
    Factory function to get TTS provider
    
    Args:
        provider_name: Provider name ('piper', 'coqui', or None for auto-detect)
    
    Returns:
        TTSProvider instance
    """
    from ..config import config
    
    # Auto-detect if not specified
    if provider_name is None:
        provider_name = os.getenv("TTS_PROVIDER", "piper")
    
    if provider_name.lower() == "piper":
        return PiperTTSProvider()
    elif provider_name.lower() == "coqui":
        # Check if enabled via config
        if os.getenv("ENABLE_COQUI_TTS", "false").lower() == "true":
            return CoquiXTTSProvider()
        else:
            logger.warning("Coqui TTS requested but not enabled. Using Piper.")
            return PiperTTSProvider()
    else:
        raise ValueError(f"Unknown TTS provider: {provider_name}")

