"""
Content Moderation Service
Rules-based filtering + optional open-source classifier for content safety
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ..config import config

logger = logging.getLogger(__name__)


class ModerationReason(str, Enum):
    """Moderation block reason codes"""
    DISALLOWED_CONTENT = "disallowed_content"
    PII_DETECTED = "pii_detected"
    CLASSIFIER_BLOCKED = "classifier_blocked"
    TOXIC_CONTENT = "toxic_content"
    SPAM = "spam"
    UNKNOWN = "unknown"


class ModerationResult:
    """Result of content moderation check"""
    
    def __init__(
        self,
        passed: bool,
        reason_code: Optional[ModerationReason] = None,
        details: Optional[Dict] = None
    ):
        self.passed = passed
        self.reason_code = reason_code
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for SSE events"""
        return {
            "passed": self.passed,
            "reason_code": self.reason_code.value if self.reason_code else None,
            "details": self.details
        }


class ModerationService:
    """
    Content moderation service
    
    Performs rules-based checks and optional classifier-based checks
    """
    
    def __init__(self):
        """Initialize moderation service"""
        self.enable_classifier = config.ENABLE_CONTENT_MODERATION_CLASSIFIER
        self.disallowed_keywords = self._load_disallowed_keywords()
        self.pii_patterns = self._load_pii_patterns()
        self.classifier = None
        
        if self.enable_classifier:
            self._initialize_classifier()
    
    def _load_disallowed_keywords(self) -> List[str]:
        """Load disallowed content keywords from config"""
        # Default disallowed keywords (can be overridden via env)
        default_keywords = [
            # Violence
            "kill", "murder", "violence", "weapon", "gun", "bomb",
            # Hate speech
            "hate", "discrimination", "racism", "sexism",
            # Illegal activities
            "drug", "illegal", "fraud", "scam",
            # Adult content
            "explicit", "porn", "adult"
        ]
        
        # Load from environment if set
        keywords_env = config.MODERATION_DISALLOWED_KEYWORDS if hasattr(config, 'MODERATION_DISALLOWED_KEYWORDS') else None
        if keywords_env:
            return [kw.strip().lower() for kw in keywords_env.split(",")]
        
        return default_keywords
    
    def _load_pii_patterns(self) -> List[Tuple[str, str]]:
        """Load PII detection patterns (pattern, type)"""
        return [
            # Email pattern
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
            # Phone number pattern (US format)
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'phone'),
            # SSN pattern (US format)
            (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
            # Credit card pattern (basic)
            (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'credit_card'),
        ]
    
    def _initialize_classifier(self):
        """Initialize optional open-source classifier"""
        try:
            # Try to import and initialize an open-source text safety classifier
            # Example: using transformers library with a safety model
            # This is feature-flagged and optional
            logger.info("Content moderation classifier enabled, but not yet implemented")
            logger.info("Classifier integration can be added using transformers library")
            # Placeholder for future classifier integration
            # from transformers import pipeline
            # self.classifier = pipeline("text-classification", model="unitary/toxic-bert")
        except ImportError:
            logger.warning("Classifier dependencies not available, using rules-based moderation only")
            self.enable_classifier = False
    
    def moderate_input(self, text: str, context: Optional[Dict] = None) -> ModerationResult:
        """
        Moderate input text (before generation)
        
        Args:
            text: Input text to moderate
            context: Optional context (e.g., topic, user_id)
        
        Returns:
            ModerationResult
        """
        if not text or not text.strip():
            return ModerationResult(passed=True)
        
        text_lower = text.lower()
        
        # Check for disallowed keywords
        for keyword in self.disallowed_keywords:
            if keyword in text_lower:
                logger.warning(f"Input blocked: disallowed keyword '{keyword}' detected")
                return ModerationResult(
                    passed=False,
                    reason_code=ModerationReason.DISALLOWED_CONTENT,
                    details={
                        "keyword": keyword,
                        "matched_text": text[:100]  # First 100 chars for context
                    }
                )
        
        # Check for PII
        pii_found = []
        for pattern, pii_type in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                pii_found.append({
                    "type": pii_type,
                    "count": len(matches)
                })
        
        if pii_found:
            logger.warning(f"Input blocked: PII detected: {pii_found}")
            return ModerationResult(
                passed=False,
                reason_code=ModerationReason.PII_DETECTED,
                details={
                    "pii_types": pii_found
                }
            )
        
        # Run classifier if enabled
        if self.enable_classifier and self.classifier:
            try:
                classifier_result = self._run_classifier(text)
                if not classifier_result.passed:
                    return classifier_result
            except Exception as e:
                logger.warning(f"Classifier check failed: {e}, allowing content")
        
        return ModerationResult(passed=True)
    
    def moderate_output(self, text: str, content_type: str, context: Optional[Dict] = None) -> ModerationResult:
        """
        Moderate output text (before saving artifact)
        
        Args:
            text: Generated content text
            content_type: Type of content (blog, social, audio, video)
            context: Optional context (e.g., job_id, artifact_type)
        
        Returns:
            ModerationResult
        """
        if not text or not text.strip():
            return ModerationResult(passed=True)
        
        text_lower = text.lower()
        
        # Check for disallowed keywords (stricter for outputs)
        for keyword in self.disallowed_keywords:
            if keyword in text_lower:
                logger.warning(f"Output blocked: disallowed keyword '{keyword}' detected in {content_type}")
                return ModerationResult(
                    passed=False,
                    reason_code=ModerationReason.DISALLOWED_CONTENT,
                    details={
                        "keyword": keyword,
                        "content_type": content_type,
                        "matched_text": text[:100]
                    }
                )
        
        # Check for PII in output (more strict)
        pii_found = []
        for pattern, pii_type in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                pii_found.append({
                    "type": pii_type,
                    "count": len(matches)
                })
        
        if pii_found:
            logger.warning(f"Output blocked: PII detected in {content_type}: {pii_found}")
            return ModerationResult(
                passed=False,
                reason_code=ModerationReason.PII_DETECTED,
                details={
                    "pii_types": pii_found,
                    "content_type": content_type
                }
            )
        
        # Run classifier if enabled
        if self.enable_classifier and self.classifier:
            try:
                classifier_result = self._run_classifier(text)
                if not classifier_result.passed:
                    return ModerationResult(
                        passed=False,
                        reason_code=ModerationReason.CLASSIFIER_BLOCKED,
                        details={
                            "content_type": content_type,
                            **classifier_result.details
                        }
                    )
            except Exception as e:
                logger.warning(f"Classifier check failed: {e}, allowing content")
        
        return ModerationResult(passed=True)
    
    def _run_classifier(self, text: str) -> ModerationResult:
        """
        Run optional classifier on text
        
        Args:
            text: Text to classify
        
        Returns:
            ModerationResult
        """
        if not self.classifier:
            return ModerationResult(passed=True)
        
        try:
            # Placeholder for classifier integration
            # result = self.classifier(text)
            # if result and result[0]['label'] in ['toxic', 'hate', 'spam']:
            #     return ModerationResult(
            #         passed=False,
            #         reason_code=ModerationReason.CLASSIFIER_BLOCKED,
            #         details={"label": result[0]['label'], "score": result[0]['score']}
            #     )
            pass
        except Exception as e:
            logger.error(f"Classifier error: {e}")
        
        return ModerationResult(passed=True)


# Singleton instance
_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    """Get singleton ModerationService instance"""
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service

