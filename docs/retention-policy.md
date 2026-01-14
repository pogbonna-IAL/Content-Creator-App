# Artifact Retention Policy

## Overview

This document describes the automatic artifact retention and deletion policy for the Content Creation Crew platform. Artifacts are automatically deleted based on your subscription tier to control storage costs and support GDPR data minimization principles.

---

## Retention Periods by Plan

| Plan | Retention Period | Description |
|------|-----------------|-------------|
| **Free** | 30 days | Artifacts older than 30 days are automatically deleted |
| **Basic** | 90 days | Artifacts older than 90 days are automatically deleted |
| **Pro** | 365 days | Artifacts older than 1 year are automatically deleted |
| **Enterprise** | Unlimited | No automatic deletion based on age |

---

## What Gets Deleted

### Artifacts Included in Retention Policy

The following artifacts are subject to automatic deletion:

1. **Blog Content** - Generated blog posts and articles
2. **Social Media Posts** - Generated social media content
3. **Voiceovers** - Audio files (`.wav`, `.mp3`)
4. **Storyboard Images** - Generated images for video scenes
5. **Video Clips** - Rendered video segments
6. **Video Scripts** - Generated video scripts

### Deletion Process

When an artifact expires:
1. **Storage files are deleted** from the storage backend (local disk or S3)
2. **Database records are removed** from the `content_artifacts` table
3. **Job records remain** in the `content_jobs` table (for audit purposes)

---

## Retention Calculation

**Retention is calculated from the artifact creation date:**

```
deletion_eligible = (current_date - artifact.created_at) > retention_days
```

**Example:**
- Plan: Pro (365 days retention)
- Artifact created: January 1, 2025
- Current date: January 2, 2026
- Age: 366 days
- **Result: Eligible for deletion**

---

## GDPR Override Behavior

### User Deletion (GDPR Right to be Forgotten)

When a user requests account deletion:
- **ALL artifacts are deleted** regardless of subscription plan
- This includes Enterprise plan artifacts
- Deletion occurs during the GDPR hard delete process
- No retention period applies

### Organization Deletion

When an organization is deleted:
- **ALL member artifacts are evaluated**
- Artifacts are deleted according to the organization's plan
- Enterprise organizations: artifacts deleted only on explicit deletion request

---

## Email Notifications (M1 Enhancement)

**Users receive advance warning before artifact deletion**

### Notification Schedule

**Notifications sent daily at 10:00 AM UTC** (user-friendly time)

Notification timing:
- **7 days before deletion** (default)
- Configurable via `RETENTION_NOTIFY_DAYS_BEFORE`

### Notification Content

Each notification email includes:
1. **Total artifacts expiring**
2. **Breakdown by expiration date**
   - Expiring today
   - Expiring in 3 days
   - Expiring in 7 days
3. **Artifact details**
   - Type (video, audio, image, etc.)
   - Topic/title
   - Creation date
4. **Action recommendations**
   - Download content before deletion
   - Upgrade plan for longer retention
5. **Plan-specific retention info**

### Example Email

```
Subject: ⚠️ 5 artifacts will be deleted soon

Hello,

This is a reminder that 5 of your content artifacts will be deleted 
soon due to your FREE plan retention policy.

Artifacts by expiration:

Expiring today: 2 artifacts
  - video: AI Tutorial Introduction
  - audio: Podcast Episode 15

Expiring in 5 days: 3 artifacts
  - video: Marketing Demo
  - image: Social Media Banner
  - blog: Content Strategy Guide

What you can do:
  1. Download your content before it's deleted
  2. Upgrade your plan for longer retention:
     - Basic: 90 days
     - Pro: 365 days
     - Enterprise: Unlimited

⚠️ Once deleted, your content cannot be recovered.

Questions? Contact support@contentcreationcrew.com
```

### Notification Eligibility

Notifications are sent to users who:
- ✅ Have verified email addresses
- ✅ Have artifacts expiring within notification window
- ✅ Are on plans with finite retention (Free, Basic, Pro)
- ❌ Enterprise users (unlimited retention) receive no notifications

### Configuration

