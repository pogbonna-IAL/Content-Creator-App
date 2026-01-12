# Security Baseline for First Deploy

This document outlines the security measures implemented for the first deployment.

## Backend Security

### 1. Strict CORS by Environment ✅

**Implementation:**
- CORS origins configured via `CORS_ORIGINS` environment variable
- Methods restricted based on environment:
  - **Dev**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`
  - **Staging/Prod**: `GET`, `POST`, `DELETE`, `OPTIONS` (more restrictive)
- Headers restricted:
  - **Dev**: `Content-Type`, `Authorization`, `X-Request-ID`, `Accept`, `Origin`, `Referer`
  - **Staging/Prod**: `Content-Type`, `Authorization`, `X-Request-ID`, `Accept` (essential only)
- `X-Request-ID` exposed to clients for debugging

**Location:** `api_server.py` (lines 172-210)

### 2. Request Size Limits ✅

**Implementation:**
- `RequestSizeLimitMiddleware` enforces 10MB maximum request body size
- Checks `Content-Length` header before processing
- Returns `413 Request Entity Too Large` if exceeded
- Applied globally to all endpoints

**Location:** 
- `src/content_creation_crew/middleware/security.py`
- `api_server.py` (line 168)

**Additional Validation:**
- Pydantic models enforce field-level limits:
  - `topic`: max 5000 characters
  - `idempotency_key`: max 255 characters
  - `content_types`: max 4 items

**Location:** `src/content_creation_crew/content_routes.py` (GenerateRequest model)

### 3. Webhook Signature Verification + Replay Protection ✅

**Implementation:**
- **Stripe**: Signature verified using `stripe.Webhook.construct_event()`
- **Paystack**: Signature verified using HMAC-SHA512
- **Replay Protection**: `BillingEvent` table has unique constraint on `provider_event_id`
- Duplicate events are detected and ignored (logged as warning)

**Location:**
- `src/content_creation_crew/billing_routes.py` (webhook endpoints)
- `src/content_creation_crew/services/billing_service.py` (update_subscription_from_webhook)
- `src/content_creation_crew/db/models/billing.py` (unique constraint)

### 4. Request ID in Logs + Error Responses ✅

**Implementation:**
- `RequestIDMiddleware` generates/reads `X-Request-ID` header
- Request ID included in all log messages via `StructuredFormatter`
- Request ID returned in all error responses via `ErrorResponse.create()`
- Request ID exposed in response headers (`X-Request-ID`)

**Location:**
- `src/content_creation_crew/logging_config.py` (RequestIDMiddleware, StructuredFormatter)
- `src/content_creation_crew/exceptions.py` (ErrorResponse, exception handlers)
- `api_server.py` (exception handlers registered)

**Error Response Format:**
```json
{
  "detail": "Error message",
  "status_code": 400,
  "request_id": "uuid-here",
  "error_code": "validation_error"  // optional
}
```

### 5. Debug Mode Disabled in Staging/Prod ✅

**Implementation:**
- FastAPI `debug` parameter set based on `ENV`:
  - `dev`: `debug=True` (enables detailed error pages)
  - `staging/prod`: `debug=False` (generic error messages)
- API docs (`/docs`, `/redoc`) disabled in staging/prod
- Only enabled in development for easier debugging

**Location:** `api_server.py` (lines 159-163)

### 6. HTTPOnly Cookies for Tokens ✅

**Implementation:**
- Authentication tokens set as `httpOnly` cookies (not accessible from JavaScript)
- Cookies configured with:
  - `httponly=True`: Prevents XSS attacks
  - `secure=True` in staging/prod: HTTPS only
  - `samesite="lax"`: CSRF protection
  - `path="/"`: Available site-wide
- Token still returned in JSON response for backward compatibility
- User info stored in non-httpOnly cookie (for display purposes)

**Location:**
- `src/content_creation_crew/auth_routes.py` (signup, login, logout)
- `src/content_creation_crew/oauth_routes.py` (OAuth callbacks)

**Cookie Configuration:**
```python
response.set_cookie(
    key="auth_token",
    value=access_token,
    max_age=cookie_max_age,
    httponly=True,
    secure=config.ENV in ["staging", "prod"],
    samesite="lax",
    path="/"
)
```

### 7. CSRF Protection for Billing Actions ✅

**Implementation:**
- `verify_csrf_token()` function checks `X-CSRF-Token` header
- Required for billing endpoints in staging/prod:
  - `/v1/billing/upgrade`
  - `/v1/billing/cancel`
  - Other billing state-changing operations
- Skipped in development for easier testing
- Token format validated (16-128 characters)

**Location:**
- `src/content_creation_crew/middleware/csrf.py`
- `src/content_creation_crew/billing_routes.py` (upgrade_subscription endpoint)

**Note:** Full CSRF token generation/validation can be enhanced in the future with session-based tokens.

## Frontend Security

### 1. HTTPOnly Cookies (No localStorage) ✅

**Current State:**
- Backend sets `httpOnly` cookies automatically
- Frontend should stop using `js-cookie` for token storage
- Frontend can read `auth_user` cookie (non-sensitive) for display
- Frontend should use `/api/auth/me` to verify authentication status

**Migration Note:**
- Frontend `AuthContext` currently uses `js-cookie` to read tokens
- This should be updated to rely on automatic cookie sending
- Token verification should use `/api/auth/me` endpoint instead

**Location:** `web-ui/contexts/AuthContext.tsx`

### 2. CSRF Mitigation for Billing Actions ✅

**Implementation:**
- Frontend should send `X-CSRF-Token` header for billing requests
- Token can be generated client-side or fetched from a dedicated endpoint
- SameSite cookie policy (`lax`) provides additional CSRF protection

**Required Header:**
```typescript
headers: {
  'X-CSRF-Token': csrfToken,
  'Authorization': `Bearer ${token}`  // if not using cookies
}
```

## Testing

### Security Checks Covered

1. **CORS Testing:**
   - Verify only allowed origins can make requests
   - Verify methods are restricted in staging/prod
   - Verify headers are restricted appropriately

2. **Request Size Limits:**
   - Test with requests > 10MB (should return 413)
   - Test with valid requests < 10MB (should succeed)

3. **Webhook Replay Protection:**
   - Send same webhook event twice (second should be ignored)
   - Verify signature validation works

4. **Request ID:**
   - Verify request ID appears in logs
   - Verify request ID appears in error responses
   - Verify request ID appears in response headers

5. **Debug Mode:**
   - Verify debug=False in staging/prod
   - Verify API docs disabled in staging/prod

6. **HTTPOnly Cookies:**
   - Verify cookies are httpOnly
   - Verify cookies are secure in staging/prod
   - Verify cookies are not accessible from JavaScript

7. **CSRF Protection:**
   - Test billing endpoints without CSRF token (should fail in staging/prod)
   - Test billing endpoints with CSRF token (should succeed)

## Environment Variables

### Required for Security

```bash
# Environment
ENV=dev|staging|prod

