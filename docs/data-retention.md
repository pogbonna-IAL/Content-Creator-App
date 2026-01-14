# Data Retention Policy

**Last Updated:** January 13, 2026  
**Version:** 1.0  
**Review Period:** Quarterly

---

## Overview

This document defines what data is retained, what is deleted, and the timelines for data lifecycle management in compliance with GDPR and other data protection regulations.

---

## Data Lifecycle

### Active Users

**Data Retained:**
- ✅ User profile (email, name, provider info)
- ✅ Authentication sessions
- ✅ Organization memberships
- ✅ Subscriptions
- ✅ Usage counters
- ✅ Content generation jobs
- ✅ Generated artifacts (text, audio, video)
- ✅ Storage files
- ✅ Billing events

**Retention Period:** Indefinite (while account is active)

---

## Soft Delete (Account Disabled)

When a user requests account deletion via `/api/user/delete` or `/v1/user/delete` (without `hard_delete=true`):

### Immediately Upon Soft Delete

**Actions Taken:**
- ✅ `deleted_at` timestamp set
- ✅ `is_active` set to `false`
- ✅ All sessions invalidated/deleted
- ✅ Authentication disabled (cannot login)
- ✅ API access disabled

**Data Retained:**
- ✅ User profile
- ✅ Organization data
- ✅ Content jobs and artifacts
- ✅ Storage files
- ✅ Billing events
- ✅ Usage counters

### Grace Period

**Duration:** 30 days (configurable via `GDPR_DELETION_GRACE_DAYS`)

**Purpose:**
- Allow users to change their mind
- Provide time for support to assist with restoration
- Ensure no accidental data loss

**Restoration:**
- Users can contact support within grace period
- Support can restore account by setting `deleted_at = NULL` and `is_active = TRUE`
- All data remains intact

---

## Hard Delete (Permanent Deletion)

Hard delete occurs in two scenarios:
1. **After grace period:** Automated cleanup job processes accounts past retention window
2. **Immediate request:** User explicitly requests `hard_delete=true`

### What Gets Deleted

#### 1. User Profile
- ❌ **DELETED:** User record (ID, email, name, password hash)
- ✅ **Method:** `purge_user(user_id)`

#### 2. Authentication & Sessions
- ❌ **DELETED:** All sessions and tokens
- ✅ **Method:** `purge_sessions(user_id)`

#### 3. Content Generation Data
- ❌ **DELETED:** All content jobs
- ❌ **DELETED:** All content artifacts (database records)
- ❌ **DELETED:** All generated files (storage)
  - Audio files (voiceovers)
  - Video files (rendered videos)
  - Storyboard images
  - Video clips
- ✅ **Method:** `purge_user_artifacts(user_id)`

#### 4. Organization Data

**If User is Sole Owner:**
- ❌ **DELETED:** Organization record
- ❌ **DELETED:** Subscriptions
- ❌ **DELETED:** Usage counters
- ❌ **DELETED:** Memberships

**If Organization Has Other Members:**
- ✅ **TRANSFERRED:** Ownership to another admin/member
- ✅ **RETAINED:** Organization data (belongs to organization)
- ❌ **DELETED:** User's membership only

**If User is Member Only:**
- ❌ **DELETED:** Membership record only
- ✅ **RETAINED:** Organization data (not owned by user)

#### 5. Billing Events

**Action:** **ANONYMIZED** (not deleted)

**Why:** Legal requirement for financial audit (typically 1-2 years)

**Anonymization:**
- ❌ `org_id` set to `NULL`
- ✅ Event type and date retained
- ✅ Provider event ID retained
- ❌ Payment details removed

**Example:**
```json
// Before
{
  "id": 123,
  "org_id": 456,
  "provider": "stripe",
  "event_type": "payment_succeeded",
  "provider_event_id": "evt_abc123"
}

// After anonymization
{
  "id": 123,
  "org_id": null,  // Removed
  "provider": "stripe",
  "event_type": "payment_succeeded",
  "provider_event_id": "evt_abc123"
}
```

#### 6. Audit Logs (Future)

**Action:** **ANONYMIZED** (not deleted)

**Why:** Security audit requirements

**Anonymization:**
- ❌ User ID replaced with anonymized hash
- ❌ Email redacted
- ❌ IP address anonymized (last octet masked)
- ✅ Event type and timestamp retained
- ✅ Security-relevant actions retained (login attempts, permission changes)

**Note:** Audit log table not yet implemented. When implemented, retention period will be 1-2 years.

---

## Retention Timelines

| Data Type | Active User | Soft Delete | Hard Delete | After Hard Delete |
|-----------|-------------|-------------|-------------|-------------------|
| User Profile | ✅ Retained | ✅ Retained | ❌ Deleted | N/A |
| Sessions | ✅ Active | ❌ Revoked | ❌ Deleted | N/A |
| Content Jobs | ✅ Retained | ✅ Retained | ❌ Deleted | N/A |
| Artifacts | ✅ Retained | ✅ Retained | ❌ Deleted | N/A |
| Storage Files | ✅ Retained | ✅ Retained | ❌ Deleted | N/A |
| Organizations (owned) | ✅ Retained | ✅ Retained | ❌ Deleted or Transferred | N/A |
| Memberships | ✅ Retained | ✅ Retained | ❌ Deleted | N/A |
| Billing Events | ✅ Retained | ✅ Retained | ✅ Anonymized | 1-2 years |
| Audit Logs (future) | ✅ Retained | ✅ Retained | ✅ Anonymized | 1-2 years |

---

## Automated Cleanup

### Cleanup Job

**Script:** `scripts/gdpr_cleanup.py`  
**Frequency:** Daily at 2 AM (recommended)  
**Process:**
1. Find users with `deleted_at` older than grace period
2. Execute hard delete for each user
3. Log results (with redacted emails)
4. Report success/failure

