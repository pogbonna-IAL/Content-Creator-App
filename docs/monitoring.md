# Monitoring and Metrics Guide

## Overview

This document describes the Prometheus metrics available for monitoring expensive operations, performance bottlenecks, and cost drivers.

All metrics are exposed at the `/metrics` endpoint in Prometheus text format.

---

## Metrics Endpoint

**GET** `/metrics`

Returns all collected metrics in Prometheus text format.

**Example:**
```bash
curl http://localhost:8000/metrics
```

---

## LLM/Ollama Metrics

Track LLM API calls, costs, and performance.

### Counters

**`llm_calls_total{model}`**
- Total number of LLM API calls
- Labels:
  - `model`: Model name (e.g., "llama3.2:1b", "mistral:7b")
- Usage: Track API call volume per model

**`llm_failures_total{model}`**
- Total number of failed LLM API calls
- Labels:
  - `model`: Model name
- Usage: Monitor error rates

### Histograms

**`llm_call_seconds{model}`**
- Duration of LLM API calls in seconds
- Labels:
  - `model`: Model name
- Metrics:
  - `llm_call_seconds_count`: Total number of calls
  - `llm_call_seconds_sum`: Total duration of all calls
  - `llm_call_seconds{quantile="0.5"}`: p50 (median)
  - `llm_call_seconds{quantile="0.95"}`: p95
  - `llm_call_seconds{quantile="0.99"}`: p99
- Usage: Track latency, identify slow models

### Example Queries

```promql
# Average LLM call duration per model
rate(llm_call_seconds_sum[5m]) / rate(llm_call_seconds_count[5m])

# LLM error rate
rate(llm_failures_total[5m]) / rate(llm_calls_total[5m])

# p95 latency by model
llm_call_seconds{quantile="0.95"}
```

### Alert Examples

```yaml
- alert: HighLLMErrorRate
  expr: rate(llm_failures_total[5m]) / rate(llm_calls_total[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High LLM error rate: {{ $value | humanizePercentage }}"

- alert: SlowLLMCalls
  expr: llm_call_seconds{quantile="0.95"} > 60
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Slow LLM calls: p95 = {{ $value }}s"
```

---

## Storage Metrics

Track storage operations, bandwidth, and costs.

### Counters

**`storage_put_total{artifact_type}`**
- Total number of PUT operations
- Labels:
  - `artifact_type`: Type of artifact ("voiceover", "video_clip", "storyboard_image", "blog")
- Usage: Track storage write volume

**`storage_get_total{artifact_type}`**
- Total number of GET operations
- Labels:
  - `artifact_type`: Type of artifact
- Usage: Track storage read volume

**`storage_delete_total{artifact_type}`**
- Total number of DELETE operations
- Labels:
  - `artifact_type`: Type of artifact
- Usage: Track cleanup operations

**`storage_bytes_written_total{artifact_type}`**
- Total bytes written
- Labels:
  - `artifact_type`: Type of artifact
- Usage: Track storage costs, bandwidth

**`storage_bytes_read_total{artifact_type}`**
- Total bytes read
- Labels:
  - `artifact_type`: Type of artifact
- Usage: Track bandwidth costs

**`storage_failures_total{artifact_type, operation}`**
- Total number of failed storage operations
- Labels:
  - `artifact_type`: Type of artifact
  - `operation`: Operation type ("put", "get", "delete")
- Usage: Monitor storage reliability

### Example Queries

```promql
# Storage write rate (bytes/sec)
rate(storage_bytes_written_total[5m])

# Storage read rate (bytes/sec)
rate(storage_bytes_read_total[5m])

# Storage failure rate
rate(storage_failures_total[5m]) / (
  rate(storage_put_total[5m]) + 
  rate(storage_get_total[5m]) + 
  rate(storage_delete_total[5m])
)

# Total storage used (cumulative bytes written minus deleted)
storage_bytes_written_total - storage_bytes_deleted_total
```

### Alert Examples

```yaml
- alert: HighStorageFailureRate
  expr: rate(storage_failures_total[5m]) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High storage failure rate: {{ $value }} failures/sec"

- alert: HighStorageBandwidth
  expr: rate(storage_bytes_written_total[5m]) > 100000000  # 100MB/s
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High storage bandwidth: {{ $value | humanize }}B/s"
```

---

## Video Rendering Metrics

Track video rendering operations and performance (when enabled).

### Counters

**`video_renders_total{renderer}`**
- Total number of video render operations
- Labels:
  - `renderer`: Renderer name ("remotion", "ffmpeg", "manual")
- Usage: Track video generation volume

**`video_render_failures_total{renderer}`**
- Total number of failed renders
- Labels:
  - `renderer`: Renderer name
- Usage: Monitor render reliability

### Histograms

**`video_render_seconds{renderer}`**
- Duration of video render operations in seconds
- Labels:
  - `renderer`: Renderer name
