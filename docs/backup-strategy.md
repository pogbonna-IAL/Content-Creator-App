# Backup Strategy

## Overview

This document outlines the backup strategy for Content Creation Crew, covering PostgreSQL database, Redis cache, and file storage artifacts.

## Table of Contents

1. [PostgreSQL Backup](#postgresql-backup)
2. [Redis Backup](#redis-backup)
3. [File Storage Backup](#file-storage-backup)
4. [Backup Schedule](#backup-schedule)
5. [Backup Retention](#backup-retention)
6. [Backup Encryption](#backup-encryption)
7. [Backup Storage](#backup-storage)
8. [Verification](#verification)

---

## PostgreSQL Backup

### Backup Method

**Tool:** `pg_dump` (PostgreSQL native utility)

**Format:** Custom format (`.dump`) - compressed and allows selective restore

**Command:**
```bash
pg_dump -Fc -h <host> -U <user> -d <database> -f <backup_file.dump>
```

### Backup Script

**Location:** `infra/scripts/backup-postgres.sh`

**Features:**
- Automatic timestamp in filename
- Compression (custom format)
- Optional encryption
- Error handling
- Backup verification

**Usage:**
```bash
# Using Makefile
make backup-db

# Direct script
bash infra/scripts/backup-postgres.sh

# With custom output
bash infra/scripts/backup-postgres.sh /path/to/backup.dump
```

### Backup Schedule

**Production:**
- **Daily:** Full database backup at 2:00 AM UTC
- **Hourly:** Incremental backups (if using WAL archiving)
- **Before deployments:** Manual backup

**Staging:**
- **Daily:** Full database backup at 3:00 AM UTC

**Development:**
- **On-demand:** Manual backups before major changes

### Backup Retention

| Environment | Retention Period | Number of Backups |
|-------------|------------------|-------------------|
| **Production** | 30 days | ~30 daily backups |
| **Staging** | 7 days | ~7 daily backups |
| **Development** | 3 days | ~3 backups |

**Retention Policy:**
- Keep daily backups for 7 days
- Keep weekly backups (Sunday) for 4 weeks
- Keep monthly backups (1st of month) for 12 months
- Keep pre-deployment backups indefinitely (until verified)

### Backup Encryption

**At Rest:**
- Backups stored in encrypted storage (S3 with encryption, or encrypted filesystem)
- Encryption key managed via environment variable: `BACKUP_ENCRYPTION_KEY`

**In Transit:**
- Backups transferred via TLS/HTTPS
- Database connections use SSL (production)

**Encryption Method:**
```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup.dump

# Or use openssl
openssl enc -aes-256-cbc -salt -in backup.dump -out backup.dump.enc -k $BACKUP_ENCRYPTION_KEY
```

### Backup Storage Locations

**Local Development:**
- `./backups/postgres/` directory
- Git-ignored (see `.gitignore`)

**Staging/Production:**
- **Primary:** S3-compatible storage (encrypted)
- **Secondary:** Off-site backup (different region/provider)
- **Tertiary:** Local backup server (if available)

**S3 Structure:**
```
s3://backups-bucket/
  postgres/
    daily/
      content_crew_2026-01-13_020000.dump
      content_crew_2026-01-14_020000.dump
    weekly/
      content_crew_2026-01-07_020000.dump
    monthly/
      content_crew_2026-01-01_020000.dump
```

### Restore Steps

**See:** `docs/disaster-recovery.md` for detailed restore procedures

**Quick Restore:**
```bash
# Using Makefile
make restore-db backup_file.dump

# Direct script
bash infra/scripts/restore-postgres.sh backup_file.dump
```

---

## Redis Backup

### Backup Method

**Current Configuration:** Redis AOF (Append-Only File) enabled

**Docker Compose:**
```yaml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

### Backup Strategy

**Redis Persistence:**
- **AOF (Append-Only File):** Enabled by default
- **RDB Snapshots:** Optional (can be enabled)

**Why Redis Backup is Less Critical:**
- Redis is primarily a cache (can be rebuilt)
- User sessions can be recreated
- Content cache can be regenerated

**When to Backup Redis:**
- Before major cache invalidation
- If storing critical session data
- For disaster recovery completeness

### Backup Methods

**Method 1: Copy AOF File (Recommended)**
```bash
# Docker
docker compose exec redis redis-cli BGSAVE
docker cp content-crew-redis:/data/appendonly.aof ./backups/redis/appendonly_$(date +%Y%m%d).aof

# Local
cp ~/.redis/appendonly.aof ./backups/redis/appendonly_$(date +%Y%m%d).aof
```

**Method 2: RDB Snapshot**
```bash
# Create snapshot
docker compose exec redis redis-cli BGSAVE

# Copy snapshot
docker cp content-crew-redis:/data/dump.rdb ./backups/redis/dump_$(date +%Y%m%d).rdb
```

**Method 3: Redis Dump Command**
```bash
# Export all keys
docker compose exec redis redis-cli --rdb - > ./backups/redis/dump_$(date +%Y%m%d).rdb
```

### Backup Schedule

**Production:**
- **Daily:** AOF file backup (if critical data stored)
- **Weekly:** RDB snapshot

**Staging/Development:**
- **On-demand:** Manual backups only

### Backup Retention

| Environment | Retention Period |
|-------------|------------------|
| **Production** | 7 days (if backed up) |
| **Staging** | 3 days |
| **Development** | Not required |

### Restore Steps

**Restore AOF:**
```bash
# Stop Redis
docker compose stop redis

# Copy AOF file back
docker cp ./backups/redis/appendonly_20260113.aof content-crew-redis:/data/appendonly.aof

# Start Redis (will load AOF)
docker compose start redis
```

**Restore RDB:**
```bash
# Stop Redis
docker compose stop redis

# Copy RDB file
docker cp ./backups/redis/dump_20260113.rdb content-crew-redis:/data/dump.rdb

# Start Redis
docker compose start redis
```

---

## File Storage Backup

### Storage Types

**Local Disk Storage (Development):**
- Location: `./storage/` (or `STORAGE_PATH` env var)
- Subdirectories:
  - `voiceovers/` - TTS audio files
  - `artifacts/` - Content artifacts
  - `videos/` - Rendered video files
  - `storyboard_images/` - Storyboard images
  - `video_clips/` - Video clip segments

**S3-Compatible Storage (Production):**
- Provider: AWS S3, MinIO, or compatible service
- Bucket: Configured via `S3_BUCKET_NAME`
- Versioning: Enabled (recommended)

### Backup Strategy

**Local Disk:**
- **Method:** File system backup (rsync, tar, or cloud sync)
- **Schedule:** Daily incremental, weekly full
- **Retention:** 30 days

**S3-Compatible:**
- **Method:** S3 versioning + cross-region replication
- **Schedule:** Continuous (automatic via versioning)
- **Retention:** 90 days (via lifecycle policies)

### Backup Methods

**Method 1: rsync (Local)**
```bash
# Full backup
rsync -av --delete ./storage/ ./backups/storage/full_$(date +%Y%m%d)/

# Incremental backup
rsync -av ./storage/ ./backups/storage/incremental_$(date +%Y%m%d)/
```

**Method 2: tar Archive (Local)**
```bash
# Create compressed archive
tar -czf ./backups/storage/storage_$(date +%Y%m%d).tar.gz ./storage/

# With encryption
tar -czf - ./storage/ | openssl enc -aes-256-cbc -out ./backups/storage/storage_$(date +%Y%m%d).tar.gz.enc
```

**Method 3: S3 Sync (Local to S3)**
```bash
# Sync to S3 backup bucket
aws s3 sync ./storage/ s3://backups-bucket/storage/$(date +%Y%m%d)/ --delete
```

**Method 4: S3 Versioning (Production)**
```bash
# Enable versioning on bucket
aws s3api put-bucket-versioning \
  --bucket content-crew-storage \
  --versioning-configuration Status=Enabled

# Enable lifecycle policy for old versions
aws s3api put-bucket-lifecycle-configuration \
  --bucket content-crew-storage \
  --lifecycle-configuration file://lifecycle.json
```

### Backup Schedule

**Production (S3):**
- **Continuous:** Via S3 versioning
- **Daily:** Cross-region replication check

**Production (Local):**
- **Daily:** Incremental backup at 3:00 AM UTC
- **Weekly:** Full backup on Sunday at 2:00 AM UTC

**Staging:**
- **Daily:** Full backup at 4:00 AM UTC

**Development:**
- **On-demand:** Manual backups

### Backup Retention

| Storage Type | Retention Period |
|--------------|------------------|
| **S3 Versioning** | 90 days (current + previous versions) |
| **Local Full Backups** | 30 days |
| **Local Incremental** | 7 days |

### Restore Steps

**Local Storage:**
```bash
# Restore from tar archive
tar -xzf ./backups/storage/storage_20260113.tar.gz -C ./

# Restore from rsync backup
rsync -av ./backups/storage/full_20260113/ ./storage/
```

**S3 Storage:**
```bash
# Restore specific version
aws s3api get-object \
  --bucket content-crew-storage \
  --key voiceovers/file.wav \
  --version-id <version-id> \
  restored_file.wav

# Restore entire prefix
aws s3 sync s3://backups-bucket/storage/20260113/ s3://content-crew-storage/ --delete
```

---

## Backup Schedule Summary

### Production Schedule

| Component | Frequency | Time (UTC) | Retention |
|-----------|-----------|------------|-----------|
| **PostgreSQL** | Daily | 2:00 AM | 30 days |
| **PostgreSQL** | Weekly | Sunday 2:00 AM | 4 weeks |
| **PostgreSQL** | Monthly | 1st of month 2:00 AM | 12 months |
| **Redis** | Daily (if critical) | 2:30 AM | 7 days |
| **File Storage** | Daily (incremental) | 3:00 AM | 7 days |
| **File Storage** | Weekly (full) | Sunday 3:00 AM | 30 days |
| **S3 Versioning** | Continuous | N/A | 90 days |

### Staging Schedule

| Component | Frequency | Time (UTC) | Retention |
|-----------|-----------|------------|-----------|
| **PostgreSQL** | Daily | 3:00 AM | 7 days |
| **File Storage** | Daily | 4:00 AM | 7 days |

---

## Backup Encryption

### Encryption Requirements

**Production Backups:**
- ✅ Must be encrypted at rest
- ✅ Must use TLS/HTTPS in transit
- ✅ Encryption keys stored securely (not in code)

**Staging Backups:**
- ✅ Should be encrypted at rest
- ✅ Must use TLS/HTTPS in transit

**Development Backups:**
- ⚠️ Optional encryption (recommended if contains real data)

### Encryption Methods

**GPG Encryption:**
```bash
# Encrypt
gpg --symmetric --cipher-algo AES256 backup.dump

# Decrypt
gpg --decrypt backup.dump.gpg > backup.dump
```

**OpenSSL Encryption:**
```bash
# Encrypt
openssl enc -aes-256-cbc -salt -in backup.dump -out backup.dump.enc -k $BACKUP_ENCRYPTION_KEY

# Decrypt
openssl enc -aes-256-cbc -d -in backup.dump.enc -out backup.dump -k $BACKUP_ENCRYPTION_KEY
```

**S3 Server-Side Encryption:**
```bash
# Enable SSE-S3 (AWS managed keys)
aws s3 cp backup.dump s3://backups-bucket/ --server-side-encryption AES256

# Enable SSE-KMS (customer managed keys)
aws s3 cp backup.dump s3://backups-bucket/ --server-side-encryption aws:kms --ssekms-key-id <key-id>
```

---

## Backup Storage

### Storage Locations

**Primary Storage:**
- S3-compatible bucket (production)
- Local `./backups/` directory (development)

**Secondary Storage (Disaster Recovery):**
- Different AWS region (production)
- Off-site backup server (if available)
- Cloud storage provider (Backblaze, Wasabi, etc.)

### Storage Requirements

**PostgreSQL Backups:**
- **Size:** ~100-500 MB per backup (compressed)
- **Monthly:** ~15-150 GB (30 daily backups)
- **Yearly:** ~180 GB - 1.8 TB (with monthly backups)

**File Storage Backups:**
- **Size:** Varies by usage (typically 1-10 GB)
- **Monthly:** ~30-300 GB (daily incremental + weekly full)

**Total Storage Estimate:**
- **Minimum:** 50 GB
- **Typical:** 200-500 GB
- **High Usage:** 1-2 TB

---

## Verification

### Backup Verification Checklist

**PostgreSQL:**
- [ ] Backup file exists and is non-empty
- [ ] Backup file size is reasonable (not 0 bytes)
- [ ] Can restore backup to test database
- [ ] Backup contains expected tables
- [ ] Backup is encrypted (if required)

**Redis:**
- [ ] AOF file exists and is recent
- [ ] Can restore AOF to test Redis instance
- [ ] Keys are restored correctly

**File Storage:**
- [ ] Backup contains all subdirectories
- [ ] File counts match source
- [ ] File sizes match source
- [ ] Can restore files from backup

### Automated Verification

**PostgreSQL:**
```bash
# Verify backup file
pg_restore --list backup.dump | head -20

# Test restore to temporary database
createdb test_restore
pg_restore -d test_restore backup.dump
dropdb test_restore
```

**File Storage:**
```bash
# Verify tar archive
tar -tzf storage_backup.tar.gz | wc -l

# Compare file counts
tar -tzf storage_backup.tar.gz | wc -l
find ./storage -type f | wc -l
```

---

## Best Practices

### ✅ DO

- ✅ Test backups regularly (monthly restore test)
- ✅ Store backups in multiple locations
- ✅ Encrypt sensitive backups
- ✅ Monitor backup success/failure
- ✅ Document backup procedures
- ✅ Keep backup logs
- ✅ Verify backup integrity

### ❌ DON'T

- ❌ Don't store backups on same server as database
- ❌ Don't skip backup verification
- ❌ Don't ignore backup failures
- ❌ Don't store unencrypted backups with sensitive data
- ❌ Don't delete backups without verification
- ❌ Don't rely on single backup location

---

## Related Documentation

- [Disaster Recovery Guide](./disaster-recovery.md) - Restore procedures
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

