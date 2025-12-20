# Application Restart/Shutdown Debug

## Log: "Shutting down"

The application is shutting down. This could be:
1. **Normal restart** - Railway restarting the service
2. **Crash** - Application encountered an error
3. **Health check failure** - Railway restarting due to failed health checks
4. **Resource issue** - Memory/CPU limits exceeded

## Immediate Checks

### Step 1: Check if Service is Restarting

1. Go to Railway Dashboard → Backend Service
2. Check **"Deployments"** tab
3. Look for:
   - Multiple recent deployments
   - Service status (Running/Restarting)
   - Any error indicators

**If you see multiple deployments in short time:**
- Service is in restart loop
- Need to find what's causing crashes

**If single shutdown:**
- Might be normal restart
- Check if new deployment starts

### Step 2: Check Deploy Logs Before Shutdown

1. Go to Backend Service → Deployments → Latest
2. Click **"Deploy Logs"**
3. **Scroll up** from "Shutting down" to see:
   - What happened before shutdown
   - Any error messages
   - Health check failures
   - Resource warnings

### Step 3: Check Railway Metrics

Go to Railway Dashboard → Backend Service → Metrics:
- **CPU Usage**: Was it high before shutdown?
- **Memory Usage**: Was it high before shutdown?
- **Request Count**: How many requests before shutdown?
- **Error Rate**: Any errors before shutdown?

## Common Causes

### Cause 1: Health Check Failing

**Symptoms:**
- Health checks start failing
- Railway restarts service
- Loop continues

**Check:**
- Look for health check failures in logs
- Verify `/health` endpoint still works
- Check if app becomes unresponsive

**Fix:**
- Ensure health endpoint always responds
- Check for blocking operations
- Verify app doesn't hang

### Cause 2: Memory/Resource Exhaustion

**Symptoms:**
- Memory usage spikes
- Application gets killed
- Railway restarts it

**Check:**
- Railway Metrics → Memory usage
- Look for memory warnings in logs
- Check for memory leaks

**Fix:**
- Optimize memory usage
- Check for memory leaks
- Railway provides adequate resources usually

### Cause 3: Runtime Error After Running

**Symptoms:**
- App runs fine initially
- Then encounters error
- Crashes

**Check:**
- Look for error messages before shutdown
- Check for Python exceptions
- Look for unhandled errors

**Fix:**
- Fix the specific error
- Add error handling
- Check for unhandled exceptions

### Cause 4: Database Connection Issues

**Symptoms:**
- Database connection fails
- App tries to use DB
- Crashes

**Check:**
- Database connection errors in logs
- PostgreSQL service status
- DATABASE_URL correctness

**Fix:**
- Verify DATABASE_URL
- Check PostgreSQL is running
- With our fixes, app should handle DB failures gracefully

### Cause 5: Port/Network Issues

**Symptoms:**
- Port binding issues
- Network errors
- Connection problems

**Check:**
- Port binding errors
- Network connectivity
- Railway network configuration

## What to Look For

### In Deploy Logs Before Shutdown:

**Look for:**
- Error messages
- Tracebacks
- "Out of memory" warnings
- Health check failures
- Database errors
- Import errors
- Runtime exceptions

### In Railway Metrics:

**Check:**
- Memory usage trend (was it increasing?)
- CPU usage (was it high?)
- Request patterns (any spikes?)
- Error rate (any errors before shutdown?)

## Debugging Steps

### 1. Check Logs Chronologically

Read logs from start to shutdown:
1. Application startup
2. Health checks
3. Any requests
4. Any errors
5. Shutdown message

### 2. Check for Patterns

- Does it always shut down after X minutes?
- Does it shut down after certain requests?
- Does it shut down randomly?
- Is there a pattern to the shutdowns?

### 3. Check Service Status

- Is service restarting repeatedly?
- Or was this a one-time shutdown?
- Is new deployment starting?

## Quick Fixes

### Fix 1: Check for Specific Error

**Most important:** Find error message before shutdown
- Copy exact error
- Look for Python tracebacks
- Check for specific error types

### Fix 2: Verify Health Endpoint

If health checks are failing:
- Test manually: `curl https://your-backend.up.railway.app/health`
- Should return 200 OK quickly
- Check response time

### Fix 3: Check Resource Usage

If memory/CPU is high:
- Check Railway Metrics
- Look for resource warnings
- Optimize if needed

### Fix 4: Add More Logging

Add logging to catch what's happening:
- Log before shutdown
- Log resource usage
- Log any errors

## Next Steps

1. ✅ **Check if service restarts** - Is it in a loop?
2. ✅ **Check deploy logs** - What happened before shutdown?
3. ✅ **Check Railway Metrics** - Resource usage patterns
4. ✅ **Look for errors** - Any error messages before shutdown?
5. ✅ **Check service status** - Running or restarting?

## Most Important: Find the Cause

The key is finding what's causing the shutdown:
- Is it an error? (check logs)
- Is it resource exhaustion? (check metrics)
- Is it health check failure? (check health endpoint)
- Is it normal restart? (check if new deployment starts)

**Share:**
- What do you see in logs before shutdown?
- Is the service restarting or stopped?
- Any error messages?
- What do Railway Metrics show?

Once we identify the cause, we can fix it!