```bash
# Enable/disable notifications
RETENTION_NOTIFY_ENABLED=true

# Days before deletion to notify
RETENTION_NOTIFY_DAYS_BEFORE=7

# Max notifications per batch
RETENTION_NOTIFY_BATCH_SIZE=100
```

---

## Cleanup Schedule

**Automated cleanup runs daily at 4:00 AM UTC**

The cleanup job:
1. Evaluates each organization's active subscription
2. Calculates retention cutoff date based on plan
3. Identifies expired artifacts
4. Deletes storage files
5. Removes database records
6. Logs audit events

**Job execution is idempotent** - safe to run multiple times.

---

## Safety Features

### Dry-Run Mode

Enable dry-run mode to test retention policy without deleting data:

```bash
RETENTION_DRY_RUN=true
```

When enabled:
- All deletion logic executes
- Actions are logged
- **No actual deletions occur**
- Database transactions are not committed

### Transaction Safety

All deletions use database transactions:
- Atomic operations (all or nothing)
- Automatic rollback on error
- Retry-safe (idempotent)

### Audit Logging

All retention deletions are logged:
- Action type: `ARTIFACT_RETENTION_DELETE`
- Timestamp
- Number of artifacts deleted
- Bytes freed
- No PII (personally identifiable information)

---

## Configuration

### Environment Variables

```bash
# Retention periods (days)
RETENTION_DAYS_FREE=30
RETENTION_DAYS_BASIC=90
RETENTION_DAYS_PRO=365
RETENTION_DAYS_ENTERPRISE=-1  # -1 = unlimited

# Email notifications (M1 Enhancement)
RETENTION_NOTIFY_ENABLED=true
RETENTION_NOTIFY_DAYS_BEFORE=7
RETENTION_NOTIFY_BATCH_SIZE=100

# Dry-run mode (no actual deletions or notifications)
RETENTION_DRY_RUN=false
```

### Customization

Retention periods can be customized per environment:

**Development:**
```bash
RETENTION_DAYS_FREE=7   # 1 week for testing
RETENTION_DAYS_BASIC=14  # 2 weeks
```

**Production:**
```bash
# Use defaults or customize as needed
RETENTION_DAYS_PRO=730  # 2 years for pro users
```

---

## Restore Limitations

### ⚠️ Deleted Data Cannot Be Restored

Once artifacts are deleted:
- **Storage files are permanently removed**
- **Database records are permanently removed**
- **No backup or restore is available**
- **Users must regenerate content if needed**

### Before Deletion

Users are advised to:
1. **Watch for notification emails** - Sent 7 days before deletion
2. **Download important content** before expiration
3. **Upgrade subscription tier** for longer retention
4. **Regularly export artifacts** for backup

**Note:** Email notifications are sent automatically, but users should not rely solely on them. Check artifact ages regularly.

---

## Monitoring and Metrics

### Prometheus Metrics

Track retention cleanup operations:

```promql
# Artifacts deleted per day
rate(retention_deletes_total[24h]) * 86400

# Storage freed per day
rate(retention_bytes_freed_total[24h]) * 86400

# Cleanup job runs
retention_cleanup_runs_total
```

### Audit Logs

Query retention deletion events:

```sql
SELECT * FROM audit_log 
WHERE action_type = 'ARTIFACT_RETENTION_DELETE'
ORDER BY created_at DESC
LIMIT 100;
```

---

## User Impact

### Free Plan Users

- Artifacts deleted after 30 days
- **Recommendation**: Download content regularly or upgrade

### Basic Plan Users

- Artifacts deleted after 90 days
- **Recommendation**: Sufficient for most use cases

### Pro Plan Users

- Artifacts deleted after 365 days
- **Recommendation**: Excellent for long-term projects

### Enterprise Plan Users

- No automatic deletion
- Unlimited storage (fair use applies)
- **Recommendation**: Manual cleanup recommended for cost optimization

---

## Best Practices

### For Users

1. **Download Important Content**
   - Export artifacts before expiration
   - Store locally or in personal cloud storage

2. **Monitor Artifact Age**
   - Check artifact creation dates
   - Plan downloads accordingly

