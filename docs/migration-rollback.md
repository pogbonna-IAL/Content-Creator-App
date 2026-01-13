# Migration Rollback Procedures

## Overview

This document describes how to safely rollback database migrations, including data-loss risks and recovery procedures.

## ⚠️ Important Warnings

### When Rollbacks Are Safe

- ✅ **Development/Staging** environments
- ✅ **Immediately after deployment** (before new data is written)
- ✅ **Testing rollback procedures** (on staging)
- ✅ **Non-destructive migrations** (adding columns, indexes)

### When Rollbacks Are Dangerous

- ❌ **Production with live data** (may cause data loss)
- ❌ **After data has been written** using new schema
- ❌ **Destructive migrations** (dropping columns, tables)
- ❌ **Data migrations** (may lose transformed data)

---

## Rollback Procedures

### Check Current Migration Status

**Before rolling back, always check:**
```bash
# Check current revision
alembic current

# Or using Makefile
make migrate-current

# Or using migrate_db.py
python migrate_db.py current
```

**Output Example:**
```
Current database revision: 0607bc5b8536
Latest migration available: 0607bc5b8536
```

### Rollback One Migration

**Method 1: Using Makefile (Recommended)**
```bash
make migrate-down-one
```

**Method 2: Using Alembic**
```bash
# Rollback one revision
alembic downgrade -1

# Or explicitly
alembic downgrade 0607bc5b8535
```

**Method 3: Using migrate_db.py**
```bash
# Rollback one revision
python migrate_db.py downgrade

# Or to specific revision
python migrate_db.py downgrade 0607bc5b8535
```

**Method 4: Docker**
```bash
docker compose exec api alembic downgrade -1
```

### Rollback Multiple Migrations

**Rollback to Specific Revision:**
```bash
# Rollback to revision 0607bc5b8535
alembic downgrade 0607bc5b8535

# Or using migrate_db.py
python migrate_db.py downgrade 0607bc5b8535
```

**Rollback Multiple Steps:**
```bash
# Rollback 3 revisions
alembic downgrade -3
```

**⚠️ Warning:** Rolling back multiple migrations increases data loss risk!

### Verify Rollback Success

**After rollback:**
```bash
# Check current revision
alembic current

# Verify application still works
curl http://localhost:8000/health

# Check database schema
psql $DATABASE_URL -c "\d users"
```

---

## Data Loss Risks by Migration Type

### 1. Adding Columns (Low Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('preferences', sa.JSON()))

def downgrade() -> None:
    op.drop_column('users', 'preferences')
```

**Risk Level:** 🟢 **LOW**

**Data Loss:** None (column didn't exist before)

**Rollback Safety:** ✅ Safe if no data was written to new column

**Considerations:**
- If application wrote data to new column, rollback will lose that data
- Check if column has data before rolling back:
  ```sql
  SELECT COUNT(*) FROM users WHERE preferences IS NOT NULL;
  ```

### 2. Removing Columns (HIGH Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.drop_column('users', 'old_preferences')

def downgrade() -> None:
    op.add_column('users', sa.Column('old_preferences', sa.String()))
```

**Risk Level:** 🔴 **HIGH**

**Data Loss:** All data in removed column is lost permanently

**Rollback Safety:** ❌ **NOT SAFE** - Data cannot be recovered

**Mitigation:**
- Never rollback migrations that drop columns
- If rollback needed, restore from backup instead
- Create new migration to restore column (data will be NULL)

### 3. Modifying Columns (Medium Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.alter_column('users', 'email', type_=sa.String(255))

def downgrade() -> None:
    op.alter_column('users', 'email', type_=sa.String(100))
```

**Risk Level:** 🟡 **MEDIUM**

**Data Loss:** Possible if data doesn't fit in smaller type

**Rollback Safety:** ⚠️ **RISKY** - May fail if data exceeds limits

**Check Before Rollback:**
```sql
-- Check if any emails exceed 100 characters
SELECT COUNT(*) FROM users WHERE LENGTH(email) > 100;
```

### 4. Adding Tables (Low Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.create_table('user_preferences', ...)

def downgrade() -> None:
    op.drop_table('user_preferences')
```

**Risk Level:** 🟢 **LOW**

**Data Loss:** All data in new table is lost

**Rollback Safety:** ✅ Safe if table is empty or data can be recreated

**Considerations:**
- Check if table has important data:
  ```sql
  SELECT COUNT(*) FROM user_preferences;
  ```

### 5. Removing Tables (HIGH Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.drop_table('old_sessions')

def downgrade() -> None:
    op.create_table('old_sessions', ...)
```

**Risk Level:** 🔴 **HIGH**

**Data Loss:** All table data is lost permanently

**Rollback Safety:** ❌ **NOT SAFE** - Data cannot be recovered

**Mitigation:**
- Never rollback migrations that drop tables
- Restore from backup if rollback needed

### 6. Data Migrations (HIGH Risk)

**Migration Example:**
```python
def upgrade() -> None:
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")

def downgrade() -> None:
    op.execute("UPDATE users SET status = NULL WHERE status = 'active'")
