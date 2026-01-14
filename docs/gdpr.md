# GDPR Compliance Documentation

**Last Updated:** January 13, 2026  
**Schema Version:** 1.0

---

## Overview

This document describes the GDPR-compliant data export and deletion functionality implemented in the Content Creation Crew API.

### GDPR Rights Implemented

1. **Article 20 - Right to Data Portability** ✅
   - Users can export all their data in machine-readable format (JSON)
   - Endpoints: `GET /api/user/export`, `GET /v1/user/export`

2. **Article 17 - Right to Erasure (Right to be Forgotten)** ✅
   - Users can request account deletion
   - Endpoints: `DELETE /api/user/delete`, `DELETE /v1/user/delete`

---

## Data Export

### Endpoints

- `GET /api/user/export` (legacy compatibility)
- `GET /v1/user/export` (preferred)

**Authentication:** Required (Bearer token or HTTPOnly cookie)

### Export Format

The export returns a JSON object with the following structure:

```json
{
  "schema_version": "1.0",
  "export_date": "2026-01-13T10:30:00Z",
  "user_id": 123,
  "profile": {
    "id": 123,
    "email": "user@example.com",
    "full_name": "John Doe",
    "provider": "email",
    "is_active": true,
    "is_verified": true,
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2026-01-10T15:30:00Z"
  },
  "memberships": [
    {
      "org_id": 1,
      "role": "owner",
      "created_at": "2025-10-01T10:05:00Z"
    }
  ],
  "organizations": [
    {
      "id": 1,
      "name": "My Organization",
      "owner_user_id": 123,
      "is_owner": true,
      "created_at": "2025-10-01T10:05:00Z"
    }
  ],
  "subscriptions": [
    {
      "id": 1,
      "org_id": 1,
      "plan": "pro",
      "status": "active",
      "provider": "stripe",
      "current_period_end": "2026-02-01T00:00:00Z",
      "created_at": "2025-10-01T10:10:00Z"
    }
  ],
  "usage": [
    {
      "org_id": 1,
      "period_month": "2026-01",
      "blog_count": 15,
      "social_count": 30,
      "audio_count": 5,
      "video_count": 3,
      "voiceover_count": 5,
      "video_render_count": 3
    }
  ],
  "billing_events": [
    {
      "id": 1,
      "org_id": 1,
      "provider": "stripe",
      "event_type": "payment_succeeded",
      "created_at": "2025-10-15T10:00:00Z",
      "metadata": {
        "event_id": "evt_123",
        "type": "payment_succeeded"
      }
    }
  ],
  "content_jobs": [
    {
      "id": 101,
      "org_id": 1,
      "topic": "Introduction to AI",
      "formats_requested": ["blog", "social"],
      "status": "completed",
      "created_at": "2026-01-10T09:00:00Z",
      "finished_at": "2026-01-10T09:05:00Z",
      "artifact_count": 2
    }
  ],
  "artifact_references": [
    {
      "id": 201,
      "job_id": 101,
      "type": "blog",
      "model_used": "ollama/llama3.1:8b",
      "created_at": "2026-01-10T09:05:00Z",
      "has_text": true,
      "text_preview": "## Introduction to AI\n\nArtificial intelligence is..."
    },
    {
      "id": 202,
      "job_id": 101,
      "type": "voiceover_audio",
      "model_used": "piper",
      "created_at": "2026-01-10T09:10:00Z",
      "metadata": {
        "storage_key": "voiceovers/abc123.wav",
        "format": "wav",
        "duration_sec": 120.5
      }
    }
  ],
  "statistics": {
    "total_jobs": 50,
    "total_artifacts": 125,
    "artifacts_by_type": {
      "blog": 50,
      "social": 40,
      "audio_script": 20,
      "voiceover_audio": 10,
      "video_script": 5
    },
    "jobs_by_status": {
      "completed": 48,
      "failed": 2
    }
  }
}
```

### What's Included

- **Profile Data:** Email, name, account status, provider info
- **Memberships:** All organization memberships
- **Organizations:** Organizations where user is a member
- **Subscriptions:** Subscription history
- **Usage Stats:** Monthly usage counters
- **Billing Events:** Anonymized billing event history (payment confirmations, etc.)
- **Content Jobs:** All content generation jobs
- **Artifact References:** Metadata for all generated artifacts
  - For text artifacts: preview of content
  - For media artifacts: storage keys and metadata (duration, format, etc.)
  - **Note:** Large binary files are NOT included in export; only references/metadata

### What's NOT Included

- **Large Binary Files:** Audio/video files are referenced by storage key, not embedded
- **Other Users' Data:** Only data the authenticated user owns or has access to
- **Sensitive Payment Info:** Full payment details (card numbers, etc.) are not exported

---

## Account Deletion

### Endpoints

- `DELETE /api/user/delete?hard_delete=false` (legacy compatibility)
- `DELETE /v1/user/delete?hard_delete=false` (preferred)

**Authentication:** Required (Bearer token or HTTPOnly cookie)

### Deletion Types

#### 1. Soft Delete (Default)

**Query Parameter:** `hard_delete=false` (or omit)

**What Happens:**
- ✅ Account disabled immediately (cannot login)
- ✅ All sessions revoked
- ✅ Auth tokens invalidated
- ✅ Data retained for grace period (default: 30 days)
- ✅ User can request restoration by contacting support within grace period
- ✅ Hard delete automatically scheduled after grace period

