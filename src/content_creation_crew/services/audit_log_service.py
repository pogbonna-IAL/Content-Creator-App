"""
Audit Log Service
Append-only logging of security-critical actions for compliance and forensics
"""
import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, JSON, DateTime, text
from sqlalchemy.ext.declarative import declarative_base

from ..database import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """
    Audit log table - append-only for compliance
    
    Records security-critical actions with PII-protected metadata
    """
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False, index=True)  # Action enum value
    actor_user_id = Column(Integer, nullable=True, index=True)  # User performing action
    target_user_id = Column(Integer, nullable=True)  # User affected (if different)
    ip_hash = Column(String, nullable=True)  # SHA256 hash of IP
    user_agent_hash = Column(String, nullable=True)  # SHA256 hash of user agent
    details = Column(JSON, nullable=True)  # Additional context (no PII)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AuditAction:
    """Audit action types (enum-like constants)"""
    # Authentication
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAIL = "LOGIN_FAIL"
    LOGOUT = "LOGOUT"
    SIGNUP = "SIGNUP"
    
    # Password & Token
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    PASSWORD_RESET_CONFIRM = "PASSWORD_RESET_CONFIRM"
    TOKEN_REVOKE = "TOKEN_REVOKE"
    TOKEN_BLACKLIST = "TOKEN_BLACKLIST"
    
    # Email Verification
    EMAIL_VERIFICATION_SENT = "EMAIL_VERIFICATION_SENT"
    EMAIL_VERIFICATION_SUCCESS = "EMAIL_VERIFICATION_SUCCESS"
    EMAIL_VERIFICATION_FAIL = "EMAIL_VERIFICATION_FAIL"
    
    # GDPR & Data
    USER_EXPORT = "USER_EXPORT"
    USER_DELETE_SOFT = "USER_DELETE_SOFT"
    USER_DELETE_HARD = "USER_DELETE_HARD"
    USER_RESTORE = "USER_RESTORE"
    
    # Billing & Subscription
    BILLING_EVENT_RECEIVED = "BILLING_EVENT_RECEIVED"
    PLAN_CHANGED = "PLAN_CHANGED"
    SUBSCRIPTION_CREATED = "SUBSCRIPTION_CREATED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    
    # Security
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    AUTH_RATE_LIMIT_HIT = "AUTH_RATE_LIMIT_HIT"
    PROMPT_INJECTION_BLOCKED = "PROMPT_INJECTION_BLOCKED"
    CONTENT_MODERATION_BLOCKED = "CONTENT_MODERATION_BLOCKED"
    
    # Admin Actions (future)
    ADMIN_USER_IMPERSONATE = "ADMIN_USER_IMPERSONATE"
    ADMIN_USER_SUSPEND = "ADMIN_USER_SUSPEND"
    ADMIN_USER_UNSUSPEND = "ADMIN_USER_UNSUSPEND"


class AuditLogService:
    """
    Service for creating and querying audit logs
    
    Features:
    - PII protection (hashes IP and user agent)
    - Append-only (no updates/deletes)
    - Structured details (JSON)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def _hash_pii(value: Optional[str]) -> Optional[str]:
        """
        Hash PII data for privacy
        
        Args:
            value: Value to hash (IP, user agent, etc.)
        
        Returns:
            SHA256 hash or None
        """
        if not value:
            return None
        
        return hashlib.sha256(value.encode()).hexdigest()
    
    def log(
        self,
        action_type: str,
        actor_user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Create an audit log entry
        
        Args:
            action_type: Action type (use AuditAction constants)
            actor_user_id: User performing the action
            target_user_id: User affected by action (if different from actor)
            ip_address: Client IP address (will be hashed)
            user_agent: Client user agent (will be hashed)
            details: Additional context (no PII!)
        
        Returns:
            Created AuditLog instance
        """
        # Hash PII
        ip_hash = self._hash_pii(ip_address)
        user_agent_hash = self._hash_pii(user_agent)
        
        # Create log entry
        audit_entry = AuditLog(
            action_type=action_type,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            details=details or {},
            created_at=datetime.utcnow()
        )
        
        try:
            self.db.add(audit_entry)
            self.db.commit()
            self.db.refresh(audit_entry)
            
            logger.debug(f"Audit log created: {action_type} by user {actor_user_id}")
            return audit_entry
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def log_login_success(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        login_method: str = "password"
    ):
        """Log successful login"""
        self.log(
            action_type=AuditAction.LOGIN_SUCCESS,
            actor_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"login_method": login_method}
        )
    
    def log_login_fail(
        self,
        email: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log failed login attempt
        
        Note: email is hashed to prevent PII leakage
        """
        email_hash = self._hash_pii(email)
        self.log(
            action_type=AuditAction.LOGIN_FAIL,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "email_hash": email_hash,
                "reason": reason
            }
        )
    
    def log_logout(self, user_id: int):
        """Log logout"""
        self.log(
            action_type=AuditAction.LOGOUT,
            actor_user_id=user_id
        )
    
    def log_token_revoke(self, user_id: int, reason: str = "logout"):
        """Log token revocation"""
        self.log(
            action_type=AuditAction.TOKEN_REVOKE,
            actor_user_id=user_id,
            details={"reason": reason}
        )
    
    def log_user_export(self, user_id: int):
        """Log GDPR data export"""
        self.log(
            action_type=AuditAction.USER_EXPORT,
            actor_user_id=user_id,
            target_user_id=user_id
        )
    
    def log_user_delete(self, user_id: int, deletion_type: str = "soft"):
        """Log GDPR user deletion"""
        action = AuditAction.USER_DELETE_SOFT if deletion_type == "soft" else AuditAction.USER_DELETE_HARD
        self.log(
            action_type=action,
            actor_user_id=user_id,
            target_user_id=user_id,
            details={"deletion_type": deletion_type}
        )
    
    def log_email_verification_sent(self, user_id: int, email_hash: str):
        """Log verification email sent"""
        self.log(
            action_type=AuditAction.EMAIL_VERIFICATION_SENT,
            actor_user_id=user_id,
            details={"email_hash": email_hash}
        )
    
    def log_email_verification_success(self, user_id: int):
        """Log successful email verification"""
        self.log(
            action_type=AuditAction.EMAIL_VERIFICATION_SUCCESS,
            actor_user_id=user_id,
            target_user_id=user_id
        )
    
    def log_prompt_injection_blocked(
        self,
        user_id: Optional[int],
        reason: str,
        ip_address: Optional[str] = None
    ):
        """Log blocked prompt injection attempt"""
        self.log(
            action_type=AuditAction.PROMPT_INJECTION_BLOCKED,
            actor_user_id=user_id,
            ip_address=ip_address,
            details={"reason": reason}
        )
    
    def get_user_audit_log(
        self,
        user_id: int,
        limit: int = 100,
        action_type: Optional[str] = None
    ) -> list[AuditLog]:
        """
        Get audit log entries for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of entries
            action_type: Optional filter by action type
        
        Returns:
            List of AuditLog entries
        """
        query = self.db.query(AuditLog).filter(AuditLog.actor_user_id == user_id)
        
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


def get_audit_log_service(db: Session) -> AuditLogService:
    """
    Get audit log service instance
    
    Args:
        db: Database session
    
    Returns:
        AuditLogService instance
    """
    return AuditLogService(db)