3. **Upgrade When Needed**
   - Consider upgrade if hitting retention limits
   - Balance cost vs. retention needs

### For Administrators

1. **Monitor Storage Growth**
   - Track `storage_bytes_written_total` metric
   - Alert on unusual growth

2. **Review Retention Policy**
   - Adjust periods based on usage patterns
   - Balance cost vs. user expectations

3. **Test in Dry-Run Mode**
   - Validate retention logic before deployment
   - Verify expected artifacts are targeted

4. **Audit Regularly**
   - Review audit logs for anomalies
   - Verify cleanup job executions

---

## Compliance

### GDPR Data Minimization

The retention policy supports GDPR's data minimization principle:
- Data is not kept longer than necessary
- Automatic deletion reduces data exposure risk
- Users have right to request immediate deletion

### Data Protection

- Deleted data is permanently removed
- No soft-delete or recycle bin
- Storage files are overwritten (depending on storage backend)

---

## FAQ

### Q: Can I extend my retention period?

**A:** Yes, upgrade to a higher-tier plan:
- Basic → Pro: 90 days → 365 days
- Pro → Enterprise: 365 days → Unlimited

### Q: What happens if I downgrade my plan?

**A:** New retention period applies immediately:
- Existing artifacts beyond new retention period are deleted in next cleanup cycle
- **Example**: Pro (365d) → Basic (90d) → Artifacts older than 90 days deleted

### Q: Can I request manual deletion before expiration?

**A:** Yes, use the GDPR deletion endpoint:
- `DELETE /v1/user/delete` - Delete all your data
- Individual artifact deletion not currently supported

### Q: Are job records deleted?

**A:** No, job records are retained for audit purposes:
- Only artifacts (content + files) are deleted
- Job metadata (status, timestamps) remains

### Q: How do I know when my artifacts will expire?

**A:** You will receive email notifications 7 days before expiration. You can also calculate from artifact creation date:
- Free: `created_at + 30 days`
- Basic: `created_at + 90 days`
- Pro: `created_at + 365 days`
- Enterprise: Never (unless GDPR deleted)

### Q: Can I opt out of expiration notification emails?

**A:** Currently, notification emails are sent to all users with verified email addresses. Email preference management will be added in a future update.

### Q: Can I disable automatic deletion for my organization?

**A:** Yes, upgrade to Enterprise plan for unlimited retention.

### Q: What if the cleanup job fails?

**A:** The job is retry-safe:
- Runs daily automatically
- Failed deletions are retried in next run
- Errors are logged and monitored

---

## Related Documentation

- [GDPR Compliance](./gdpr.md) - User deletion and data export
- [Data Retention](./data-retention.md) - General data retention policy
- [Monitoring](./monitoring.md) - Metrics and alerting
- [Storage](./storage.md) - Storage provider configuration

---

## Changelog

### Version 1.2.0 (M1 Enhancements) - 2026-01-14
- ✨ **HTML email templates** with professional design
- ✨ **Duplicate prevention** via notification tracking
- ✨ **Test script** for simulation and debugging
- Color-coded urgency levels (red/orange/yellow)
- Mobile-responsive email layout
- Database-backed notification history
- Automatic retry for failed notifications

### Version 1.1.0 (M1 Enhancement) - 2026-01-14
- ✨ Email notifications before deletion
- Configurable notification window (default: 7 days)
- User-friendly notification scheduling (10 AM UTC)
- Grouped artifact expiration display
- Upgrade recommendations in notifications

### Version 1.0.0 (M1) - 2026-01-14
- Initial retention policy implementation
- Tier-based retention periods
- Automated cleanup job
- GDPR override support
- Audit logging
- Dry-run mode

---

## Support

For questions or concerns about the retention policy:
- Email: support@contentcreationcrew.com
- Documentation: https://docs.contentcreationcrew.com
- Status Page: https://status.contentcreationcrew.com

---

**Last Updated:** 2026-01-14  
**Policy Version:** 1.2.0 (M1 Enhancements - HTML Templates, Tracking, Test Script)

