"""
Admin routes for cache invalidation and system management (M6)
Protected endpoints for administrative operations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from .db.engine import get_db
from .db.models.user import User
from .db.models.user_model_preference import UserModelPreference
from .auth import get_current_user
from .services.cache_invalidation import get_cache_invalidation_service
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


# ============================================================================
# Request/Response Models
# ============================================================================

class InvalidateUserRequest(BaseModel):
    """Request to invalidate user cache"""
    user_ids: List[int]
    reason: Optional[str] = "admin_action"


class InvalidateOrgRequest(BaseModel):
    """Request to invalidate organization cache"""
    org_ids: List[int]
    reason: Optional[str] = "admin_action"


class InvalidateContentRequest(BaseModel):
    """Request to invalidate content cache"""
    topics: Optional[List[str]] = None
    clear_all: bool = False
    reason: Optional[str] = "admin_action"


# ============================================================================
# Admin Guard Dependency
# ============================================================================

async def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Require user to be an admin
    
    Checks the is_admin flag on the user model.
    Backward compatible: existing users default to is_admin=False.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        User if admin
    
    Raises:
        HTTPException: If user is not admin
    """
    # Refresh user from database to ensure we have latest is_admin value
    db.refresh(current_user)
    
    # Check admin flag
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.id} ({current_user.email}) attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"Admin access granted to user {current_user.id} ({current_user.email})")
    return current_user


# ============================================================================
# Cache Invalidation Endpoints
# ============================================================================

