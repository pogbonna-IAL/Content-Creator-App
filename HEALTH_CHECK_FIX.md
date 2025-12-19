# Railway Health Check Failure Fix

## Error: "service unavailable" on `/health` endpoint

This means Railway can't reach your application. The app is either:
1. Not starting
2. Crashing before responding
3. Not binding to the correct port
4. Taking too long to start

## Immediate Steps

### Step 1: Check Deploy Logs (CRITICAL!)

**This will tell you exactly what's wrong:**

1. Go to **Railway Dashboard** → Your Service
2. Click **"Deployments"** tab
3. Click the **latest deployment**
4. Click **"Deploy Logs"** (NOT Build Logs)
5. **Look for:**
   - "Starting Content Creation Crew API server on port XXXX"
   - Error messages
   - Tracebacks
   - "Failed to start server"

### Step 2: Verify Application Starts

In deploy logs, you should see:
```
==================================================
Content Creation Crew API - Starting Up
==================================================
Python version: ...
Working directory: /app
PYTHONPATH: /app/src:/app
PORT: XXXX
Testing critical imports...
✓ content_creation_crew imported successfully
Starting Content Creation Crew API server on port XXXX
```

**If you DON'T see "Starting Content Creation Crew API server":**
- Application is crashing before startup
- Check for errors above this line
- Look for import errors, database errors, etc.

### Step 3: Check Port Configuration

Railway sets `PORT` automatically. Verify in logs:
- `PORT: XXXX` (should be a number, not "NOT SET")
- Application should bind to `0.0.0.0:XXXX`

**If PORT is not set:**
- Railway should set it automatically
- Check Railway service settings
- Verify environment variables

### Step 4: Verify Health Endpoint

The health endpoint should be at `/health` and return:
```json
{"status": "healthy", "service": "content-creation-crew"}
```

**Test manually:**
```bash
curl https://your-app.up.railway.app/health
```

**If curl fails:**
- Application isn't running
- Check deploy logs for startup errors
- Verify port binding

## Common Issues & Fixes

### Issue 1: Application Crashes on Startup

**Symptoms:**
- No "Starting server" message in logs
- Error messages or tracebacks
- Application exits immediately

**Fix:**
- Check deploy logs for specific error
- Common causes:
  - Database initialization failing
  - Import errors
  - Missing environment variables
  - Port binding issues

### Issue 2: Application Starts But Health Check Fails

**Symptoms:**
- See "Starting server" in logs
- But health check still fails
- Application might be binding to wrong port

**Fix:**
- Verify `PORT` environment variable is set
- Check that app binds to `0.0.0.0` (not `127.0.0.1`)
- Verify health endpoint is accessible

### Issue 3: Health Check Timeout

**Symptoms:**
- Health check times out
- Application takes too long to start

**Fix:**
- Increase `healthcheckTimeout` in `railway.json`
- Check if application is doing heavy initialization
- Consider lazy initialization

### Issue 4: Wrong Health Check Path

**Symptoms:**
- Health check configured but endpoint doesn't exist
- 404 errors

**Fix:**
- Verify `/health` endpoint exists in `api_server.py`
- Check `railway.json` has correct `healthcheckPath: "/health"`

## Railway Health Check Configuration

Current configuration in `railway.json`:
```json
{
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**What this means:**
- Railway checks `http://localhost:PORT/health`
- Timeout is 100 seconds
- If it fails, Railway retries

## Debugging Steps

### 1. Check if Application is Running

In Railway Dashboard → Metrics:
- Check CPU/Memory usage
- If zero, app isn't running
- If high, app might be stuck

### 2. Check Deploy Logs

Look for these key messages:
- ✅ "Starting Content Creation Crew API server"
- ✅ "Health check endpoint: http://0.0.0.0:XXXX/health"
- ❌ Any error messages
- ❌ "Failed to start server"

### 3. Test Health Endpoint Manually

```bash
# Replace with your Railway URL
curl https://your-app.up.railway.app/health

# Should return:
# {"status": "healthy", "service": "content-creation-crew"}
```

### 4. Check Railway Service Status

1. Go to Railway Dashboard → Your Service
2. Check **"Metrics"** tab
3. Look for:
   - Request count
   - Error rate
   - Response time

## Quick Fixes

### Fix 1: Increase Health Check Timeout

If app takes time to start:
```json
{
  "deploy": {
    "healthcheckTimeout": 200  // Increase from 100 to 200 seconds
  }
}
```

### Fix 2: Verify Port Binding

Ensure application binds to `0.0.0.0`:
```python
uvicorn.run(app, host="0.0.0.0", port=port)
```

### Fix 3: Add Startup Delay

If needed, add a simple delay before starting:
```python
import time
time.sleep(5)  # Wait 5 seconds before starting
uvicorn.run(...)
```

## Verification Checklist

- [ ] Checked Deploy Logs (found actual error or startup message)
- [ ] Application shows "Starting server" message
- [ ] PORT environment variable is set correctly
- [ ] Health endpoint `/health` exists and works
- [ ] Application binds to `0.0.0.0` (not `127.0.0.1`)
- [ ] Tested health endpoint manually with curl
- [ ] Railway Metrics show application is running

## Next Steps

1. ✅ **Check Deploy Logs** - Find the actual error
2. ✅ **Verify Application Starts** - Look for startup messages
3. ✅ **Test Health Endpoint** - Verify it's accessible
4. ✅ **Check Port Binding** - Ensure correct host/port
5. ✅ **Review Railway Metrics** - See if app is running

## Most Likely Cause

Based on the error, the application is **not starting successfully**. Check the **Deploy Logs** to see:
- What error is occurring
- Why the application isn't starting
- What's preventing it from binding to the port

The enhanced logging we added should show exactly what's happening during startup.

