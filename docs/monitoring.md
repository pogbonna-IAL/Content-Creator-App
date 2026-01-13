# Monitoring and Metrics Guide

## Overview

Content Creation Crew exposes Prometheus-compatible metrics for production monitoring. This document describes available metrics, scrape configuration, and alert recommendations.

## Table of Contents

1. [Metrics Endpoint](#metrics-endpoint)
2. [Available Metrics](#available-metrics)
3. [Prometheus Scrape Configuration](#prometheus-scrape-configuration)
4. [Grafana Dashboard Examples](#grafana-dashboard-examples)
5. [Alert Recommendations](#alert-recommendations)
6. [Request ID Correlation](#request-id-correlation)

---

## Metrics Endpoint

### Endpoint

**URL:** `GET /metrics` or `GET /v1/metrics`

**Format:** Prometheus text format (text/plain)

**Example:**
```bash
curl http://localhost:8000/metrics
```

**Response:**
```
# HELP requests_total Total number of HTTP requests
# TYPE requests_total counter
requests_total{method="GET",route="/v1/content/jobs",status="200"} 42
requests_total{method="POST",route="/v1/content/generate",status="201"} 15
requests_total{method="POST",route="/v1/content/generate",status="500"} 2

# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds summary
request_duration_seconds_count{method="GET",route="/v1/content/jobs"} 42
request_duration_seconds_sum{method="GET",route="/v1/content/jobs"} 12.5
request_duration_seconds{method="GET",route="/v1/content/jobs",quantile="0.5"} 0.25
request_duration_seconds{method="GET",route="/v1/content/jobs",quantile="0.95"} 0.5
request_duration_seconds{method="GET",route="/v1/content/jobs",quantile="0.99"} 1.2

# HELP jobs_total Total number of content generation jobs
# TYPE jobs_total counter
jobs_total{content_types="blog",plan="free"} 100
jobs_total{content_types="blog,social",plan="pro"} 50

# HELP job_failures_total Total number of failed jobs
# TYPE job_failures_total counter
job_failures_total{error_type="timeout",plan="free"} 5
job_failures_total{error_type="ValidationError",plan="pro"} 2

# HELP cache_hits_total Total number of cache hits
# TYPE cache_hits_total counter
cache_hits_total 150

# HELP cache_misses_total Total number of cache misses
# TYPE cache_misses_total counter
cache_misses_total 50

# HELP rate_limited_total Total number of rate-limited requests
# TYPE rate_limited_total counter
rate_limited_total{method="POST",route="/v1/content/generate"} 10

# HELP tts_jobs_total Total number of TTS (voiceover) jobs
# TYPE tts_jobs_total counter
tts_jobs_total{status="success",voice_id="default"} 25
tts_jobs_total{status="failure",voice_id="default"} 2

# HELP video_renders_total Total number of video render jobs
# TYPE video_renders_total counter
video_renders_total{status="success",renderer="baseline"} 10
video_renders_total{status="failure",renderer="baseline"} 1
```

---

## Available Metrics

### Request Metrics

#### `requests_total`
**Type:** Counter  
**Labels:**
- `route` - Normalized route path (e.g., `/v1/content/jobs/{id}`)
- `method` - HTTP method (GET, POST, etc.)
- `status` - HTTP status code (200, 201, 400, 500, etc.)

**Description:** Total number of HTTP requests received

**Example Query:**
```promql
# Total requests per route
sum(requests_total) by (route)

# Requests per status code
sum(requests_total) by (status)

# Error rate (5xx)
sum(requests_total{status=~"5.."}) / sum(requests_total)
```

#### `request_duration_seconds`
**Type:** Summary (histogram-like)  
**Labels:**
- `route` - Normalized route path
- `method` - HTTP method

**Description:** Request duration in seconds (p50, p95, p99 quantiles)

**Example Query:**
```promql
# 95th percentile latency
histogram_quantile(0.95, request_duration_seconds{route="/v1/content/generate"})

# Average request duration
rate(request_duration_seconds_sum[5m]) / rate(request_duration_seconds_count[5m])
```

#### `errors_total`
**Type:** Counter  
**Labels:**
- `route` - Normalized route path
- `status` - HTTP status code

**Description:** Total number of server errors (5xx)

**Example Query:**
```promql
# Error rate per route
rate(errors_total[5m])
```

### Job Metrics

#### `jobs_total`
**Type:** Counter  
**Labels:**
- `content_types` - Comma-separated content types (e.g., "blog", "blog,social")
- `plan` - User subscription plan (free, basic, pro, enterprise)

**Description:** Total number of content generation jobs created

**Example Query:**
```promql
# Jobs per plan
sum(jobs_total) by (plan)

# Jobs per content type
sum(jobs_total) by (content_types)
```

#### `job_failures_total`
**Type:** Counter  
**Labels:**
- `error_type` - Error type (timeout, ValidationError, etc.)
- `plan` - User subscription plan

**Description:** Total number of failed jobs

**Example Query:**
```promql
# Failure rate
rate(job_failures_total[5m]) / rate(jobs_total[5m])

# Failures by error type
sum(job_failures_total) by (error_type)
```

### Cache Metrics

#### `cache_hits_total`
**Type:** Counter  
**Description:** Total number of cache hits

**Example Query:**
```promql
# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

#### `cache_misses_total`
**Type:** Counter  
**Description:** Total number of cache misses

**Example Query:**
```promql
# Cache miss rate
rate(cache_misses_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

### Rate Limiting Metrics

#### `rate_limited_total`
**Type:** Counter  
**Labels:**
- `route` - Normalized route path
- `method` - HTTP method

**Description:** Total number of rate-limited requests

**Example Query:**
```promql
# Rate limit hits per route
sum(rate_limited_total) by (route)

# Rate limit rate
rate(rate_limited_total[5m])
```

### Media Generation Metrics

#### `tts_jobs_total`
**Type:** Counter  
**Labels:**
- `status` - Job status (success, failure)
- `voice_id` - Voice identifier (default, etc.)

**Description:** Total number of TTS (voiceover) jobs

**Example Query:**
```promql
# TTS success rate
sum(tts_jobs_total{status="success"}) / sum(tts_jobs_total)

# TTS jobs per voice
sum(tts_jobs_total) by (voice_id)
```

#### `video_renders_total`
**Type:** Counter  
**Labels:**
- `status` - Job status (success, failure)
- `renderer` - Renderer name (baseline, comfyui)

**Description:** Total number of video render jobs

**Example Query:**
```promql
# Video render success rate
sum(video_renders_total{status="success"}) / sum(video_renders_total)

# Video renders per renderer
sum(video_renders_total) by (renderer)
```

---

## Prometheus Scrape Configuration

### Basic Configuration

**File:** `prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'content-crew-api'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          environment: 'production'
          service: 'api'
```

### Docker Compose Configuration

**File:** `docker-compose.yml` (add Prometheus service)

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: content-crew-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - content-crew-network
    depends_on:
      - api

volumes:
  prometheus_data:
```

### Kubernetes Configuration

**File:** `prometheus-config.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    
    scrape_configs:
      - job_name: 'content-crew-api'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: content-crew-api
          - source_labels: [__meta_kubernetes_pod_ip]
            action: replace
            target_label: __address__
            replacement: ${1}:8000
        metrics_path: '/metrics'
```

### Scrape Interval Recommendations

| Environment | Scrape Interval | Rationale |
|-------------|----------------|-----------|
| **Production** | 15-30 seconds | Balance between freshness and load |
| **Staging** | 30-60 seconds | Less critical, reduce load |
| **Development** | 60 seconds | Minimal impact on development |

---

## Grafana Dashboard Examples

### Request Rate Dashboard

**Panel 1: Request Rate**
```promql
sum(rate(requests_total[5m])) by (route)
```

**Panel 2: Error Rate**
```promql
sum(rate(errors_total[5m])) / sum(rate(requests_total[5m])) * 100
```

**Panel 3: P95 Latency**
```promql
histogram_quantile(0.95, request_duration_seconds{route="/v1/content/generate"})
```

### Job Metrics Dashboard

**Panel 1: Jobs Created**
```promql
sum(rate(jobs_total[5m])) by (plan)
```

**Panel 2: Job Failure Rate**
```promql
sum(rate(job_failures_total[5m])) / sum(rate(jobs_total[5m])) * 100
```

**Panel 3: Jobs by Content Type**
```promql
sum(jobs_total) by (content_types)
```

### Cache Performance Dashboard

**Panel 1: Cache Hit Rate**
```promql
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100
```

**Panel 2: Cache Operations**
```promql
sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))
```

### Media Generation Dashboard

**Panel 1: TTS Success Rate**
```promql
sum(tts_jobs_total{status="success"}) / sum(tts_jobs_total) * 100
```

**Panel 2: Video Render Success Rate**
```promql
sum(video_renders_total{status="success"}) / sum(video_renders_total) * 100
```

**Panel 3: Media Jobs Per Hour**
```promql
sum(rate(tts_jobs_total[1h])) + sum(rate(video_renders_total[1h]))
```

---

## Alert Recommendations

### Critical Alerts

#### High Error Rate
**Alert:** `HighErrorRate`  
**Condition:** Error rate > 5% for 5 minutes  
**Severity:** Critical

```yaml
groups:
  - name: content_crew_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(errors_total[5m])) / sum(rate(requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
```

#### High Latency
**Alert:** `HighLatency`  
**Condition:** P95 latency > 5 seconds for 5 minutes  
**Severity:** Warning

```yaml
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, request_duration_seconds{route="/v1/content/generate"}) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s (threshold: 5s)"
```

#### High Job Failure Rate
**Alert:** `HighJobFailureRate`  
**Condition:** Job failure rate > 10% for 10 minutes  
**Severity:** Critical

```yaml
      - alert: HighJobFailureRate
        expr: |
          sum(rate(job_failures_total[10m])) / sum(rate(jobs_total[10m])) > 0.10
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "High job failure rate"
          description: "Job failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
```

### Warning Alerts

#### Low Cache Hit Rate
**Alert:** `LowCacheHitRate`  
**Condition:** Cache hit rate < 50% for 15 minutes  
**Severity:** Warning

```yaml
      - alert: LowCacheHitRate
        expr: |
          sum(rate(cache_hits_total[15m])) / (sum(rate(cache_hits_total[15m])) + sum(rate(cache_misses_total[15m]))) < 0.50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 50%)"
```

#### High Rate Limit Hits
**Alert:** `HighRateLimitHits`  
**Condition:** Rate limit hits > 100 per minute for 5 minutes  
**Severity:** Warning

```yaml
      - alert: HighRateLimitHits
        expr: |
          sum(rate(rate_limited_total[5m])) > 100/60
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate limit hits"
          description: "Rate limit hits: {{ $value | humanize }} per second"
```

#### TTS Failure Rate
**Alert:** `TTSFailureRate`  
**Condition:** TTS failure rate > 5% for 10 minutes  
**Severity:** Warning

```yaml
      - alert: TTSFailureRate
        expr: |
          sum(tts_jobs_total{status="failure"}) / sum(tts_jobs_total) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High TTS failure rate"
          description: "TTS failure rate is {{ $value | humanizePercentage }}"
```

#### Video Render Failure Rate
**Alert:** `VideoRenderFailureRate`  
**Condition:** Video render failure rate > 5% for 10 minutes  
**Severity:** Warning

```yaml
      - alert: VideoRenderFailureRate
        expr: |
          sum(video_renders_total{status="failure"}) / sum(video_renders_total) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High video render failure rate"
          description: "Video render failure rate is {{ $value | humanizePercentage }}"
```

---

## Request ID Correlation

### Request ID Header

Every API response includes a `X-Request-ID` header for request correlation:

```bash
curl -v http://localhost:8000/v1/content/jobs
# Response headers:
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Request ID in Error Responses

Error responses include `request_id` in the JSON payload:

```json
{
  "detail": "Job not found",
  "status_code": 404,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Using Request ID for Debugging

**1. Find logs for a specific request:**
```bash
# Search logs by request ID
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/api.log
```

**2. Correlate metrics with logs:**
- Use request ID from error response
- Search logs for that request ID
- Find related metrics (if logged)

**3. Trace request flow:**
- Request ID is consistent across:
  - API logs
  - Error responses
  - Response headers
  - Database operations (if logged)

### Request ID Format

- **Format:** UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- **Generation:** Auto-generated if not provided in `X-Request-ID` header
- **Persistence:** Available throughout request lifecycle via context variables

---

## Best Practices

### ✅ DO

- ✅ Monitor error rates and latency continuously
- ✅ Set up alerts for critical metrics
- ✅ Use request IDs for debugging
- ✅ Track cache hit rates for optimization
- ✅ Monitor job failure rates by error type
- ✅ Correlate metrics with logs using request IDs

### ❌ DON'T

- ❌ Don't scrape metrics too frequently (< 5 seconds)
- ❌ Don't ignore high error rates
- ❌ Don't expose metrics endpoint publicly (use authentication)
- ❌ Don't store sensitive data in metric labels
- ❌ Don't create too many unique label combinations (cardinality explosion)

---

## Related Documentation

- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Health Checks](./health-checks-implementation.md) - Health endpoint documentation

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

