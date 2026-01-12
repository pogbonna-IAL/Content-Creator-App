"""
Video Rendering Provider Interface and Implementations
Adapter pattern for supporting multiple video rendering engines
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
import logging
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoProvider(ABC):
    """Abstract base class for video rendering providers"""
    
    @abstractmethod
    def render(
        self,
        video_script_json: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render video from video script
        
        Args:
            video_script_json: Video script JSON (from video ContentArtifact)
            options: Rendering options:
                - resolution: Tuple[int, int] (width, height), default (1920, 1080)
                - fps: int, default 30
                - background_type: str ("solid", "placeholder", "upload"), default "solid"
                - background_color: str (hex color), default "#000000"
                - background_image_path: Optional[str] (for upload type)
                - include_narration: bool, default True (uses voiceover_audio if available)
                - renderer: str ("baseline", "comfyui"), default "baseline"
        
        Returns:
            Dict containing:
            - video_file: bytes (mp4)
            - metadata: Dict with duration_sec, resolution, fps, scenes_count, renderer, model_used?
            - assets: List[Dict] with type, file_path, metadata for storyboard images, clips, etc.
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if video provider is available/configured"""
        pass
    
    @abstractmethod
    def get_supported_resolutions(self) -> List[Tuple[int, int]]:
        """Get list of supported resolutions"""
        pass


