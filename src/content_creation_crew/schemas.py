"""
Pydantic schemas for content generation outputs
Strict JSON schemas for predictable, validated content generation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


# Prompt version constant - increment when prompts change
PROMPT_VERSION = "1.0.0"


class BlogContentSchema(BaseModel):
    """Schema for blog post content"""
    title: str = Field(..., description="Blog post title", min_length=10, max_length=200)
    introduction: str = Field(..., description="Introduction paragraph", min_length=100)
    sections: List[str] = Field(..., description="Main content sections", min_items=3, max_items=10)
    conclusion: str = Field(..., description="Conclusion paragraph", min_length=50)
    
    @field_validator('sections')
    @classmethod
    def validate_sections(cls, v):
        """Ensure each section has meaningful content"""
        for i, section in enumerate(v):
            if len(section.strip()) < 100:
                raise ValueError(f"Section {i+1} is too short (minimum 100 characters)")
        return v
    
    def to_text(self) -> str:
        """Convert structured content to markdown text"""
        lines = [
            f"# {self.title}",
            "",
            self.introduction,
            ""
        ]
        for i, section in enumerate(self.sections, 1):
            lines.append(f"## Section {i}")
            lines.append("")
            lines.append(section)
            lines.append("")
        lines.append("## Conclusion")
        lines.append("")
        lines.append(self.conclusion)
        return "\n".join(lines)


class SocialMediaContentSchema(BaseModel):
    """Schema for social media content"""
    linkedin_post: str = Field(..., description="LinkedIn post (200-300 words)", min_length=200)
    twitter_post: str = Field(..., description="Twitter/X post (under 280 characters)", max_length=280)
    hashtags: List[str] = Field(..., description="3-5 relevant hashtags", min_items=3, max_items=5)
    cta: str = Field(..., description="Call-to-action text", min_length=10)
    
    @field_validator('hashtags')
    @classmethod
    def validate_hashtags(cls, v):
        """Ensure hashtags don't include # symbol"""
        return [tag.replace('#', '') if tag.startswith('#') else tag for tag in v]
    
    def to_text(self) -> str:
        """Convert structured content to markdown text"""
        lines = [
            "# Social Media Content",
            "",
            "## LinkedIn Post",
            "",
            self.linkedin_post,
            "",
            "## Twitter/X Post",
            "",
            self.twitter_post,
            "",
            "## Hashtags",
            "",
            " ".join([f"#{tag}" for tag in self.hashtags]),
            "",
            "## Call-to-Action",
            "",
            self.cta
        ]
        return "\n".join(lines)


class AudioContentSchema(BaseModel):
    """Schema for audio script content"""
    intro_hook: str = Field(..., description="Intro hook (30-60 seconds)", min_length=100)
    main_sections: List[str] = Field(..., description="Main content sections with transitions", min_items=2, max_items=8)
    conclusion: str = Field(..., description="Conclusion with CTA", min_length=50)
    pacing_notes: Optional[str] = Field(None, description="Pacing and tone notes")
    
    @field_validator('main_sections')
    @classmethod
    def validate_sections(cls, v):
        """Ensure each section has meaningful content"""
        for i, section in enumerate(v):
            if len(section.strip()) < 80:
                raise ValueError(f"Section {i+1} is too short (minimum 80 characters)")
        return v
    
    def to_text(self) -> str:
        """Convert structured content to markdown text"""
        lines = [
            "# Audio Script",
            "",
            "## Intro Hook (30-60 seconds)",
            "",
            self.intro_hook,
            ""
        ]
        for i, section in enumerate(self.main_sections, 1):
            lines.append(f"## Section {i}")
            lines.append("")
            lines.append(section)
            lines.append("")
        lines.append("## Conclusion")
        lines.append("")
        lines.append(self.conclusion)
        if self.pacing_notes:
            lines.append("")
            lines.append("## Pacing Notes")
            lines.append("")
            lines.append(self.pacing_notes)
        return "\n".join(lines)


class VideoContentSchema(BaseModel):
    """Schema for video script content"""
    hook: str = Field(..., description="Hook (15-30 seconds)", min_length=50)
    scenes: List[dict] = Field(..., description="Video scenes with visual cues", min_items=2, max_items=10)
    conclusion: str = Field(..., description="Conclusion with CTA", min_length=50)
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes(cls, v):
        """Ensure each scene has required fields"""
        for i, scene in enumerate(v):
            if not isinstance(scene, dict):
                raise ValueError(f"Scene {i+1} must be a dictionary")
            if 'content' not in scene:
                raise ValueError(f"Scene {i+1} must have 'content' field")
            if len(scene.get('content', '').strip()) < 50:
                raise ValueError(f"Scene {i+1} content is too short (minimum 50 characters)")
        return v
    
    def to_text(self) -> str:
        """Convert structured content to markdown text"""
        lines = [
            "# Video Script",
            "",
            "## Hook (15-30 seconds)",
            "",
            self.hook,
            ""
        ]
        for i, scene in enumerate(self.scenes, 1):
            lines.append(f"## Scene {i}")
            lines.append("")
            if 'visual_cue' in scene:
                lines.append(f"**Visual:** {scene['visual_cue']}")
                lines.append("")
            if 'on_screen_text' in scene:
                lines.append(f"**On-screen text:** {scene['on_screen_text']}")
                lines.append("")
            lines.append(scene.get('content', ''))
            lines.append("")
        lines.append("## Conclusion")
        lines.append("")
        lines.append(self.conclusion)
        return "\n".join(lines)


def validate_content_json(content_type: str, json_str: str, repair: bool = False) -> tuple[bool, Optional[BaseModel], Optional[str]]:
    """
    Validate JSON content against schema
    
    Args:
        content_type: 'blog', 'social', 'audio', or 'video'
        json_str: JSON string to validate
        repair: If True, attempt to repair invalid JSON
    
    Returns:
        Tuple of (is_valid, validated_model, error_message)
    """
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        if repair:
            # Attempt to repair common JSON issues
            repaired = _repair_json(json_str)
            if repaired:
                try:
                    data = json.loads(repaired)
                    logger.info(f"Repaired JSON for {content_type}")
                except json.JSONDecodeError:
                    return False, None, f"Invalid JSON: {str(e)}"
            else:
                return False, None, f"Invalid JSON: {str(e)}"
        else:
            return False, None, f"Invalid JSON: {str(e)}"
    
    # Validate against schema
    try:
        if content_type == 'blog':
            model = BlogContentSchema(**data)
        elif content_type == 'social':
            model = SocialMediaContentSchema(**data)
        elif content_type == 'audio':
            model = AudioContentSchema(**data)
        elif content_type == 'video':
            model = VideoContentSchema(**data)
        else:
            return False, None, f"Unknown content type: {content_type}"
        
        return True, model, None
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"


def _repair_json(json_str: str) -> Optional[str]:
    """
    Attempt to repair common JSON issues
    
    Returns:
        Repaired JSON string or None if repair not possible
    """
    import re
    
    # Remove markdown code blocks
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```\s*$', '', json_str)
    json_str = json_str.strip()
    
    # Try to extract JSON from text that might have extra content
    # Look for first { and last }
    first_brace = json_str.find('{')
    last_brace = json_str.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = json_str[first_brace:last_brace + 1]
    
    # Fix common trailing comma issues
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unquoted keys (basic attempt)
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    
    return json_str

