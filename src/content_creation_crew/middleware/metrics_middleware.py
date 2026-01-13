"""
Metrics collection middleware for Prometheus monitoring
Tracks request counts, durations, and status codes
"""
import time
import logging
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..services.metrics import increment_counter, record_histogram, RequestTimer

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics for Prometheus
    Tracks:
    - requests_total (by route and status code)
    - request_duration_seconds (histogram)
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics"""
        start_time = time.time()
        
        # Get route path (normalize for metrics)
        route_path = request.url.path
        
        # Skip metrics collection for /metrics endpoint itself
        if route_path == "/metrics" or route_path == "/v1/metrics":
            return await call_next(request)
        
        # Normalize route path (remove IDs, etc.)
        normalized_path = self._normalize_path(route_path)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Exception occurred
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Increment request counter
            increment_counter(
                "requests_total",
                labels={
                    "route": normalized_path,
                    "method": request.method,
                    "status": str(status_code)
                }
            )
            
            # Record request duration
            record_histogram(
                "request_duration_seconds",
                duration,
                labels={
                    "route": normalized_path,
                    "method": request.method
                }
            )
            
            # Track error rates
            if status_code >= 500:
                increment_counter("errors_total", labels={"route": normalized_path, "status": str(status_code)})
            elif status_code == 429:
                increment_counter("rate_limited_total", labels={"route": normalized_path})
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metrics (remove IDs, etc.)
        
        Examples:
        /v1/content/jobs/123 -> /v1/content/jobs/{id}
        /v1/users/456 -> /v1/users/{id}
        """
        # Common patterns to normalize
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Limit path depth for better aggregation
        parts = path.split('/')
        if len(parts) > 5:
            # Keep first 4 parts, replace rest with "{...}"
            path = '/'.join(parts[:4]) + '/{...}'
        
        return path

