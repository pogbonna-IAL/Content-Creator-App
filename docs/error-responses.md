# Error Response Standardization

## Overview

Content Creation Crew uses standardized error responses across all API endpoints. Error responses follow a consistent schema for better client handling and debugging.

## Table of Contents

1. [Error Response Schema](#error-response-schema)
2. [Error Codes](#error-codes)
3. [Legacy Format Support](#legacy-format-support)
4. [Exception Handlers](#exception-handlers)
5. [Usage Examples](#usage-examples)

---

## Error Response Schema

### Standardized Format (v1 endpoints)

**Schema:** `{ code, message, details?, request_id, status_code }`

**Example:**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation error: topic: field required",
  "status_code": 422,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "errors": [
      {
        "loc": ["body", "topic"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

### Legacy Format (api endpoints)

**Schema:** `{ detail, status_code, request_id?, error_code? }`

**Example:**
```json
{
  "detail": "Validation error: topic: field required",
  "status_code": 422,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_code": "validation_error"
}
```

---

## Error Codes

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTH_ERROR` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Access denied |
| `NOT_FOUND` | 404 | Resource not found |
| `PLAN_LIMIT_EXCEEDED` | 403 | Subscription plan limit exceeded |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `BAD_REQUEST` | 400 | Invalid request |
| `CONFLICT` | 409 | Resource conflict |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service unavailable |

### Error Code Details

#### `VALIDATION_ERROR` (422)

**When:** Request body validation fails

**Details:**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation error: topic: field required",
  "details": {
    "errors": [
      {
        "loc": ["body", "topic"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

#### `AUTH_ERROR` (401)

**When:** Authentication token is missing, invalid, or expired

**Details:**
```json
{
  "code": "AUTH_ERROR",
  "message": "Invalid or expired authentication token. Please log in again.",
  "status_code": 401
}
```

#### `PLAN_LIMIT_EXCEEDED` (403)

**When:** User has exceeded their subscription plan limit

**Details:**
```json
{
  "code": "PLAN_LIMIT_EXCEEDED",
  "message": "You have reached your blog generation limit (10 per month).",
  "status_code": 403,
  "details": {
    "content_type": "blog",
    "used": 10,
    "limit": 10,
    "plan": "free"
  }
}
```

#### `RATE_LIMITED` (429)

**When:** Rate limit exceeded

**Details:**
```json
{
  "code": "RATE_LIMITED",
  "message": "Rate limit exceeded. Limit: 10 requests per minute.",
  "status_code": 429,
  "details": {
    "limit": 10,
    "reset_after_seconds": 45,
    "retry_after": 45
  }
}
```

#### `INTERNAL_ERROR` (500)

**When:** Unexpected server error

**Details (dev only):**
```json
{
  "code": "INTERNAL_ERROR",
  "message": "Internal server error: Database connection failed",
  "status_code": 500,
  "details": {
    "exception_type": "ConnectionError"
  }
}
```

**Details (production):**
```json
{
  "code": "INTERNAL_ERROR",
  "message": "Internal server error",
  "status_code": 500
}
```

---

## Legacy Format Support

### Endpoint Detection

**Legacy Format:** `/api/*` endpoints (except `/api/v1/*`)

**Standard Format:** `/v1/*` and `/api/v1/*` endpoints

### Legacy Format Schema

```json
{
  "detail": "Error message",
  "status_code": 422,
  "request_id": "...",
  "error_code": "VALIDATION_ERROR"
}
```

### Migration Path

1. **Phase 1 (Current):** Legacy endpoints use legacy format, v1 endpoints use standard format
2. **Phase 2 (Future):** All endpoints migrate to standard format
3. **Phase 3 (Future):** Legacy endpoints deprecated

---

## Exception Handlers

### 1. Validation Error Handler

**Handler:** `validation_exception_handler`

**Triggers:** Pydantic validation errors

**Response:**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation error: ...",
  "details": {
    "errors": [...]
  }
}
```

### 2. HTTP Exception Handler

**Handler:** `http_exception_handler`

**Triggers:** `HTTPException` (FastAPI/Starlette)

**Response:**
- Detects error code from exception detail
- Handles plan limit errors specially
- Formats according to endpoint (legacy vs standard)

### 3. General Exception Handler

**Handler:** `general_exception_handler`

**Triggers:** Unhandled exceptions

**Response:**
```json
{
  "code": "INTERNAL_ERROR",
  "message": "Internal server error",
  "details": {...}  // Only in dev mode
}
```

### 4. Plan Limit Error Handler

**Handler:** Handled by `http_exception_handler`

**Triggers:** `HTTPException` with `detail` containing `"error": "PLAN_LIMIT_EXCEEDED"`

**Response:**
```json
{
  "code": "PLAN_LIMIT_EXCEEDED",
  "message": "You have reached your blog generation limit...",
  "details": {
    "content_type": "blog",
    "used": 10,
    "limit": 10,
    "plan": "free"
  }
}
```

---

## Usage Examples

### Standard Format (v1 endpoints)

**Request:**
```bash
POST /v1/content/generate
{
  "topic": ""
}
```

**Response (422):**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation error: topic: field required",
  "status_code": 422,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "errors": [
      {
        "loc": ["body", "topic"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

### Legacy Format (api endpoints)

**Request:**
```bash
POST /api/generate
{
  "topic": ""
}
```

**Response (422):**
```json
{
  "detail": "Validation error: topic: field required",
  "status_code": 422,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_code": "validation_error"
}
```

### Plan Limit Error

**Request:**
```bash
POST /v1/content/generate
{
  "topic": "Test",
  "content_types": ["blog"]
}
```

**Response (403):**
```json
{
  "code": "PLAN_LIMIT_EXCEEDED",
  "message": "You have reached your blog generation limit (10 per month).",
  "status_code": 403,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "content_type": "blog",
    "used": 10,
    "limit": 10,
    "plan": "free"
  }
}
```

### Auth Error

**Request:**
```bash
GET /v1/content/jobs
# No Authorization header
```

**Response (401):**
```json
{
  "code": "AUTH_ERROR",
  "message": "Authentication token is missing. Please log in again.",
  "status_code": 401,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Request ID

### Always Present

All error responses include `request_id` for correlation:

- **Standard Format:** `request_id` field
- **Legacy Format:** `request_id` field (if available)

### Usage

**Correlate logs:**
```bash
# Search logs by request ID
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/api.log
```

**Client handling:**
```javascript
try {
  const response = await fetch('/v1/content/generate', {...});
  if (!response.ok) {
    const error = await response.json();
    console.error(`Error ${error.code}: ${error.message}`);
    console.error(`Request ID: ${error.request_id}`);
    // Report error with request ID for support
  }
} catch (error) {
  // Handle error
}
```

---

## Client Handling

### Standard Format

```javascript
async function handleApiError(response) {
  const error = await response.json();
  
  switch (error.code) {
    case 'VALIDATION_ERROR':
      // Show validation errors
      console.error('Validation errors:', error.details.errors);
      break;
    
    case 'AUTH_ERROR':
      // Redirect to login
      window.location.href = '/auth';
      break;
    
    case 'PLAN_LIMIT_EXCEEDED':
      // Show upgrade prompt
      showUpgradePrompt(error.details);
      break;
    
    case 'RATE_LIMITED':
      // Wait and retry
      await sleep(error.details.retry_after * 1000);
      return retryRequest();
    
    default:
      // Generic error handling
      showError(error.message, error.request_id);
  }
}
```

### Legacy Format

```javascript
async function handleLegacyApiError(response) {
  const error = await response.json();
  
  // Check error_code for legacy format
  if (error.error_code) {
    switch (error.error_code) {
      case 'validation_error':
        // Handle validation error
        break;
      case 'PLAN_LIMIT_EXCEEDED':
        // Handle plan limit
        break;
      // ...
    }
  }
  
  // Fallback to detail message
  showError(error.detail, error.request_id);
}
```

---

## Best Practices

### ✅ DO

- ✅ Always include `request_id` in error responses
- ✅ Use appropriate error codes
- ✅ Provide helpful error messages
- ✅ Include relevant details in `details` field
- ✅ Log errors with request ID for correlation

### ❌ DON'T

- ❌ Don't expose sensitive information in error messages
- ❌ Don't include stack traces in production
- ❌ Don't use generic error messages
- ❌ Don't skip request ID in error responses

---

## Related Documentation

- [Rate Limits](./rate-limits.md) - Rate limiting and `RATE_LIMITED` errors
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Monitoring](./monitoring.md) - Error tracking and metrics

---

## Quick Reference

### Standard Format

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable message",
  "status_code": 422,
  "request_id": "...",
  "details": {}
}
```

### Legacy Format

```json
{
  "detail": "Error message",
  "status_code": 422,
  "request_id": "...",
  "error_code": "error_code"
}
```

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

