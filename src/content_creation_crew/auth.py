"""
Authentication utilities and JWT token handling
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db, User

# Import config for SECRET_KEY (will be imported after config is initialized)
# Use lazy import to avoid circular dependency
def get_secret_key():
    """Get secret key from config module"""
    from .config import config
    return config.SECRET_KEY

# Security configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours (reduced from 7 days for security)

# Bcrypt configuration
# Cost factor (rounds): Higher = more secure but slower
# - Development: 10-12 rounds (fast enough for dev)
# - Production: 12-14 rounds (recommended for security)
# - Default: 12 rounds (good balance)
# Each increment doubles the time: 12→~300ms, 13→~600ms, 14→~1200ms
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS
)
# Use HTTPBearer for more reliable token extraction
# It handles Authorization header extraction more robustly
http_bearer = HTTPBearer(auto_error=False)

# Keep OAuth2PasswordBearer for compatibility with login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    if not plain_password or not hashed_password:
        return False
    
    # Handle bcrypt's 72-byte limit by hashing long passwords first
    # We need to check if the stored hash was created with a pre-hashed password
    password_bytes = len(plain_password.encode('utf-8'))
    if password_bytes > 72:
        # Hash with SHA256 first if password is too long (matches get_password_hash)
        # SHA256 produces a 64-byte hex string, which is under bcrypt's limit
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    
    try:
        # Try using passlib first
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # If passlib fails, try bcrypt directly
        try:
            # Extract the salt and hash from the bcrypt hash string
            # bcrypt hashes are in format: $2b$12$salt+hash
            if hashed_password.startswith('$2'):
                # Use bcrypt directly
                password_bytes = plain_password.encode('utf-8')
                if len(password_bytes) > 72:
                    # Pre-hash with SHA256
                    password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
                return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
            return False
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Password verification failed: {type(e).__name__}")
            return False


def get_password_hash(password: str) -> str:
    """Hash a password, handling bcrypt's 72-byte limit"""
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Bcrypt has a 72-byte limit, so we hash long passwords with SHA256 first
    password_bytes = password.encode('utf-8')
    password_byte_length = len(password_bytes)
    
    if password_byte_length > 72:
        # Hash with SHA256 first (produces 64-byte hex string), then bcrypt the hash
        # SHA256 hex digest is always 64 bytes (32 bytes * 2 for hex), which is under bcrypt's 72-byte limit
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        # Use the hex digest as bytes for bcrypt
        password_to_hash = password_hash.encode('utf-8')
    else:
        # For passwords <= 72 bytes, use directly
        password_to_hash = password_bytes
    
    # Use bcrypt directly to avoid passlib initialization issues
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_to_hash, salt)
    
    # Return as string (bcrypt returns bytes)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with JTI (JWT ID) for blacklist support
    
    Args:
        data: Dictionary with user data (must include 'sub' - user ID)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    import uuid
    
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add JTI (JWT ID) for token blacklist support
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "jti": jti,  # Unique token identifier for blacklist
        "iat": datetime.utcnow(),  # Issued at
    })
    
    secret_key = get_secret_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        secret_key = get_secret_key()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: Token has expired")
        return None
    except jwt.JWTClaimsError as e:
        logger.warning(f"Token verification failed: Invalid token claims - {str(e)}")
        return None
    except JWTError as e:
        logger.warning(f"Token verification failed: {type(e).__name__} - {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {type(e).__name__} - {str(e)}")
        return None


def get_auth_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)
) -> Optional[str]:
    """
    Extract authentication token from Authorization header or cookie.
    Returns None if no token is found.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try Authorization header first
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
        logger.debug("Token found in Authorization header")
        return token
    
    # Fallback to cookie
    try:
        cookie_token = request.cookies.get("auth_token")
        if cookie_token:
            logger.info("Using token from cookie (no Authorization header present)")
            return cookie_token
        else:
            # Log for debugging - check what cookies are available
            all_cookies = list(request.cookies.keys())
            cookie_count = len(all_cookies)
            logger.warning(
                f"No auth_token cookie found. "
                f"Total cookies received: {cookie_count}, "
                f"Cookie names: {all_cookies}, "
                f"Request URL: {request.url}, "
                f"Request headers: {dict(request.headers)}"
            )
    except AttributeError as e:
        logger.error(f"Request object missing cookies attribute: {e}, Request type: {type(request)}")
    except Exception as e:
        logger.error(f"Error accessing request.cookies: {e}, Request type: {type(request)}")
    
    return None


async def get_current_user(
    token: Optional[str] = Depends(get_auth_token),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token
    
    Checks both Authorization header (Bearer token) and auth_token cookie.
    Cookie is checked as fallback when Authorization header is not present.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate token exists and is not empty
    if not token or not token.strip():
        logger.warning("Authentication failed: No authorization credentials provided (neither header nor cookie)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = token.strip()
    logger.info(f"Verifying token (length: {len(token)})")
    
    payload = verify_token(token)
    if payload is None:
        logger.warning("Authentication failed: Token verification failed (invalid or expired token)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user_id from token - JWT 'sub' claim is a string, convert to int
    user_id_str = payload.get("sub")
    if user_id_str is None:
        logger.warning("Authentication failed: Token payload missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format: missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert string to int (JWT requires 'sub' to be string)
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning(f"Authentication failed: Invalid user ID format in token: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format: user identifier is not valid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token blacklist (for revoked tokens)
    jti = payload.get("jti")
    if jti:
        try:
            from .services.token_blacklist import get_token_blacklist
            blacklist = get_token_blacklist()
            
            if blacklist.is_revoked(jti):
                logger.warning(f"Authentication failed: Token {jti[:8]}... is blacklisted")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if token was issued before user-level revocation (password change, etc.)
            token_issued_at = payload.get("iat")
            if token_issued_at:
                token_issued_datetime = datetime.utcfromtimestamp(token_issued_at)
                if blacklist.is_user_revoked(user_id, token_issued_datetime):
                    logger.warning(f"Authentication failed: Token for user {user_id} issued before revocation")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked. Please log in again.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            # Continue anyway - don't block auth if blacklist check fails
    
    logger.debug(f"Looking up user with ID: {user_id}")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"Authentication failed: User with ID {user_id} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Authentication failed: User {user_id} account is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    logger.debug(f"Authentication successful for user: {user.email}")
    return user