- Metrics:
  - `video_render_seconds_count`: Total renders
  - `video_render_seconds_sum`: Total duration
  - `video_render_seconds{quantile="0.5"}`: p50
  - `video_render_seconds{quantile="0.95"}`: p95
  - `video_render_seconds{quantile="0.99"}`: p99
- Usage: Track render performance

### Example Queries

```promql
# Average render duration
rate(video_render_seconds_sum[5m]) / rate(video_render_seconds_count[5m])

# Render success rate
rate(video_renders_total[5m]) / (rate(video_renders_total[5m]) + rate(video_render_failures_total[5m]))

# p95 render time
video_render_seconds{quantile="0.95"}
```

### Alert Examples

```yaml
- alert: HighVideoRenderFailureRate
  expr: rate(video_render_failures_total[5m]) / rate(video_renders_total[5m]) > 0.2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High video render failure rate: {{ $value | humanizePercentage }}"

- alert: SlowVideoRenders
  expr: video_render_seconds{quantile="0.95"} > 300
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Slow video renders: p95 = {{ $value }}s"
```

---

## TTS (Text-to-Speech) Metrics

Track TTS operations and costs.

### Counters

**`tts_jobs_total{provider}`**
- Total number of TTS synthesis operations
- Labels:
  - `provider`: TTS provider ("elevenlabs", "gtts", "piper")
- Usage: Track TTS usage

**`tts_failures_total{provider}`**
- Total number of failed TTS operations
- Labels:
  - `provider`: TTS provider
- Usage: Monitor TTS reliability

### Histograms

**`tts_seconds{provider}`**
- Duration of TTS synthesis in seconds
- Labels:
  - `provider`: TTS provider
- Metrics:
  - `tts_seconds_count`: Total operations
  - `tts_seconds_sum`: Total duration
  - `tts_seconds{quantile="0.5"}`: p50
  - `tts_seconds{quantile="0.95"}`: p95
  - `tts_seconds{quantile="0.99"}`: p99
- Usage: Track TTS performance

### Example Queries

```promql
# TTS requests per second
rate(tts_jobs_total[5m])

# Average TTS duration
rate(tts_seconds_sum[5m]) / rate(tts_seconds_count[5m])

# TTS error rate by provider
rate(tts_failures_total[5m]) / rate(tts_jobs_total[5m])
```

### Alert Examples

```yaml
- alert: HighTTSErrorRate
  expr: rate(tts_failures_total[5m]) / rate(tts_jobs_total[5m]) > 0.15
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High TTS error rate for {{ $labels.provider }}: {{ $value | humanizePercentage }}"

- alert: SlowTTSSynthesis
  expr: tts_seconds{quantile="0.95"} > 30
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Slow TTS synthesis: p95 = {{ $value }}s"
```

---

## Retention/Cleanup Metrics

Track data retention cleanup operations.

### Counters

**`retention_deletes_total{plan}`**
- Total number of items deleted by retention policy
- Labels:
  - `plan`: Subscription plan ("free", "pro", "enterprise", "gdpr")
- Usage: Track cleanup operations

**`retention_bytes_freed_total{plan}`**
- Total bytes freed by retention cleanup
- Labels:
  - `plan`: Subscription plan
- Usage: Track storage recovery

**`retention_cleanup_runs_total`**
- Total number of cleanup job runs
- Usage: Monitor job execution

**`retention_cleanup_items_total`**
- Total items cleaned across all runs
- Usage: Track overall cleanup volume

**`retention_cleanup_bytes_total`**
- Total bytes freed across all runs
- Usage: Track overall storage recovery

### Histograms

**`retention_cleanup_seconds`**
- Duration of cleanup job runs in seconds
- Usage: Monitor job performance

### Example Queries

```promql
# Cleanup rate (items/day)
rate(retention_deletes_total[24h]) * 86400

# Storage freed per day
rate(retention_bytes_freed_total[24h]) * 86400

# Average cleanup duration
retention_cleanup_seconds_sum / retention_cleanup_seconds_count
```

### Alert Examples

```yaml
- alert: RetentionCleanupFailed
  expr: rate(retention_cleanup_runs_total[24h]) == 0
  for: 25h
  labels:
    severity: warning
  annotations:
    summary: "Retention cleanup job hasn't run in 24+ hours"

- alert: LowStorageRecovery
  expr: rate(retention_bytes_freed_total[24h]) < 1000000000  # < 1GB/day
  for: 1d
  labels:
    severity: info
  annotations:
    summary: "Low storage recovery: {{ $value | humanize }}B/day"
```

---

## Cost Analysis

Use these metrics to analyze operational costs:

### LLM Costs

```promql
# Estimate LLM costs (assuming $0.10 per 1M tokens, ~750 tokens/call)
llm_calls_total * 750 * 0.0000001
```

### Storage Costs

