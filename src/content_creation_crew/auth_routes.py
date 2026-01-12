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
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .config import config

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


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


@router.post("/signup", response_model=Token)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Register a new user with email and password"""
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
        
        # Validate password length
        if len(user_data.password) < 8:
            logger.warning(f"Signup failed: Password too short for email - {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
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


@router.post("/login", response_model=Token)
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

