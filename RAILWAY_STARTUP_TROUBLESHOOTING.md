# Railway Application Startup Troubleshooting

## Error: "Application failed to respond"

This means the build succeeded, but the application crashed or isn't starting properly.

## Common Causes & Fixes

### 1. Missing Environment Variables

**Check Railway Dashboard → Your Service → Variables**

Required variables:
```
SECRET_KEY=your-strong-secret-key-min-32-characters
DATABASE_URL=postgresql://... (if using PostgreSQL)
OLLAMA_BASE_URL=http://your-ollama-instance:11434
```

**How to fix:**
1. Go to Railway Dashboard → Your Service → Variables
2. Add missing environment variables
3. Redeploy service

### 2. Database Connection Issues

**Symptoms:**
- Application crashes on startup
- Database connection errors in logs

**Fix:**
- If using PostgreSQL: Add PostgreSQL service in Railway and use provided `DATABASE_URL`
- If using SQLite: Ensure `/app/data` directory exists (Dockerfile creates this)

### 3. Port Configuration

**Check:**
- Railway automatically sets `PORT` environment variable
- Application should use `os.getenv("PORT", 8000)`
- Verify in `api_server.py` line 1095

### 4. Import Errors

**Check deploy logs for:**
- `ModuleNotFoundError`
- `ImportError`
- `content_creation_crew` import failures

**Fix:**
- Verify `PYTHONPATH=/app/src:/app` is set in Dockerfile
- Check that package installation succeeded

### 5. Application Crashes on Startup

**Check deploy logs for:**
- Python tracebacks
- Error messages
- Stack traces

**Common issues:**
- Missing dependencies
- Configuration errors
- Database initialization failures

## Step-by-Step Debugging

### Step 1: Check Deploy Logs

1. Go to Railway Dashboard → Your Service
2. Click **"Deployments"** tab
3. Click on the latest deployment
4. Click **"Deploy Logs"** (not Build Logs)
5. Look for:
   - Error messages
   - Stack traces
   - "Application started" messages
   - Port binding messages

### Step 2: Verify Environment Variables

In Railway Dashboard → Variables, ensure you have:

**Minimum Required:**
```
SECRET_KEY=<generate-a-strong-key>
```

**If using PostgreSQL:**
```
DATABASE_URL=<railway-provides-this>
```

**If using Ollama:**
```
OLLAMA_BASE_URL=http://your-ollama:11434
```

### Step 3: Check Health Endpoint

After deployment, test:
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "content-creation-crew"}
```

### Step 4: Verify Startup Command

In Railway Dashboard → Settings → Deploy:
- **Start Command**: `python api_server.py`
- Should match `railway.json` configuration

## Quick Fixes

### Fix 1: Add Missing SECRET_KEY

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to Railway Variables:
```
SECRET_KEY=<generated-key>
```

### Fix 2: Check Database URL

If using PostgreSQL:
1. Add PostgreSQL service in Railway
2. Railway provides `DATABASE_URL` automatically
3. Verify it's set in Variables

If using SQLite:
- Application should work without `DATABASE_URL`
- Database file created in `/app/data`

### Fix 3: Verify Port Binding

Check deploy logs for:
```
Starting Content Creation Crew API server on port XXXX
```

If you see port errors, verify:
- Railway sets `PORT` automatically
- Application reads `os.getenv("PORT", 8000)`

## Common Error Messages

### "ModuleNotFoundError: No module named 'content_creation_crew'"
**Fix:** Check PYTHONPATH in Dockerfile, verify package installation

### "Database connection failed"
**Fix:** Check DATABASE_URL, verify PostgreSQL service is running

### "SECRET_KEY not set"
**Fix:** Add SECRET_KEY to Railway Variables

### "Port already in use"
**Fix:** Railway handles ports automatically, shouldn't happen

### "Application failed to respond"
**Fix:** Check deploy logs for actual error, usually one of above

## Verification Checklist

- [ ] Build succeeded (check Build Logs)
- [ ] All required environment variables set
- [ ] Deploy logs show application starting
- [ ] Health endpoint responds: `/health`
- [ ] No Python errors in deploy logs
- [ ] Port is being used correctly
- [ ] Database connection works (if using DB)

## Next Steps

1. ✅ Check Deploy Logs (not Build Logs)
2. ✅ Verify all environment variables
3. ✅ Test health endpoint
4. ✅ Check for Python errors in logs
5. ✅ Verify database connection (if applicable)

## Getting Help

If still failing:
1. Copy full error from Deploy Logs
2. Check Railway status page
3. Contact Railway support with:
   - Service name
   - Deployment ID
   - Error logs
   - Environment variables (without values)