```promql
# S3 storage costs (assuming $0.023/GB/month)
(storage_bytes_written_total - storage_bytes_deleted_total) / 1073741824 * 0.023

# S3 bandwidth costs (assuming $0.09/GB egress)
storage_bytes_read_total / 1073741824 * 0.09
```

### TTS Costs

```promql
# TTS costs (provider-specific, example for ElevenLabs)
tts_jobs_total{provider="elevenlabs"} * 0.30  # $0.30 per 1000 characters
```

---

## Grafana Dashboard

### Recommended Panels

**1. LLM Performance**
- Graph: `llm_calls_total` by model
- Graph: `llm_call_seconds{quantile="0.95"}` by model
- Stat: Error rate

**2. Storage Usage**
- Graph: `storage_bytes_written_total` rate
- Graph: `storage_bytes_read_total` rate
- Stat: Total storage used
- Stat: Failure rate

**3. Content Generation**
- Graph: `tts_jobs_total` rate
- Graph: `video_renders_total` rate
- Stat: Success rates

**4. Costs**
- Stat: Estimated LLM costs/day
- Stat: Storage costs/month
- Stat: Bandwidth costs/day

**5. Retention**
- Graph: `retention_bytes_freed_total` rate
- Graph: `retention_deletes_total` by plan
- Stat: Last cleanup run

### Dashboard JSON

Example Grafana dashboard configuration:

```json
{
  "dashboard": {
    "title": "Content Creation Crew - Operations",
    "panels": [
      {
        "title": "LLM Calls/sec",
        "targets": [
          {
            "expr": "rate(llm_calls_total[5m])"
          }
        ]
      },
      {
        "title": "Storage Write Rate",
        "targets": [
          {
            "expr": "rate(storage_bytes_written_total[5m])"
          }
        ]
      }
    ]
  }
}
```

---

## Best Practices

### 1. Set Up Alerts

Configure alerts for:
- High error rates (> 10%)
- Slow operations (p95 > threshold)
- Failed cleanup jobs
- High costs

### 2. Monitor Trends

Track weekly/monthly trends:
- LLM call volume
- Storage growth
- Cost increases
- Performance degradation

### 3. Capacity Planning

Use metrics to plan:
- When to scale LLM infrastructure
- Storage capacity needs
- Cost budget allocation

### 4. Performance Optimization

Identify optimization opportunities:
- Slow models to replace
- Inefficient storage patterns
- Retry storms
- Cache miss rates

---

## Troubleshooting

### High LLM Latency

1. Check `llm_call_seconds{quantile="0.99"}`
2. Identify slow models
3. Consider:
   - Switching to faster models
   - Increasing timeouts
   - Load balancing across instances

### Storage Failures

1. Check `storage_failures_total` by operation
2. Check storage provider health
3. Verify credentials and permissions
4. Check disk space (local) or quotas (S3)

### High Costs

1. Analyze cost breakdown:
   - LLM: `llm_calls_total` by model
   - Storage: `storage_bytes_written_total`
   - TTS: `tts_jobs_total` by provider
2. Identify cost drivers
3. Optimize:
   - Use cheaper models when possible
   - Implement caching
   - Enable retention policies
   - Compress artifacts

---

## Related Documentation

- [Prompt S7: Database Pool Monitoring](./PROMPT-S7-COMPLETE.md)
- [Prompt M5: Health Check System](./PROMPT-M5-COMPLETE.md)
- [Security Metrics](./security.md#metrics)
- [Performance Tuning](./performance.md)

---

## Metrics Reference

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_calls_total` | Counter | `model` | Total LLM API calls |
| `llm_failures_total` | Counter | `model` | Failed LLM calls |
| `llm_call_seconds` | Histogram | `model` | LLM call duration |
| `storage_put_total` | Counter | `artifact_type` | Storage PUT operations |
| `storage_get_total` | Counter | `artifact_type` | Storage GET operations |
| `storage_delete_total` | Counter | `artifact_type` | Storage DELETE operations |
| `storage_bytes_written_total` | Counter | `artifact_type` | Bytes written |
| `storage_bytes_read_total` | Counter | `artifact_type` | Bytes read |
| `storage_failures_total` | Counter | `artifact_type`, `operation` | Storage failures |
| `video_renders_total` | Counter | `renderer` | Video renders |
| `video_render_failures_total` | Counter | `renderer` | Failed renders |
| `video_render_seconds` | Histogram | `renderer` | Render duration |
| `tts_jobs_total` | Counter | `provider` | TTS operations |
| `tts_failures_total` | Counter | `provider` | Failed TTS operations |
| `tts_seconds` | Histogram | `provider` | TTS duration |
| `retention_deletes_total` | Counter | `plan` | Items deleted |
| `retention_bytes_freed_total` | Counter | `plan` | Bytes freed |
| `retention_cleanup_seconds` | Histogram | - | Cleanup duration |

---

**Last Updated:** 2026-01-14  
**Version:** 1.0.0 (M7)