### Cron Configuration

```bash
# Run daily at 2 AM
0 2 * * * cd /app && python scripts/gdpr_cleanup.py >> /var/log/gdpr_cleanup.log 2>&1
```

### APScheduler Configuration (Alternative)

For containerized deployments or when cron is not available:

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_gdpr_cleanup,
    trigger='cron',
    hour=2,
    minute=0,
    id='gdpr_cleanup',
    replace_existing=True
)
scheduler.start()
```

### Safety Features

- ✅ **Dry-run mode:** Test without deleting
- ✅ **Idempotent:** Safe to run multiple times
- ✅ **Transaction safety:** Rollback on error
- ✅ **Retry logic:** 3 attempts with exponential backoff
- ✅ **Logging:** Comprehensive audit trail (emails redacted)

---

## Storage Management

### Storage Retention by Tier

| Tier | Retention Period | Action After Period |
|------|------------------|---------------------|
| Free | 30 days | Auto-delete old artifacts |
| Basic | 90 days | Auto-delete old artifacts |
| Pro | 365 days | Auto-delete old artifacts |
| Enterprise | Unlimited | Never auto-delete |

**Note:** Retention only applies to *active* users. Deleted users have all data removed after grace period regardless of tier.

### Storage Cleanup Job (Future Enhancement)

**Purpose:** Delete old artifacts for active users based on tier retention

**Implementation:** TODO - Create separate cleanup job

```python
# Pseudocode
for tier in ['free', 'basic', 'pro']:
    retention_days = get_retention_days(tier)
    cutoff_date = now() - timedelta(days=retention_days)
    
    # Find old artifacts
    old_artifacts = find_artifacts_older_than(cutoff_date, tier)
    
    # Delete storage files
    for artifact in old_artifacts:
        delete_storage_file(artifact.storage_key)
        delete_artifact_record(artifact)
```

---

## Compliance Requirements

### GDPR

- ✅ **Article 17 (Right to Erasure):** Users can request deletion
- ✅ **Article 5 (Data Minimization):** Only necessary data retained
- ✅ **Article 5 (Storage Limitation):** Time-limited retention
- ✅ **Article 30 (Records):** Documented retention policy

### Financial Regulations

- ✅ **Payment Data:** Anonymized billing events retained for 1-2 years
- ✅ **Audit Trail:** Financial transactions kept for compliance
- ✅ **Sarbanes-Oxley (if applicable):** 7-year retention for financial records

### Security Best Practices

- ✅ **Audit Logs:** Security events retained for incident investigation
- ✅ **Access Logs:** Anonymized after user deletion
- ✅ **Backup Data:** Deleted in backups after retention period

---

## Backup Retention

### Database Backups

**Frequency:** Daily  
**Retention:**
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

**GDPR Compliance:**
- Deleted user data purged from backups after grace period
- Option 1: Restore to new DB, delete users, re-backup
- Option 2: Note deleted users and exclude from restores

### Storage Backups

**Frequency:** Daily (if using S3 with versioning)  
**Retention:** Follows main storage retention policy

---

## Data Export Before Deletion

Users should be encouraged to export their data before requesting deletion:

**Recommended Flow:**
1. User requests account deletion
2. System offers data export first
3. User downloads export (JSON format)
4. User confirms deletion
5. Soft delete executed (30-day grace period)
6. Hard delete after grace period

**Implementation:** Frontend should show warning and export button before deletion.

---

## Disaster Recovery

### Accidental Deletion

**Within Grace Period:**
- ✅ Contact support
- ✅ Account restored (all data intact)
- ✅ User can login normally

**After Grace Period:**
- ❌ Data permanently deleted
- ❌ Cannot be restored
- ⚠️ May be recoverable from backup if within backup retention window

### System Failure During Deletion

- ✅ Transaction rollback prevents partial deletion
- ✅ Retry logic attempts completion
- ✅ Failed deletions logged for manual review

---

## Monitoring & Alerts

### Metrics to Track

- `gdpr_soft_deletes_total` - Soft deletes per day
- `gdpr_hard_deletes_total` - Hard deletes per day
- `gdpr_cleanup_runs_total` - Cleanup job executions
- `gdpr_cleanup_failures_total` - Failed cleanup attempts
- `gdpr_restoration_requests_total` - Restoration requests

### Alerts

- ⚠️ Cleanup job failure
- ⚠️ Unusual spike in deletions (potential abuse)
- ⚠️ Failed hard delete (requires manual intervention)

---

## Legal Requirements by Jurisdiction

### EU (GDPR)

- ✅ Right to deletion (Article 17)
- ✅ 30-day response time
- ✅ Data minimization
- ✅ Documented retention policy

### California (CCPA)

- ✅ Right to deletion
- ✅ 45-day response time
- ✅ Data inventory

### Other Jurisdictions

Consult legal counsel for specific requirements in your operating regions.

---

## Configuration

### Environment Variables

```bash
# Grace period before hard delete (days)
GDPR_DELETION_GRACE_DAYS=30

# Storage retention by tier (days, -1 = unlimited)
STORAGE_RETENTION_FREE=30
STORAGE_RETENTION_BASIC=90
STORAGE_RETENTION_PRO=365
STORAGE_RETENTION_ENTERPRISE=-1
```

---

## Support Contact

For questions about data retention or deletion:

- **Email:** support@example.com
- **Restoration Window:** 30 days after soft delete
- **Response Time:** Within 24 hours

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-13 | Initial version |

**Next Review:** April 2026 (Quarterly)

---

**Legal Disclaimer:** This policy is subject to change. Users will be notified of material changes. For legal advice specific to your situation, please consult a qualified attorney.

