# Database Pool `_do_get()` Error Fix

## Error: `File "/usr/local/lib/python3.11/site-packages/sqlalchemy/pool/impl.py", line 177, in _do_get`

This error occurs when SQLAlchemy cannot get a connection from the pool. This is a critical error that can happen when:
- Pool is exhausted (all connections in use)
- Connection timeout exceeded
- Database connectivity issues
- Pool configuration too aggressive

## Fixes Applied

### 1. Further Reduced Pool Size (Ultra-Minimal)

**Changed:**
- `pool_size`: 3 → **2** (minimal for Railway)
- `max_overflow`: 5 → **3** (minimal overflow)
- `pool_recycle`: 1800 → **900** (15 minutes - very aggressive)
- `pool_timeout`: 20 → **10** (fail very fast)
- `connect_timeout`: 5 → **3** (very short connection timeout)

**Why:**
- Railway instances are extremely small
- Minimal pool = less resource contention
- Faster recycling = fewer stale connections
- Faster timeouts = quicker failure detection

### 2. Added Connection Retry Logic

**Enhanced `get_db()` function:**
- Retry logic for getting connection from pool (up to 3 attempts)
- Exponential backoff between retries
- Only retries on pool-related errors
- Better error detection and handling

**How it works:**
1. Try to get connection from pool (with retry)
2. If successful, yield session
3. Commit on success, rollback on error
4. Always close connection in finally block

### 3. Improved Pool Event Listeners

**Added:**
- Connection ping validation (via `pool_pre_ping`)
- Better logging for connection lifecycle
- Connection tracking

### 4. Added Application Name

**Added to connect_args:**
- `application_name`: "content_creation_crew"
- Helps with connection tracking in PostgreSQL
- Useful for debugging connection issues

## What This Fixes

### Issue 1: Pool Exhaustion

**Symptoms:**
- `_do_get()` errors
- All connections in use

**Fix:**
- Minimal pool size (2 connections)
- Minimal overflow (3 connections)
- Faster connection recycling (15 minutes)
- Retry logic handles temporary pool exhaustion

### Issue 2: Connection Timeout

**Symptoms:**
- Slow connection attempts
- Timeout errors

**Fix:**
- Very short timeouts (3-10 seconds)
- Retry logic with exponential backoff
- Faster failure detection

### Issue 3: Stale Connections

**Symptoms:**
- Connections timeout
- Database disconnects

**Fix:**
- Very aggressive recycling (15 minutes)
- `pool_pre_ping` validates connections
- Better keepalive settings

### Issue 4: Temporary Pool Issues

**Symptoms:**
- Intermittent `_do_get()` errors
- Connection failures

**Fix:**
- Retry logic handles temporary issues
- Exponential backoff prevents thundering herd
- Better error detection

## Expected Behavior

With these fixes:
- ✅ Minimal connection pool (2 connections)
- ✅ Very fast connection recycling (15 minutes)
- ✅ Retry logic for temporary pool issues
- ✅ Better error handling and logging
- ✅ Faster failure detection

## Verification

After deploying, check backend deploy logs for:
```
PostgreSQL engine created successfully with optimized pool settings and event listeners
```

## Monitoring

Watch for these in logs:
- `Database pool error getting connection (attempt X/3): ...` - Retry happening
- `Connection checked out from pool` - Normal operation
- `Connection invalidated: ...` - Connection issue detected

## If Still Having Issues

### Option 1: Use NullPool (Disable Pooling)

If pool issues persist, you can disable pooling entirely:

```python
from sqlalchemy.pool import NullPool

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # No pooling - new connection for each request
    # ... other settings
)
```

**Pros:**
- No pool exhaustion issues
- Simple connection management

**Cons:**
- Slower (new connection per request)
- More database connections
- Higher resource usage

### Option 2: Check Database Connection

1. **Verify PostgreSQL is running:**
   ```bash
   # Check Railway database logs
   # Should see "database system is ready to accept connections"
   ```

2. **Test connection manually:**
   ```python
   import psycopg2
   conn = psycopg2.connect(DATABASE_URL)
   conn.close()
   ```

3. **Check DATABASE_URL:**
   - Verify it's correct in Railway Variables
   - Check for typos or missing parts

### Option 3: Upgrade Railway Plan

If pool issues persist:
- Consider upgrading Railway plan for more resources
- More resources = can handle larger pool
- Better connection stability

## Next Steps

1. ✅ **Commit and push** the updated database.py
2. ✅ **Redeploy backend** service
3. ✅ **Check deploy logs** for pool creation message
4. ✅ **Monitor** for `_do_get()` errors

## Alternative: NullPool Configuration

If errors persist, uncomment this in `database.py`:

```python
from sqlalchemy.pool import NullPool

# In create_database_engine(), change:
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disables pooling
    pool_pre_ping=True,
    # Remove pool_size, max_overflow, pool_recycle, pool_timeout
    connect_args={...}
)
```

The minimal pool settings and retry logic should resolve the `_do_get()` errors!

