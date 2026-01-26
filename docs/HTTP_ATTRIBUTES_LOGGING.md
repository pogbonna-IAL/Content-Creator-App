# HTTP Attributes Logging

This document describes the HTTP attributes logging system that captures comprehensive request/response metadata for monitoring and querying.

## Overview

The `HTTPAttributesLoggerMiddleware` captures all HTTP request and response attributes in a structured JSON format that can be queried using standard operators. This enables powerful log analysis and monitoring capabilities.

## Logged Attributes

### Request Attributes
- `@host` - Request hostname
- `@path` - Request path
- `@method` - HTTP method (GET, POST, etc.)
- `@requestId` - Unique request ID (from X-Request-ID header or generated)
- `@clientUa` - Client user agent
- `@rxBytes` - Received bytes (request body size)

### Response Attributes
- `@httpStatus` - HTTP status code
- `@txBytes` - Transmitted bytes (response body size)
- `@responseDetails` - Response details (for error responses)

### Timing Attributes
- `@totalDuration` - Total request duration (ms)
- `@responseTime` - Response time (ms)
- `@upstreamRqDuration` - Upstream request duration (ms, if proxied)

### Deployment Attributes
- `@deploymentId` - Deployment ID (from RAILWAY_DEPLOYMENT_ID env var)
- `@deploymentInstanceId` - Deployment instance ID (from RAILWAY_REPLICA_ID env var)
- `@edgeRegion` - Edge region (from RAILWAY_REGION env var)

### Protocol Attributes
- `@upstreamProto` - Upstream protocol (HTTP/1.1, HTTP/2.0)
- `@downstreamProto` - Downstream protocol (HTTP/1.1, HTTP/2.0)
- `@upstreamAddress` - Upstream address (if proxied)
- `@upstreamErrors` - Upstream errors (if any)

## Log Format

All HTTP attributes are logged as structured JSON with the `[HTTP_ATTR]` prefix:

```json
{
  "@host": "api.example.com",
  "@path": "/api/v1/content/generate",
  "@method": "POST",
  "@httpStatus": 200,
  "@totalDuration": 45230.5,
  "@responseTime": 45120.3,
  "@requestId": "abc123-def456-ghi789",
  "@deploymentId": "deploy-123",
  "@deploymentInstanceId": "replica-456",
  "@txBytes": 15234,
  "@rxBytes": 1234,
  "@clientUa": "Mozilla/5.0...",
  "@edgeRegion": "us-east-1",
  "@downstreamProto": "HTTP/2.0",
  "@upstreamProto": "HTTP/1.1"
}
```

## Querying Logs

### Basic Queries

**Find all requests to a specific path:**
```
@path = "/api/v1/content/generate"
```

**Find all POST requests:**
```
@method = "POST"
```

**Find all error responses (4xx and 5xx):**
```
@httpStatus >= 400
```

**Find all slow requests (>5 seconds):**
```
@totalDuration > 5000
```

### Complex Queries

**Find slow POST requests that returned errors:**
```
@method = "POST" AND @totalDuration > 5000 AND @httpStatus >= 400
```

**Find requests from a specific deployment:**
```
@deploymentId = "deploy-123"
```

**Find requests with upstream errors:**
```
@upstreamErrors != null
```

**Find requests to content generation endpoint that took longer than 2 minutes:**
```
@path = "/api/v1/content/generate" AND @totalDuration > 120000
```

### Comparison Operators

- `=` - Equals
- `!=` - Not equals
- `>` - Greater than
- `>=` - Greater than or equal
- `<` - Less than
- `<=` - Less than or equal
- `..` - Range (e.g., `@httpStatus 200..299`)

### Logical Operators

- `AND` - Both conditions must be true
- `OR` - Either condition can be true
- `-` - Negation (NOT)

## Log Levels

The middleware uses different log levels based on the response:

- **ERROR**: HTTP status >= 500 (server errors)
- **WARNING**: HTTP status >= 400 (client errors) OR total duration > 5000ms (slow requests)
- **INFO**: All other successful requests

## Environment Variables

The middleware reads the following environment variables for deployment metadata:

- `RAILWAY_DEPLOYMENT_ID` or `DEPLOYMENT_ID` - Sets `@deploymentId`
- `RAILWAY_REPLICA_ID` or `DEPLOYMENT_INSTANCE_ID` - Sets `@deploymentInstanceId`
- `RAILWAY_REGION` or `EDGE_REGION` - Sets `@edgeRegion`

## Integration

The middleware is automatically enabled in `api_server.py` and runs after `RequestIDMiddleware` to ensure request IDs are available.

## Example Use Cases

### 1. Monitor API Performance
```
@path = "/api/v1/content/generate" AND @totalDuration > 180000
```
Find content generation requests that exceed the 180-second timeout.

### 2. Track Error Rates
```
@httpStatus >= 500
```
Monitor server errors.

### 3. Analyze Request Patterns
```
@method = "POST" AND @path LIKE "/api/v1/content/%"
```
Find all POST requests to content endpoints.

### 4. Debug Specific Requests
```
@requestId = "abc123-def456-ghi789"
```
Find all logs for a specific request ID.

### 5. Monitor Deployment Health
```
@deploymentId = "deploy-123" AND @httpStatus >= 400
```
Find errors for a specific deployment.

## Benefits

1. **Structured Logging**: All HTTP attributes in queryable JSON format
2. **Performance Monitoring**: Track response times and identify slow requests
3. **Error Tracking**: Easily find and analyze errors
4. **Deployment Monitoring**: Track performance across different deployments
5. **Request Tracing**: Follow requests through the system using request IDs
6. **Capacity Planning**: Analyze request sizes and response times
