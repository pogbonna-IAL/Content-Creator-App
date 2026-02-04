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
    # SECRET_KEY: No default - must be set via environment variable
    # This ensures deployments fail fast if secret is not configured
    SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
    DATABASE_URL: str = os.getenv("DATABASE_URL") or ""  # Must be PostgreSQL - no default
    
    # LLM Provider Configuration
    # OpenAI API Key (required if using OpenAI models like gpt-4o-mini)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # Ollama Base URL (optional - only needed if using Ollama models)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL_NAMES: Optional[str] = os.getenv("MODEL_NAMES")  # Comma-separated list of Ollama models to download
    
    # Optional but recommended
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Frontend URLs
    FRONTEND_CALLBACK_URL: str = os.getenv(
        "FRONTEND_CALLBACK_URL", 
        "http://localhost:3000/auth/callback"
    )
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000"  # Base frontend URL for email links (verification, etc.)
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
    # Increased from 180s to 300s to allow sufficient time for content generation
    # This prevents premature timeouts while still catching hanging operations
    CREWAI_TIMEOUT: int = int(os.getenv("CREWAI_TIMEOUT", "300"))
    
    # Video rendering feature flag
    ENABLE_VIDEO_RENDERING: bool = os.getenv("ENABLE_VIDEO_RENDERING", "false").lower() in ("true", "1", "yes")
    
    # Rate limiting configuration
    RATE_LIMIT_RPM: int = int(os.getenv("RATE_LIMIT_RPM", "60"))  # Default: 60 requests per minute
    RATE_LIMIT_GENERATE_RPM: int = int(os.getenv("RATE_LIMIT_GENERATE_RPM", "10"))  # Default: 10 generation requests per minute
    RATE_LIMIT_SSE_CONNECTIONS: int = int(os.getenv("RATE_LIMIT_SSE_CONNECTIONS", "5"))  # Default: 5 SSE connections per user
    
    # Content moderation configuration
    ENABLE_CONTENT_MODERATION: bool = os.getenv("ENABLE_CONTENT_MODERATION", "true").lower() in ("true", "1", "yes")
    ENABLE_CONTENT_MODERATION_CLASSIFIER: bool = os.getenv("ENABLE_CONTENT_MODERATION_CLASSIFIER", "false").lower() in ("true", "1", "yes")
    MODERATION_DISALLOWED_KEYWORDS: Optional[str] = os.getenv("MODERATION_DISALLOWED_KEYWORDS", None)  # Comma-separated keywords
    MODERATION_VERSION: str = os.getenv("MODERATION_VERSION", "1.0.0")  # Bump to invalidate content cache (M6)
    
    # GDPR Compliance
    GDPR_DELETION_GRACE_DAYS: int = int(os.getenv("GDPR_DELETION_GRACE_DAYS", "30"))
    
    # Artifact Retention Policy (M1)
    RETENTION_DAYS_FREE: int = int(os.getenv("RETENTION_DAYS_FREE", "30"))
    RETENTION_DAYS_BASIC: int = int(os.getenv("RETENTION_DAYS_BASIC", "90"))
    RETENTION_DAYS_PRO: int = int(os.getenv("RETENTION_DAYS_PRO", "365"))
    RETENTION_DAYS_ENTERPRISE: int = int(os.getenv("RETENTION_DAYS_ENTERPRISE", "-1"))  # -1 = unlimited
    RETENTION_DRY_RUN: bool = os.getenv("RETENTION_DRY_RUN", "false").lower() in ("true", "1", "yes")
    
    # Retention Notification Settings (M1 Enhancement)
    RETENTION_NOTIFY_DAYS_BEFORE: int = int(os.getenv("RETENTION_NOTIFY_DAYS_BEFORE", "7"))  # Notify 7 days before deletion
    RETENTION_NOTIFY_ENABLED: bool = os.getenv("RETENTION_NOTIFY_ENABLED", "true").lower() in ("true", "1", "yes")
    RETENTION_NOTIFY_BATCH_SIZE: int = int(os.getenv("RETENTION_NOTIFY_BATCH_SIZE", "100"))  # Max notifications per run
    
    # Health Check Configuration (M5)
    HEALTHCHECK_TIMEOUT_SECONDS: int = int(os.getenv("HEALTHCHECK_TIMEOUT_SECONDS", "3"))
    MIN_FREE_SPACE_MB: int = int(os.getenv("MIN_FREE_SPACE_MB", "1024"))
    HEALTHCHECK_STORAGE_WRITE_TEST: bool = os.getenv("HEALTHCHECK_STORAGE_WRITE_TEST", "true").lower() in ("true", "1", "yes")
    
    # Password Security (S9)
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_UPPERCASE: bool = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() in ("true", "1", "yes")
    PASSWORD_REQUIRE_LOWERCASE: bool = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() in ("true", "1", "yes")
    PASSWORD_REQUIRE_DIGIT: bool = os.getenv("PASSWORD_REQUIRE_DIGIT", "true").lower() in ("true", "1", "yes")
    PASSWORD_REQUIRE_SYMBOL: bool = os.getenv("PASSWORD_REQUIRE_SYMBOL", "true").lower() in ("true", "1", "yes")
    PASSWORD_BLOCK_COMMON: bool = os.getenv("PASSWORD_BLOCK_COMMON", "true").lower() in ("true", "1", "yes")
    PASSWORD_COMMON_LIST_FILE: str = os.getenv("PASSWORD_COMMON_LIST_FILE", "src/content_creation_crew/data/common_passwords.txt")
    
    # Bcrypt Configuration (S9)
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
    
    # Request Size Limits (M4)
    MAX_REQUEST_BYTES: int = int(os.getenv("MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))  # 2MB default
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10MB for uploads
    
    # Database Pool Configuration (S7)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "900"))  # 15 minutes (900s) - prevents stale SSL connections
    DB_STATEMENT_TIMEOUT: int = int(os.getenv("DB_STATEMENT_TIMEOUT", "10000"))  # 10 seconds in milliseconds
    
    # Ollama URL alias (for compatibility)
    OLLAMA_URL: str = OLLAMA_BASE_URL
    
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
        
        # SECRET_KEY is required for all environments - fail fast if missing
        if not self.SECRET_KEY:
            errors.append(
                "SECRET_KEY is required but not set. "
                "Set it via environment variable or .env file. "
                "Generate a secure key with: openssl rand -hex 32"
            )
        elif len(self.SECRET_KEY) < 32:
            errors.append(
                f"SECRET_KEY must be at least 32 characters (current: {len(self.SECRET_KEY)}). "
                "Generate a secure key with: openssl rand -hex 32"
            )
        elif self.SECRET_KEY == "your-secret-key-change-in-production-min-32-chars":
            errors.append(
                "SECRET_KEY must be changed from default value. "
                "Generate a secure key with: openssl rand -hex 32"
            )
        
        # Database URL validation - PostgreSQL required for all environments
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required but not set")
        elif not self.DATABASE_URL.startswith("postgresql"):
            errors.append(f"DATABASE_URL must be a PostgreSQL connection string (got: {self.DATABASE_URL[:30]}...). SQLite is no longer supported.")
        
        # LLM Provider validation - at least one provider must be configured
        if not self.OPENAI_API_KEY and not self.OLLAMA_BASE_URL:
            errors.append("Either OPENAI_API_KEY or OLLAMA_BASE_URL must be set for LLM provider")
        elif self.OPENAI_API_KEY and not self.OPENAI_API_KEY.startswith("sk-"):
            errors.append("OPENAI_API_KEY appears to be invalid (should start with 'sk-')")
        
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

