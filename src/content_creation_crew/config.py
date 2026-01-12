"""
Central configuration module for Content Creation Crew
Reads and validates environment variables with strict checks for production
"""
import os
import sys
from typing import Optional, List
from pathlib import Path

# Load environment variables from .env file if it exists (dev only)
try:
    from dotenv import load_dotenv
    # Only load .env in development
    if os.getenv("ENV", "dev").lower() == "dev":
        load_dotenv()
except ImportError:
    pass


class Config:
    """Central configuration class with environment variable validation"""
    
    # Environment
    ENV: str = os.getenv("ENV", "dev").lower()
    
    # Required for all environments
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # Must be PostgreSQL - no default
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Optional but recommended
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Frontend URLs
    FRONTEND_CALLBACK_URL: str = os.getenv(
        "FRONTEND_CALLBACK_URL", 
        "http://localhost:3000/auth/callback"
    )
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # CORS
    CORS_ORIGINS: List[str] = []
    
    # OAuth (optional)
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # Payment providers - Stripe
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY: Optional[str] = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_TEST_SECRET_KEY: Optional[str] = os.getenv("STRIPE_TEST_SECRET_KEY")
    STRIPE_TEST_PUBLIC_KEY: Optional[str] = os.getenv("STRIPE_TEST_PUBLIC_KEY")
    STRIPE_TEST_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_TEST_WEBHOOK_SECRET")
    
    # Payment providers - Paystack
    PAYSTACK_SECRET_KEY: Optional[str] = os.getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_PUBLIC_KEY: Optional[str] = os.getenv("PAYSTACK_PUBLIC_KEY")
    PAYSTACK_WEBHOOK_SECRET: Optional[str] = os.getenv("PAYSTACK_WEBHOOK_SECRET")
    PAYSTACK_TEST_SECRET_KEY: Optional[str] = os.getenv("PAYSTACK_TEST_SECRET_KEY")
    PAYSTACK_TEST_PUBLIC_KEY: Optional[str] = os.getenv("PAYSTACK_TEST_PUBLIC_KEY")
    PAYSTACK_TEST_WEBHOOK_SECRET: Optional[str] = os.getenv("PAYSTACK_TEST_WEBHOOK_SECRET")
    
    # Bank Transfer
    BANK_ACCOUNT_NUMBER: Optional[str] = os.getenv("BANK_ACCOUNT_NUMBER")
    BANK_NAME: Optional[str] = os.getenv("BANK_NAME")
    BANK_ACCOUNT_NAME: Optional[str] = os.getenv("BANK_ACCOUNT_NAME")
    BANK_ROUTING_NUMBER: Optional[str] = os.getenv("BANK_ROUTING_NUMBER")
    
    # Build version (set during build/deploy)
    BUILD_VERSION: str = os.getenv("BUILD_VERSION", "dev")
    BUILD_COMMIT: str = os.getenv("BUILD_COMMIT", "unknown")
    BUILD_TIME: str = os.getenv("BUILD_TIME", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # CrewAI execution timeout (in seconds, default 5 minutes)
    CREWAI_TIMEOUT: int = int(os.getenv("CREWAI_TIMEOUT", "300"))
    
    def __init__(self):
        """Initialize configuration and validate required variables"""
        self._load_cors_origins()
        self._validate()
    
    def _load_cors_origins(self):
        """Load CORS origins from environment variable"""
        # Default origins for development
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://frontend:3000",  # Docker network
        ]
        
        # Add environment variable origins if set
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            env_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
            self.CORS_ORIGINS = default_origins + env_origins
        else:
            self.CORS_ORIGINS = default_origins
    
    def _validate(self):
        """Validate required configuration based on environment"""
        errors = []
        
        # Validate environment
        if self.ENV not in ["dev", "staging", "prod"]:
            errors.append(f"Invalid ENV value: {self.ENV}. Must be 'dev', 'staging', or 'prod'")
        
        # SECRET_KEY is required for all environments
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY is required but not set")
        elif len(self.SECRET_KEY) < 32:
            errors.append(f"SECRET_KEY must be at least 32 characters (current: {len(self.SECRET_KEY)})")
        elif self.ENV != "dev" and self.SECRET_KEY == "your-secret-key-change-in-production-min-32-chars":
            errors.append("SECRET_KEY must be changed from default value in non-dev environments")
        
        # Database URL validation - PostgreSQL required for all environments
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required but not set")
        elif not self.DATABASE_URL.startswith("postgresql"):
            errors.append(f"DATABASE_URL must be a PostgreSQL connection string (got: {self.DATABASE_URL[:30]}...). SQLite is no longer supported.")
        
        # OLLAMA_BASE_URL validation
        if not self.OLLAMA_BASE_URL:
            errors.append("OLLAMA_BASE_URL is required but not set")
        
        # Payment webhook secrets required in staging/prod
        if self.ENV in ["staging", "prod"]:
            # Stripe webhook secret required if Stripe is configured
            if self.STRIPE_SECRET_KEY or self.STRIPE_TEST_SECRET_KEY:
                stripe_webhook = self.STRIPE_WEBHOOK_SECRET if self.ENV == "prod" else self.STRIPE_TEST_WEBHOOK_SECRET
                if not stripe_webhook:
                    errors.append(f"STRIPE_{'TEST_' if self.ENV == 'staging' else ''}WEBHOOK_SECRET is required when Stripe is configured in {self.ENV}")
            
            # Paystack webhook secret required if Paystack is configured
            if self.PAYSTACK_SECRET_KEY or self.PAYSTACK_TEST_SECRET_KEY:
                paystack_webhook = self.PAYSTACK_WEBHOOK_SECRET if self.ENV == "prod" else self.PAYSTACK_TEST_WEBHOOK_SECRET
                if not paystack_webhook:
                    errors.append(f"PAYSTACK_{'TEST_' if self.ENV == 'staging' else ''}WEBHOOK_SECRET is required when Paystack is configured in {self.ENV}")
        
        # Frontend URLs validation for staging/prod
        if self.ENV in ["staging", "prod"]:
            if not self.FRONTEND_CALLBACK_URL.startswith("https://"):
                errors.append("FRONTEND_CALLBACK_URL must use HTTPS in staging/production")
            if not self.API_BASE_URL.startswith("https://"):
                errors.append("API_BASE_URL must use HTTPS in staging/production")
            if not self.CORS_ORIGINS or all(not origin.startswith("https://") for origin in self.CORS_ORIGINS):
                errors.append("CORS_ORIGINS must include HTTPS origins in staging/production")
        
        # Fail fast in staging/prod
        if errors and self.ENV in ["staging", "prod"]:
            print("=" * 60, file=sys.stderr)
            print("CONFIGURATION VALIDATION FAILED", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            for error in errors:
                print(f"  ❌ {error}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            sys.exit(1)
        
        # Warn in dev
        if errors and self.ENV == "dev":
            print("=" * 60, file=sys.stderr)
            print("CONFIGURATION WARNINGS (dev mode - continuing)", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            for error in errors:
                print(f"  ⚠️  {error}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
    
    @property
    def is_dev(self) -> bool:
        """Check if running in development mode"""
        return self.ENV == "dev"
    
    @property
    def is_prod(self) -> bool:
        """Check if running in production mode"""
        return self.ENV == "prod"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode"""
        return self.ENV == "staging"
    
    def get_database_url(self) -> str:
        """Get database URL (alias for DATABASE_URL)"""
        return self.DATABASE_URL
    
    def get_secret_key(self) -> str:
        """Get secret key (alias for SECRET_KEY)"""
        return self.SECRET_KEY


# Create global config instance
config = Config()

