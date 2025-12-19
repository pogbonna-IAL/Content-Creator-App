# Frontend-Backend Connection Guide

## Frontend is Deployed - Now Verify Connection

Since your frontend is deployed and running, let's verify it can connect to your backend.

## Step 1: Verify Environment Variables

### Frontend Service Variables

In Railway Dashboard → Frontend Service → Variables, ensure:

```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

**Important:**
- ✅ Must be HTTPS (not HTTP)
- ✅ Must match your backend Railway URL exactly
- ✅ No trailing slash
- ✅ Must be set before build (if you change it, rebuild is needed)

### Backend Service Variables

In Railway Dashboard → Backend Service → Variables, ensure:

```
CORS_ORIGINS=https://your-frontend.up.railway.app
```

**Important:**
- ✅ Must include your frontend Railway URL
- ✅ Use HTTPS
- ✅ No trailing slash
- ✅ Can have multiple URLs separated by commas

## Step 2: Test Backend Health

```bash
curl https://your-backend.up.railway.app/health
```

**Expected response:**
```json
{"status": "healthy", "service": "content-creation-crew"}
```

**If it fails:**
- Backend isn't running properly
- Check backend deploy logs
- Verify backend service is running

## Step 3: Test Frontend

1. Open your frontend URL in browser: `https://your-frontend.up.railway.app`
2. Open browser DevTools (F12) → Console tab
3. Look for:
   - ✅ No CORS errors
   - ✅ API calls going to correct backend URL
   - ❌ "Cannot connect to API" errors
   - ❌ CORS errors
   - ❌ 502/404 errors on API calls

## Step 4: Common Connection Issues

### Issue 1: CORS Errors

**Symptoms:**
- Browser console shows CORS errors
- "Access-Control-Allow-Origin" errors

**Fix:**
1. Go to Backend Service → Variables
2. Add/Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://your-frontend.up.railway.app
   ```
3. Redeploy backend (or restart service)

### Issue 2: API Calls Going to Wrong URL

**Symptoms:**
- API calls going to `http://localhost:8000` instead of Railway URL
- "Cannot connect to API" errors

**Fix:**
1. Check `NEXT_PUBLIC_API_URL` in Frontend Service → Variables
2. Verify it's set to your backend Railway URL (HTTPS)
3. **Important:** If you change it, you need to rebuild frontend
4. Redeploy frontend after updating

### Issue 3: Backend Not Responding

**Symptoms:**
- Frontend loads but API calls fail
- 502/503 errors on API endpoints

**Fix:**
1. Check backend deploy logs
2. Verify backend is running
3. Test backend health endpoint manually
4. Check backend service status in Railway

### Issue 4: Authentication Not Working

**Symptoms:**
- Can't login/signup
- Auth errors in console

**Fix:**
1. Verify backend is running
2. Check `NEXT_PUBLIC_API_URL` is correct
3. Check CORS includes frontend URL
4. Test backend auth endpoints manually

## Step 5: Verify Configuration

### Frontend Configuration

Check that frontend is using correct API URL:

1. Open browser console on frontend
2. Type: `process.env.NEXT_PUBLIC_API_URL`
3. Should show your backend Railway URL (HTTPS)

**Note:** This only works if you check during build or in server-side code. For client-side, check Network tab to see actual API calls.

### Backend CORS Configuration

Verify backend allows frontend:

1. Check `api_server.py` CORS configuration
2. Should include your frontend Railway URL
3. Or use `CORS_ORIGINS` environment variable

## Step 6: Test API Connection

### Manual Test

```bash
# Test backend health
curl https://your-backend.up.railway.app/health

# Test backend root
curl https://your-backend.up.railway.app/

# Test from frontend domain (if possible)
curl -H "Origin: https://your-frontend.up.railway.app" \
     https://your-backend.up.railway.app/health
```

### Browser Test

1. Open frontend in browser
2. Open DevTools → Network tab
3. Try to login or make an API call
4. Check the request:
   - ✅ URL should be `https://your-backend.up.railway.app/api/...`
   - ✅ Status should be 200 (not 502/404/CORS error)
   - ✅ Response should be JSON

## Quick Troubleshooting Checklist

- [ ] Frontend URL accessible (loads landing page)
- [ ] Backend URL accessible (`/health` returns 200)
- [ ] `NEXT_PUBLIC_API_URL` set correctly (HTTPS, backend URL)
- [ ] `CORS_ORIGINS` includes frontend URL
- [ ] No CORS errors in browser console
- [ ] API calls go to correct backend URL
- [ ] Backend responds to API calls (not 502/404)

## Common Error Messages

### "Cannot connect to API server"
- **Cause:** `NEXT_PUBLIC_API_URL` wrong or backend down
- **Fix:** Check API URL, verify backend is running

### CORS Error
- **Cause:** Backend doesn't allow frontend origin
- **Fix:** Add frontend URL to `CORS_ORIGINS`

### 502 Bad Gateway
- **Cause:** Backend crashed or not running
- **Fix:** Check backend deploy logs, restart service

### 404 Not Found
- **Cause:** Wrong API endpoint or backend route missing
- **Fix:** Verify API routes exist in backend

## Next Steps

1. ✅ **Verify backend is running** - Test `/health` endpoint
2. ✅ **Check environment variables** - Both frontend and backend
3. ✅ **Test API connection** - Make a test API call
4. ✅ **Check browser console** - Look for errors
5. ✅ **Verify CORS** - No CORS errors in console

If you're still having issues, share:
- What you see in browser console
- What happens when you try to use the frontend
- Any error messages
- Backend health check result

