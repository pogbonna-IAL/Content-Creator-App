# Content Moderation Documentation

## Overview

Content moderation filters are implemented to reduce unsafe/low-quality outputs before deployment. The moderation system uses rules-based checks and optional open-source classifier integration.

## Architecture

### ModerationService

The `ModerationService` provides:
- **Rules-based checks**: Keyword filtering and PII detection
- **Optional classifier**: Open-source text safety classifier (feature-flagged)
- **Input moderation**: Runs before content generation
- **Output moderation**: Runs before saving artifacts

### Moderation Flow

1. **Input Moderation** (before generation):
   - Topic/narration text is checked for disallowed keywords
   - PII (emails, phone numbers, SSN, credit cards) detection
   - Optional classifier check (if enabled)

2. **Output Moderation** (before saving artifacts):
   - Generated content is checked for disallowed keywords
   - PII detection (stricter than input)
   - Optional classifier check (if enabled)

## Configuration

### Environment Variables

```bash
# Enable/disable content moderation (default: true)
ENABLE_CONTENT_MODERATION=true

# Enable optional classifier (default: false)
ENABLE_CONTENT_MODERATION_CLASSIFIER=false

# Custom disallowed keywords (comma-separated, optional)
MODERATION_DISALLOWED_KEYWORDS=kill,murder,violence,hate,drug,illegal
```

### Default Disallowed Keywords

- **Violence**: kill, murder, violence, weapon, gun, bomb
- **Hate speech**: hate, discrimination, racism, sexism
- **Illegal activities**: drug, illegal, fraud, scam
- **Adult content**: explicit, porn, adult

## Moderation Results

### ModerationResult

```python
{
    "passed": bool,
    "reason_code": "disallowed_content" | "pii_detected" | "classifier_blocked" | null,
    "details": {
        "keyword": str,  # If disallowed_content
        "pii_types": [{"type": str, "count": int}],  # If pii_detected
        "content_type": str,  # For output moderation
        ...
    }
}
```

### Reason Codes

- `disallowed_content`: Disallowed keyword detected
- `pii_detected`: PII (email, phone, SSN, credit card) detected
- `classifier_blocked`: Classifier flagged content as unsafe
- `toxic_content`: Toxic content detected (classifier)
- `spam`: Spam detected (classifier)

## API Behavior

### Input Moderation

**Endpoint:** `POST /v1/content/generate`

If input is blocked:
- Returns `403 Forbidden` with `CONTENT_BLOCKED` error code
- Job is not created
- Error response includes `reason_code` and `details`

**Example Error Response:**
```json
{
    "code": "CONTENT_BLOCKED",
    "message": "Content moderation failed: disallowed_content",
    "status_code": 403,
    "request_id": "abc123",
    "details": {
        "reason_code": "disallowed_content",
        "keyword": "violence",
        "matched_text": "Topic about violence..."
    }
}
```

### Output Moderation

**Behavior:**
- If output is blocked:
  - Artifact is **not created**
  - SSE event `moderation_blocked` is sent
  - Job continues (other artifacts may still be created)
- If output passes:
  - SSE event `moderation_passed` is sent
  - Artifact is created normally

## SSE Events

### moderation_passed

**Event:** `moderation_passed`

**Data:**
```json
{
    "job_id": 123,
    "artifact_type": "blog"
}
```

### moderation_blocked

**Event:** `moderation_blocked`

**Data:**
```json
{
    "job_id": 123,
    "artifact_type": "blog",
    "reason_code": "disallowed_content",
    "details": {
        "keyword": "violence",
        "content_type": "blog",
        "matched_text": "..."
    }
}
```

## PII Detection

### Detected Patterns

- **Email**: `user@example.com`
- **Phone**: `123-456-7890` (US format)
- **SSN**: `123-45-6789` (US format)
- **Credit Card**: `1234-5678-9012-3456` (basic pattern)

### PII Detection Behavior

- **Input**: Blocks if PII detected
- **Output**: Blocks if PII detected (stricter enforcement)

## Classifier Integration (Optional)

### Feature Flag

Set `ENABLE_CONTENT_MODERATION_CLASSIFIER=true` to enable classifier.

### Implementation

The classifier integration is designed to use open-source models via the `transformers` library:

```python
# Example integration (not yet implemented)
from transformers import pipeline
classifier = pipeline("text-classification", model="unitary/toxic-bert")
```

### Future Enhancement

To add classifier support:
1. Install dependencies: `pip install transformers torch`
2. Set `ENABLE_CONTENT_MODERATION_CLASSIFIER=true`
3. Update `ModerationService._initialize_classifier()` to load model
4. Update `ModerationService._run_classifier()` to use model

## Usage Examples

### Check Input Before Generation

```python
from content_creation_crew.services.moderation_service import get_moderation_service

moderation_service = get_moderation_service()
result = moderation_service.moderate_input(
    "Topic about AI and machine learning",
    context={"user_id": 123, "plan": "pro"}
)

if not result.passed:
    # Handle blocked content
    print(f"Blocked: {result.reason_code}")
```

### Check Output Before Saving

```python
result = moderation_service.moderate_output(
    generated_content,
    "blog",
    context={"job_id": 456, "user_id": 123}
)

if not result.passed:
    # Skip artifact creation
    logger.warning(f"Content blocked: {result.reason_code}")
```

## Testing

### Test Moderation Service

```python
import pytest
from content_creation_crew.services.moderation_service import ModerationService

def test_disallowed_keyword():
    service = ModerationService()
    result = service.moderate_input("This is about violence and weapons")
    assert not result.passed
    assert result.reason_code == ModerationReason.DISALLOWED_CONTENT

def test_pii_detection():
    service = ModerationService()
    result = service.moderate_input("Contact me at user@example.com")
    assert not result.passed
    assert result.reason_code == ModerationReason.PII_DETECTED

def test_safe_content():
    service = ModerationService()
    result = service.moderate_input("This is a safe topic about AI")
    assert result.passed
```

## Monitoring

### Metrics

Moderation events are logged with:
- `reason_code`: Reason for blocking
- `content_type`: Type of content moderated
- `user_id`: User who generated content

### Logs

Moderation events are logged at `WARNING` level:
```
WARNING: Input blocked: disallowed keyword 'violence' detected
WARNING: Output blocked: PII detected in blog: [{'type': 'email', 'count': 1}]
```

## Best Practices

1. **Customize Keywords**: Update `MODERATION_DISALLOWED_KEYWORDS` for your use case
2. **Enable Classifier**: For production, consider enabling classifier for better detection
3. **Monitor Blocked Content**: Review logs to understand what content is being blocked
4. **Adjust Strictness**: Modify keyword lists and PII patterns based on your needs

## Related Documentation

- [Error Responses](./error-responses.md) - Error response format
- [SSE Events](./api.md) - Server-Sent Events documentation
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

