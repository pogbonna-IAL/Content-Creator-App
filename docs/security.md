# Security Documentation

**Last Updated:** January 14, 2026  
**Version:** 1.0

---

## Overview

This document describes the security measures and policies implemented in the Content Creation Crew application. All security features are designed to protect user data, prevent abuse, and ensure compliance with industry standards (GDPR, SOC2).

---

## Table of Contents

1. [Request Size Limits](#request-size-limits)
2. [Authentication & Authorization](#authentication--authorization)
3. [Password Security](#password-security)
4. [Rate Limiting](#rate-limiting)
5. [Input Validation & Sanitization](#input-validation--sanitization)
6. [Logging & Monitoring](#logging--monitoring)
7. [Data Protection](#data-protection)
8. [GDPR Compliance](#gdpr-compliance)

---

## Request Size Limits

**Status:** ✅ Implemented (M4)  
**Priority:** Medium

### Overview

Global request body size limits prevent abuse and protect against memory pressure attacks. All API endpoints that accept request bodies are subject to configurable size limits.

### Configuration

**Environment Variables:**
```bash
# Maximum request body size for JSON/form data (default: 2MB)
MAX_REQUEST_BYTES=2097152  # 2 * 1024 * 1024

# Maximum upload size for file uploads (default: 10MB)
MAX_UPLOAD_BYTES=10485760  # 10 * 1024 * 1024
```

**Recommended Values:**

| Environment | MAX_REQUEST_BYTES | MAX_UPLOAD_BYTES | Rationale |
|-------------|-------------------|------------------|-----------|
| Development | 2MB | 10MB | Fast testing |
| Staging | 2MB | 10MB | Production-like |
| Production | 2MB | 10MB | Balanced security/usability |
| High-Security | 1MB | 5MB | Maximum protection |

### How It Works

1. **Header Check:** Middleware reads `Content-Length` header before processing request
2. **Fast Rejection:** Oversized requests are rejected immediately (< 1ms)
3. **No Body Read:** Entire body is never loaded into memory for oversized requests
4. **Selective Limits:** Different limits for regular requests vs file uploads

### Response Format

**Oversized Request:**
```json
{
  "code": "REQUEST_TOO_LARGE",
  "message": "Request body too large. Maximum allowed size is 2.0MB, but received 3.5MB.",
  "status_code": 413,
  "request_id": "abc123...",
  "details": {
    "max_size_bytes": 2097152,
    "max_size_mb": 2.0,
    "received_bytes": 3670016,
    "received_mb": 3.5
  }
}
```

**HTTP Status:** `413 Payload Too Large`

**Headers:**
```
Retry-After: 60
X-RateLimit-Limit: 2097152
X-RateLimit-Remaining: 0
```

### Endpoints Affected

**All POST/PUT/PATCH endpoints:**
- `/api/auth/signup`
- `/api/auth/login`
- `/api/generate`
- `/v1/content/*`
- All other endpoints accepting request bodies

**Excluded:**
- `GET` requests (no body)
- `HEAD` requests (no body)
- `OPTIONS` requests (preflight)
- `DELETE` requests (typically no body)
- SSE streaming endpoints (uses different mechanism)

### Upload Endpoints

Endpoints detected as file uploads use `MAX_UPLOAD_BYTES`:
- `Content-Type: multipart/form-data`
- URL path contains `/upload`
- URL path contains `/artifacts`

### Security Benefits

1. **DoS Prevention:** Prevents attackers from exhausting server memory
2. **Resource Protection:** Limits memory usage per request
3. **Fast Rejection:** Rejects attacks before significant resources are consumed
4. **Cost Control:** Reduces bandwidth and processing costs for abuse attempts

### Performance Impact

- **Minimal:** Header check adds < 1ms per request
- **Fast Rejection:** Oversized requests rejected in < 1ms
- **No False Positives:** Normal requests unaffected

### Testing

**Test Oversized Request:**
```bash
# Create 3MB payload (exceeds 2MB limit)
dd if=/dev/zero bs=1M count=3 | base64 > large_payload.txt

curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -H "Content-Length: 3145728" \
  -d @large_payload.txt

# Expected: 413 Payload Too Large
```

**Test Normal Request:**
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"MyP@ssw0rd123"}'

# Expected: 200 OK (or other non-413 response)
```

### Monitoring

**Metrics to Track:**
```python
# Rejected requests (413 responses)
request_size_limit_rejected_total

# Request sizes histogram
request_size_bytes_histogram

# By endpoint
request_size_rejected_by_endpoint{endpoint="/api/auth/signup"}
```

**Alerts:**
- High rate of 413 responses (potential attack)
- Sudden increase in average request size
- Repeated oversized requests from same IP

### Troubleshooting

**Problem:** Legitimate requests rejected

**Diagnosis:**
1. Check request size: `Content-Length` header
2. Check configured limits: `MAX_REQUEST_BYTES`
3. Review application logs for size details

**Solutions:**
1. Increase `MAX_REQUEST_BYTES` if appropriate
2. Split large payloads into multiple requests
3. Use pagination for bulk operations
4. Compress request bodies (gzip)

**Problem:** Oversized requests not rejected

**Diagnosis:**
1. Verify middleware is loaded: Check startup logs
2. Check request method (GET/HEAD/OPTIONS excluded)
3. Verify `Content-Length` header is present

**Solutions:**
1. Ensure middleware is added to app
2. Check middleware order (should be early)
3. Verify configuration is loaded

---

## Authentication & Authorization

### Overview

Secure authentication using JWT tokens with bcrypt password hashing, token blacklisting, and rate limiting.

### Key Features

- ✅ JWT tokens with configurable expiry (2 hours default)
- ✅ Bcrypt hashing with configurable cost factor (12 rounds default)
- ✅ Token blacklist (Redis-backed)
- ✅ HTTPOnly cookies for token storage
- ✅ Auth-specific rate limiting
- ✅ Email verification

### Configuration

```bash
# JWT Configuration
JWT_SECRET=<strong-random-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120  # 2 hours

# Bcrypt Configuration
BCRYPT_ROUNDS=12  # 10-14 recommended

# Token Blacklist (requires Redis)
REDIS_URL=redis://localhost:6379/0
```

---

## Password Security

### Overview

Comprehensive password policy with complexity requirements, common password blocking, and secure storage.

### Password Requirements

- ✅ Minimum 8 characters
- ✅ At least one uppercase letter (A-Z)
- ✅ At least one lowercase letter (a-z)
- ✅ At least one digit (0-9)
- ✅ At least one special character (!@#$%^&* etc.)
- ✅ Not a commonly used password (500+ blocked)

### Configuration

```bash
# Password Policy
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SYMBOL=true
PASSWORD_BLOCK_COMMON=true

# Optional: Custom common passwords file
PASSWORD_COMMON_LIST_FILE=/path/to/passwords.txt
```

### Security Benefits

- **Strong Entropy:** ~52.4 bits (95 character keyspace)
- **Credential Stuffing Protection:** Common passwords blocked
- **Bcrypt Storage:** Adaptive hashing with salt

---

## Rate Limiting

### Overview

Redis-backed rate limiting prevents brute-force attacks and abuse.

### Limits

**Authentication Endpoints:**
- Login: 5 attempts per minute per IP
- Signup: 3 attempts per minute per IP
- Password reset: 3 attempts per hour per email

**API Endpoints:**
- Standard: 60 requests per minute per user
- Generation: 10 requests per minute per user

### Configuration

```bash
# Rate Limiting
RATE_LIMIT_RPM=60
RATE_LIMIT_GENERATE_RPM=10
RATE_LIMIT_SSE_CONNECTIONS=5
```

---

## Input Validation & Sanitization

### Overview

Multi-layered input validation prevents injection attacks and ensures data integrity.

### Layers

1. **Schema Validation:** Pydantic models enforce structure
2. **Prompt Safety:** Blocks prompt injection attempts
3. **Content Moderation:** Filters inappropriate content
4. **SQL Injection Prevention:** Parameterized queries (SQLAlchemy ORM)
5. **XSS Prevention:** Output escaping in frontend

### Prompt Injection Defense

**Blocked Patterns:**
- System prompt extraction attempts
- Secret exfiltration attempts
- Instruction override attempts
- Hidden command injection

---

## Logging & Monitoring

### Overview

Comprehensive logging with PII protection and audit trails.

### Key Features

- ✅ PII redaction (emails, IPs, tokens)
- ✅ Request ID correlation
- ✅ Audit logging for security events
- ✅ Structured logging (JSON)
- ✅ Prometheus metrics

### Configuration

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text
```

### Audit Events

All security-critical actions are logged:
- Authentication (login, logout, signup)
- GDPR requests (export, delete)
- Password changes
- Token revocations
- Failed authentication attempts
- Rate limit hits
- Prompt injection blocks

---

## Data Protection

### Overview

Data protection at rest and in transit using industry-standard encryption.

### Measures

- ✅ HTTPS/TLS for all connections
- ✅ Bcrypt for password storage
- ✅ JWT for stateless authentication
- ✅ Database encryption (provider-dependent)
- ✅ Secure cookie flags (HTTPOnly, Secure, SameSite)

---

## GDPR Compliance

### Overview

Full GDPR compliance with user data export and deletion capabilities.

### Rights Implemented

1. **Right to Access (Article 15):**
   - `GET /api/user/export` - Export all user data
   - Machine-readable JSON format

2. **Right to Erasure (Article 17):**
   - `DELETE /api/user/delete` - Request account deletion
   - Soft delete (immediate access disable)
   - Hard delete (after 7-30 day retention)

3. **Data Minimization (Article 5):**
   - Only essential data collected
   - PII hashed/redacted in logs
   - Automatic cleanup of expired data

### Configuration

```bash
# GDPR Configuration
GDPR_DELETION_GRACE_DAYS=30  # Retention window
FRONTEND_URL=https://yourdomain.com  # For email links
```

---

## Security Checklist

**Before Production Deployment:**

- [ ] Set strong `JWT_SECRET` (not default)
- [ ] Configure `BCRYPT_ROUNDS` (12-14)
- [ ] Enable `HTTPS` (TLS certificates)
- [ ] Set `MAX_REQUEST_BYTES` appropriately
- [ ] Configure `CORS_ORIGINS` (specific domains)
- [ ] Enable Redis for rate limiting
- [ ] Set up monitoring/alerting
- [ ] Run security regression tests
- [ ] Review audit logs configuration
- [ ] Test GDPR endpoints
- [ ] Enable email verification (production)
- [ ] Configure database backups
- [ ] Set up disaster recovery plan

---

## Security Contact

**Report Security Issues:**
- Email: security@yourcompany.com
- PGP Key: [Link to public key]
- Bug Bounty: [Program details]

**Response Time:**
- Critical: 24 hours
- High: 72 hours
- Medium: 7 days
- Low: 30 days

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GDPR Official Text](https://gdpr-info.eu/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Bcrypt Specification](https://en.wikipedia.org/wiki/Bcrypt)

---

**Document Version:** 1.0  
**Last Review:** January 14, 2026  
**Next Review:** April 14, 2026 (Quarterly)

