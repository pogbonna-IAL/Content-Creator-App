# Backup Directory

This directory contains database and storage backups for disaster recovery.

## Structure

```
backups/
├── database/           # PostgreSQL dumps
│   ├── backup_20260114_020000.sql.gz
│   ├── backup_20260115_020000.sql.gz
│   └── ...
└── storage/            # Artifact backups
    ├── artifacts_20260114_030000.tar.gz
    ├── artifacts_20260115_030000.tar.gz
    └── ...
```

## Creating Backups

### Database Backup
```bash
# Using Makefile (recommended)
make backup

# Using script directly
bash infra/scripts/create-backup.sh

# Custom output path
bash infra/scripts/create-backup.sh backups/database/manual_backup.sql
```

### Storage Backup
```bash
# Create tar.gz of storage directory
tar -czf backups/storage/artifacts_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/storage
```

## Verifying Backups

```bash
# Verify latest backup
make backup-verify

# Verify specific backup
make backup-verify-file FILE=backups/database/backup_20260114_020000.sql

# Full restore test
make backup-restore-test
```

## Cleanup

Backups are automatically cleaned up after 30 days:

```bash
# Manual cleanup
make backup-cleanup

# Or directly
find backups/database -name "backup_*.sql.gz" -mtime +30 -delete
find backups/storage -name "artifacts_*.tar.gz" -mtime +30 -delete
```

## Retention Policy

| Type | Retention | Method |
|------|-----------|--------|
| **Daily Database** | 30 days | Automated cleanup |
| **Daily Storage** | 30 days | Automated cleanup |
| **Weekly Full** | 90 days | Manual archive |
| **Annual** | 7 years | Compliance archive |

## Restore Procedures

See [docs/backup-strategy.md](../docs/backup-strategy.md) for complete restore procedures.

### Quick Restore

```bash
# 1. Stop application
docker-compose down

# 2. Extract backup
gunzip backups/database/backup_20260114_020000.sql.gz

# 3. Restore database
psql -U postgres -d content_creation_crew -f backups/database/backup_20260114_020000.sql

# 4. Restart application
docker-compose up -d
```

## Monitoring

- **CI/CD:** Nightly verification at 2 AM UTC
- **Alerts:** Configured for backup failures
- **Metrics:** Tracked in Prometheus

## Important Notes

⚠️ **Do not commit actual backup files to git!**
- Only `.gitkeep` files are tracked
- Backup files are in `.gitignore`
- Store production backups securely

⚠️ **Test restores regularly!**
- Quarterly restore drills recommended
- Use `make backup-restore-test` for verification

## Support

For issues or questions:
- Documentation: [docs/backup-strategy.md](../docs/backup-strategy.md)
- Runbook: [docs/runbooks/backup-restore.md](../docs/runbooks/backup-restore.md)
- Operations: ops@contentcreationcrew.com

