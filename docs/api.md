# Content Creation Crew API Documentation

## Overview

Content Creation Crew provides a RESTful API for AI-powered content generation. This document describes authentication, key endpoints, and usage patterns.

## Table of Contents

1. [Authentication](#authentication)
2. [Base URL](#base-url)
3. [Key Endpoints](#key-endpoints)
4. [SSE Usage Patterns](#sse-usage-patterns)
5. [Error Handling](#error-handling)
6. [Rate Limits](#rate-limits)
7. [Examples](#examples)

---

## Authentication

### Method

All endpoints (except `/health`, `/meta`, `/metrics`) require **Bearer token authentication**.

### Obtaining a Token

**1. Sign Up:**
```bash
POST /v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "John Doe"
}
```

**2. Log In:**
```bash
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Expiration

Tokens expire after 24 hours. Refresh by logging in again.

---

## Base URL

**Development:** `http://localhost:8000`  
**Production:** `https://api.contentcreationcrew.com`

All endpoints are prefixed with `/v1` (e.g., `/v1/content/generate`).

---

## Key Endpoints

### Content Generation

#### Create Generation Job

**Endpoint:** `POST /v1/content/generate`

**Request:**
```json
{
  "topic": "Introduction to AI",
  "content_types": ["blog", "social"],
  "idempotency_key": "optional-unique-key"
}
```

**Response (201):**
```json
{
  "id": 123,
  "topic": "Introduction to AI",
  "formats_requested": ["blog", "social"],
  "status": "pending",
  "idempotency_key": "optional-unique-key",
  "created_at": "2026-01-13T10:30:00Z",
  "started_at": null,
  "finished_at": null,
  "artifacts": []
}
```

**Content Types:**
- `blog`: Blog post content
- `social`: Social media posts
- `audio`: Audio script/narration
- `video`: Video script

#### Get Job Details

**Endpoint:** `GET /v1/content/jobs/{job_id}`

**Response (200):**
```json
{
  "id": 123,
  "topic": "Introduction to AI",
  "formats_requested": ["blog", "social"],
  "status": "completed",
  "created_at": "2026-01-13T10:30:00Z",
  "started_at": "2026-01-13T10:30:05Z",
  "finished_at": "2026-01-13T10:35:00Z",
  "artifacts": [
    {
      "id": 1,
      "type": "blog",
      "created_at": "2026-01-13T10:35:00Z",
      "has_content": true
    }
  ]
}
```

#### List Jobs

**Endpoint:** `GET /v1/content/jobs?status=completed&limit=50&offset=0`

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `running`, `completed`, `failed`, `cancelled`)
- `limit` (optional): Number of results (1-100, default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response (200):**
```json
{
  "jobs": [...],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### Voice Generation (TTS)

#### Generate Voiceover

**Endpoint:** `POST /v1/content/voiceover`

**Request:**
```json
{
  "job_id": 123,
  "voice_id": "default",
  "speed": 1.0,
  "format": "wav"
}
```

**Alternative (standalone):**
```json
{
  "narration_text": "This is the narration text...",
  "voice_id": "default",
  "speed": 1.0,
  "format": "wav"
}
```

**Response (202):**
```json
{
  "job_id": 123,
  "status": "processing",
  "message": "Voiceover generation started"
}
```

**Progress:** Track via SSE stream at `/v1/content/jobs/{job_id}/stream`

### Video Rendering

#### Render Video

**Endpoint:** `POST /v1/content/video/render`

**Request:**
```json
{
  "job_id": 123,
  "resolution": [1920, 1080],
  "fps": 30,
  "background_type": "solid",
  "background_color": "#000000",
  "include_narration": true,
  "renderer": "baseline"
}
```

**Response (202):**
```json
{
  "job_id": 123,
  "status": "processing",
  "message": "Video rendering started"
}
```

**Progress:** Track via SSE stream at `/v1/content/jobs/{job_id}/stream`

---

## SSE Usage Patterns

### Overview

Server-Sent Events (SSE) provide real-time progress updates for long-running operations.

### Endpoint

**Endpoint:** `GET /v1/content/jobs/{job_id}/stream`

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Last-Event-ID: <event_id>` (optional, for reconnection)

### Event Types

#### Content Generation Events

- **`job_started`**: Job has started processing
- **`agent_progress`**: Progress update from an agent
- **`artifact_ready`**: An artifact has been generated
- **`complete`**: Job completed successfully
- **`error`**: Job failed

#### TTS Events

- **`tts_started`**: TTS generation started
- **`tts_progress`**: TTS generation progress
- **`tts_completed`**: TTS generation completed
- **`tts_failed`**: TTS generation failed

#### Video Rendering Events

- **`video_render_started`**: Video rendering started
- **`scene_started`**: Scene rendering started
- **`scene_completed`**: Scene rendering completed
- **`video_render_completed`**: Video rendering completed
- **`video_render_failed`**: Video rendering failed

### Event Format

```
id: 1
event: job_started
data: {"type":"job_started","job_id":123,"status":"running"}

id: 2
event: artifact_ready
data: {"type":"artifact_ready","job_id":123,"artifact_type":"blog"}

id: 3
event: complete
data: {"type":"complete","job_id":123,"artifacts":[...]}
```

### JavaScript Example

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/v1/content/jobs/${jobId}/stream`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

eventSource.addEventListener('job_started', (e) => {
  const data = JSON.parse(e.data);
  console.log('Job started:', data);
});

eventSource.addEventListener('artifact_ready', (e) => {
  const data = JSON.parse(e.data);
  console.log('Artifact ready:', data.artifact_type);
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Job completed:', data);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  console.error('SSE error:', e);
  eventSource.close();
});
```

### Reconnection

**Automatic Reconnection:**

SSE clients automatically reconnect on connection loss. Use `Last-Event-ID` header to replay missed events:

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/v1/content/jobs/${jobId}/stream`,
  {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Last-Event-ID': lastEventId  // Replay events after this ID
    }
  }
);
```

**Manual Reconnection:**

```javascript
let lastEventId = null;

eventSource.onmessage = (e) => {
  lastEventId = e.lastEventId;
  const data = JSON.parse(e.data);
  // Process event
};

eventSource.onerror = () => {
  // Reconnect with Last-Event-ID
  eventSource.close();
  setTimeout(() => {
    eventSource = new EventSource(
      `http://localhost:8000/v1/content/jobs/${jobId}/stream?last_event_id=${lastEventId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
  }, 1000);
};
```

### Python Example

```python
import requests
import json

def stream_job_progress(job_id, token):
    url = f"http://localhost:8000/v1/content/jobs/{job_id}/stream"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream"
    }
    
    with requests.get(url, headers=headers, stream=True) as response:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data = json.loads(line_str[6:])
                    print(f"Event: {data.get('type')}")
                    print(f"Data: {data}")
```

---

## Error Handling

### Error Response Format

**Standard Format (v1 endpoints):**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation error: topic: field required",
  "status_code": 422,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "errors": [...]
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTH_ERROR` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Access denied |
| `NOT_FOUND` | 404 | Resource not found |
| `PLAN_LIMIT_EXCEEDED` | 403 | Subscription plan limit exceeded |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Handling Errors

```javascript
try {
  const response = await fetch('/v1/content/generate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ topic: 'AI' })
  });
  
  if (!response.ok) {
    const error = await response.json();
    
    switch (error.code) {
      case 'VALIDATION_ERROR':
        // Show validation errors
        console.error('Validation errors:', error.details.errors);
        break;
      
      case 'PLAN_LIMIT_EXCEEDED':
        // Show upgrade prompt
        console.error('Plan limit exceeded:', error.message);
        break;
      
      case 'RATE_LIMITED':
        // Wait and retry
        const retryAfter = error.details.retry_after;
        await sleep(retryAfter * 1000);
        // Retry request
        break;
      
      default:
        console.error('Error:', error.message);
    }
  } else {
    const data = await response.json();
    // Process success
  }
} catch (error) {
  console.error('Request failed:', error);
}
```

---

## Rate Limits

Rate limits are applied per subscription tier. See `/docs/rate-limits.md` for details.

**Headers:**
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset-After`: Seconds until reset
- `Retry-After`: Seconds until retry

**Default Limits:**
- Free: 10 RPM (general), 10 RPM (generation)
- Basic: 30 RPM (general), 10 RPM (generation)
- Pro: 100 RPM (general), 10 RPM (generation)
- Enterprise: 500 RPM (general), 10 RPM (generation)

---

## Examples

### Complete Workflow

**1. Authenticate:**
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

**2. Create Generation Job:**
```bash
curl -X POST http://localhost:8000/v1/content/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Introduction to AI","content_types":["blog"]}'
```

**3. Stream Progress:**
```bash
curl -N http://localhost:8000/v1/content/jobs/123/stream \
  -H "Authorization: Bearer <token>" \
  -H "Accept: text/event-stream"
```

**4. Get Job Details:**
```bash
curl http://localhost:8000/v1/content/jobs/123 \
  -H "Authorization: Bearer <token>"
```

**5. Generate Voiceover:**
```bash
curl -X POST http://localhost:8000/v1/content/voiceover \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"job_id":123,"voice_id":"default"}'
```

**6. Render Video:**
```bash
curl -X POST http://localhost:8000/v1/content/video/render \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"job_id":123,"resolution":[1920,1080],"fps":30}'
```

---

## Related Documentation

- [OpenAPI Schema](./openapi.json) - Complete API schema
- [Error Responses](./error-responses.md) - Error handling guide
- [Rate Limits](./rate-limits.md) - Rate limiting details
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**API Version:** v1  
**Status:** ✅ Production Ready

