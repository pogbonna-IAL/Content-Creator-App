"""
OAuth authentication routes for Google, Facebook, and GitHub
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi_sso import GoogleSSO, FacebookSSO, GithubSSO
from .database import get_db, User
from .auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])

# OAuth configuration from environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID", "")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# OAuth redirect URLs
# Frontend callback URL (where backend redirects after processing OAuth)
FRONTEND_CALLBACK_URL = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:3000/auth/callback")
# Backend API base URL (where OAuth providers redirect to)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize SSO providers
# Note: redirect_uri must point to the BACKEND API endpoint, not the frontend
google_sso = GoogleSSO(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri=f"{API_BASE_URL}/api/auth/oauth/google/callback" if GOOGLE_CLIENT_ID else None,
    allow_insecure_http=True  # For local development
) if GOOGLE_CLIENT_ID else None

facebook_sso = FacebookSSO(
    client_id=FACEBOOK_CLIENT_ID,
    client_secret=FACEBOOK_CLIENT_SECRET,
    redirect_uri=f"{API_BASE_URL}/api/auth/oauth/facebook/callback" if FACEBOOK_CLIENT_ID else None,
    allow_insecure_http=True
) if FACEBOOK_CLIENT_ID else None

github_sso = GithubSSO(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    redirect_uri=f"{API_BASE_URL}/api/auth/oauth/github/callback" if GITHUB_CLIENT_ID else None,
    allow_insecure_http=True
) if GITHUB_CLIENT_ID else None


def get_or_create_oauth_user(
    db: Session,
    provider: str,
    provider_id: str,
    email: str,
    full_name: str = None
) -> User:
    """Get existing user or create new user from OAuth provider"""
    # Check if user exists with this provider and provider_id
    user = db.query(User).filter(
        User.provider == provider,
        User.provider_id == provider_id
    ).first()
    
    if user:
        return user
    
    # Check if user exists with this email (link accounts)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link OAuth provider to existing account
        user.provider = provider
        user.provider_id = provider_id
        if not user.full_name and full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user
    
    # Create new user
    new_user = User(
        email=email,
        full_name=full_name,
        provider=provider,
        provider_id=provider_id,
        hashed_password=None,  # OAuth users don't have passwords
        is_active=True,
        is_verified=True  # OAuth providers verify emails
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    if not google_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables. See OAUTH_SETUP.md for instructions."
        )
    async with google_sso:
        return await google_sso.get_login_redirect()


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    if not google_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    
    try:
        async with google_sso:
            user_info = await google_sso.verify_and_process(request)
        
        # Get or create user
        user = get_or_create_oauth_user(
            db=db,
            provider="google",
            provider_id=user_info.id,
            email=user_info.email,
            full_name=user_info.display_name or user_info.first_name
        )
        
        # Create access token
        # JWT requires 'sub' claim to be a string
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{FRONTEND_CALLBACK_URL}?token={access_token}&provider=google"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google OAuth failed: {str(e)}"
        )


@router.get("/facebook/login")
async def facebook_login():
    """Initiate Facebook OAuth login"""
    if not facebook_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook Signin Coming soon"
        )
    async with facebook_sso:
        return await facebook_sso.get_login_redirect()


@router.get("/facebook/callback")
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Facebook OAuth callback"""
    if not facebook_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook Signin Coming soon"
        )
    
    try:
        async with facebook_sso:
            user_info = await facebook_sso.verify_and_process(request)
        
        # Get or create user
        user = get_or_create_oauth_user(
            db=db,
            provider="facebook",
            provider_id=user_info.id,
            email=user_info.email or f"{user_info.id}@facebook.com",
            full_name=user_info.display_name or user_info.first_name
        )
        
        # Create access token
        # JWT requires 'sub' claim to be a string
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{FRONTEND_CALLBACK_URL}?token={access_token}&provider=facebook"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Facebook OAuth failed: {str(e)}"
        )


@router.get("/github/login")
async def github_login():
    """Initiate GitHub OAuth login"""
    if not github_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub Signin is Coming Soon"
        )
    async with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback"""
    if not github_sso:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub Signin is Coming Soon"
        )
    
    try:
        async with github_sso:
            user_info = await github_sso.verify_and_process(request)
        
        # Get or create user
        user = get_or_create_oauth_user(
            db=db,
            provider="github",
            provider_id=user_info.id,
            email=user_info.email or f"{user_info.id}@github.com",
            full_name=user_info.display_name or user_info.first_name or user_info.username
        )
        
        # Create access token
        # JWT requires 'sub' claim to be a string
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{FRONTEND_CALLBACK_URL}?token={access_token}&provider=github"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub OAuth failed: {str(e)}"
        )

