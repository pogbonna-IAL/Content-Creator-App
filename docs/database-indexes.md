# Database Indexes Documentation

## Overview

Database indexes have been added to optimize common query patterns and ensure production performance.

## Indexes Added

### 1. users(email) unique

**Status:** ✅ Already exists (from initial migration)

**Purpose:** Fast user lookup by email during authentication

**Query Pattern:**
```sql
SELECT * FROM users WHERE email = ?;
```

### 2. memberships(org_id, user_id)

**Index Name:** `idx_memberships_org_user`

**Purpose:** Fast membership lookups when filtering by organization and user

**Query Pattern:**
```sql
SELECT * FROM memberships WHERE org_id = ? AND user_id = ?;
SELECT * FROM memberships WHERE org_id = ?;
```

**Migration:** `0607bc5b8537`

### 3. subscriptions(org_id, status)

**Index Name:** `idx_subscriptions_org_status`

**Purpose:** Fast subscription filtering by organization and status

**Query Pattern:**
```sql
SELECT * FROM subscriptions WHERE org_id = ? AND status = ?;
SELECT * FROM subscriptions WHERE org_id = ?;
```

**Migration:** `0607bc5b8537`

### 4. usage_counters(org_id, period_month)

**Index Name:** `idx_usage_counters_org_period`

**Purpose:** Fast usage counter lookups by organization and period

**Query Pattern:**
```sql
SELECT * FROM usage_counters WHERE org_id = ? AND period_month = ?;
SELECT * FROM usage_counters WHERE org_id = ?;
```

**Note:** Already has unique constraint, but explicit index improves query performance

**Migration:** `0607bc5b8537`

### 5. content_jobs(org_id, created_at DESC)

**Index Name:** `idx_content_jobs_org_created_desc`

**Purpose:** Fast job listing by organization, ordered by creation date (newest first)

**Query Pattern:**
```sql
SELECT * FROM content_jobs 
WHERE org_id = ? 
ORDER BY created_at DESC 
LIMIT ? OFFSET ?;
```

**Migration:** `0607bc5b8537`

### 6. content_jobs(status)

**Index Name:** `idx_content_jobs_status`

**Purpose:** Fast job filtering by status

**Query Pattern:**
```sql
SELECT * FROM content_jobs WHERE status = ?;
```

**Note:** Already has index from model definition, but migration ensures it exists

**Migration:** `0607bc5b8537`

### 7. content_artifacts(job_id, type)

**Index Name:** `idx_content_artifacts_job_type`

**Status:** ✅ Already exists (from model definition)

**Purpose:** Fast artifact lookups by job and type

**Query Pattern:**
```sql
SELECT * FROM content_artifacts WHERE job_id = ? AND type = ?;
SELECT * FROM content_artifacts WHERE job_id = ?;
```

### 8. billing_events(provider, provider_event_id) unique

**Constraint Name:** `uq_billing_events_provider_event_id`

**Purpose:** Prevent duplicate webhook processing and fast lookups

**Query Pattern:**
```sql
SELECT * FROM billing_events WHERE provider = ? AND provider_event_id = ?;
```

**Migration:** `0607bc5b8537`

## Migration

### Apply Migration

```bash
# Using Makefile
make migrate-up

# Using Alembic directly
alembic upgrade head
```

### Rollback Migration

```bash
# Using Makefile
make migrate-down-one

# Using Alembic directly
alembic downgrade -1
```

## Verification

### Check Indexes Exist

**Using psql:**
```sql
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public'
AND tablename IN ('users', 'memberships', 'subscriptions', 'usage_counters', 
                 'content_jobs', 'content_artifacts', 'billing_events')
ORDER BY tablename, indexname;
```

**Using Integration Test:**
```bash
pytest tests/integration/test_critical_flows.py::TestDatabaseMigration::test_key_indexes_exist -v
```

### Verify Index Usage

**Check if indexes are being used:**
```sql
EXPLAIN ANALYZE 
SELECT * FROM content_jobs 
WHERE org_id = 1 
ORDER BY created_at DESC 
LIMIT 10;
```

Look for `Index Scan` or `Index Only Scan` in the query plan.

## Performance Impact

### Expected Improvements

1. **Membership Lookups:** 10-100x faster for org/user queries
2. **Subscription Filtering:** 5-50x faster for org/status queries
3. **Usage Counter Lookups:** 10-100x faster for org/period queries
4. **Job Listing:** 5-20x faster for org-sorted queries
5. **Status Filtering:** 2-10x faster for status-based queries
6. **Webhook Deduplication:** Prevents duplicate processing, improves reliability

### Monitoring

Monitor index usage with:
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## Maintenance

### Index Maintenance

PostgreSQL automatically maintains indexes, but you can:

**Rebuild indexes (if needed):**
```sql
REINDEX INDEX idx_content_jobs_org_created_desc;
```

**Analyze tables (update statistics):**
```sql
ANALYZE content_jobs;
```

### Index Size

Check index sizes:
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Related Documentation

- [Database Migrations](./db-migrations.md) - Migration strategy
- [Migration Rollback](./migration-rollback.md) - Rollback procedures
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**Migration:** `0607bc5b8537`  
**Status:** ✅ Production Ready

