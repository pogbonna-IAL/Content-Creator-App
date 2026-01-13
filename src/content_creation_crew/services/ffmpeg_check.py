"""
FFmpeg availability check for video rendering readiness
Validates FFmpeg installation at startup
"""
import subprocess
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def check_ffmpeg_availability(timeout: float = 5.0) -> Tuple[bool, Optional[str]]:
    """
    Check if FFmpeg is available and working
    
    Args:
        timeout: Maximum time to wait for ffmpeg -version command (seconds)
    
    Returns:
        Tuple of (is_available, error_message)
        - is_available: True if FFmpeg is available and working
        - error_message: Error message if not available, None if available
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            # Extract version info from output
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown"
            logger.info(f"FFmpeg is available: {version_line}")
            return True, None
        else:
            error_msg = f"FFmpeg command failed with exit code {result.returncode}"
            logger.error(error_msg)
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = "FFmpeg is not installed or not in PATH"
        logger.error(error_msg)
        return False, error_msg
        
    except subprocess.TimeoutExpired:
        error_msg = f"FFmpeg check timed out after {timeout} seconds"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Error checking FFmpeg: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def validate_ffmpeg_startup(enable_video_rendering: bool, timeout: float = 5.0) -> None:
    """
    Validate FFmpeg availability at startup
    
    Args:
        enable_video_rendering: Whether video rendering is enabled
        timeout: Maximum time to wait for FFmpeg check (seconds)
    
    Raises:
        RuntimeError: If video rendering is enabled but FFmpeg is not available
    """
    is_available, error_message = check_ffmpeg_availability(timeout)
    
    if enable_video_rendering:
        if not is_available:
            error_msg = (
                f"Video rendering is enabled (ENABLE_VIDEO_RENDERING=true) but FFmpeg is not available. "
                f"{error_message or 'FFmpeg check failed'}. "
                f"Install FFmpeg or set ENABLE_VIDEO_RENDERING=false to disable video features."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            logger.info("✓ FFmpeg validation passed - video rendering is ready")
    else:
        if not is_available:
            logger.warning(
                f"⚠️  FFmpeg is not available. Video rendering features will be disabled. "
                f"Set ENABLE_VIDEO_RENDERING=true and install FFmpeg to enable video rendering."
            )
        else:
            logger.info("✓ FFmpeg is available (video rendering disabled by config)")

