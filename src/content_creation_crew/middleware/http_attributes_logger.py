"""
HTTP Attributes Logging Middleware
Captures comprehensive HTTP request/response attributes for monitoring and querying
"""
import logging
import time
import os
from typing import Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
import json

logger = logging.getLogger(__name__)

# Import request ID getter if available
try:
    from ..logging_config import get_request_id
except ImportError:
    def get_request_id() -> Optional[str]:
        return None


class HTTPAttributesLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log comprehensive HTTP attributes for monitoring and querying
    
    Logs attributes in structured JSON format that can be queried:
    - @host, @path, @method, @httpStatus
    - @totalDuration, @responseTime, @upstreamRqDuration
    - @requestId, @deploymentId, @deploymentInstanceId
    - @txBytes, @rxBytes, @clientUa, @edgeRegion
    - @upstreamProto, @downstreamProto, @upstreamAddress
    - @upstreamErrors, @responseDetails
    """
    
    def __init__(self, app, deployment_id: str = None, deployment_instance_id: str = None):
        super().__init__(app)
        self.deployment_id = deployment_id or os.getenv("RAILWAY_DEPLOYMENT_ID") or os.getenv("DEPLOYMENT_ID")
        self.deployment_instance_id = deployment_instance_id or os.getenv("RAILWAY_REPLICA_ID") or os.getenv("DEPLOYMENT_INSTANCE_ID")
        self.edge_region = os.getenv("RAILWAY_REGION") or os.getenv("EDGE_REGION") or "unknown"
    
    def _get_request_size(self, request: StarletteRequest) -> int:
        """Calculate request body size in bytes"""
        try:
            if hasattr(request, '_body'):
                return len(request._body) if request._body else 0
            # For streaming requests, estimate from headers
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)
        except Exception:
            pass
        return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Calculate response body size in bytes"""
        try:
            if hasattr(response, 'body'):
                return len(response.body) if response.body else 0
        except Exception:
            pass
        return 0
    
    async def dispatch(self, request: StarletteRequest, call_next):
        """Process request and log HTTP attributes"""
        # Start timing
        start_time = time.time()
        request_start_time = start_time
        
        # Extract request attributes
        # Try to get request ID from context first (set by RequestIDMiddleware), then headers
        request_id = get_request_id() or request.headers.get("X-Request-ID") or request.headers.get("x-request-id") or request.headers.get("X-Railway-Request-ID")
        host = request.headers.get("host") or request.url.hostname
        path = str(request.url.path)
        method = request.method
        client_ua = request.headers.get("user-agent", "unknown")
        
        # Extract Railway-specific headers if available
        railway_request_id = request.headers.get("X-Railway-Request-ID")
        src_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() if request.headers.get("X-Forwarded-For") else request.headers.get("X-Real-IP")
        edge_region_header = request.headers.get("X-Railway-Edge") or request.headers.get("X-Edge-Region")
        
        # Calculate request size
        rx_bytes = self._get_request_size(request)
        
        # Track upstream request duration (for proxied requests)
        upstream_rq_duration = None
        upstream_errors = None
        upstream_proto = None
        upstream_address = None
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - request_start_time) * 1000  # ms
            
            # Get response attributes
            http_status = response.status_code
            tx_bytes = self._get_response_size(response)
            
            # Check for upstream information in headers (if proxied by Railway)
            # Railway may set these headers automatically
            upstream_rq_duration_header = response.headers.get("X-Upstream-Request-Duration") or response.headers.get("X-Railway-Upstream-Duration")
            if upstream_rq_duration_header:
                try:
                    upstream_rq_duration = float(upstream_rq_duration_header)
                except (ValueError, TypeError):
                    pass
            
            # Extract upstream address from Railway headers if available
            upstream_address_header = response.headers.get("X-Upstream-Address") or response.headers.get("X-Railway-Upstream-Address")
            if upstream_address_header:
                upstream_address = upstream_address_header
            
            upstream_proto = response.headers.get("X-Upstream-Proto") or response.headers.get("X-Railway-Upstream-Proto") or "HTTP/1.1"
            downstream_proto = "HTTP/2.0" if request.scope.get("http_version") == "2" else "HTTP/1.1"
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000  # ms
            
            # Extract response details
            response_details = None
            if http_status >= 400:
                # For error responses, try to extract error details
                try:
                    if hasattr(response, 'body') and response.body:
                        # Try to parse error response
                        body_str = response.body.decode('utf-8') if isinstance(response.body, bytes) else str(response.body)
                        if body_str:
                            try:
                                error_data = json.loads(body_str)
                                response_details = error_data.get("detail") or error_data.get("message") or body_str[:200]
                            except json.JSONDecodeError:
                                response_details = body_str[:200]
                except Exception:
                    pass
            
            # Check for upstream errors
            upstream_errors_header = response.headers.get("X-Upstream-Errors")
            if upstream_errors_header:
                upstream_errors = upstream_errors_header
            
        except Exception as e:
            # Error occurred during request processing
            response_time = (time.time() - request_start_time) * 1000  # ms
            total_duration = (time.time() - start_time) * 1000  # ms
            http_status = 500
            tx_bytes = 0
            upstream_errors = str(e)
            response_details = str(e)
            downstream_proto = "HTTP/1.1"
            upstream_proto = None
            
            # Re-raise the exception
            raise
        
        # Build HTTP attributes log entry
        # Use Railway request ID if available, otherwise use our generated one
        final_request_id = railway_request_id or request_id
        
        http_attributes = {
            "@host": host,
            "@path": path,
            "@method": method,
            "@httpStatus": http_status,
            "@totalDuration": round(total_duration, 2),
            "@responseTime": round(response_time, 2),
            "@requestId": final_request_id,
            "@deploymentId": self.deployment_id,
            "@deploymentInstanceId": self.deployment_instance_id,
            "@txBytes": tx_bytes,
            "@rxBytes": rx_bytes,
            "@clientUa": client_ua,
            "@edgeRegion": edge_region_header or self.edge_region,
            "@downstreamProto": downstream_proto,
        }
        
        # Add source IP if available
        if src_ip:
            http_attributes["@srcIp"] = src_ip
        
        # Add Railway request ID separately if different from our request ID
        if railway_request_id and railway_request_id != final_request_id:
            http_attributes["@railwayRequestId"] = railway_request_id
        
        # Add optional attributes if available
        if upstream_rq_duration is not None:
            http_attributes["@upstreamRqDuration"] = round(upstream_rq_duration, 2)
        
        if upstream_proto:
            http_attributes["@upstreamProto"] = upstream_proto
        
        if upstream_address:
            http_attributes["@upstreamAddress"] = upstream_address
        
        if upstream_errors:
            http_attributes["@upstreamErrors"] = upstream_errors
        
        if response_details:
            http_attributes["@responseDetails"] = response_details
        
        # Log HTTP attributes in structured JSON format
        # This format allows querying with operators like @httpStatus >= 400, @totalDuration < 1000, etc.
        log_message = json.dumps(http_attributes, ensure_ascii=False)
        
        # Use appropriate log level based on status code
        if http_status >= 500:
            logger.error(f"[HTTP_ATTR] {log_message}")
        elif http_status >= 400:
            logger.warning(f"[HTTP_ATTR] {log_message}")
        elif total_duration > 5000:  # Log slow requests (>5s) as warning
            logger.warning(f"[HTTP_ATTR] {log_message}")
        else:
            logger.info(f"[HTTP_ATTR] {log_message}")
        
        return response
