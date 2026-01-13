# Disaster Recovery Plan

## Overview

This document provides step-by-step procedures for disaster recovery scenarios, including RPO/RTO assumptions, restore runbooks, and failure scenario handling.

## Table of Contents

1. [RPO/RTO Assumptions](#rporto-assumptions)
2. [Restore Runbook](#restore-runbook)
3. [Verify Restore Procedure](#verify-restore-procedure)
4. [Failure Scenarios](#failure-scenarios)
5. [Prevention Measures](#prevention-measures)

---

## RPO/RTO Assumptions

### Recovery Point Objective (RPO)

**RPO Definition:** Maximum acceptable data loss (how much data can be lost)

| Component | RPO | Rationale |
|-----------|-----|-----------|
| **PostgreSQL** | 24 hours | Daily backups, acceptable to lose up to 24 hours of data |
| **Redis** | 1 hour | Cache can be rebuilt, sessions can be recreated |
| **File Storage** | 24 hours | Daily backups, artifacts can be regenerated if needed |

**Note:** For critical production systems, consider:
- **PostgreSQL:** 1 hour RPO (hourly backups + WAL archiving)
- **File Storage:** 1 hour RPO (hourly incremental backups)

### Recovery Time Objective (RTO)

**RTO Definition:** Maximum acceptable downtime (how long system can be down)

| Scenario | RTO | Rationale |
|----------|-----|-----------|
| **Database Loss** | 4 hours | Restore from backup + verification |
| **Storage Loss** | 2 hours | Restore from backup or regenerate |
| **Full System Loss** | 8 hours | Complete infrastructure rebuild |
| **Partial Failure** | 1 hour | Single component restore |

**Note:** These are baseline targets. Adjust based on business requirements.

---

## Restore Runbook

### Pre-Restore Checklist

- [ ] **Identify failure scope**
  - What component failed?
  - When did failure occur?
  - What data is affected?

- [ ] **Locate backups**
  - Find most recent backup before failure
  - Verify backup integrity
  - Check backup location accessibility

- [ ] **Prepare restore environment**
  - Ensure sufficient disk space
  - Verify database credentials
  - Check network connectivity

- [ ] **Notify stakeholders**
  - Inform team of recovery process
  - Set expectations for downtime
  - Document incident

### Scenario 1: PostgreSQL Database Loss

#### Step 1: Stop Application

```bash
# Stop API service
docker compose stop api

# Or if running locally
# Stop the application process
```

#### Step 2: Identify Backup

```bash
# List available backups
ls -lh ./backups/postgres/

# Or check S3
aws s3 ls s3://backups-bucket/postgres/daily/
```

**Select backup:**
- Most recent backup before failure
- Verify backup timestamp
- Check backup file size (not 0 bytes)

#### Step 3: Restore Database

**Option A: Restore to Existing Database**

```bash
# Using Makefile
make restore-db ./backups/postgres/content_crew_2026-01-13_020000.dump

# Using script directly
bash infra/scripts/restore-postgres.sh ./backups/postgres/content_crew_2026-01-13_020000.dump
```

**Option B: Restore to New Database**

```bash
# Create new database
docker compose exec db psql -U contentcrew -c "CREATE DATABASE content_crew_restored;"

# Restore to new database
docker compose exec -T db pg_restore -U contentcrew -d content_crew_restored < ./backups/postgres/content_crew_2026-01-13_020000.dump

# Verify restore
docker compose exec db psql -U contentcrew -d content_crew_restored -c "\dt"

# Switch databases (update DATABASE_URL)
# Then drop old database
docker compose exec db psql -U contentcrew -c "DROP DATABASE content_crew;"
docker compose exec db psql -U contentcrew -c "ALTER DATABASE content_crew_restored RENAME TO content_crew;"
```

#### Step 4: Verify Restore

```bash
# Check table counts
docker compose exec db psql -U contentcrew -d content_crew -c "SELECT COUNT(*) FROM users;"
docker compose exec db psql -U contentcrew -d content_crew -c "SELECT COUNT(*) FROM content_jobs;"

# Check recent data
docker compose exec db psql -U contentcrew -d content_crew -c "SELECT MAX(created_at) FROM content_jobs;"
```

#### Step 5: Restart Application

```bash
# Start API service
docker compose start api

# Verify health
curl http://localhost:8000/health
```

#### Step 6: Post-Restore Verification

- [ ] Application starts successfully
- [ ] Health check passes
- [ ] Can log in with test account
- [ ] Can create new content job
- [ ] Data matches backup timestamp

### Scenario 2: File Storage Loss

#### Step 1: Identify Affected Storage

```bash
# Check storage location
ls -lh ./storage/

# Check S3 bucket
aws s3 ls s3://content-crew-storage/ --recursive
```

#### Step 2: Locate Backup

```bash
# Local backup
ls -lh ./backups/storage/

# S3 backup
aws s3 ls s3://backups-bucket/storage/
```

#### Step 3: Restore Storage

**Local Storage:**

```bash
# Restore from tar archive
tar -xzf ./backups/storage/storage_2026-01-13.tar.gz -C ./

# Or restore from rsync backup
rsync -av ./backups/storage/full_2026-01-13/ ./storage/
```

**S3 Storage:**

```bash
# Restore entire prefix
aws s3 sync s3://backups-bucket/storage/2026-01-13/ s3://content-crew-storage/ --delete

# Or restore specific files
aws s3 cp s3://backups-bucket/storage/2026-01-13/voiceovers/file.wav s3://content-crew-storage/voiceovers/file.wav
```

#### Step 4: Verify Restore

```bash
# Check file counts
find ./storage -type f | wc -l
tar -tzf ./backups/storage/storage_2026-01-13.tar.gz | wc -l

# Check specific files
ls -lh ./storage/voiceovers/
ls -lh ./storage/videos/
```

#### Step 5: Test Application

```bash
# Test file access
curl http://localhost:8000/v1/storage/voiceovers/test.wav

# Create test content job
# Verify artifacts are accessible
```

### Scenario 3: Full System Loss

#### Step 1: Provision Infrastructure

```bash
# Start fresh infrastructure
docker compose up -d db redis

# Wait for services to be healthy
docker compose ps
```

#### Step 2: Restore Database

```bash
# Follow Scenario 1 steps
make restore-db ./backups/postgres/content_crew_2026-01-13_020000.dump
```

#### Step 3: Restore File Storage

```bash
# Follow Scenario 2 steps
tar -xzf ./backups/storage/storage_2026-01-13.tar.gz -C ./
```

#### Step 4: Restore Application

```bash
# Start application
docker compose up -d

# Verify all services
docker compose ps
curl http://localhost:8000/health
```

#### Step 5: Verify System

- [ ] Database restored
- [ ] Storage restored
- [ ] Application running
- [ ] Health checks passing
- [ ] Can create content jobs
- [ ] Artifacts accessible

---

## Verify Restore Procedure

### Database Verification

**Step 1: Check Database Connection**
```bash
docker compose exec db psql -U contentcrew -d content_crew -c "SELECT version();"
```

**Step 2: Verify Table Counts**
```bash
# Expected tables
docker compose exec db psql -U contentcrew -d content_crew -c "\dt"

# Check row counts
docker compose exec db psql -U contentcrew -d content_crew -c "
SELECT 
  'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 'content_jobs', COUNT(*) FROM content_jobs
UNION ALL
SELECT 'content_artifacts', COUNT(*) FROM content_artifacts;
"
```

**Step 3: Verify Data Integrity**
```bash
# Check foreign key constraints
docker compose exec db psql -U contentcrew -d content_crew -c "
SELECT 
  conname as constraint_name,
  conrelid::regclass as table_name
FROM pg_constraint
WHERE contype = 'f';
"

# Check for orphaned records
docker compose exec db psql -U contentcrew -d content_crew -c "
SELECT COUNT(*) as orphaned_jobs
FROM content_jobs j
LEFT JOIN users u ON j.user_id = u.id
WHERE u.id IS NULL;
"
```

**Step 4: Test Application Queries**
```bash
# Test user login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'

# Test content job creation
# (Use authenticated session)
```

### Storage Verification

**Step 1: Check File Counts**
```bash
# Count files in each directory
find ./storage/voiceovers -type f | wc -l
find ./storage/videos -type f | wc -l
find ./storage/artifacts -type f | wc -l
```

**Step 2: Verify File Integrity**
```bash
# Check file sizes (not 0 bytes)
find ./storage -type f -size 0

# Check file permissions
ls -lh ./storage/voiceovers/
```

**Step 3: Test File Access**
```bash
# Test static file serving
curl -I http://localhost:8000/v1/storage/voiceovers/test.wav

# Test artifact URLs from database
docker compose exec db psql -U contentcrew -d content_crew -c "
SELECT storage_key, storage_url 
FROM content_artifacts 
WHERE artifact_type = 'voiceover_audio' 
LIMIT 5;
"
```

### Application Verification

**Step 1: Health Check**
```bash
curl http://localhost:8000/health | jq
```

**Step 2: Functional Tests**
```bash
# Test authentication
# Test content generation
# Test artifact retrieval
# Test file downloads
```

**Step 3: Monitor Logs**
```bash
# Check for errors
docker compose logs api | grep -i error

# Check for warnings
docker compose logs api | grep -i warning
```

---

## Failure Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Database connection fails
- Queries return errors
- Application crashes

**Recovery Steps:**
1. Stop application
2. Attempt database repair (if possible)
3. If repair fails, restore from backup
4. Verify restore
5. Restart application

**Prevention:**
- Regular backups
- Database health monitoring
- Disk space monitoring

### Scenario 2: Storage Disk Full

**Symptoms:**
- File writes fail
- Database writes fail
- Application errors

**Recovery Steps:**
1. Free up disk space (delete old backups, logs)
2. If critical, restore from backup
3. Add disk space or migrate to larger storage
4. Implement disk space monitoring

**Prevention:**
- Disk space monitoring
- Automatic cleanup of old files
- Storage quotas

### Scenario 3: Accidental Data Deletion

**Symptoms:**
- Data missing from database
- Files missing from storage
- User reports missing content

**Recovery Steps:**
1. Identify deletion timestamp
2. Find backup before deletion
3. Restore affected data
4. Verify restore
5. Investigate cause

**Prevention:**
- Access controls
- Audit logging
- Soft deletes (mark as deleted, don't remove)

### Scenario 4: Webhook Replay Attack

**Symptoms:**
- Duplicate billing events
- Multiple subscription charges
- Payment provider errors

**Recovery Steps:**
1. Identify duplicate events
2. Check webhook replay protection
3. Reverse duplicate charges
4. Update webhook handling
5. Monitor for future duplicates

**Prevention:**
- Webhook idempotency keys
- Event deduplication
- Webhook signature verification

### Scenario 5: Ransomware/Data Encryption

**Symptoms:**
- Files encrypted
- Database encrypted
- Ransom note

**Recovery Steps:**
1. **DO NOT PAY RANSOM**
2. Isolate affected systems
3. Restore from clean backups
4. Verify no malware remains
5. Strengthen security

**Prevention:**
- Regular backups (offline/immutable)
- Security monitoring
- Access controls
- Network segmentation

### Scenario 6: Provider Outage

**Symptoms:**
- Cloud provider down
- Database unavailable
- Storage unavailable

**Recovery Steps:**
1. Check provider status
2. Wait for provider recovery (if temporary)
3. If extended, restore to alternative provider
4. Update DNS/configurations
5. Verify functionality

**Prevention:**
- Multi-region backups
- Multi-provider strategy
- Disaster recovery testing

---

## Prevention Measures

### Monitoring

**Database Monitoring:**
- Disk space usage
- Connection pool usage
- Query performance
- Backup success/failure

**Storage Monitoring:**
- Disk space usage
- File count
- Access patterns
- Backup success/failure

**Application Monitoring:**
- Health check status
- Error rates
- Response times
- Resource usage

### Automated Alerts

**Critical Alerts:**
- Backup failures
- Disk space > 80%
- Database connection failures
- Storage write failures

**Warning Alerts:**
- Disk space > 60%
- Slow query performance
- High error rates

### Regular Testing

**Monthly:**
- Test database restore
- Verify backup integrity
- Review backup logs

**Quarterly:**
- Full disaster recovery drill
- Test restore procedures
- Update documentation

**Annually:**
- Disaster recovery plan review
- Update RPO/RTO targets
- Test alternative recovery methods

---

## Related Documentation

- [Backup Strategy](./backup-strategy.md) - Backup procedures
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