**Response:**
```json
{
  "status": "deleted",
  "deletion_type": "soft",
  "deleted_at": "2026-01-13T10:30:00Z",
  "hard_delete_scheduled": "2026-02-12T10:30:00Z",
  "grace_period_days": 30,
  "message": "Your account has been disabled. All data will be permanently deleted on 2026-02-12. Contact support to restore your account before then."
}
```

#### 2. Hard Delete (Permanent)

**Query Parameter:** `hard_delete=true`

**What Happens:**
- ✅ Account permanently deleted immediately
- ✅ All sessions revoked
- ✅ Content jobs deleted
- ✅ Artifacts deleted (database records and storage files)
- ✅ Memberships removed
- ✅ Organizations handled based on ownership:
  - **Sole owner with no other members:** Organization and all data deleted
  - **Owner with other members:** Ownership transferred to another admin/member
  - **Member only:** Membership removed, organization remains
- ✅ Billing events anonymized (kept for audit, PII removed)
- ✅ Usage counters deleted (if sole organization member)
- ⚠️ **CANNOT BE UNDONE**

**Response:**
```json
{
  "status": "permanently_deleted",
  "deletion_type": "hard",
  "deleted_at": "2026-01-13T10:30:00Z",
  "message": "Your account and all associated data have been permanently deleted."
}
```

### What Gets Deleted

| Data Type | Soft Delete | Hard Delete |
|-----------|-------------|-------------|
| User profile | Marked as deleted | ✅ Deleted |
| Sessions | ✅ Revoked | ✅ Deleted |
| Content jobs | Retained | ✅ Deleted |
| Artifacts | Retained | ✅ Deleted |
| Storage files | Retained | ✅ Deleted |
| Memberships | Retained | ✅ Deleted |
| Organizations (if sole owner) | Retained | ✅ Deleted |
| Usage counters | Retained | ✅ Deleted |
| Billing events | Retained | Anonymized (kept for audit) |

### Data Retention for Audit

Certain data is retained for legal/audit purposes even after hard delete:

- **Billing Events:** Anonymized and kept (org_id removed, only event type/date retained)
- **Audit Logs:** Transaction logs may be retained for compliance (when implemented)

**Retention Period:** Typically 1-2 years for financial audit compliance

---

## Grace Period Configuration

The soft delete grace period is configurable via environment variable:

```bash
GDPR_DELETION_GRACE_DAYS=30  # Default: 30 days
```

**Recommended Values:**
- **Development:** 7 days
- **Production:** 30 days (standard)
- **Enterprise:** Configurable per contract

---

## Automated Hard Delete

A scheduled job should be implemented to automatically execute hard deletes for accounts past the grace period:

```bash
# Run daily
python scripts/gdpr_cleanup.py
```

**Recommended Schedule:** Once daily at off-peak hours

---

## Security Considerations

### Authentication

- Both export and delete endpoints require valid authentication
- Endpoints validate that the user is requesting their own data

### Authorization

- Users can only export/delete their own data
- Organization owners can export organization data (future enhancement)
- No cross-user data access

### Audit Trail

All GDPR operations should be logged:

- **Data Export:** User ID, timestamp, IP address
- **Soft Delete:** User ID, timestamp, scheduled hard delete date
- **Hard Delete:** User ID, timestamp, data deleted summary

**TODO:** Implement audit logging service (see QA Security Audit Report)

---

## API Examples

### Export User Data

```bash
# Using Bearer token
curl -X GET "https://api.example.com/v1/user/export" \
  -H "Authorization: Bearer <token>"

# Using HTTPOnly cookies (browser)
fetch('https://api.example.com/v1/user/export', {
  method: 'GET',
  credentials: 'include'
})
.then(res => res.json())
.then(data => {
  // Save to file or display
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `user-data-export-${Date.now()}.json`;
  a.click();
});
```

### Soft Delete Account

```bash
curl -X DELETE "https://api.example.com/v1/user/delete" \
  -H "Authorization: Bearer <token>"
```

### Hard Delete Account

```bash
curl -X DELETE "https://api.example.com/v1/user/delete?hard_delete=true" \
  -H "Authorization: Bearer <token>"
```

---

## Restoration Process (Soft Delete Only)

If a user requests account restoration within the grace period:

1. User contacts support with email/account details
2. Support verifies identity
3. Support reactivates account:

```python
# In Django shell or admin panel
user = User.objects.get(email="user@example.com")
user.deleted_at = None
user.is_active = True
user.save()
```

4. User can login normally

**Note:** Hard deletes CANNOT be restored

---

## Compliance Checklist

- [x] Right to Data Portability (GDPR Article 20)
- [x] Right to Erasure (GDPR Article 17)
- [ ] Consent Management (GDPR Article 6) - **TODO**
- [ ] Privacy Policy - **TODO**
- [ ] Data Processing Agreements - **TODO**
- [ ] Breach Notification Procedures - **TODO**
- [ ] Audit Logging - **TODO**

---

## Future Enhancements

1. **ZIP Export:** Include binary files in export (optional)
2. **Scheduled Exports:** Allow users to schedule regular exports
3. **Organization Export:** Allow org owners to export all org data
4. **Restoration API:** Self-service restoration within grace period
5. **Audit Logging:** Track all GDPR operations
6. **Email Notifications:** Notify users before hard delete
7. **Consent Management:** Track user consents for data processing

---

## Support Contact

For questions about data export/deletion or account restoration:

- **Email:** support@example.com
- **Response Time:** Within 24 hours
- **Restoration Window:** 30 days after soft delete

---

**Document Version:** 1.0  
**Last Reviewed:** January 13, 2026  
**Next Review:** Quarterly (April 2026)

