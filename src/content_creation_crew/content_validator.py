"""
Content validation and JSON repair layer
Validates agent outputs against Pydantic schemas with self-repair capability
"""
import json
import logging
import re
from typing import Optional, Tuple
from pydantic import ValidationError

from .schemas import (
    PROMPT_VERSION,
    BlogContentSchema,
    SocialMediaContentSchema,
    AudioContentSchema,
    VideoContentSchema,
    validate_content_json,
)

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON from text that might contain extra content
    
    Args:
        text: Text that may contain JSON
    
    Returns:
        Extracted JSON string or None
    """
    if not text:
        return None
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    
    # Look for JSON object boundaries
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = text[first_brace:last_brace + 1]
        # Try to parse to verify it's valid JSON
        try:
            json.loads(json_candidate)
            return json_candidate
        except json.JSONDecodeError:
            pass
    
    # If no JSON object found, try to parse entire text
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    
    return None


def repair_json(json_str: str) -> Optional[str]:
    """
    Attempt to repair common JSON issues
    
    Args:
        json_str: Potentially broken JSON string
    
    Returns:
        Repaired JSON string or None if repair not possible
    """
    if not json_str:
        return None
    
    # Remove markdown code blocks
    repaired = re.sub(r'```json\s*', '', json_str)
    repaired = re.sub(r'```\s*$', '', repaired)
    repaired = repaired.strip()
    
    # Extract JSON object if embedded in text
    first_brace = repaired.find('{')
    last_brace = repaired.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        repaired = repaired[first_brace:last_brace + 1]
    
    # Fix trailing commas
    repaired = re.sub(r',\s*}', '}', repaired)
    repaired = re.sub(r',\s*]', ']', repaired)
    
    # Fix unquoted keys (basic attempt - be careful not to break strings)
    # Only fix keys at the start of lines or after commas/braces
    repaired = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', repaired)
    
    # Fix single quotes to double quotes (basic)
    repaired = re.sub(r"'([^']*)':", r'"\1":', repaired)
    
    # Try to parse to verify repair worked
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return None


def validate_and_repair_content(
    content_type: str,
    raw_output: str,
    model_name: str,
    allow_repair: bool = True
) -> Tuple[bool, Optional[object], str, bool]:
    """
    Validate content against schema with optional self-repair
    
    Args:
        content_type: 'blog', 'social', 'audio', or 'video'
        raw_output: Raw agent output text
        model_name: Model name used for generation
        allow_repair: If True, attempt repair on validation failure
    
    Returns:
        Tuple of (is_valid, validated_model, final_text, was_repaired)
    """
    logger.info(f"Validating {content_type} content (model: {model_name}, prompt_version: {PROMPT_VERSION})")
    
    # First attempt: try to extract and validate JSON
    json_str = extract_json_from_text(raw_output)
    
    if json_str:
        is_valid, model, error = validate_content_json(content_type, json_str, repair=False)
        if is_valid:
            logger.info(f"✓ {content_type} content validated successfully on first attempt")
            return True, model, model.to_text(), False
    
    # If validation failed and repair is allowed, try repair
    if allow_repair and json_str:
        logger.warning(f"Validation failed for {content_type}, attempting repair...")
        repaired_json = repair_json(json_str)
        
        if repaired_json:
            is_valid, model, error = validate_content_json(content_type, repaired_json, repair=False)
            if is_valid:
                logger.info(f"✓ {content_type} content validated successfully after repair")
                return True, model, model.to_text(), True
            else:
                logger.warning(f"Repair attempt failed for {content_type}: {error}")
        else:
            logger.warning(f"Could not repair JSON for {content_type}")
    
    # If still invalid, log and return failure
    error_msg = f"Content validation failed for {content_type}"
    if json_str:
        error_msg += f": {error if 'error' in locals() else 'Unknown error'}"
    else:
        error_msg += ": No JSON found in output"
    
    logger.error(error_msg)
    logger.debug(f"Raw output preview: {raw_output[:500]}")
    
    return False, None, raw_output, False


def validate_content_with_retry(
    content_type: str,
    raw_output: str,
    model_name: str,
    llm_instance=None,
    repair_prompt: str = None
) -> Tuple[bool, Optional[object], str]:
    """
    Validate content with self-repair retry using LLM if available
    
    Args:
        content_type: 'blog', 'social', 'audio', or 'video'
        raw_output: Raw agent output text
        model_name: Model name used for generation
        llm_instance: Optional LLM instance for repair retry
        repair_prompt: Optional custom repair prompt
    
    Returns:
        Tuple of (is_valid, validated_model, final_text)
    """
    # First attempt: standard validation with repair
    is_valid, model, text, was_repaired = validate_and_repair_content(
        content_type, raw_output, model_name, allow_repair=True
    )
    
    if is_valid:
        return True, model, text
    
    # If still invalid and LLM is available, try LLM-based repair
    if llm_instance and not was_repaired:
        logger.info(f"Attempting LLM-based repair for {content_type}...")
        
        # Get schema for repair prompt
        schema_map = {
            'blog': BlogContentSchema,
            'social': SocialMediaContentSchema,
            'audio': AudioContentSchema,
            'video': VideoContentSchema,
        }
        
        schema = schema_map.get(content_type)
        if schema:
            repair_prompt = repair_prompt or f"""
The following output failed JSON validation for {content_type} content. 
Please fix it to match this JSON schema exactly:

{schema.model_json_schema()}

Original output:
{raw_output[:2000]}

Output ONLY valid JSON matching the schema above. Do not include any explanations or markdown.
"""
            
            try:
                repaired_output = llm_instance.invoke(repair_prompt)
                is_valid, model, text, _ = validate_and_repair_content(
                    content_type, repaired_output, model_name, allow_repair=False
                )
                if is_valid:
                    logger.info(f"✓ {content_type} content validated successfully after LLM repair")
                    return True, model, text
            except Exception as e:
                logger.error(f"LLM repair failed for {content_type}: {e}")
    
    # Final fallback: return original text (will use fallback extraction)
    logger.warning(f"Content validation failed for {content_type}, using fallback extraction")
    return False, None, raw_output

