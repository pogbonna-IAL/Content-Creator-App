# Debug Railway Application Startup Failure

## Step 1: Check Deploy Logs (CRITICAL!)

**This is the most important step - the logs will tell you exactly what's wrong.**

1. Go to **Railway Dashboard** → Your Service
2. Click **"Deployments"** tab  
3. Click the **latest/failed deployment**
4. Click **"Deploy Logs"** (NOT "Build Logs")
5. **Scroll to the bottom** - look for:
   - Error messages
   - Tracebacks
   - "Traceback (most recent call last)"
   - Any red error text

**Copy the error message** - this tells you exactly what's failing.

## Step 2: Common Startup Failures

### Issue 1: Database Initialization Failing

**Error in logs:**
```
Database connection failed
Migration failed
alembic.ini not found
```

**Fix:**
- If using PostgreSQL: Add PostgreSQL service, use provided `DATABASE_URL`
- If using SQLite: Should work automatically
- Check that `alembic.ini` exists in repository root

### Issue 2: Import Errors

**Error in logs:**
```
ModuleNotFoundError: No module named 'content_creation_crew'
ImportError: ...
```

**Fix:**
- Check PYTHONPATH is set: `/app/src:/app`
- Verify package installation succeeded in build logs
- Check that `src/content_creation_crew/__init__.py` exists

### Issue 3: Port Binding Issues

**Error in logs:**
```
Address already in use
Port XXXX is already in use
```

**Fix:**
- Railway handles ports automatically - shouldn't happen
- Verify `PORT` environment variable is being read correctly
- Check `os.getenv("PORT", 8000)` in api_server.py

### Issue 4: Missing Dependencies

**Error in logs:**
```
ModuleNotFoundError: No module named 'X'
```

**Fix:**
- Check build logs - dependency installation might have failed
- Verify all packages in `pyproject.toml` are installed
- Check for version conflicts

### Issue 5: Application Crashes Silently

**No clear error in logs:**
- Application starts but crashes immediately
- No error messages

**Fix:**
- Add more logging to startup code
- Check if `init_db()` is failing silently
- Verify all imports succeed

## Step 3: Add Debugging to Startup

If logs don't show clear errors, add debugging:

**Modify `api_server.py` startup section:**

```python
if __name__ == "__main__":
    import uvicorn
    import sys
    import logging
    
    # Enhanced logging
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Log environment
    logger.info("Environment variables:")
    logger.info(f"PORT: {os.getenv('PORT', 'NOT SET')}")
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
    logger.info(f"PYTHONPATH: {os.getenv('PYTHONPATH', 'NOT SET')}")
    
    # Test imports
    try:
        logger.info("Testing imports...")
        import content_creation_crew
        logger.info("✓ content_creation_crew imported")
    except Exception as e:
        logger.error(f"✗ Import failed: {e}", exc_info=True)
        sys.exit(1)
    
    # Test database
    try:
        logger.info("Testing database connection...")
        from content_creation_crew.database import init_db
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database init failed: {e}", exc_info=True)
        # Don't exit - app might work without DB
    
    # Get port
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}...")
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=port)
```

## Step 4: Verify Environment Variables

In Railway Dashboard → Variables, check:

**Required:**
- `PORT` - Railway sets this automatically (don't set manually)
- `SECRET_KEY` - Has default, but set a strong one for production

**Optional:**
- `DATABASE_URL` - If using PostgreSQL
- `OLLAMA_BASE_URL` - Your Ollama instance
- `PYTHONPATH` - Should be `/app/src:/app` (set in Dockerfile)

## Step 5: Test Health Endpoint

After deployment:

```bash
curl https://your-app.up.railway.app/health
```

**Expected:**
```json
{"status": "healthy", "service": "content-creation-crew"}
```

**If it fails:**
- Check deploy logs for errors
- Verify application is actually running
- Check Railway service status

## Step 6: Check Railway Service Status

1. Go to Railway Dashboard → Your Service
2. Check **"Metrics"** tab
3. Look for:
   - CPU usage
   - Memory usage
   - Request count
   - Error rate

## Quick Diagnostic Commands

**Test locally first:**
```bash
cd content_creation_crew
python api_server.py
```

If local works but Railway doesn't:
- Check environment variables
- Check Railway-specific configuration
- Compare local vs Railway logs

## What to Share for Help

If still stuck, share:
1. **Full error from Deploy Logs** (last 50-100 lines)
2. **Environment variables** (names only, not values)
3. **Railway service configuration** (Root Directory, Dockerfile Path)
4. **Build logs** (to verify build succeeded)

## Most Likely Issues (in order)

1. **Database initialization failing** - Check `init_db()` in logs
2. **Import errors** - Check `ModuleNotFoundError` in logs  
3. **Missing environment variables** - Check Railway Variables
4. **Port binding issues** - Check PORT env var
5. **Silent crash** - Add more logging

## Next Steps

1. ✅ **Check Deploy Logs** - Find actual error
2. ✅ **Add debugging** - If logs don't show errors
3. ✅ **Verify environment variables** - All required vars set
4. ✅ **Test health endpoint** - Verify app responds
5. ✅ **Check Railway metrics** - See if app is running

The key is **checking the Deploy Logs** - that will tell you exactly what's failing!

