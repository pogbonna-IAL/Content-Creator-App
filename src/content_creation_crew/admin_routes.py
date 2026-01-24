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
from .auth import get_current_user
from .services.cache_invalidation import get_cache_invalidation_service

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

