# Health Check System

## Overview

The `/health` endpoint provides comprehensive health monitoring for all system components, enabling early detection of issues before they impact users.

## Endpoint

```
GET /health
```

**Response Codes:**
- `200 OK` - All components are healthy
- `503 Service Unavailable` - One or more components are degraded or down

## Components Monitored

### 1. Database
- Verifies PostgreSQL connectivity
- Tests with simple `SELECT 1` query
- Reports connection status

### 2. Redis (Optional)
- Checks Redis availability with ping
- Returns OK if not configured (optional component)
- Reports connection status

### 3. Storage ⭐
- **Accessibility**: Verifies storage path exists and is accessible
- **Writability**: Performs optional write test
- **Free Space**: Checks free space meets minimum threshold
- **Type**: Reports storage provider type (LocalDisk, S3, etc.)

### 4. LLM Provider (Ollama)
- Checks Ollama API availability
- Reports number of available models
- Non-critical (degraded vs down)

## Health Status Levels

### OK
All checks passed. System is fully operational.

### DEGRADED
One or more non-critical components have issues:
- Redis unavailable (optional)
- LLM provider unavailable (can queue jobs)
- Storage space low (but still writable)

### DOWN
Critical component failures:
- Database unavailable
- Storage not accessible
- Storage not writable

## Configuration

Configure via environment variables:

```bash
# Timeout for each component check (seconds)
HEALTHCHECK_TIMEOUT_SECONDS=3

# Minimum free space required (MB)
MIN_FREE_SPACE_MB=1024

# Enable write test for storage
HEALTHCHECK_STORAGE_WRITE_TEST=true
```

### Recommended Thresholds

**Development:**
```bash
MIN_FREE_SPACE_MB=100  # 100 MB
```

**Staging:**
```bash
MIN_FREE_SPACE_MB=2048  # 2 GB
```

**Production:**
```bash
MIN_FREE_SPACE_MB=5120  # 5 GB
```

**High-Traffic Production:**
```bash
MIN_FREE_SPACE_MB=10240  # 10 GB
```

## Response Format

```json
{
  "status": "ok|degraded|down",
  "timestamp": "2026-01-14T12:34:56.789Z",
  "response_time_ms": 123.45,
  "service": "content-creation-crew",
  "environment": "prod",
  "components": {
    "database": {
      "status": "ok",
      "message": "Database is accessible",
      "checked_at": "2026-01-14T12:34:56.789Z",
      "response_time_ms": 45.23,
      "details": {
        "connection": "active"
      }
    },
    "redis": {
      "status": "ok",
      "message": "Redis is accessible",
      "checked_at": "2026-01-14T12:34:56.789Z",
      "response_time_ms": 12.34,
      "details": {
        "connection": "active"
      }
    },
    "storage": {
      "status": "ok",
      "message": "Storage is accessible with 15234MB free",
      "checked_at": "2026-01-14T12:34:56.789Z",
      "response_time_ms": 23.45,
      "details": {
        "type": "LocalDiskStorageProvider",
        "accessible": true,
        "writable": true,
        "free_space_mb": 15234,
        "total_space_mb": 50000,
        "free_space_percent": 30.47,
        "path": "/var/app/storage",
        "error": null
      }
    },
    "llm": {
      "status": "ok",
      "message": "LLM provider is accessible",
      "checked_at": "2026-01-14T12:34:56.789Z",
      "response_time_ms": 42.11,
      "details": {
        "provider": "ollama",
        "models_count": 3
      }
    }
  }
}
```

## Storage Health Details

### Local Disk Storage

```json
"storage": {
  "status": "ok",
  "message": "Storage is accessible with 15234MB free",
  "details": {
    "type": "LocalDiskStorageProvider",
    "accessible": true,
    "writable": true,
    "free_space_mb": 15234,
    "total_space_mb": 50000,
    "free_space_percent": 30.47,
    "path": "/var/app/storage",
    "error": null
  }
}
```

### S3 Storage