# CORS (comma-separated list)
CORS_ORIGINS=https://your-frontend.com,https://staging.your-frontend.com

# Secrets
SECRET_KEY=your-secret-key-here

# Webhook secrets (required if using payment providers)
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TEST_WEBHOOK_SECRET=whsec_...
PAYSTACK_WEBHOOK_SECRET=your-paystack-secret
PAYSTACK_TEST_WEBHOOK_SECRET=your-paystack-test-secret
```

## Deployment Checklist

- [ ] Set `ENV=staging` or `ENV=prod`
- [ ] Configure `CORS_ORIGINS` with production frontend URL(s)
- [ ] Set strong `SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] Configure webhook secrets for payment providers
- [ ] Verify HTTPS is enabled (required for secure cookies)
- [ ] Test CORS restrictions
- [ ] Test request size limits
- [ ] Test webhook replay protection
- [ ] Verify debug mode is disabled
- [ ] Verify httpOnly cookies are set
- [ ] Test CSRF protection for billing actions

## Future Enhancements

1. **CSRF Token Generation:**
   - Implement proper CSRF token generation endpoint
   - Store tokens in Redis with expiration
   - Validate tokens server-side

2. **Rate Limiting:**
   - Per-endpoint rate limits
   - Per-user rate limits
   - IP-based rate limiting

3. **Content Security Policy (CSP):**
   - Add CSP headers to prevent XSS
   - Configure allowed sources for scripts/styles

4. **Security Headers:**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Strict-Transport-Security` (HSTS)

5. **Token Blacklisting:**
   - Implement JWT blacklist for logout
   - Store blacklisted tokens in Redis

6. **Audit Logging:**
   - Log all security-relevant events
   - Track failed authentication attempts
   - Monitor suspicious activity

