"""
Logging Filter for PII Redaction
Automatically redacts sensitive information from logs
"""
import re
import logging
from typing import Optional


class PIIRedactionFilter(logging.Filter):
    """
    Logging filter that redacts PII and sensitive data from log messages
    
    Redacts:
    - Email addresses
    - Phone numbers
    - API keys and tokens
    - Passwords
    - Authorization headers
    - Credit card numbers
    """
    
    # Patterns to redact
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    
    # API keys and tokens (various formats)
    API_KEY_PATTERNS = [
        re.compile(r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
        re.compile(r'(secret[_-]?key|secretkey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
        re.compile(r'(token|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE),
        re.compile(r'(bearer\s+)([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE),
        re.compile(r'sk-[a-zA-Z0-9]{48}'),  # OpenAI API key format
        re.compile(r'xox[baprs]-[a-zA-Z0-9-]+'),  # Slack tokens
    ]
    
    # Password patterns
    PASSWORD_PATTERNS = [
        re.compile(r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\',]{4,})', re.IGNORECASE),
        re.compile(r'"password"\s*:\s*"([^"]{4,})"', re.IGNORECASE),
    ]
    
    # Authorization headers
    AUTH_HEADER_PATTERN = re.compile(r'(authorization|auth)["\']?\s*:\s*["\']?(bearer\s+)?([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE)
    
    # Credit card numbers (basic)
    CC_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
    
    # Social Security Numbers (US)
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    
    def __init__(self, name: str = ''):
        """
        Initialize PII redaction filter
        
        Args:
            name: Logger name filter applies to (empty = all loggers)
        """
        super().__init__(name)
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record and redact PII
        
        Args:
            record: Log record to filter
        
        Returns:
            True (always allow the record, just modify it)
        """
        # Redact message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.redact_pii(record.msg)
        
        # Redact args (if any)
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.redact_pii(str(v)) if isinstance(v, str) else v 
                             for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self.redact_pii(str(arg)) if isinstance(arg, str) else arg 
                                  for arg in record.args)
        
        return True
    
    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text
        
        Args:
            text: Text to redact
        
        Returns:
            Redacted text
        """
        if not text or not isinstance(text, str):
            return text
        
        redacted = text
        
        # 1. Redact emails
        redacted = self.EMAIL_PATTERN.sub(self._redact_email, redacted)
        
        # 2. Redact phone numbers
        redacted = self.PHONE_PATTERN.sub('XXX-XXX-XXXX', redacted)
        
        # 3. Redact API keys and tokens
        for pattern in self.API_KEY_PATTERNS:
            redacted = pattern.sub(r'\1=***REDACTED***', redacted)
        
        # 4. Redact passwords
        for pattern in self.PASSWORD_PATTERNS:
            redacted = pattern.sub(r'\1=***REDACTED***', redacted)
        
        # 5. Redact authorization headers
        redacted = self.AUTH_HEADER_PATTERN.sub(r'\1: Bearer ***REDACTED***', redacted)
        
        # 6. Redact credit card numbers
        redacted = self.CC_PATTERN.sub('XXXX-XXXX-XXXX-XXXX', redacted)
        
        # 7. Redact SSN
        redacted = self.SSN_PATTERN.sub('XXX-XX-XXXX', redacted)
        
        return redacted
    
    def _redact_email(self, match: re.Match) -> str:
        """
        Redact email address (keep first 2 chars and domain)
        
        Args:
            match: Regex match object
        
        Returns:
            Redacted email
        """
        email = match.group(0)
        if '@' not in email:
            return '***@***'
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            return f'**@{domain}'
        
        # Hash for uniqueness in logs (helps correlate same user)
        import hashlib
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:6]
        return f'{local[:2]}***{email_hash}@{domain}'


def setup_pii_redaction():
    """
    Set up PII redaction for all loggers
    
    Call this during application initialization
    """
    # Add filter to root logger
    root_logger = logging.getLogger()
    
    # Check if filter already added
    for filter_obj in root_logger.filters:
        if isinstance(filter_obj, PIIRedactionFilter):
            return  # Already set up
    
    # Add filter
    pii_filter = PIIRedactionFilter()
    root_logger.addFilter(pii_filter)
    
    logging.info("PII redaction filter enabled for all loggers")