```json
"storage": {
  "status": "ok",
  "message": "Storage is accessible (cloud storage)",
  "details": {
    "type": "S3StorageProvider",
    "accessible": true,
    "writable": true,
    "free_space_mb": -1,  // Not applicable for S3
    "total_space_mb": -1,
    "bucket": "my-content-bucket",
    "region": "us-east-1",
    "error": null
  }
}
```

## Kubernetes Integration

### Liveness Probe

Use for restart decisions:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Readiness Probe

Use for traffic routing:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 2
```

### Startup Probe

Use for slow-starting containers:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 30  # 150s total
```

## Monitoring and Alerting

### Alert on Degraded State

```yaml
- alert: ServiceDegraded
  expr: up{job="content-creation"} == 1 and health_status != 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Service is degraded"
```

### Alert on Down State

```yaml
- alert: ServiceDown
  expr: up{job="content-creation"} == 0 or health_status == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Service is down"
```

### Alert on Low Storage

```yaml
- alert: StorageLowSpace
  expr: storage_free_space_mb < 2048
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Storage space running low"
    description: "Free space: {{ $value }}MB"

- alert: StorageCritical
  expr: storage_free_space_mb < 512
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Storage space critically low"
    description: "Free space: {{ $value }}MB"
```

## Troubleshooting

### Health check times out

**Symptoms:** Health endpoint returns 503 with timeout errors

**Solutions:**
1. Increase `HEALTHCHECK_TIMEOUT_SECONDS`
2. Disable write test: `HEALTHCHECK_STORAGE_WRITE_TEST=false`
3. Check component performance (DB, Redis, Storage, Ollama)

### Storage reports "not writable"

**Symptoms:** Storage status is "down" with "not writable" error

**Solutions:**
1. Check directory permissions: `ls -la /path/to/storage`
2. Verify application user has write access
3. Check if filesystem is mounted read-only: `mount | grep storage`
4. Ensure disk is not full: `df -h`

### Low disk space warnings

**Symptoms:** Storage status is "degraded" with "low disk space" message

**Solutions:**
1. Clean up old artifacts: Run cleanup job
2. Increase disk size or add volume
3. Adjust threshold: Lower `MIN_FREE_SPACE_MB` if appropriate
4. Implement automatic cleanup policies

### S3 health check fails

**Symptoms:** Storage status is "down" with S3 errors

**Solutions:**
1. Verify AWS credentials are configured
2. Check bucket exists and is accessible
3. Verify bucket permissions (PUT, GET, DELETE)
4. Check network connectivity to S3
5. Verify S3 endpoint URL if using compatible storage

### Redis "unavailable" but service still works

**Explanation:** Redis is optional. The service falls back to in-memory caching.

**Action:** No immediate action required, but:
1. Check Redis connectivity
2. Verify Redis URL is correct
3. Consider fixing for better performance

## Best Practices

### 1. Regular Monitoring
- Monitor health endpoint continuously
- Set up alerts for degraded/down states
- Track response times over time

### 2. Appropriate Thresholds
- Set `MIN_FREE_SPACE_MB` based on:
  - Average file sizes
  - Expected traffic
  - Cleanup frequency
- Leave headroom for spikes

### 3. Proactive Cleanup
- Implement automatic artifact cleanup
- Monitor storage usage trends
- Alert before reaching critical levels

### 4. Timeout Configuration
- Balance between thoroughness and speed
- Kubernetes: 2-3 seconds recommended
- Manual checks: 5 seconds acceptable
- Never set timeouts > 10 seconds

### 5. Write Test Usage
- Enable for readiness probes
- Disable for high-frequency liveness probes
- Enable for manual debugging

## Related Endpoints

- `/health/pool` - Database connection pool statistics
- `/metrics` - Prometheus metrics (includes health metrics)
- `/meta` - Service metadata and version info

## References

- [Health Check Service](../src/content_creation_crew/services/health_check.py)
- [Storage Provider](../src/content_creation_crew/services/storage_provider.py)
- [Implementation Details](./PROMPT-M5-COMPLETE.md)

