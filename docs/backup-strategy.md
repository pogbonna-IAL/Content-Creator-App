## Backup & Restore Strategy (M2)

**Last Updated:** 2026-01-14  
**Version:** 1.0.0  
**Status:** Production Ready

---

## Overview

This document describes the backup, restore, and verification strategy for the Content Creation Crew platform. A robust backup strategy is critical for disaster recovery, data protection, and business continuity.

---

## Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [Restore Strategy](#restore-strategy)
3. [Verification Procedure](#verification-procedure)
4. [Automated Verification](#automated-verification)
5. [Manual Operations](#manual-operations)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Disaster Recovery](#disaster-recovery)
8. [Compliance](#compliance)

---

## Backup Strategy

### What Gets Backed Up

#### 1. Database (PostgreSQL)
- **All tables** - Users, organizations, subscriptions, content jobs, artifacts, etc.
- **Schema** - Tables, indexes, constraints, sequences
- **Data** - All user and system data

#### 2. Storage Artifacts (Files)
- **Content artifacts** - Videos, audio, images, documents
- **User uploads** - Profile images, custom assets
- **Generated content** - AI-created content files

### Backup Schedule

| Type | Frequency | Retention | Method |
|------|-----------|-----------|---------|
| **Database** | Daily at 2 AM UTC | 30 days | `pg_dump` |
| **Storage** | Daily at 3 AM UTC | 30 days | rsync/rclone |
| **Full System** | Weekly (Sunday) | 90 days | Complete snapshot |

### Backup Location

```
backups/
├── database/
│   ├── backup_20260114_020000.sql.gz
│   ├── backup_20260115_020000.sql.gz
│   └── ...
└── storage/
    ├── artifacts_20260114_030000.tar.gz
    ├── artifacts_20260115_030000.tar.gz
    └── ...
```

### Backup Format

**Database:**
- Format: Plain SQL (`--format=plain`)
- Compression: gzip
- Options: `--no-owner`, `--no-acl`, `--clean`, `--if-exists`

**Storage:**
- Format: tar.gz or incremental rsync
- Compression: gzip level 6
- Includes: Metadata and file checksums

---

## Restore Strategy

### Restore Priority

1. **Critical** (RTO: 1 hour)
   - Database schema
   - User accounts
   - Active subscriptions

2. **High** (RTO: 4 hours)
   - Recent content artifacts (last 7 days)
   - Active jobs

3. **Normal** (RTO: 24 hours)
   - Historical data
   - Archived content

### Restore Process

#### Database Restore

```bash
# 1. Stop application
docker-compose down

# 2. Extract backup
gunzip backups/database/backup_20260114_020000.sql.gz

# 3. Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS content_creation_crew;"
psql -U postgres -c "CREATE DATABASE content_creation_crew;"

# 4. Restore backup
psql -U postgres -d content_creation_crew -f backups/database/backup_20260114_020000.sql

# 5. Verify restore
psql -U postgres -d content_creation_crew -c "SELECT COUNT(*) FROM users;"

# 6. Restart application
docker-compose up -d
```

#### Storage Restore

```bash
# 1. Extract storage backup
tar -xzf backups/storage/artifacts_20260114_030000.tar.gz -C /path/to/storage

# 2. Verify file counts
find /path/to/storage -type f | wc -l

# 3. Check permissions
chown -R appuser:appgroup /path/to/storage
```

---

## Verification Procedure

### Automated Verification Script

**Location:** `infra/scripts/verify-backup-restore.py`

**Purpose:** Ensures backups can be restored and contain valid data

### Verification Process

The script performs the following checks:

1. **Backup File Validation**
   - File exists and is readable
   - File size > 0 bytes
   - File format is valid SQL

2. **Container Setup**
   - Start temporary PostgreSQL container
   - Wait for database readiness
   - Create test database

3. **Restore Operation**
   - Copy backup file to container
   - Execute restore (`psql -f backup.sql`)
   - Check for fatal errors

4. **Schema Verification**
   - ✓ Alembic version table exists
   - ✓ Users table exists
   - ✓ Organizations table exists
   - ✓ Content jobs table exists
   - ✓ Content artifacts table exists
   - ✓ Subscriptions table exists

5. **Data Integrity Checks**
   - ✓ Users count >= 0
   - ✓ Organizations count >= 0
   - ✓ Content jobs count >= 0
   - ✓ Content artifacts count >= 0
   - ✓ Subscriptions count >= 0

6. **Migration State**
   - ✓ Migration version exists
   - ✓ Schema is up-to-date

### Running Verification Manually

```bash
# Verify latest backup
make backup-verify

# Verify specific backup
make backup-verify-file FILE=backups/database/backup_20260114_020000.sql

# Verify with verbose output
python3 infra/scripts/verify-backup-restore.py --latest --backup-dir ./backups --verbose

# Keep test container for inspection
python3 infra/scripts/verify-backup-restore.py --latest --no-cleanup
```

### Verification Output

```
================================================================================
BACKUP RESTORE VERIFICATION
================================================================================
Backup file: backups/database/backup_20260114_020000.sql
✓ Backup file exists: 15,234,567 bytes

Starting PostgreSQL 15 container...
✓ Container started: backup-restore-test
✓ PostgreSQL ready after 5 attempts

Restoring backup into restore_test...
Copying backup file to container...
Creating database: restore_test
Restoring backup (this may take a while)...
✓ Backup restored successfully

Verifying database schema...
  ✓ Alembic version table exists
  ✓ Users table exists
  ✓ Organizations table exists
  ✓ Content jobs table exists
  ✓ Content artifacts table exists
  ✓ Subscriptions table exists

Verifying data integrity...
  ✓ Users count >= 0 (count: 142)
  ✓ Organizations count >= 0 (count: 89)
  ✓ Content jobs count >= 0 (count: 1,234)
  ✓ Content artifacts count >= 0 (count: 5,678)
  ✓ Subscriptions count >= 0 (count: 67)

Verifying migrations...
  ✓ Migration version: 0607bc5b8541

================================================================================
VERIFICATION SUMMARY
================================================================================
Backup file: backups/database/backup_20260114_020000.sql
Total checks: 12
Passed: 12
Failed: 0

✅ VERIFICATION PASSED
Backup can be restored successfully
================================================================================
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more checks failed |
| `2` | Script error (e.g., backup file not found) |

---

## Automated Verification

### CI/CD Integration

**GitHub Actions:** `.github/workflows/backup-verification.yml`

**Schedule:** Nightly at 2 AM UTC

**Process:**
1. Start PostgreSQL service
2. Run migrations to create schema
3. Create test data (users, orgs, jobs)
4. Create backup with `pg_dump`
5. Run verification script
6. Upload backup and logs as artifacts

**Artifacts:**
- `test-backup` - The created backup file (7 days retention)
- `verification-logs` - Verification output (30 days retention)

### Viewing CI Results

```bash
# Via GitHub CLI
gh run list --workflow=backup-verification.yml

# View latest run
gh run view --log

# Download artifacts
gh run download <run-id>
```

### CI Alerts

The workflow will:
- ✅ Pass if verification succeeds
- ❌ Fail if verification fails
- 📧 Send notification on failure (if configured)

---

## Manual Operations

### Creating a Backup

```bash
# Using Makefile
make backup

# Using script directly
bash infra/scripts/create-backup.sh

# With custom output path
bash infra/scripts/create-backup.sh backups/manual_backup.sql
```

### Verifying a Backup

```bash
# Verify latest backup
make backup-verify

# Verify specific file
make backup-verify-file FILE=path/to/backup.sql

# With Docker Compose profile
make backup-restore-test
```

### Restoring from Backup

**⚠️ WARNING: This will replace existing data!**

```bash
# 1. Stop application
docker-compose down

# 2. Backup current database (safety)
make backup

# 3. Restore from backup
gunzip -c backups/database/backup_20260114_020000.sql.gz | \
  psql -U postgres -d content_creation_crew

# 4. Verify restore
psql -U postgres -d content_creation_crew -c "SELECT version_num FROM alembic_version;"

# 5. Restart application
docker-compose up -d
```

### Cleanup Old Backups

```bash
# Remove backups older than 30 days
make backup-cleanup

# Manual cleanup
find backups/ -name "backup_*.sql.gz" -mtime +30 -delete
```

---

## Monitoring & Alerts

### Metrics to Track

1. **Backup Success Rate**
   ```promql
   rate(backup_success_total[24h]) /
   rate(backup_attempts_total[24h])
   ```

2. **Backup Size Trend**
   ```promql
   backup_size_bytes
   ```

3. **Verification Success Rate**
   ```promql
   rate(backup_verification_success_total[7d]) /
   rate(backup_verification_attempts_total[7d])
   ```

4. **Restore Duration**
   ```promql
   histogram_quantile(0.95, backup_restore_seconds)
   ```

### Alerts

#### Critical Alerts

```yaml
# Backup failed
- alert: BackupFailed
  expr: backup_success_total{status="failed"} > 0
  for: 5m
  annotations:
    summary: "Database backup failed"
    
# Verification failed
- alert: BackupVerificationFailed
  expr: backup_verification_success_total{status="failed"} > 0
  for: 5m
  annotations:
    summary: "Backup restore verification failed"
    
# No backup in 25 hours
- alert: BackupMissing
  expr: (time() - backup_last_success_timestamp) > 90000
  for: 1h
  annotations:
    summary: "No successful backup in 25+ hours"
```

#### Warning Alerts

```yaml
# Backup size anomaly
- alert: BackupSizeAnomaly
  expr: abs(backup_size_bytes - backup_size_bytes offset 1d) / backup_size_bytes > 0.5
  for: 30m
  annotations:
    summary: "Backup size changed by >50%"
    
# Restore duration high
- alert: RestoreDurationHigh
  expr: backup_restore_seconds > 300
  for: 5m
  annotations:
    summary: "Backup restore taking >5 minutes"
```

---

## Disaster Recovery

### Scenarios

#### 1. Database Corruption

**RTO:** 1 hour  
**RPO:** 1 day (last backup)

**Steps:**
1. Identify corruption (failed queries, data inconsistencies)
2. Stop application immediately
3. Isolate corrupted database
4. Restore from latest verified backup
5. Verify restore with verification script
6. Restart application
7. Monitor for issues

#### 2. Complete Data Loss

**RTO:** 4 hours  
**RPO:** 1 day

**Steps:**
1. Provision new infrastructure
2. Restore database from backup
3. Restore storage artifacts from backup
4. Run verification on all restored data
5. Update DNS/load balancers
6. Restart application
7. Notify users of potential data loss

#### 3. Ransomware Attack

**RTO:** 24 hours  
**RPO:** 1 day

**Steps:**
1. Isolate infected systems
2. Verify backup integrity (pre-infection)
3. Provision clean infrastructure
4. Restore from verified clean backup
5. Apply security patches
6. Scan restored data
7. Gradually bring systems online

### Recovery Testing

**Frequency:** Quarterly

**Process:**
1. Schedule maintenance window
2. Create fresh backup
3. Provision test environment
4. Perform full restore
5. Run application tests
6. Document timing and issues
7. Update RTO/RPO estimates

---

## Compliance

### Data Retention

- **Backups:** 30 days (database), 30 days (storage)
- **Weekly backups:** 90 days
- **Annual backups:** 7 years (compliance)

### GDPR Compliance

- Backups include deleted user data (within retention)
- After retention window, data is purged from backups
- Right to be forgotten: user data removed after 30 days
- Backup encryption: at rest and in transit

### Audit Trail

All backup operations are logged:
- Timestamp
- Operator (if manual)
- Backup size
- Success/failure
- Verification status

---

## Best Practices

### For Operators

1. **Verify backups regularly** - Don't wait for disaster
2. **Test restores quarterly** - Practice makes perfect
3. **Monitor backup metrics** - Catch issues early
4. **Keep backup credentials secure** - Separate from production
5. **Document procedures** - Make it repeatable

### For Developers

1. **Design for backups** - Consider restore complexity
2. **Test migrations** - Ensure they're reversible
3. **Avoid breaking changes** - Keep backward compatibility
4. **Log changes** - Audit trail for debugging

### Checklist

**Daily:**
- [ ] Check backup CI job passed
- [ ] Verify backup size is reasonable
- [ ] Review verification logs

**Weekly:**
- [ ] Manual backup verification test
- [ ] Review backup storage usage
- [ ] Check for failed verifications

**Monthly:**
- [ ] Full restore test to staging
- [ ] Review backup retention policy
- [ ] Audit backup access logs

**Quarterly:**
- [ ] Disaster recovery drill
- [ ] Update RTO/RPO estimates
- [ ] Review and update procedures

---

## Troubleshooting

### Issue: Backup Verification Fails

**Symptoms:**
- Verification script exits with code 1
- Schema checks fail
- Data integrity checks fail

**Diagnosis:**
```bash
# Run with verbose output
python3 infra/scripts/verify-backup-restore.py --latest --verbose

# Keep container for manual inspection
python3 infra/scripts/verify-backup-restore.py --latest --no-cleanup

# Connect to test database
docker exec -it backup-restore-test psql -U postgres -d restore_test
```

**Solutions:**
1. Check backup file integrity
2. Verify PostgreSQL version compatibility
3. Check for migration issues
4. Review restore logs for errors

### Issue: Backup Size Anomaly

**Symptoms:**
- Backup suddenly much larger/smaller
- Compression ratio changed significantly

**Diagnosis:**
```bash
# Compare backup sizes
ls -lh backups/database/ | tail -5

# Check table sizes
psql -d content_creation_crew -c "
  SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**Solutions:**
1. Check for data anomalies (mass inserts/deletes)
2. Vacuum/analyze database
3. Review retention cleanup jobs

### Issue: Restore Takes Too Long

**Symptoms:**
- Restore duration > expected
- Timeout errors

**Diagnosis:**
```bash
# Check backup file size
ls -lh backup.sql.gz

# Monitor restore progress
docker exec backup-restore-test tail -f /var/log/postgresql/postgresql.log
```

**Solutions:**
1. Increase restore timeout
2. Optimize backup format (consider custom format)
3. Use parallel restore for large databases
4. Provision more resources for restore

---

## Related Documentation

- [GDPR Compliance](./gdpr.md) - Data retention and deletion
- [Data Retention Policy](./retention-policy.md) - Artifact retention
- [Monitoring Guide](./monitoring.md) - Backup metrics and alerts
- [Disaster Recovery Plan](./disaster-recovery.md) - Complete DR procedures

---

## Changelog

### Version 1.0.0 (M2) - 2026-01-14
- Initial backup strategy documentation
- Automated restore verification script
- CI/CD integration for nightly verification
- Makefile targets for backup operations
- Docker Compose restore-test profile

---

## Support

For questions or issues with backups:
- **Runbook:** `/docs/runbooks/backup-restore.md`
- **Slack:** `#ops-alerts`
- **On-call:** PagerDuty escalation
- **Email:** ops@contentcreationcrew.com

---

**Last Updated:** 2026-01-14  
**Next Review:** 2026-04-14 (Quarterly)  
**Owner:** DevOps Team
