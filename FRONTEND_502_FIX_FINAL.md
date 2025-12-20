# Frontend 502 Bad Gateway - Final Fix

## Error: 502 Bad Gateway on Frontend

The frontend service isn't responding. This means the Next.js application isn't starting properly.

## Critical: Check Frontend Deploy Logs

**This is the most important step:**

1. Go to Railway Dashboard → **Frontend Service** (`content-creator-user-app`)
2. Click **"Deployments"** tab
3. Click the **latest deployment**
4. Click **"Deploy Logs"** (NOT Build Logs)
5. **Look for:**
   - "Starting server" or "Ready on http://0.0.0.0:XXXX"
   - Error messages
   - "Module not found"
   - "server.js not found"
   - Port binding errors

## Common Issues & Fixes

### Issue 1: Standalone Build Failed

**Symptoms:**
- Build logs show errors
- `server.js` file doesn't exist
- Standalone output not created

**Fix:**
- Check build logs for Next.js build errors
- Verify `output: 'standalone'` in `next.config.js`
- Ensure build completes successfully

### Issue 2: server.js Not Found

**Symptoms:**
- "server.js not found" in logs
- Application exits immediately

**Fix:**
- The Dockerfile now checks multiple locations
- Falls back to `npm start` if `server.js` doesn't exist
- Verify standalone build created the file

### Issue 3: Port Binding Issue

**Symptoms:**
- Application starts but 502 persists
- Port might be wrong

**Fix:**
- Railway sets `PORT` automatically
- Application should use `PORT` env var
- Verify binding to `0.0.0.0` (not `127.0.0.1`)

### Issue 4: npm start Failing

**Symptoms:**
- "server.js not found, using npm start..."
- Then npm start fails

**Fix:**
- Check if `.next` directory exists
- Verify `package.json` has correct start script
- Check for missing dependencies

## Fixes Applied

I've updated:

1. **Dockerfile CMD**: More robust checking for `server.js`
   - Checks `./server.js` first
   - Then checks `server.js` in root
   - Falls back to `npm start` if neither exists
   - Uses `PORT` env var correctly

2. **railway.json**: Removed conflicting startCommand
   - Let Dockerfile CMD handle startup
   - Railway will use Dockerfile CMD

## What to Check in Deploy Logs

**Success Pattern:**
```
Starting Next.js standalone server...
Ready on http://0.0.0.0:XXXX
```

**Or:**
```
server.js not found, using npm start...
Ready on http://0.0.0.0:XXXX
```

**Failure Patterns:**
```
Error: ...
Module not found: ...
Port XXXX is already in use
Failed to start server
```

## Verification Steps

### Step 1: Check Build Logs

1. Frontend Service → Deployments → Latest → **Build Logs**
2. Look for:
   - "Creating an optimized production build"
   - "Standalone build complete"
   - Any build errors

### Step 2: Check Deploy Logs

1. Same deployment → **Deploy Logs**
2. Look for:
   - Startup messages
   - "Ready on http://0.0.0.0:XXXX"
   - Error messages

### Step 3: Verify Environment Variables

In Railway Dashboard → Frontend Service → Variables:
- `NEXT_PUBLIC_API_URL` should be set (HTTPS backend URL)
- `PORT` is set automatically (don't set manually)

### Step 4: Test Frontend

After fixes:
```bash
curl https://content-creator-user-app.up.railway.app/
```

Should return HTML (not 502).

## Quick Checklist

- [ ] Checked Build Logs (build succeeded)
- [ ] Checked Deploy Logs (found startup message or error)
- [ ] Verified `NEXT_PUBLIC_API_URL` is set correctly
- [ ] Verified PORT is being used (Railway sets automatically)
- [ ] Tested frontend URL (should work after fix)

## Next Steps

1. ✅ **Commit and push** the updated Dockerfile and railway.json
2. ✅ **Railway will rebuild** frontend automatically
3. ✅ **Check deploy logs** for startup messages
4. ✅ **Test frontend URL** - should work

## Most Likely Causes

1. **server.js not found** - Standalone build didn't create it
2. **npm start failing** - Missing dependencies or wrong path
3. **Port binding issue** - Wrong port or binding address
4. **Build failed** - Check build logs for errors

**The key is checking the Deploy Logs** - that will show exactly what's failing!

Share what you see in the deploy logs and I can help fix the specific issue.

