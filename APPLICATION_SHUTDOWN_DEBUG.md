# Application Shutdown Debug Guide

## Log Message: "Application shutdown complete"

This means the application started but then shut down. This could indicate:
1. Application crashed after starting
2. Health check failed and Railway restarted it
3. Runtime error caused exit
4. Application is in a restart loop

## Immediate Steps

### Step 1: Check Full Deploy Logs

1. Go to Railway Dashboard → Backend Service
2. Click **"Deployments"** tab
3. Click the **latest deployment**
4. Click **"Deploy Logs"**
5. **Scroll up** from the shutdown message to see:
   - What happened before shutdown
   - Any error messages
   - Application startup messages
   - Runtime errors

### Step 2: Look for Error Patterns

**Before shutdown, you should see:**
- Application startup messages
- Database connection attempts
- Any error messages
- Health check attempts

**Common patterns:**

**Pattern 1: Application Started Then Crashed**
```
Starting Content Creation Crew API server on port XXXX
[some error here]
Application shutdown complete.
```

**Pattern 2: Health Check Failed**
```
Starting server...
[no errors, but health check fails]
Application shutdown complete.
```

**Pattern 3: Database Connection Failed**
```
Testing database connection...
Database connection test failed: ...
[application continues]
[then crashes later]
Application shutdown complete.
```

**Pattern 4: Import/Runtime Error**
```
Starting server...
[error during import or runtime]
Application shutdown complete.
```

### Step 3: Check for Restart Loops

1. Go to Railway Dashboard → Backend Service
2. Check **"Deployments"** tab
3. Look for multiple recent deployments
4. If you see many deployments in short time = restart loop

**Signs of restart loop:**
- Multiple deployments in last few minutes
- Each deployment shows "Application shutdown complete"
- Service keeps restarting

## Common Causes & Fixes

### Cause 1: Health Check Failing

**Symptoms:**
- Application starts
- Health check fails
- Railway restarts service
- Loop continues

**Fix:**
- Check health endpoint is accessible: `/health`
- Verify PORT is set correctly
- Check application binds to `0.0.0.0` (not `127.0.0.1`)

### Cause 2: Runtime Error After Startup

**Symptoms:**
- Application starts successfully
- Then crashes with error
- Shuts down

**Fix:**
- Check deploy logs for error message
- Look for Python tracebacks
- Fix the specific error

### Cause 3: Database Connection Issues

**Symptoms:**
- Database connection fails
- Application tries to use database
- Crashes when accessing DB

**Fix:**
- Verify DATABASE_URL is set correctly
- Check PostgreSQL service is running
- With our fixes, app should continue even if DB fails

### Cause 4: Port Binding Issues

**Symptoms:**
- Port already in use
- Can't bind to port
- Application exits

**Fix:**
- Railway sets PORT automatically
- Verify application uses `os.getenv("PORT", 8000)`
- Check no other process using the port

### Cause 5: Memory/Resource Issues

**Symptoms:**
- Application starts
- Runs out of memory
- Gets killed

**Fix:**
- Check Railway Metrics → Memory usage
- Optimize application if using too much memory
- Railway provides adequate resources usually

## Debugging Steps

### 1. Check What Happened Before Shutdown

In deploy logs, look for messages **before** "Application shutdown complete":
- Error messages
- Tracebacks
- "Failed to start server"
- Database errors
- Import errors

### 2. Check Railway Metrics

Go to Railway Dashboard → Backend Service → Metrics:
- **CPU Usage**: Should be > 0 if running
- **Memory Usage**: Check if it's too high
- **Request Count**: Should show requests if working
- **Error Rate**: Check for errors

### 3. Check Service Status

In Railway Dashboard:
- Is service showing as "Running" or "Restarting"?
- Are there multiple recent deployments?
- Any error indicators?

### 4. Review Recent Changes

Since we just:
- Added `psycopg2-binary` dependency
- Fixed database connection handling
- Added better error handling

Check if:
- Build completed successfully
- New code deployed
- Any new errors appeared

## What to Look For in Logs

### Success Pattern:
```
==================================================
Content Creation Crew API - Starting Up
==================================================
Starting Content Creation Crew API server on port XXXX
Ready on http://0.0.0.0:XXXX
```

### Failure Pattern:
```
Starting server...
[ERROR MESSAGE HERE]
Application shutdown complete.
```

## Quick Fixes

### Fix 1: Check for Specific Error

**Most important:** Find the error message **before** "Application shutdown complete"
- Copy the exact error
- Look for Python tracebacks
- Check for specific error types

### Fix 2: Verify Health Check

If health check is failing:
- Check `/health` endpoint exists
- Verify it returns 200 OK
- Test manually: `curl https://your-backend.up.railway.app/health`

### Fix 3: Check Database Connection

If database-related:
- Verify DATABASE_URL is set
- Check PostgreSQL is running
- With our fixes, app should continue even if DB fails

### Fix 4: Increase Health Check Timeout

If app takes time to start:
- In `railway.json`, increase `healthcheckTimeout`
- Give app more time to start

## Next Steps

1. ✅ **Check deploy logs** - Find error before shutdown
2. ✅ **Look for error messages** - Copy exact error
3. ✅ **Check Railway Metrics** - See resource usage
4. ✅ **Verify service status** - Running or restarting?
5. ✅ **Review recent changes** - Did new code cause issue?

## Most Important: Find the Error

The key is finding what happened **before** "Application shutdown complete". 

**Share:**
- What do you see in deploy logs before shutdown?
- Any error messages or tracebacks?
- Is the service restarting repeatedly?

Once we see the actual error, we can fix it!

