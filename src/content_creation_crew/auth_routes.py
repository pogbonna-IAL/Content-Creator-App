"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta, datetime
from .database import get_db, User, init_db
from .auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    http_bearer
)
from fastapi.security import HTTPAuthorizationCredentials
from .config import config
from .services.gdpr_export_service import GDPRExportService
from .services.gdpr_deletion_service import GDPRDeletionService
from .middleware.auth_rate_limit import get_auth_rate_limiter

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "MyP@ssw0rd123",
                "full_name": "John Doe"
            }
        }


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    provider: Optional[str] = None


@router.get("/password-requirements", status_code=status.HTTP_200_OK)
async def get_password_requirements():
    """
    Get password requirements for signup
    
    Returns the current password policy requirements.
    Use this to show requirements on the signup form.
    """
    from .services.password_validator import get_password_validator
    
    validator = get_password_validator()
    
    return {
        "requirements": validator.get_requirements_list(),
        "description": validator.get_requirements_text(),
        "example": "MyP@ssw0rd123"
    }


@router.post("/signup", response_model=Token, dependencies=[Depends(get_auth_rate_limiter())])
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new user with email and password
    
    Password Requirements:
    - At least 8 characters
    - One uppercase letter (A-Z)
    - One lowercase letter (a-z)
    - One number (0-9)
    - One special character (!@#$%^&* etc.)
    - Not a commonly used password
    
    Use GET /api/auth/password-requirements to get dynamic requirements.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Signup attempt for email: {user_data.email}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Signup failed: Email already registered - {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        from .services.password_validator import get_password_validator
        
        validator = get_password_validator()
        is_valid, error_message = validator.validate(user_data.password)
        
        if not is_valid:
            logger.warning(f"Signup failed: Weak password for email - {user_data.email}: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Create new user
        logger.info(f"Creating user for email: {user_data.email}")
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name if user_data.full_name else None,
            provider="email",
            is_active=True,
            is_verified=False  # Email verification can be added later
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User created successfully with ID: {new_user.id}")
        
        # Audit log
        from .services.audit_log_service import get_audit_log_service
        audit_service = get_audit_log_service(db)
        audit_service.log(
            action_type="SIGNUP",
            actor_user_id=new_user.id,
            details={"provider": "email"}
        )
        
        # Create access token
        # JWT requires 'sub' claim to be a string
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(new_user.id)}, expires_delta=access_token_expires
        )
        logger.info(f"Access token created for user ID: {new_user.id}")
        
        # Prepare response data
        response_data = {
            "access_token": access_token,  # Keep for backward compatibility
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "is_active": new_user.is_active,
                "is_verified": new_user.is_verified,
                "provider": new_user.provider
            }
        }
        
        # Create response with httpOnly cookie
        from fastapi.responses import JSONResponse
        response = JSONResponse(content=response_data)
        
        # Set httpOnly cookie for token (secure in production)
        cookie_max_age = int(access_token_expires.total_seconds())
        response.set_cookie(
            key="auth_token",
            value=access_token,
            max_age=cookie_max_age,
            httponly=True,
            secure=config.ENV in ["staging", "prod"],  # HTTPS only in staging/prod
            samesite="lax",  # CSRF protection
            path="/"
        )
        
        # Set user info cookie (not sensitive, can be readable)
        import json
        response.set_cookie(
            key="auth_user",
            value=json.dumps(response_data["user"]),
            max_age=cookie_max_age,
            httponly=False,  # Can be read by frontend for display
            secure=config.ENV in ["staging", "prod"],
            samesite="lax",
            path="/"
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.post("/login", response_model=Token, dependencies=[Depends(get_auth_rate_limiter())])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email and password"""
    # Find user by email (username field in OAuth2PasswordRequestForm)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses OAuth login. Please sign in with your provider.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    # JWT requires 'sub' claim to be a string
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Prepare response data
    response_data = {
        "access_token": access_token,  # Keep for backward compatibility
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "provider": user.provider
        }
    }
    
    # Create response with httpOnly cookie
    from fastapi.responses import JSONResponse
    response = JSONResponse(content=response_data)
    
    # Set httpOnly cookie for token (secure in production)
    cookie_max_age = int(access_token_expires.total_seconds())
    response.set_cookie(
        key="auth_token",
        value=access_token,
        max_age=cookie_max_age,
        httponly=True,
        secure=config.ENV in ["staging", "prod"],  # HTTPS only in staging/prod
        samesite="lax",  # CSRF protection
        path="/"
    )
    
    # Set user info cookie (not sensitive, can be readable)
    import json
    response.set_cookie(
        key="auth_user",
        value=json.dumps(response_data["user"]),
        max_age=cookie_max_age,
        httponly=False,  # Can be read by frontend for display
        secure=config.ENV in ["staging", "prod"],
        samesite="lax",
        path="/"
    )
    
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "provider": current_user.provider
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user and clear httpOnly cookie"""
    from fastapi.responses import JSONResponse
    
    # Create response
    response = JSONResponse(content={"message": "Logged out successfully"})
    
    # Clear httpOnly cookie
    response.delete_cookie(
        key="auth_token",
        path="/",
        samesite="lax",
        httponly=True
    )
    response.delete_cookie(
        key="auth_user",
        path="/",
        samesite="lax"
    )
    
    return response


@router.get("/csrf-token")
async def get_csrf_token(current_user: User = Depends(get_current_user)):
    """
    Generate CSRF token for authenticated users
    
    Returns a CSRF token that should be included in X-CSRF-Token header
    for state-changing operations (e.g., billing actions).
    """
    import uuid
    import hashlib
    import hmac
    from datetime import datetime, timedelta
    
    # Generate CSRF token based on user ID and timestamp
    # In production, you might want to store this in Redis with expiration
    timestamp = int(datetime.utcnow().timestamp())
    user_id_str = str(current_user.id)
    
    # Create token: HMAC(user_id + timestamp, secret_key)
    message = f"{user_id_str}:{timestamp}".encode()
    token = hmac.new(
        config.SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Return token and expiration info
    return {
        "csrf_token": token,
        "expires_in": 3600,  # 1 hour
        "header_name": "X-CSRF-Token"
    }


# =====================================================================
# Email Verification Endpoints (S8)
# =====================================================================

class EmailVerificationRequest(BaseModel):
    """Request model for email verification"""
    pass


class EmailVerificationConfirm(BaseModel):
    """Confirm model for email verification"""
    token: str


@router.post("/verify-email/request", status_code=status.HTTP_200_OK)
async def request_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request email verification email to be sent
    
    Sends a verification email to the user's registered email address.
    The email contains a verification link with a unique token.
    """
    import logging
    import secrets
    from .services.email_provider import send_verification_email
    from .services.audit_log_service import get_audit_log_service
    
    logger = logging.getLogger(__name__)
    
    # Check if already verified
    if current_user.email_verified:
        return {
            "message": "Email already verified",
            "email_verified": True
        }
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Store token and timestamp
    current_user.email_verification_token = verification_token
    current_user.email_verification_sent_at = datetime.utcnow()
    
    db.commit()
    
    # Build verification URL
    frontend_url = config.FRONTEND_URL or "http://localhost:3000"
    verification_url = f"{frontend_url}/verify-email?token={verification_token}"
    
    # Send verification email
    try:
        send_verification_email(current_user.email, verification_url)
        logger.info(f"Verification email sent to user {current_user.id}")
        
        # Audit log
        audit_service = get_audit_log_service(db)
        audit_service.log_email_verification_sent(
            user_id=current_user.id,
            email_hash=audit_service._hash_pii(current_user.email)
        )
        
        return {
            "message": "Verification email sent",
            "email": current_user.email
        }
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/verify-email/confirm", status_code=status.HTTP_200_OK)
async def confirm_email_verification(
    data: EmailVerificationConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm email verification with token
    
    Verifies the user's email address using the token from the verification email.
    """
    import logging
    from .services.audit_log_service import get_audit_log_service
    
    logger = logging.getLogger(__name__)
    
    # Find user by verification token
    user = db.query(User).filter(
        User.email_verification_token == data.token
    ).first()
    
    if not user:
        logger.warning(f"Invalid verification token: {data.token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Check if token is expired (24 hours)
    if user.email_verification_sent_at:
        token_age = datetime.utcnow() - user.email_verification_sent_at
        if token_age.total_seconds() > 86400:  # 24 hours
            logger.warning(f"Expired verification token for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one."
            )
    
    # Mark email as verified
    user.email_verified = True
    user.email_verification_token = None  # Clear token after use
    user.email_verification_sent_at = None
    
    db.commit()
    
    logger.info(f"Email verified for user {user.id}")
    
    # Audit log
    audit_service = get_audit_log_service(db)
    audit_service.log_email_verification_success(user_id=user.id)
    
    # Invalidate user cache (M6)
    from .services.cache_invalidation import get_cache_invalidation_service
    cache_invalidation = get_cache_invalidation_service()
    cache_invalidation.invalidate_user_on_email_verification(user.id)
    
    return {
        "message": "Email verified successfully",
        "email_verified": True
    }


@router.get("/verify-email/status", status_code=status.HTTP_200_OK)
async def get_email_verification_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current email verification status
    
    Returns whether the user's email has been verified.
    """
    return {
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "verification_required": not current_user.email_verified
    }

