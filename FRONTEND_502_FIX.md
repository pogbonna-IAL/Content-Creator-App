# Frontend 502 Bad Gateway Fix

## Error: 502 Bad Gateway on Frontend

This means Railway's gateway can't reach your frontend application. The app is either:
1. Not starting
2. Crashing after starting
3. Not listening on the correct port
4. Build/startup error

## Immediate Steps

### Step 1: Check Frontend Deploy Logs (CRITICAL!)

1. Go to **Railway Dashboard** → **Frontend Service** (`content-creator-user-app`)
2. Click **"Deployments"** tab
3. Click the **latest deployment**
4. Click **"Deploy Logs"** (NOT Build Logs)
5. **Look for:**
   - "Starting server" or "Starting Next.js" messages
   - Error messages
   - Port binding messages
   - Application crash messages

### Step 2: Check Build Logs

1. Same deployment → Click **"Build Logs"**
2. **Look for:**
   - ✅ Build succeeded
   - ❌ Build failed
   - Missing dependencies
   - TypeScript errors
   - Next.js build errors

## Common Issues & Fixes

### Issue 1: Next.js Standalone Build Failed

**Symptoms:**
- Build logs show errors
- No `server.js` file created
- Standalone output missing

**Fix:**
- Check `next.config.js` has `output: 'standalone'`
- Verify build completes successfully
- Check for TypeScript/build errors

### Issue 2: Application Not Starting

**Symptoms:**
- Build succeeded but no "Starting server" in deploy logs
- Application exits immediately

**Fix:**
- Check deploy logs for startup errors
- Verify `package.json` has correct start script
- Check if `server.js` exists (for standalone) or use `npm start`

### Issue 3: Port Binding Issue

**Symptoms:**
- Application starts but 502 persists
- Port might be wrong

**Fix:**
- Verify Railway sets `PORT` automatically
- Check application binds to `0.0.0.0` (not `127.0.0.1`)
- Verify `PORT` env var is used correctly

### Issue 4: Missing Dependencies

**Symptoms:**
- "Module not found" errors
- Runtime errors about missing packages

**Fix:**
- Check `package.json` has all dependencies
- Verify `npm ci` or `npm install` succeeded
- Check build logs for installation errors

### Issue 5: NEXT_PUBLIC_API_URL Not Set

**Symptoms:**
- Build might succeed but runtime errors
- API calls fail

**Fix:**
- Set `NEXT_PUBLIC_API_URL` in Railway Variables
- **Must rebuild** if you change it (used at build time)
- Use HTTPS URL: `https://your-backend.up.railway.app`

## Quick Fixes

### Fix 1: Verify Start Command

In Railway Dashboard → Frontend Service → Settings → Deploy:
- **Start Command**: Should be `node server.js || npm start`
- Or leave empty (Railway uses Dockerfile CMD)

### Fix 2: Check Port Configuration

Verify in deploy logs:
- `PORT` environment variable is set
- Application uses `PORT` env var (not hardcoded 3000)
- Application binds to `0.0.0.0` (not `127.0.0.1`)

### Fix 3: Verify Standalone Build

Check build logs for:
- `Creating an optimized production build`
- `Standalone build complete`
- `.next/standalone` directory created

### Fix 4: Check Environment Variables

In Railway Dashboard → Frontend Service → Variables:
- `NEXT_PUBLIC_API_URL` should be set (if needed)
- `PORT` is set automatically (don't set manually)
- `NODE_ENV=production` (optional, Railway sets this)

## Debugging Steps

### 1. Check Railway Metrics

Go to Railway Dashboard → Frontend Service → Metrics:
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

### 3. Review Deploy Logs

Look for these patterns:

**Success Pattern:**
```
> next start
Ready on http://0.0.0.0:3000
```

**Failure Patterns:**
```
Error: ...
Module not found: ...
Port XXXX is already in use
Failed to start server
```

## Verification Checklist

- [ ] Checked Deploy Logs (found actual error or startup message)
- [ ] Checked Build Logs (build succeeded)
- [ ] Verified application shows "Starting server" or "Ready"
- [ ] Checked for errors after startup
- [ ] Verified PORT is set correctly
- [ ] Checked Railway Metrics (CPU/Memory > 0)
- [ ] Verified NEXT_PUBLIC_API_URL is set (if needed)
- [ ] Tested frontend URL manually

## What to Look For in Logs

### Build Logs Should Show:
```
Creating an optimized production build
Compiled successfully
Standalone build complete
```

### Deploy Logs Should Show:
```
Starting server...
Ready on http://0.0.0.0:XXXX
```

### If You See Errors:
- Copy the exact error message
- Check what line/file it's failing on
- Look for missing dependencies
- Check for port binding issues

## Next Steps

1. ✅ **Check Deploy Logs** - Find the actual error
2. ✅ **Check Build Logs** - Verify build succeeded
3. ✅ **Verify Application Starts** - Look for startup messages
4. ✅ **Check for Runtime Errors** - Errors after startup
5. ✅ **Verify Port Binding** - Application listening on correct port

## Most Likely Causes (in order)

1. **Application crashes after startup** - Check deploy logs for runtime errors
2. **Build failed** - Check build logs for errors
3. **Port binding issue** - Check PORT env var and binding address
4. **Missing dependencies** - Check for ModuleNotFoundError
5. **Start command wrong** - Verify start command in Railway

**The key is checking the Deploy Logs** - that will tell you exactly what's failing!

Share what you see in the deploy logs and I can help fix the specific issue.

