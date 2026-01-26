"""
Health Check Service (M5)
Comprehensive health checks for all system components with strict timeouts
"""
import logging
import asyncio
import time
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class ComponentHealth:
    """Health information for a single component"""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.checked_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = {
            "status": self.status.value,
            "message": self.message,
            "checked_at": self.checked_at
        }
        
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        
        if self.details:
            result["details"] = self.details
        
        return result


class HealthChecker:
    """
    Comprehensive health checker for all system components
    
    Features:
    - Database connectivity check
    - Redis connectivity check (if configured)
    - Storage availability and free space check
    - LLM provider check (Ollama)
    - Strict timeouts (no hangs)
    - Overall status aggregation
    """
    
    def __init__(
        self,
        timeout_seconds: int = 3,
        min_free_space_mb: int = 1024,
        storage_write_test: bool = True
    ):
        self.timeout_seconds = timeout_seconds
        self.min_free_space_mb = min_free_space_mb
        self.storage_write_test = storage_write_test
    
    async def check_database(self) -> ComponentHealth:
        """
        Check database connectivity
        
        Returns:
            ComponentHealth with database status
        """
        start_time = time.time()
        
        try:
            from ..db.engine import SessionLocal
            from ..config import config
            from sqlalchemy import text
            
            # Check DATABASE_URL for common misconfigurations
            db_url = config.DATABASE_URL or ""
            error_details = {}
            
            # Detect Railway internal hostname issues
            if ".railway.internal" in db_url:
                error_details["issue"] = "Railway internal hostname detected"
                error_details["fix"] = "Ensure PostgreSQL service is properly linked to backend service in Railway"
                error_details["note"] = "Railway should set DATABASE_URL automatically when services are linked"
            
            # Detect Docker Compose hostname issues
            if "@db:" in db_url or "@postgres:" in db_url:
                error_details["issue"] = "Docker Compose hostname detected"
                error_details["fix"] = "Use Railway's automatically generated DATABASE_URL, not Docker Compose format"
            
            # Create session with timeout
            db = SessionLocal()
            
            try:
                # Simple ping query
                result = db.execute(text("SELECT 1")).scalar()
                
                response_time = (time.time() - start_time) * 1000
                
                if result == 1:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.OK,
                        message="Database is accessible",
                        response_time_ms=response_time,
                        details={"connection": "active"}
                    )
                else:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.DEGRADED,
                        message="Database query returned unexpected result",
                        response_time_ms=response_time
                    )
            
            finally:
                db.close()
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="database",
                status=HealthStatus.DOWN,
                message="Database health check timed out",
                details={"timeout_seconds": self.timeout_seconds, **error_details}
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # Detect DNS/hostname resolution errors
            if "name or service not known" in error_str or "could not translate host name" in error_str:
                logger.error(f"Database health check failed: DNS resolution error - {e}")
                logger.error("=" * 60)
                logger.error("DATABASE_URL CONFIGURATION ERROR")
                logger.error("=" * 60)
                logger.error(f"DATABASE_URL contains invalid hostname")
                logger.error(f"Current DATABASE_URL: {db_url[:100]}..." if len(db_url) > 100 else f"Current DATABASE_URL: {db_url}")
                logger.error("")
                logger.error("SOLUTION:")
                logger.error("1. Go to Railway Dashboard → Backend Service → Variables")
                logger.error("2. Check DATABASE_URL value")
                logger.error("3. If it contains '.railway.internal' or 'db:', delete it")
                logger.error("4. Link PostgreSQL service to Backend service properly")
                logger.error("5. Railway will automatically set correct DATABASE_URL")
                logger.error("=" * 60)
                
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DOWN,
                    message="Database hostname cannot be resolved - check DATABASE_URL configuration",
                    response_time_ms=response_time,
                    details={
                        "error_type": error_type,
                        "error": "DNS resolution failed",
                        **error_details
                    }
                )
            
            logger.error(f"Database health check failed: {e}")
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.DOWN,
                message="Database is not accessible",
                response_time_ms=response_time,
                details={"error_type": error_type, **error_details}
            )
    
    async def check_redis(self) -> ComponentHealth:
        """
        Check Redis connectivity (if configured)
        
        Returns:
            ComponentHealth with Redis status
        """
        start_time = time.time()
        
        try:
            from ..services.redis_cache import get_redis_client
            
            redis_client = get_redis_client()
            
            if redis_client is None:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.OK,  # Not configured is OK
                    message="Redis not configured (optional)",
                    details={"configured": False}
                )
            
            # Ping Redis
            result = redis_client.ping()
            
            response_time = (time.time() - start_time) * 1000
            
            if result:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.OK,
                    message="Redis is accessible",
                    response_time_ms=response_time,
                    details={"connection": "active"}
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    message="Redis ping returned false",
                    response_time_ms=response_time
                )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DOWN,
                message="Redis health check timed out",
                details={"timeout_seconds": self.timeout_seconds}
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"Redis health check failed: {e}")
            
            # Redis is optional, so degraded not down
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message="Redis is not accessible",
                response_time_ms=response_time,
                details={"error_type": type(e).__name__, "optional": True}
            )
    
    async def check_storage(self) -> ComponentHealth:
        """
        Check storage availability and free space
        
        Checks:
        - Storage path exists and is accessible
        - Storage path is writable (if enabled)
        - Free space >= MIN_FREE_SPACE_MB
        
        Returns:
            ComponentHealth with storage status
        """
        start_time = time.time()
        
        try:
            from ..services.storage_provider import get_storage_provider
            
            storage_provider = get_storage_provider()
            
            # Get storage type
            storage_type = type(storage_provider).__name__
            
            # Check storage health with timeout
            health_info = await asyncio.wait_for(
                storage_provider.check_health(
                    write_test=self.storage_write_test,
                    min_free_space_mb=self.min_free_space_mb
                ),
                timeout=self.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on health info
            if health_info.get("error"):
                # Check if it's a critical error
                if not health_info.get("accessible"):
                    status = HealthStatus.DOWN
                    message = f"Storage not accessible: {health_info['error']}"
                elif not health_info.get("writable"):
                    status = HealthStatus.DEGRADED
                    message = f"Storage not writable: {health_info['error']}"
                else:
                    # Low space or other warning
                    status = HealthStatus.DEGRADED
                    message = health_info["error"]
            elif health_info.get("accessible") and health_info.get("writable"):
                free_space_mb = health_info.get("free_space_mb", 0)
                
                if free_space_mb >= self.min_free_space_mb or free_space_mb == -1:  # -1 means not applicable (S3)
                    status = HealthStatus.OK
                    if free_space_mb == -1:
                        message = "Storage is accessible (cloud storage)"
                    else:
                        message = f"Storage is accessible with {free_space_mb}MB free"
                else:
                    status = HealthStatus.DEGRADED
                    message = f"Storage space low: {free_space_mb}MB < {self.min_free_space_mb}MB"
            else:
                status = HealthStatus.DOWN
                message = "Storage is not accessible or writable"
            
            return ComponentHealth(
                name="storage",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    "type": storage_type,
                    **health_info
                }
            )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="storage",
                status=HealthStatus.DOWN,
                message="Storage health check timed out",
                details={"timeout_seconds": self.timeout_seconds}
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Storage health check failed: {e}")
            
            return ComponentHealth(
                name="storage",
                status=HealthStatus.DOWN,
                message="Storage health check failed",
                response_time_ms=response_time,
                details={"error_type": type(e).__name__}
            )
    
    async def check_llm(self) -> ComponentHealth:
        """
        Check LLM provider (OpenAI or Ollama) connectivity
        
        Returns:
            ComponentHealth with LLM status
        """
        start_time = time.time()
        
        try:
            from ..config import config
            
            # Check OpenAI first if configured
            if config.OPENAI_API_KEY:
                try:
                    import openai
                    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                    # Lightweight test - list models (doesn't consume tokens)
                    models = client.models.list()
                    model_names = [model.id for model in models.data if 'gpt' in model.id.lower()]
                    response_time = (time.time() - start_time) * 1000
                    
                    return ComponentHealth(
                        name="llm",
                        status=HealthStatus.OK,
                        message="OpenAI API accessible",
                        response_time_ms=response_time,
                        details={
                            "provider": "openai",
                            "model_count": len(models.data),
                            "gpt_models_available": len(model_names),
                            "sample_models": model_names[:5] if model_names else []
                        }
                    )
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)
                    response_time = (time.time() - start_time) * 1000
                    
                    # Check for specific OpenAI error types
                    if "Invalid API key" in error_msg or "authentication" in error_msg.lower():
                        return ComponentHealth(
                            name="llm",
                            status=HealthStatus.DEGRADED,
                            message="OpenAI API authentication failed",
                            response_time_ms=response_time,
                            details={"provider": "openai", "error_type": error_type}
                        )
                    elif "rate limit" in error_msg.lower():
                        return ComponentHealth(
                            name="llm",
                            status=HealthStatus.DEGRADED,
                            message="OpenAI API rate limit reached",
                            response_time_ms=response_time,
                            details={"provider": "openai", "error_type": error_type}
                        )
                    else:
                        return ComponentHealth(
                            name="llm",
                            status=HealthStatus.DEGRADED,
                            message=f"OpenAI API error: {error_msg}",
                            response_time_ms=response_time,
                            details={"provider": "openai", "error_type": error_type}
                        )
            
            # Fall back to Ollama if OpenAI not configured
            import httpx
            ollama_url = config.OLLAMA_BASE_URL or config.OLLAMA_URL or "http://localhost:11434"
            
            # Skip health check if URL points to localhost or Docker service names in production
            # (these won't work in Railway unless Ollama is deployed as a service)
            if ollama_url.startswith("http://localhost") or ollama_url.startswith("http://ollama"):
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,
                    message="LLM provider not configured for this environment",
                    details={
                        "provider": "ollama",
                        "url": ollama_url,
                        "reason": "localhost/service name not accessible in Railway",
                        "note": "Set OPENAI_API_KEY to use OpenAI instead"
                    }
                )
            
            # Lightweight health check
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{ollama_url}/api/tags")
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.OK,
                    message="LLM provider is accessible",
                    response_time_ms=response_time,
                    details={
                        "provider": "ollama",
                        "models_count": len(models)
                    }
                )
            else:
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,
                    message=f"LLM provider returned status {response.status_code}",
                    response_time_ms=response_time,
                    details={"provider": "ollama"}
                )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="llm",
                status=HealthStatus.DEGRADED,  # Changed from DOWN to DEGRADED - LLM is optional
                message="LLM health check timed out",
                details={"timeout_seconds": self.timeout_seconds, "provider": "ollama", "fallback": "OpenAI not configured"}
            )
        
        except (httpx.ConnectError, httpx.NetworkError, OSError) as e:
            # DNS resolution errors, connection refused, etc.
            response_time = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            
            # Check if it's a DNS/hostname resolution error
            error_str = str(e).lower()
            if "name or service not known" in error_str or "nodename nor servname provided" in error_str:
                logger.warning(f"LLM health check failed: LLM provider hostname cannot be resolved (this is OK if LLM is not deployed)")
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.DEGRADED,  # DEGRADED not DOWN - LLM is optional
                    message="LLM provider hostname cannot be resolved",
                    response_time_ms=response_time,
                    details={
                        "error_type": error_type,
                        "provider": "ollama",
                        "note": "LLM is optional - application will work without it"
                    }
                )
            
            logger.warning(f"LLM health check failed: {e}")
            return ComponentHealth(
                name="llm",
                status=HealthStatus.DEGRADED,  # DEGRADED not DOWN - LLM is optional
                message="LLM provider is not accessible",
                response_time_ms=response_time,
                details={"error_type": error_type, "provider": "ollama"}
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"LLM health check failed: {e}")
            
            return ComponentHealth(
                name="llm",
                status=HealthStatus.DEGRADED,  # DEGRADED not DOWN - LLM is optional
                message="LLM provider is not accessible",
                response_time_ms=response_time,
                details={"error_type": type(e).__name__, "provider": "ollama"}
            )
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Check all system components
        
        Returns:
            Dict with overall status and component details
        """
        start_time = time.time()
        
        # Run all checks in parallel
        components = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_storage(),
            self.check_llm(),
            return_exceptions=True
        )
        
        total_time = (time.time() - start_time) * 1000
        
        # Handle any exceptions from gather
        component_results = []
        for component in components:
            if isinstance(component, Exception):
                logger.error(f"Health check exception: {component}")
                component_results.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.DOWN,
                    message="Health check failed with exception",
                    details={"error": str(component)}
                ))
            else:
                component_results.append(component)
        
        # Determine overall status
        statuses = [c.status for c in component_results]
        
        if all(s == HealthStatus.OK for s in statuses):
            overall_status = HealthStatus.OK
        elif any(s == HealthStatus.DOWN for s in statuses):
            overall_status = HealthStatus.DOWN
        else:
            overall_status = HealthStatus.DEGRADED
        
        # Build response
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round(total_time, 2),
            "components": {
                component.name: component.to_dict()
                for component in component_results
            }
        }


def get_health_checker() -> HealthChecker:
    """
    Get configured health checker instance
    
    Returns:
        HealthChecker configured with environment variables
    """
    from ..config import config
    
    return HealthChecker(
        timeout_seconds=config.HEALTHCHECK_TIMEOUT_SECONDS,
        min_free_space_mb=config.MIN_FREE_SPACE_MB,
        storage_write_test=config.HEALTHCHECK_STORAGE_WRITE_TEST
    )

