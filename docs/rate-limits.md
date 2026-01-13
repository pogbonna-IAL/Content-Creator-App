# Rate Limits Documentation

## Overview

Content Creation Crew implements rate limiting to protect API resources and ensure fair usage across all users. Rate limits are applied per user/organization based on subscription tier and endpoint type.

## Table of Contents

1. [Rate Limit Types](#rate-limit-types)
2. [Tier-Based Limits](#tier-based-limits)
3. [Endpoint-Specific Limits](#endpoint-specific-limits)
4. [SSE Connection Limits](#sse-connection-limits)
5. [Configuration](#configuration)
6. [Error Response](#error-response)
7. [Rate Limit Headers](#rate-limit-headers)
8. [Best Practices](#best-practices)

---

## Rate Limit Types

### 1. General API Rate Limits

**Scope:** All API endpoints (except health checks and metrics)

**Default Limits (requests per minute):**
- **Free Tier:** 10 RPM
- **Basic Tier:** 30 RPM
- **Pro Tier:** 100 RPM
- **Enterprise Tier:** 500 RPM

**Configuration:** `RATE_LIMIT_RPM` environment variable

### 2. Generation-Specific Rate Limits

**Scope:** Content generation endpoints
- `/v1/content/generate`
- `/api/generate`
- `/api/generate/stream`

**Default Limit:** 10 requests per minute (all tiers)

**Configuration:** `RATE_LIMIT_GENERATE_RPM` environment variable

**Rationale:** Generation endpoints are resource-intensive and require stricter limits to prevent abuse.

### 3. SSE Connection Limits

**Scope:** Server-Sent Events (SSE) streaming endpoints
- `/v1/content/jobs/{id}/stream`

**Default Limit:** 5 concurrent connections per user

**Configuration:** `RATE_LIMIT_SSE_CONNECTIONS` environment variable

**Rationale:** SSE connections consume server resources (memory, connections). Limiting concurrent connections prevents resource exhaustion.

---

## Tier-Based Limits

### Free Tier

- **General API:** 10 requests/minute
- **Generation:** 10 requests/minute
- **SSE Connections:** 5 concurrent

### Basic Tier

- **General API:** 30 requests/minute
- **Generation:** 10 requests/minute
- **SSE Connections:** 5 concurrent

### Pro Tier

- **General API:** 100 requests/minute
- **Generation:** 10 requests/minute
- **SSE Connections:** 5 concurrent

### Enterprise Tier

- **General API:** 500 requests/minute
- **Generation:** 10 requests/minute
- **SSE Connections:** 5 concurrent (configurable)

---

## Endpoint-Specific Limits

### Excluded Endpoints

These endpoints are **not rate limited**:

- `/health` - Health check endpoint
- `/meta` - Metadata endpoint
- `/` - Root endpoint
- `/metrics` - Prometheus metrics endpoint
- `/v1/metrics` - Alternative metrics endpoint

### Generation Endpoints

**Endpoints:**
- `POST /v1/content/generate`
- `POST /api/generate`
- `POST /api/generate/stream`

**Limit:** `RATE_LIMIT_GENERATE_RPM` (default: 10 RPM)

**Applies to:** All tiers (same limit for all)

### SSE Streaming Endpoints

**Endpoints:**
- `GET /v1/content/jobs/{id}/stream`

**Limit:** `RATE_LIMIT_SSE_CONNECTIONS` (default: 5 concurrent)

**Applies to:** Per user (not per tier)

---

## SSE Connection Limits

### How It Works

SSE (Server-Sent Events) connections are long-lived connections that consume server resources. To prevent resource exhaustion:

1. **Per-User Limit:** Each user can have up to `RATE_LIMIT_SSE_CONNECTIONS` concurrent SSE connections
2. **Connection Tracking:** Connections are tracked per user ID
3. **Graceful Handling:** When limit is exceeded, new connections are rejected with `429 Too Many Requests`

### Configuration

**Environment Variable:** `RATE_LIMIT_SSE_CONNECTIONS`

**Default:** `5`

**Example:**
```bash
# Allow 10 concurrent SSE connections per user
RATE_LIMIT_SSE_CONNECTIONS=10
```

### Implementation

SSE connection limits are enforced at the middleware level. When a user attempts to open more than the allowed number of concurrent SSE connections, the request is rejected with a `429` status code.

---

## Configuration

### Environment Variables

#### `RATE_LIMIT_RPM`

**Description:** Base rate limit for general API requests (requests per minute)

**Default:** `60`

**Example:**
```bash
# Set to 120 requests per minute
RATE_LIMIT_RPM=120
```

**Note:** Tier limits are calculated from this base value:
- Free: `max(10, RATE_LIMIT_RPM / 6)`
- Basic: `max(30, RATE_LIMIT_RPM / 2)`
- Pro: `max(100, RATE_LIMIT_RPM)`
- Enterprise: `max(500, RATE_LIMIT_RPM * 5)`

#### `RATE_LIMIT_GENERATE_RPM`

**Description:** Rate limit for content generation endpoints (requests per minute)

**Default:** `10`

**Example:**
```bash
# Allow 20 generation requests per minute
RATE_LIMIT_GENERATE_RPM=20
```

**Applies to:**
- `/v1/content/generate`
- `/api/generate`
- `/api/generate/stream`

#### `RATE_LIMIT_SSE_CONNECTIONS`

**Description:** Maximum concurrent SSE connections per user

**Default:** `5`

**Example:**
```bash
# Allow 10 concurrent SSE connections
RATE_LIMIT_SSE_CONNECTIONS=10
```

**Applies to:**
- `/v1/content/jobs/{id}/stream`

### Configuration Example

**`.env` file:**
```bash
# Rate limiting configuration
RATE_LIMIT_RPM=60
RATE_LIMIT_GENERATE_RPM=10
RATE_LIMIT_SSE_CONNECTIONS=5
```

---

## Error Response

### Rate Limit Exceeded

When a rate limit is exceeded, the API returns:

**Status Code:** `429 Too Many Requests`

**Response Body:**
```json
{
  "detail": "Rate limit exceeded. Limit: 10 requests per minute.",
  "status_code": 429,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_code": "RATE_LIMITED",
  "limit": 10,
  "reset_after_seconds": 45,
  "retry_after": 45
}
```

**Fields:**
- `detail` - Human-readable error message
- `status_code` - HTTP status code (429)
- `request_id` - Request ID for correlation
- `error_code` - Error code: `RATE_LIMITED`
- `limit` - Rate limit that was exceeded
- `reset_after_seconds` - Seconds until rate limit resets
- `retry_after` - Same as `reset_after_seconds` (for compatibility)

### Error Code

**Error Code:** `RATE_LIMITED`

**Usage:** Clients can check for `error_code === "RATE_LIMITED"` to handle rate limit errors specifically.

---

## Rate Limit Headers

All responses include rate limit headers:

### Headers

- `X-RateLimit-Limit` - Maximum requests allowed per minute
- `X-RateLimit-Remaining` - Number of requests remaining in current window
- `X-RateLimit-Reset-After` - Seconds until rate limit resets
- `Retry-After` - Seconds until rate limit resets (RFC 7231)

### Example Headers

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 3
X-RateLimit-Reset-After: 45
Retry-After: 45
```

### Usage

Clients should:
1. **Monitor headers** to track rate limit status
2. **Respect `Retry-After`** header when rate limited
3. **Implement exponential backoff** when rate limited

---

## Implementation Details

### Token Bucket Algorithm

Rate limiting uses a **token bucket algorithm**:

1. **Bucket Size:** 2x the rate limit (allows burst)
2. **Refill Rate:** Tokens refill every 60 seconds
3. **Token Consumption:** Each request consumes 1 token

**Example:**
- Limit: 10 RPM
- Bucket Size: 20 tokens
- Refill: 10 tokens per 60 seconds

### Redis Backend

**Preferred:** Redis-backed rate limiting (distributed, persistent)

**Fallback:** In-memory rate limiting (single instance, non-persistent)

**Configuration:** Automatic (uses Redis if available)

### Rate Limit Keys

**Format:** `ratelimit:{identifier}`

**Identifiers:**
- User: `ratelimit:user:{user_id}`
- IP: `ratelimit:ip:{ip_address}`

---

## Best Practices

### For API Consumers

✅ **DO:**
- Monitor `X-RateLimit-Remaining` header
- Implement exponential backoff on `429` responses
- Respect `Retry-After` header
- Cache responses when possible
- Batch requests when applicable

❌ **DON'T:**
- Don't ignore rate limit headers
- Don't retry immediately after `429` error
- Don't make unnecessary requests
- Don't open multiple SSE connections unnecessarily

### For Administrators

✅ **DO:**
- Set appropriate limits based on server capacity
- Monitor rate limit metrics (`rate_limited_total`)
- Adjust limits based on usage patterns
- Use Redis for distributed rate limiting

❌ **DON'T:**
- Don't set limits too high (risks resource exhaustion)
- Don't set limits too low (poor user experience)
- Don't ignore rate limit metrics

---

## Monitoring

### Metrics

Rate limiting is tracked via Prometheus metrics:

**Metric:** `rate_limited_total`

**Labels:**
- `route` - API route
- `method` - HTTP method

**Query Example:**
```promql
# Rate limit hits per route
sum(rate_limited_total) by (route)

# Rate limit hit rate
rate(rate_limited_total[5m])
```

### Logging

Rate limit events are logged with:
- Request ID
- User ID (if authenticated)
- IP address
- Route and method
- Limit exceeded

---

## Troubleshooting

### Rate Limits Too Strict

**Symptoms:** Users frequently hitting rate limits

**Solutions:**
1. Increase `RATE_LIMIT_RPM` for general API
2. Increase `RATE_LIMIT_GENERATE_RPM` for generation endpoints
3. Upgrade users to higher tiers

### Rate Limits Not Working

**Symptoms:** No rate limiting applied

**Possible Causes:**
1. Middleware not enabled
2. Redis not available (fallback to in-memory)
3. Configuration not loaded

**Solutions:**
1. Check middleware is added to FastAPI app
2. Verify Redis connection
3. Check environment variables are set

### SSE Connection Limits

**Symptoms:** Users can't open SSE connections

**Solutions:**
1. Increase `RATE_LIMIT_SSE_CONNECTIONS`
2. Check for connection leaks (connections not closing)
3. Monitor concurrent SSE connections

---

## Related Documentation

- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Monitoring](./monitoring.md) - Metrics and monitoring
- [Subscription Tiers](./pre-deploy-readiness.md) - Tier configuration

---

## Quick Reference

### Default Limits

| Tier | General API | Generation | SSE Connections |
|------|-------------|------------|-----------------|
| Free | 10 RPM | 10 RPM | 5 |
| Basic | 30 RPM | 10 RPM | 5 |
| Pro | 100 RPM | 10 RPM | 5 |
| Enterprise | 500 RPM | 10 RPM | 5 |

### Environment Variables

```bash
RATE_LIMIT_RPM=60
RATE_LIMIT_GENERATE_RPM=10
RATE_LIMIT_SSE_CONNECTIONS=5
```

### Error Response

```json
{
  "detail": "Rate limit exceeded...",
  "status_code": 429,
  "error_code": "RATE_LIMITED",
  "limit": 10,
  "reset_after_seconds": 45
}
```

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