@router.post("/cache/invalidate/users")
async def invalidate_user_caches(
    request: InvalidateUserRequest,
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Invalidate user caches (admin only)
    
    Emergency endpoint to force cache invalidation for specific users.
    Use when users report stale data that won't clear automatically.
    
    **Admin Access Required**
    """
    try:
        cache_invalidation = get_cache_invalidation_service()
        
        count = cache_invalidation.invalidate_multiple_users(
            request.user_ids,
            reason=f"{request.reason} (admin:{admin_user.id})"
        )
        
        logger.info(
            f"Admin {admin_user.id} invalidated {count} user caches: "
            f"user_ids={request.user_ids}, reason={request.reason}"
        )
        
        return {
            "status": "success",
            "invalidated_count": count,
            "requested_count": len(request.user_ids),
            "user_ids": request.user_ids,
            "reason": request.reason
        }
    
    except Exception as e:
        logger.error(f"Admin cache invalidation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )


@router.post("/cache/invalidate/orgs")
async def invalidate_org_caches(
    request: InvalidateOrgRequest,
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Invalidate organization/plan caches (admin only)
    
    Emergency endpoint to force cache invalidation for specific organizations.
    Use when plan changes or subscription updates are not reflecting immediately.
    
    **Admin Access Required**
    """
    try:
        cache_invalidation = get_cache_invalidation_service()
        
        count = 0
        for org_id in request.org_ids:
            if cache_invalidation.invalidate_org_plan(
                org_id,
                reason=f"{request.reason} (admin:{admin_user.id})"
            ):
                count += 1
        
        logger.info(
            f"Admin {admin_user.id} invalidated {count} org caches: "
            f"org_ids={request.org_ids}, reason={request.reason}"
        )
        
        return {
            "status": "success",
            "invalidated_count": count,
            "requested_count": len(request.org_ids),
            "org_ids": request.org_ids,
            "reason": request.reason
        }
    
    except Exception as e:
        logger.error(f"Admin cache invalidation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )


@router.post("/cache/invalidate/content")
async def invalidate_content_cache(
    request: InvalidateContentRequest,
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Invalidate content caches (admin only)
    
    **WARNING: Use with caution!**
    
    This endpoint allows invalidating content caches:
    - By specific topics (recommended)
    - ALL content at once (emergency only)
    
    Use cases:
    - Moderation rules changed globally
    - Prompt version changed
    - Critical bug fix in content generation
    - Content quality issues detected
    
    **Admin Access Required**
    """
    try:
        cache_invalidation = get_cache_invalidation_service()
        
        if request.clear_all:
            # NUCLEAR OPTION: Clear ALL content cache
            logger.warning(
                f"Admin {admin_user.id} is clearing ALL content cache! "
                f"Reason: {request.reason}"
            )
            
            success = cache_invalidation.invalidate_all_content(
                reason=f"{request.reason} (admin:{admin_user.id})"
            )
            
            return {
                "status": "success" if success else "failed",
                "action": "clear_all",
                "message": "All content cache cleared" if success else "Failed to clear cache",
                "reason": request.reason,
                "warning": "This will impact performance until cache rebuilds"
            }
        
        elif request.topics:
            # Targeted invalidation by topics
            count = 0
            for topic in request.topics:
                if cache_invalidation.invalidate_content_by_topic(
                    topic,
                    reason=f"{request.reason} (admin:{admin_user.id})"
                ):
                    count += 1
            
            logger.info(
                f"Admin {admin_user.id} invalidated {count} content topics: "
                f"topics={request.topics}, reason={request.reason}"
            )
            
            return {
                "status": "success",
                "action": "invalidate_topics",
                "invalidated_count": count,
                "topics": request.topics,
                "reason": request.reason
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify either topics or clear_all=true"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin cache invalidation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cache statistics (admin only)
    
    Returns current cache state and statistics for monitoring.
    
    **Admin Access Required**
    """
    try:
        cache_invalidation = get_cache_invalidation_service()
        stats = cache_invalidation.get_invalidation_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


# ============================================================================
# Moderation Version Management
# ============================================================================

@router.post("/moderation/bump-version")
async def bump_moderation_version(
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Bump moderation version to invalidate all content cache (admin only)
    
    **WARNING: This will invalidate ALL content cache!**
    
    Use this when:
    - Moderation rules have changed
    - Content policy updated
    - Need to force regeneration with new rules
    
    The MODERATION_VERSION should be updated in config/environment,
    but this endpoint can also clear all content to force immediate effect.
    
    **Admin Access Required**
    """
    try:
        from .config import config
        
        current_version = config.MODERATION_VERSION
        
        logger.warning(
            f"Admin {admin_user.id} requested moderation version bump. "
            f"Current version: {current_version}"
        )
        
        # Clear all content cache to force regeneration
        cache_invalidation = get_cache_invalidation_service()
        success = cache_invalidation.invalidate_all_content(
            reason=f"moderation_version_bump (admin:{admin_user.id})"
        )
        
        return {
            "status": "success" if success else "failed",
            "action": "moderation_version_bump",
            "current_version": current_version,
            "message": (
                "All content cache cleared. "
                "Update MODERATION_VERSION env var to complete version bump."
            ),
            "instructions": [
                "1. Set MODERATION_VERSION=<new_version> in environment",
                "2. Restart application to pick up new version",
                "3. Content will be regenerated with new moderation rules"
            ]
        }
    
    except Exception as e:
        logger.error(f"Moderation version bump failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Moderation version bump failed: {str(e)}"
        )


# ============================================================================
# User Management Endpoints (for admin user management)
# ============================================================================

@router.post("/users/{user_id}/make-admin")
async def make_user_admin(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Make a user an admin (admin only)
    
    **Admin Access Required**
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    if target_user.is_admin:
        return {
            "status": "success",
            "message": f"User {user_id} is already an admin",
            "user_id": user_id,
            "email": target_user.email
        }
    
    target_user.is_admin = True
    db.commit()
    db.refresh(target_user)
    
    logger.info(f"Admin {admin_user.id} made user {user_id} ({target_user.email}) an admin")
    
    return {
        "status": "success",
        "message": f"User {user_id} is now an admin",
        "user_id": user_id,
        "email": target_user.email
    }


@router.post("/users/{user_id}/remove-admin")
async def remove_user_admin(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Remove admin status from a user (admin only)
    
    **Admin Access Required**
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    if not target_user.is_admin:
        return {
            "status": "success",
            "message": f"User {user_id} is not an admin",
            "user_id": user_id,
            "email": target_user.email
        }
    
    # Prevent removing admin from yourself
    if target_user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin status from yourself"
        )
    
    target_user.is_admin = False
    db.commit()
    db.refresh(target_user)
    
    logger.info(f"Admin {admin_user.id} removed admin status from user {user_id} ({target_user.email})")
    
    return {
        "status": "success",
        "message": f"User {user_id} is no longer an admin",
        "user_id": user_id,
        "email": target_user.email
    }


@router.get("/users/admins")
async def list_admin_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all admin users (admin only)
    
    **Admin Access Required**
    """
    admins = db.query(User).filter(User.is_admin == True).all()
    
    return {
        "status": "success",
        "count": len(admins),
        "admins": [
            {
                "id": admin.id,
                "email": admin.email,
                "full_name": admin.full_name,
                "is_active": admin.is_active,
                "created_at": admin.created_at.isoformat() if admin.created_at else None
            }
            for admin in admins
        ]
    }


# ============================================================================
# Dunning Process Management Endpoints
# ============================================================================

@router.get("/dunning/processes")
async def list_dunning_processes(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List dunning processes (admin only)
    
    View all payment recovery processes with filtering options.
    
    **Admin Access Required**
    """
    from .db.models.dunning import DunningProcess
    
    query = db.query(DunningProcess)
    
    if status:
        query = query.filter(DunningProcess.status == status)
    
    total = query.count()
    processes = query.order_by(DunningProcess.created_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "status": "success",
        "count": len(processes),
        "total": total,
        "processes": [
            {
                "id": p.id,
                "subscription_id": p.subscription_id,
                "organization_id": p.organization_id,
                "status": p.status,
                "amount_due": float(p.amount_due) if p.amount_due else 0.0,
                "amount_recovered": float(p.amount_recovered) if p.amount_recovered else 0.0,
                "currency": p.currency,
                "total_attempts": p.total_attempts,
                "total_emails_sent": p.total_emails_sent,
                "current_stage": p.current_stage,
                "started_at": p.started_at.isoformat() if p.started_at else None,
                "next_action_at": p.next_action_at.isoformat() if p.next_action_at else None,
                "grace_period_ends_at": p.grace_period_ends_at.isoformat() if p.grace_period_ends_at else None,
                "will_cancel_at": p.will_cancel_at.isoformat() if p.will_cancel_at else None,
                "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
                "cancelled_at": p.cancelled_at.isoformat() if p.cancelled_at else None,
                "cancellation_reason": p.cancellation_reason,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in processes
        ]
    }


@router.get("/dunning/processes/{process_id}")
async def get_dunning_process(
    process_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed dunning process information (admin only)
    
    Includes payment attempts and notifications.
    
    **Admin Access Required**
    """
    from .db.models.dunning import DunningProcess, PaymentAttempt, DunningNotification
    
    process = db.query(DunningProcess).filter(DunningProcess.id == process_id).first()
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dunning process {process_id} not found"
        )
    
    # Get payment attempts
    payment_attempts = db.query(PaymentAttempt).filter(
        PaymentAttempt.dunning_process_id == process_id
    ).order_by(PaymentAttempt.created_at.desc()).all()
    
    # Get notifications
    notifications = db.query(DunningNotification).filter(
        DunningNotification.dunning_process_id == process_id
    ).order_by(DunningNotification.created_at.desc()).all()
    
    return {
        "status": "success",
        "process": {
            "id": process.id,
            "subscription_id": process.subscription_id,
            "organization_id": process.organization_id,
            "status": process.status,
            "amount_due": float(process.amount_due) if process.amount_due else 0.0,
            "amount_recovered": float(process.amount_recovered) if process.amount_recovered else 0.0,
            "currency": process.currency,
            "total_attempts": process.total_attempts,
            "total_emails_sent": process.total_emails_sent,
            "current_stage": process.current_stage,
            "started_at": process.started_at.isoformat() if process.started_at else None,
            "next_action_at": process.next_action_at.isoformat() if process.next_action_at else None,
            "grace_period_ends_at": process.grace_period_ends_at.isoformat() if process.grace_period_ends_at else None,
            "will_cancel_at": process.will_cancel_at.isoformat() if process.will_cancel_at else None,
            "resolved_at": process.resolved_at.isoformat() if process.resolved_at else None,
            "cancelled_at": process.cancelled_at.isoformat() if process.cancelled_at else None,
            "cancellation_reason": process.cancellation_reason,
            "created_at": process.created_at.isoformat() if process.created_at else None,
        },
        "payment_attempts": [
            {
                "id": pa.id,
                "amount": float(pa.amount) if pa.amount else 0.0,
                "currency": pa.currency,
                "status": pa.status,
                "attempt_number": pa.attempt_number,
                "is_automatic": pa.is_automatic,
                "provider": pa.provider,
                "failure_code": pa.failure_code,
                "failure_message": pa.failure_message,
                "failure_reason": pa.failure_reason,
                "attempted_at": pa.attempted_at.isoformat() if pa.attempted_at else None,
                "succeeded_at": pa.succeeded_at.isoformat() if pa.succeeded_at else None,
                "failed_at": pa.failed_at.isoformat() if pa.failed_at else None,
            }
            for pa in payment_attempts
        ],
        "notifications": [
            {
                "id": n.id,
                "notification_type": n.notification_type,
                "sent_to": n.sent_to,
                "subject": n.subject,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "delivered": n.delivered,
                "opened": n.opened,
                "clicked": n.clicked,
            }
            for n in notifications
        ]
    }


@router.get("/dunning/stats")
async def get_dunning_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get dunning process statistics (admin only)
    
    Returns summary statistics about payment recovery processes.
    
    **Admin Access Required**
    """
    from .db.models.dunning import DunningProcess, DunningStatus
    
    total = db.query(DunningProcess).count()
    active = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.ACTIVE.value).count()
    grace_period = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.GRACE_PERIOD.value).count()
    recovering = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.RECOVERING.value).count()
    recovered = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.RECOVERED.value).count()
    cancelled = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.CANCELLED.value).count()
    exhausted = db.query(DunningProcess).filter(DunningProcess.status == DunningStatus.EXHAUSTED.value).count()
    
    # Calculate total amount due and recovered
    from sqlalchemy import func
    total_due_result = db.query(func.sum(DunningProcess.amount_due)).scalar() or 0
    total_recovered_result = db.query(func.sum(DunningProcess.amount_recovered)).scalar() or 0
    
    return {
        "status": "success",
        "stats": {
            "total": total,
            "by_status": {
                "active": active,
                "grace_period": grace_period,
                "recovering": recovering,
                "recovered": recovered,
                "cancelled": cancelled,
                "exhausted": exhausted,
            },
            "total_amount_due": float(total_due_result) if total_due_result else 0.0,
            "total_amount_recovered": float(total_recovered_result) if total_recovered_result else 0.0,
            "recovery_rate": float(total_recovered_result / total_due_result * 100) if total_due_result > 0 else 0.0,
        }
    }


# ============================================================================
# User Model Preferences Management Endpoints
# ============================================================================

# Available models list - includes both OpenAI and Ollama models
# These models are available for ALL content types: blog, social, audio, and video
# The same model list is used for all content type dropdowns in the admin UI
# All models work for all content types, including audio and video content generation
AVAILABLE_MODELS = [
    # OpenAI Models (work for all content types)
    'gpt-4o-mini',
    'gpt-4o',
    'gpt-4-turbo',
    'gpt-4',
    'gpt-3.5-turbo',
    # Ollama Models (open source - work for all content types including audio and video)
    # These models are suitable for generating audio scripts, video scripts, blog posts, and social media content
    'ollama/llama3.2:1b',      # Fast, good for audio scripts and quick content
    'ollama/llama3.2:3b',      # Balanced speed/quality for audio and video scripts
    'ollama/llama3.1:8b',      # High quality for video scripts and complex content
    'ollama/llama3.1:70b',     # Best quality for complex video and audio content
    'ollama/llama3:8b',        # Alternative high-quality model
    'ollama/llama3:70b',       # Alternative best-quality model
    'ollama/mistral:7b',       # Good for conversational audio content
    'ollama/mixtral:8x7b',     # High quality for complex video content
    'ollama/codellama:7b',     # Good for technical content
    'ollama/codellama:13b',    # Better for technical content
    'ollama/phi:2.7b',         # Fast and efficient
    'ollama/neural-chat:7b',   # Good for conversational content
]

CONTENT_TYPES = ['blog', 'social', 'audio', 'video']


class UserModelPreferenceRequest(BaseModel):
    """Request to set user model preference"""
    user_id: int
    content_type: str  # 'blog', 'social', 'audio', 'video'
    model_name: str  # e.g., 'gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'


@router.get("/users/{user_id}/model-preferences")
async def get_user_model_preferences(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get model preferences for a user (admin only)
    """
    # Verify user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    preferences = db.query(UserModelPreference).filter(
        UserModelPreference.user_id == user_id
    ).all()
    
    return {
        "status": "success",
        "user_id": user_id,
        "user_email": target_user.email,
        "preferences": [
            {
                "id": p.id,
                "content_type": p.content_type,
                "model_name": p.model_name,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "created_by_admin_id": p.created_by_admin_id
            }
            for p in preferences
        ],
        "available_models": AVAILABLE_MODELS,
        "content_types": CONTENT_TYPES
    }


@router.post("/users/{user_id}/model-preferences")
async def set_user_model_preference(
    user_id: int,
    request: UserModelPreferenceRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Set model preference for a user and content type (admin only)
    """
    # Verify user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Validate content type
    if request.content_type not in CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content_type. Must be one of: {CONTENT_TYPES}"
        )
    
    # Validate model name
    if request.model_name not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model_name. Must be one of: {AVAILABLE_MODELS}"
        )
    
    # Check if preference already exists
    existing = db.query(UserModelPreference).filter(
        UserModelPreference.user_id == user_id,
        UserModelPreference.content_type == request.content_type
    ).first()
    
    if existing:
        # Update existing preference
        existing.model_name = request.model_name
        existing.updated_at = datetime.utcnow()
        existing.created_by_admin_id = admin_user.id
        db.commit()
        db.refresh(existing)
        
        logger.info(
            f"Admin {admin_user.id} updated model preference for user {user_id}: "
            f"{request.content_type} -> {request.model_name}"
        )
        
        return {
            "status": "success",
            "message": f"Model preference updated for {request.content_type}",
            "preference": {
                "id": existing.id,
                "user_id": existing.user_id,
                "content_type": existing.content_type,
                "model_name": existing.model_name,
                "updated_at": existing.updated_at.isoformat() if existing.updated_at else None
            }
        }
    else:
        # Create new preference
        preference = UserModelPreference(
            user_id=user_id,
            content_type=request.content_type,
            model_name=request.model_name,
            created_by_admin_id=admin_user.id
        )
        db.add(preference)
        db.commit()
        db.refresh(preference)
        
        logger.info(
            f"Admin {admin_user.id} set model preference for user {user_id}: "
            f"{request.content_type} -> {request.model_name}"
        )
        
        return {
            "status": "success",
            "message": f"Model preference set for {request.content_type}",
            "preference": {
                "id": preference.id,
                "user_id": preference.user_id,
                "content_type": preference.content_type,
                "model_name": preference.model_name,
                "created_at": preference.created_at.isoformat() if preference.created_at else None
            }
        }


@router.delete("/users/{user_id}/model-preferences/{content_type}")
async def delete_user_model_preference(
    user_id: int,
    content_type: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete model preference for a user and content type (admin only)
    This will revert to tier-based model selection.
    """
    preference = db.query(UserModelPreference).filter(
        UserModelPreference.user_id == user_id,
        UserModelPreference.content_type == content_type
    ).first()
    
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model preference not found for user {user_id} and content_type {content_type}"
        )
    
    db.delete(preference)
    db.commit()
    
    logger.info(
        f"Admin {admin_user.id} deleted model preference for user {user_id}: {content_type}"
    )
    
    return {
        "status": "success",
        "message": f"Model preference deleted for {content_type}. User will use tier-based model."
    }


@router.get("/model-preferences/available-models")
async def get_available_models(
    admin_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get list of available models (admin only)
    Includes both OpenAI and Ollama models.
    Dynamically fetches available Ollama models if OLLAMA_BASE_URL is configured.
    """
    from ..config import config
    import logging
    
    logger = logging.getLogger(__name__)
    
    models = list(AVAILABLE_MODELS)  # Start with base list
    
    # If Ollama is configured, try to fetch available models
    if config.OLLAMA_BASE_URL:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                ollama_url = config.OLLAMA_BASE_URL.rstrip('/')
                response = await client.get(f"{ollama_url}/api/tags")
                if response.status_code == 200:
                    ollama_data = response.json()
                    ollama_models = ollama_data.get('models', [])
                    for model in ollama_models:
                        model_name = model.get('name', '')
                        if model_name:
                            # Format as ollama/model:tag (Ollama API returns model:tag format)
                            ollama_model_name = f"ollama/{model_name}"
                            if ollama_model_name not in models:
                                models.append(ollama_model_name)
                                logger.info(f"Added Ollama model to available list: {ollama_model_name}")
                    logger.info(f"Successfully fetched {len(ollama_models)} Ollama models")
                else:
                    logger.warning(f"Ollama API returned status {response.status_code}")
        except httpx.TimeoutException:
            logger.warning("Timeout fetching Ollama models - Ollama service may be unavailable")
        except httpx.ConnectError:
            logger.warning(f"Could not connect to Ollama at {config.OLLAMA_BASE_URL} - service may not be running")
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
            # Continue with base list if Ollama fetch fails
    
    return {
        "status": "success",
        "models": sorted(models),  # Sort for consistent display
        "content_types": CONTENT_TYPES
    }