class BaselineVideoRenderer(VideoProvider):
    """Baseline CPU-friendly video renderer using PIL/moviepy/ffmpeg"""
    
    def __init__(self):
        """Initialize baseline video renderer"""
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if required dependencies are available"""
        try:
            import PIL
            import moviepy
        except ImportError as e:
            logger.warning(f"BaselineVideoRenderer dependencies not available: {e}")
            return False
        
        # Check ffmpeg availability
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
            else:
                logger.warning("FFmpeg command failed")
                return False
        except FileNotFoundError:
            logger.warning(
                "FFmpeg is not installed or not in PATH. "
                "Run 'python scripts/check_ffmpeg.py' for installation instructions."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg check timed out")
            return False
        except Exception as e:
            logger.warning(f"Error checking FFmpeg: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if baseline renderer is available"""
        return self._available
    
    def get_supported_resolutions(self) -> List[Tuple[int, int]]:
        """Get supported resolutions"""
        return [
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (854, 480),    # SD
            (640, 360),    # Low res
        ]
    
    def render(
        self,
        video_script_json: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render video using baseline method (CPU-friendly)
        
        Creates slides/frames from scenes with:
        - Background (solid color, placeholder, or uploaded image)
        - Text overlays + scene titles
        - Narration audio (if available)
        - Assembled into mp4 via ffmpeg
        """
        if not self._available:
            raise RuntimeError(
                "BaselineVideoRenderer is not available. "
                "Install PIL, moviepy, and ffmpeg."
            )
        
        import tempfile
        import shutil
        from pathlib import Path
        
        # Parse options
        opts = options or {}
        resolution = opts.get("resolution", (1920, 1080))
        fps = opts.get("fps", 30)
        background_type = opts.get("background_type", "solid")
        background_color = opts.get("background_color", "#000000")
        background_image_path = opts.get("background_image_path")
        include_narration = opts.get("include_narration", True)
        narration_audio_path = opts.get("narration_audio_path")  # Path to voiceover audio file
        
        # Extract scenes from video script
        # Video script may have hook, scenes, conclusion structure
        scenes = video_script_json.get("scenes", [])
        
        # If no scenes, try to create scenes from hook/conclusion structure
        if not scenes:
            hook = video_script_json.get("hook", "")
            conclusion = video_script_json.get("conclusion", "")
            
            if hook:
                scenes.append({
                    "title": "Hook",
                    "content": hook,
                    "duration_seconds": 5.0
                })
            if conclusion:
                scenes.append({
                    "title": "Conclusion",
                    "content": conclusion,
                    "duration_seconds": 5.0
                })
        
        if not scenes:
            raise ValueError("Video script must contain at least one scene or hook/conclusion")
        
        # Create temporary directory for assets
        temp_dir = Path(tempfile.mkdtemp())
        assets = []
        
        try:
            # Generate frames for each scene
            scene_clips = []
            total_duration = 0.0
            
            for idx, scene in enumerate(scenes):
                scene_title = scene.get("title", f"Scene {idx + 1}")
                scene_text = scene.get("content", "")
                scene_duration = scene.get("duration_seconds", 5.0)  # Default 5 seconds per scene
                
                logger.info(f"Rendering scene {idx + 1}/{len(scenes)}: {scene_title}")
                
                # Create frame image for this scene
                frame_path = self._create_scene_frame(
                    scene_title=scene_title,
                    scene_text=scene_text,
                    resolution=resolution,
                    background_type=background_type,
                    background_color=background_color,
                    background_image_path=background_image_path,
                    output_path=temp_dir / f"scene_{idx:03d}.png"
                )
                
                # Create video clip from frame
                clip_path = self._create_scene_clip(
                    frame_path=frame_path,
                    duration=scene_duration,
                    fps=fps,
                    output_path=temp_dir / f"scene_{idx:03d}.mp4"
                )
                
                scene_clips.append(clip_path)
                total_duration += scene_duration
                
                # Add to assets
                assets.append({
                    "type": "video_clip",
                    "file_path": str(clip_path),
                    "metadata": {
                        "scene_index": idx,
                        "scene_title": scene_title,
                        "duration_sec": scene_duration
                    }
                })
            
            # Concatenate all scene clips
            final_video_path = temp_dir / "final_video.mp4"
            self._concatenate_clips(
                clip_paths=scene_clips,
                output_path=final_video_path,
                fps=fps
            )
            
            # Add narration audio if available
            if include_narration and narration_audio_path and os.path.exists(narration_audio_path):
                logger.info("Adding narration audio to video")
                final_video_path = self._add_audio(
                    video_path=final_video_path,
                    audio_path=narration_audio_path,
                    output_path=temp_dir / "final_video_with_audio.mp4"
                )
            
            # Read final video file
            with open(final_video_path, 'rb') as f:
                video_bytes = f.read()
            
            metadata = {
                "duration_sec": total_duration,
                "resolution": resolution,
                "fps": fps,
                "scenes_count": len(scenes),
                "renderer": "baseline",
                "background_type": background_type
            }
            
            return {
                "video_file": video_bytes,
                "metadata": metadata,
                "assets": assets
            }
            
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")
    
    def _create_scene_frame(
        self,
        scene_title: str,
        scene_text: str,
        resolution: Tuple[int, int],
        background_type: str,
        background_color: str,
        background_image_path: Optional[str],
        output_path: Path
    ) -> Path:
        """Create a single frame image for a scene"""
        from PIL import Image, ImageDraw, ImageFont
        
        width, height = resolution
        
        # Create background
        if background_type == "upload" and background_image_path and os.path.exists(background_image_path):
            # Use uploaded image as background
            bg_image = Image.open(background_image_path)
            bg_image = bg_image.resize((width, height), Image.Resampling.LANCZOS)
            image = bg_image.copy()
        elif background_type == "placeholder":
            # Create gradient placeholder
            image = Image.new('RGB', (width, height), color='#1a1a1a')
            draw = ImageDraw.Draw(image)
            # Draw simple gradient
            for y in range(height):
                color_val = int(30 + (y / height) * 20)
                draw.line([(0, y), (width, y)], fill=(color_val, color_val, color_val))
        else:
            # Solid color background
            image = Image.new('RGB', (width, height), color=background_color)
        
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fallback to default if not available
        try:
            # Try to use a system font
            title_font = ImageFont.truetype("arial.ttf", 72)
            text_font = ImageFont.truetype("arial.ttf", 48)
        except:
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
                text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            except:
                # Use default font
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
        
        # Draw scene title (centered, top)
        title_bbox = draw.textbbox((0, 0), scene_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        title_x = (width - title_width) // 2
        title_y = height // 6
        
        # Draw title with shadow for readability
        draw.text((title_x + 2, title_y + 2), scene_title, font=title_font, fill="#000000")
        draw.text((title_x, title_y), scene_title, font=title_font, fill="#FFFFFF")
        
        # Draw scene text (centered, middle)
        # Wrap text to fit width
        max_text_width = width - 200
        words = scene_text.split()
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            word_bbox = draw.textbbox((0, 0), word + " ", font=text_font)
            word_width = word_bbox[2] - word_bbox[0]
            
            if current_width + word_width > max_text_width and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width
        
        if current_line:
            lines.append(" ".join(current_line))
        
        # Draw text lines
        try:
            # Try to get line height using textbbox
            test_bbox = draw.textbbox((0, 0), "A", font=text_font)
            line_height = (test_bbox[3] - test_bbox[1]) + 10
        except:
            # Fallback
            line_height = 50
        
        total_text_height = len(lines) * line_height
        start_y = (height - total_text_height) // 2
        
        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=text_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            line_y = start_y + i * line_height
            
            # Draw text with shadow
            draw.text((line_x + 2, line_y + 2), line, font=text_font, fill="#000000")
            draw.text((line_x, line_y), line, font=text_font, fill="#FFFFFF")
        
        # Save frame
        image.save(output_path, "PNG")
        return output_path
    
    def _create_scene_clip(
        self,
        frame_path: Path,
        duration: float,
        fps: int,
        output_path: Path
    ) -> Path:
        """Create a video clip from a single frame"""
        from moviepy.editor import ImageClip
        
        clip = ImageClip(str(frame_path), duration=duration)
        clip = clip.set_fps(fps)
        clip.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio=False,
            verbose=False,
            logger=None
        )
        clip.close()
        return output_path
    
    def _concatenate_clips(
        self,
        clip_paths: List[Path],
        output_path: Path,
        fps: int
    ) -> Path:
        """Concatenate multiple video clips into one"""
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        clips = []
        for clip_path in clip_paths:
            clip = VideoFileClip(str(clip_path))
            clips.append(clip)
        
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio=False,
            verbose=False,
            logger=None
        )
        
        # Clean up
        for clip in clips:
            clip.close()
        final_clip.close()
        
        return output_path
    
    def _add_audio(
        self,
        video_path: Path,
        audio_path: str,
        output_path: Path
    ) -> Path:
        """Add audio track to video"""
        from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips
        
        video = VideoFileClip(str(video_path))
        audio = AudioFileClip(audio_path)
        
        # Trim or loop audio to match video duration
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        elif audio.duration < video.duration:
            # Loop audio if shorter than video
            loops_needed = int(video.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * loops_needed).subclip(0, video.duration)
        
        final_video = video.set_audio(audio)
        final_video.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        video.close()
        audio.close()
        final_video.close()
        
        return output_path


class ComfyUIVideoProvider(VideoProvider):
    """ComfyUI-based video renderer (GPU, optional)"""
    
    def __init__(self, comfyui_api_url: Optional[str] = None):
        """
        Initialize ComfyUI video provider
        
        Args:
            comfyui_api_url: ComfyUI API URL (default: http://localhost:8188)
        """
        self.comfyui_api_url = comfyui_api_url or os.getenv("COMFYUI_API_URL", "http://localhost:8188")
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if ComfyUI is available"""
        try:
            import requests
            response = requests.get(f"{self.comfyui_api_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            logger.warning(f"ComfyUI not available at {self.comfyui_api_url}")
            return False
    
    def is_available(self) -> bool:
        """Check if ComfyUI is available"""
        return self._available
    
    def get_supported_resolutions(self) -> List[Tuple[int, int]]:
        """Get supported resolutions (ComfyUI typically supports various resolutions)"""
        return [
            (1920, 1080),
            (1280, 720),
            (1024, 576),
            (768, 432),
        ]
    
    def render(
        self,
        video_script_json: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render video using ComfyUI (AnimateDiff/SVD)
        
        This is a placeholder implementation.
        Full implementation would:
        1. Convert video script scenes to prompts
        2. Call ComfyUI API workflow for each scene
        3. Download generated video clips
        4. Concatenate clips
        5. Add narration if available
        """
        if not self._available:
            raise RuntimeError(
                f"ComfyUI is not available at {self.comfyui_api_url}. "
                "Start ComfyUI server or set COMFYUI_API_URL."
            )
        
        raise NotImplementedError(
            "ComfyUI video rendering requires ComfyUI server setup and workflow configuration. "
            "Use BaselineVideoRenderer for now."
        )


def get_video_provider(provider_name: str = None) -> VideoProvider:
    """
    Factory function to get video provider
    
    Args:
        provider_name: Provider name ('baseline', 'comfyui', or None for auto-detect)
    
    Returns:
        VideoProvider instance
    """
    if provider_name is None:
        # Check feature flag
        if os.getenv("ENABLE_AI_VIDEO", "false").lower() == "true":
            provider_name = "comfyui"
        else:
            provider_name = "baseline"
    
    if provider_name.lower() == "baseline":
        return BaselineVideoRenderer()
    elif provider_name.lower() == "comfyui":
        comfyui_url = os.getenv("COMFYUI_API_URL", "http://localhost:8188")
        return ComfyUIVideoProvider(comfyui_api_url=comfyui_url)
    else:
        raise ValueError(f"Unknown video provider: {provider_name}")

