# Fixing 502 Bad Gateway Error on Railway

## What 502 Means

502 Bad Gateway means Railway's gateway can't reach your application. This usually means:
1. Application crashed after starting
2. Application isn't listening on the correct port
3. Application started but then crashed
4. Health check is failing

## Immediate Steps

### Step 1: Check Deploy Logs (CRITICAL!)

1. Go to **Railway Dashboard** → Your Service
2. Click **"Deployments"** tab
3. Click the **latest deployment**
4. Click **"Deploy Logs"**
5. **Look for:**
   - "Starting Content Creation Crew API server on port XXXX"
   - Any error messages after startup
   - Application crash messages
   - Port binding errors

### Step 2: Check if Application Started

In deploy logs, you should see:
```
==================================================
Content Creation Crew API - Starting Up
==================================================
Starting Content Creation Crew API server on port XXXX
```

**If you see this but still get 502:**
- Application started but crashed immediately after
- Check for errors after the startup message
- Look for database connection errors
- Check for import errors

**If you DON'T see this:**
- Application never started
- Check for errors before startup
- Look for import/dependency errors

### Step 3: Verify Port Configuration

Check deploy logs for:
```
PORT: XXXX
```

**Common issues:**
- PORT not set (should be set automatically by Railway)
- Application binding to wrong port
- Application binding to 127.0.0.1 instead of 0.0.0.0

## Common Causes & Fixes

### Issue 1: Application Crashes After Startup

**Symptoms:**
- See "Starting server" in logs
- Then application exits
- 502 errors

**Fix:**
- Check deploy logs for errors after startup
- Common causes:
  - Database connection failing
  - Missing environment variables
  - Runtime errors in application code

### Issue 2: Wrong Port Binding

**Symptoms:**
- Application starts but 502 errors persist
- Port might be wrong

**Fix:**
- Verify application binds to `0.0.0.0` (not `127.0.0.1`)
- Check PORT environment variable is set
- Verify `uvicorn.run(app, host="0.0.0.0", port=port)`

### Issue 3: Database Connection Failing

**Symptoms:**
- Application starts
- Database connection errors in logs
- Application crashes

**Fix:**
- Verify `DATABASE_URL` is correct
- Check PostgreSQL service is running
- Verify `psycopg2-binary` is installed (we just added this)

### Issue 4: Application Not Starting

**Symptoms:**
- No "Starting server" message
- Import errors or dependency errors

**Fix:**
- Check for `ModuleNotFoundError`
- Verify all dependencies installed
- Check build logs for installation errors

## Debugging Steps

### 1. Check Railway Metrics

Go to Railway Dashboard → Your Service → Metrics:
- **CPU Usage**: Should be > 0 if app is running
- **Memory Usage**: Should be > 0 if app is running
- **Request Count**: Should show requests if app is working

**If all are zero:**
- Application isn't running
- Check deploy logs for startup errors

### 2. Check Service Status

In Railway Dashboard:
- Check if service shows as "Running"
- Check if there are restart loops
- Look for error indicators

### 3. Test Health Endpoint

Try accessing:
```
https://your-app.up.railway.app/health
```

**If 502:**
- Application isn't running
- Check deploy logs

**If 200:**
- Application is running
- Issue might be with specific routes

### 4. Review Recent Changes

Since we just added `psycopg2-binary`:
- Verify the rebuild completed successfully
- Check if new build has the dependency
- Look for any new errors in deploy logs

## Quick Fixes

### Fix 1: Verify psycopg2 Installation

After adding `psycopg2-binary`, ensure:
1. Changes are committed and pushed
2. Railway rebuilds with new dependency
3. Build logs show `psycopg2-binary` installed
4. Deploy logs show successful startup

### Fix 2: Check Database Connection

If using PostgreSQL:
1. Verify `DATABASE_URL` is set correctly
2. Check PostgreSQL service is running
3. Test connection manually if possible

### Fix 3: Add More Logging

If logs don't show clear errors, add logging to see what's happening:
- Check the enhanced logging we added
- Look for any error messages
- Check if application reaches startup code

## What to Check in Deploy Logs

Look for these patterns:

**Success Pattern:**
```
Starting Content Creation Crew API server on port XXXX
Health check endpoint: http://0.0.0.0:XXXX/health
```

**Failure Patterns:**
```
Error: ...
Traceback (most recent call last):
Failed to start server: ...
Database connection failed: ...
ModuleNotFoundError: ...
```

## Verification Checklist

- [ ] Checked Deploy Logs (found actual error or startup message)
- [ ] Verified application shows "Starting server" message
- [ ] Checked for errors after startup
- [ ] Verified PORT is set correctly
- [ ] Checked Railway Metrics (CPU/Memory > 0)
- [ ] Tested health endpoint manually
- [ ] Verified psycopg2-binary was installed in build
- [ ] Checked DATABASE_URL is correct

## Next Steps

1. ✅ **Check Deploy Logs** - Find the actual error
2. ✅ **Verify Application Starts** - Look for startup messages
3. ✅ **Check for Runtime Errors** - Errors after startup
4. ✅ **Verify Port Binding** - Application listening on correct port
5. ✅ **Test Health Endpoint** - Verify app responds

## Most Likely Causes (in order)

1. **Application crashes after startup** - Check deploy logs for runtime errors
2. **Database connection failing** - Verify DATABASE_URL and PostgreSQL service
3. **Port binding issue** - Check PORT env var and binding address
4. **Missing dependency** - Verify psycopg2-binary installed (we just added this)
5. **Import errors** - Check for ModuleNotFoundError in logs

The key is **checking the Deploy Logs** to see what's happening after the application starts (or fails to start).

