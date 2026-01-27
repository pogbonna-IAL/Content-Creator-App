"""
Text-to-Speech (TTS) Provider Interface and Implementations
Adapter pattern for supporting multiple TTS engines
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import logging
import os

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
            voice_model = self._resolve_voice_model(voice_id)
            
            # Load voice - PiperVoice.load can also accept voice_id directly
            # Try loading by path first, then by voice_id
            try:
                voice = PiperVoice.load(voice_model, config_path=None)
            except Exception as load_error:
                # If path loading fails, try loading by voice_id directly
                # PiperVoice might download automatically
                logger.info(f"Failed to load voice from path {voice_model}, trying voice_id {voice_id}: {load_error}")
                try:
                    voice = PiperVoice.load(voice_id)
                except Exception:
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
        """Download Piper model if not present using piper-tts utilities"""
        # Ensure model directory exists
        os.makedirs(self.model_path, exist_ok=True)
        
        # Try using piper-tts download utility if available
        try:
            # piper-tts may have download utilities
            from piper import download_voice, get_voices
            try:
                # Try to download the voice
                voice_path = download_voice(voice_id, self.model_path)
                if voice_path and os.path.exists(voice_path):
                    logger.info(f"Downloaded Piper voice model {voice_id} to {voice_path}")
                    return voice_path
            except Exception as download_error:
                logger.debug(f"download_voice failed: {download_error}")
            
            # Try to find voice in available voices
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
        
        return None
    
    def _resolve_voice_model(self, voice_id: str) -> str:
        """Resolve voice ID to model file path"""
        # Default voice
        if voice_id == "default":
            voice_id = self.get_available_voices()[0]
        
        # Check if voice_id is a full path
        if os.path.exists(voice_id):
            return voice_id
        
        # Check in model directory
        model_file = os.path.join(self.model_path, f"{voice_id}.onnx")
        if os.path.exists(model_file):
            return model_file
        
        # Try to download model if not found
        logger.info(f"Voice model {voice_id} not found locally, attempting to download...")
        downloaded_path = self._download_model_if_needed(voice_id)
        if downloaded_path and os.path.exists(downloaded_path):
            return downloaded_path
        
        # Check if downloaded to model directory
        if os.path.exists(model_file):
            return model_file
        
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