```

**Risk Level:** 🔴 **HIGH**

**Data Loss:** Transformed data may be lost

**Rollback Safety:** ⚠️ **RISKY** - May lose data transformations

**Considerations:**
- Rollback may not perfectly reverse transformation
- Check data before/after rollback
- Consider restoring from backup instead

---

## Rollback Checklist

### Before Rollback

- [ ] **Backup Database**
  ```bash
  # PostgreSQL backup
  pg_dump -Fc $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).dump
  ```

- [ ] **Check Current Revision**
  ```bash
  alembic current
  ```

- [ ] **Review Migration File**
  ```bash
  cat alembic/versions/0607bc5b8536_*.py
  ```

- [ ] **Assess Data Loss Risk**
  - Check if migration is destructive
  - Check if new data was written
  - Review migration's `downgrade()` function

- [ ] **Notify Team** (if production)
  - Inform about rollback plan
  - Get approval if needed

### During Rollback

- [ ] **Run Rollback Command**
  ```bash
  alembic downgrade -1
  ```

- [ ] **Monitor for Errors**
  - Watch for constraint violations
  - Check for missing dependencies
  - Verify rollback completes

### After Rollback

- [ ] **Verify Database State**
  ```bash
  alembic current
  ```

- [ ] **Test Application**
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] **Check Data Integrity**
  ```sql
  -- Verify critical tables still exist
  SELECT COUNT(*) FROM users;
  SELECT COUNT(*) FROM content_jobs;
  ```

- [ ] **Monitor Application Logs**
  - Check for errors related to schema
  - Verify features still work

---

## Recovery Procedures

### If Rollback Fails

**Scenario 1: Constraint Violation**
```
ERROR: cannot drop column "email" because other objects depend on it
```

**Solution:**
1. Check what depends on the column:
   ```sql
   SELECT * FROM pg_depend WHERE objid = 'users.email'::regclass;
   ```
2. Drop dependencies first (indexes, foreign keys)
3. Retry rollback

**Scenario 2: Data Doesn't Fit**
```
ERROR: value too long for type character varying(100)
```

**Solution:**
1. **Option A:** Fix data first, then rollback
   ```sql
   UPDATE users SET email = LEFT(email, 100) WHERE LENGTH(email) > 100;
   ```
2. **Option B:** Restore from backup (safer)

**Scenario 3: Missing Migration File**
```
ERROR: Can't locate revision identified by '0607bc5b8536'
```

**Solution:**
1. Check if migration file exists:
   ```bash
   ls alembic/versions/0607bc5b8536_*.py
   ```
2. Restore from git if missing:
   ```bash
   git checkout alembic/versions/0607bc5b8536_*.py
   ```
3. Retry rollback

### If Rollback Succeeds But Application Breaks

**Symptoms:**
- Application errors about missing columns/tables
- Database errors in logs
- Features not working

**Solution:**
1. **Immediate:** Restore from backup
   ```bash
   pg_restore -d $DATABASE_URL backup_YYYYMMDD_HHMMSS.dump
   ```

2. **Long-term:** Fix forward with new migration
   - Don't rollback again
   - Create new migration to fix issues
   - Deploy fix forward

---

## Production Rollback Policy

### Policy: Forward-Only Migrations

**Default:** Migrations in production are **forward-only**

**Rationale:**
- Rollbacks can cause data loss
- Production data may depend on new schema
- Safer to fix forward with new migration

### When Rollbacks Are Allowed

**Allowed:**
- ✅ Immediately after deployment (< 5 minutes)
- ✅ With explicit approval from team lead
- ✅ With database backup verified
- ✅ Non-destructive migrations only

**Not Allowed:**
- ❌ After data has been written using new schema
- ❌ Destructive migrations (drop columns/tables)
- ❌ Without database backup
- ❌ Without team approval

### Rollback Approval Process

1. **Assess Impact**
   - Review migration file
   - Check data loss risks
   - Estimate downtime

2. **Get Approval**
   - Team lead approval required
   - Document decision

3. **Backup Database**
   - Create verified backup
   - Test backup restore

4. **Execute Rollback**
   - Run during maintenance window
   - Monitor closely

5. **Verify Success**
   - Check application health
   - Verify data integrity
   - Monitor for issues

---

## Testing Rollback Procedures

### Automated Rollback Test

**Script:** `scripts/test_migration_rollback.sh`

**What it does:**
1. Applies all migrations
2. Rolls back one revision
3. Re-applies migration
4. Verifies database state

**Usage:**
```bash
bash scripts/test_migration_rollback.sh
```

**Expected Output:**
```
✓ Applying migrations...
✓ Current revision: 0607bc5b8536
✓ Rolling back one revision...
✓ Current revision: 0607bc5b8535
✓ Re-applying migration...
✓ Current revision: 0607bc5b8536
✓ Rollback test passed!
```

### Manual Rollback Test (Staging)

**Steps:**
1. Deploy to staging
2. Apply migrations
3. Verify application works
4. Rollback one migration
5. Verify rollback works
6. Re-apply migration
7. Verify re-application works

---

## Examples

### Example 1: Safe Rollback (Adding Column)

**Migration:**
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('preferences', sa.JSON()))

def downgrade() -> None:
    op.drop_column('users', 'preferences')
```

**Rollback:**
```bash
# Check if column has data
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE preferences IS NOT NULL;"

# If empty or acceptable, rollback
alembic downgrade -1

# Verify
alembic current
# Expected: Previous revision
```

**Risk:** 🟢 Low (no data loss if column empty)

### Example 2: Dangerous Rollback (Dropping Column)

**Migration:**
```python
def upgrade() -> None:
    op.drop_column('users', 'old_preferences')

def downgrade() -> None:
    op.add_column('users', sa.Column('old_preferences', sa.String()))
```

**Rollback:**
```bash
# ⚠️ WARNING: This will lose data!
# Check if column had data (can't check after drop)
# If rollback needed, restore from backup instead:

# DON'T DO THIS:
# alembic downgrade -1  # Column restored but data is NULL

# DO THIS INSTEAD:
pg_restore -d $DATABASE_URL backup_before_migration.dump
```

**Risk:** 🔴 High (data permanently lost)

---

## Related Documentation

- [Database Migration Strategy](./db-migrations.md) - Migration workflow
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

