"""
GDPR Compliance API routes (/v1 endpoints)
Mirrors /api/auth/user/* endpoints for consistency
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from .database import get_db, User
from .auth import get_current_user
from .services.gdpr_export_service import GDPRExportService
from .services.gdpr_deletion_service import GDPRDeletionService

router = APIRouter(prefix="/v1/user", tags=["gdpr"])
logger = logging.getLogger(__name__)


@router.get(
    "/export",
    summary="Export user data (GDPR)",
    description="""
    Export all user data in machine-readable JSON format.
    
    **GDPR Article 20 - Right to Data Portability**
    
    Returns a complete export of:
    - User profile
    - Organization memberships
    - Subscriptions and billing history
    - Usage counters
    - Content generation jobs
    - Artifact metadata and file references
    - Statistics
    
    **Format:** JSON (machine-readable)  
    **Schema Version:** Included for future compatibility
    """,
    response_model=Dict[str, Any]
)
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Export all user data (GDPR compliance)
    """
    try:
        logger.info(f"GDPR data export requested by user {current_user.id} (v1 endpoint)")
        
        # Create export service
        export_service = GDPRExportService(db, current_user)
        
        # Export data
        export_data = export_service.export_user_data()
        
        # Log export for audit
        logger.info(f"GDPR data export completed for user {current_user.id}")
        
        # TODO: Add to audit log when audit service is implemented
        
        return export_data
        
    except Exception as e:
        logger.error(f"GDPR export failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data. Please try again or contact support."
        )


@router.delete(
    "/delete",
    summary="Delete user account (GDPR)",
    description="""
    Delete user account and all associated data.
    
    **GDPR Article 17 - Right to Erasure (Right to be Forgotten)**
    
    **Soft Delete (default, hard_delete=false):**
    - Account disabled immediately (cannot login)
    - All sessions revoked
    - Data retained for grace period (default: 30 days)
    - Can be restored by contacting support within grace period
    - Hard delete automatically scheduled after grace period
    
    **Hard Delete (hard_delete=true):**
    - Account and all data permanently deleted immediately
    - Content artifacts and storage files deleted
    - Organizations handled based on ownership:
      - If sole owner with no other members: organization deleted
      - If owner with other members: ownership transferred
      - If member only: membership removed
    - Billing events anonymized (kept for audit compliance)
    - **CANNOT BE UNDONE**
    
    **Query Parameters:**
    - `hard_delete`: Boolean (default: false) - If true, permanently delete immediately
    """,
    response_model=Dict[str, Any]
)
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hard_delete: bool = False
) -> Dict[str, Any]:
    """
    Delete user account (GDPR compliance)
    """
    try:
        logger.warning(f"GDPR account deletion requested by user {current_user.id} (v1 endpoint, hard_delete={hard_delete})")
        
        # Create deletion service
        deletion_service = GDPRDeletionService(db, current_user)
        
        if hard_delete:
            # Immediate permanent deletion
            result = deletion_service.hard_delete()
            logger.warning(f"GDPR hard delete completed for user {current_user.id}")
        else:
            # Soft delete with grace period
            result = deletion_service.soft_delete()
            logger.warning(f"GDPR soft delete completed for user {current_user.id}")
        
        # Invalidate user cache (M6)
        from .services.cache_invalidation import get_cache_invalidation_service
        cache_invalidation = get_cache_invalidation_service()
        cache_invalidation.invalidate_user_on_gdpr_delete(current_user.id)
        
        return result
        
    except Exception as e:
        logger.error(f"GDPR deletion failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account. Please try again or contact support."
        )

