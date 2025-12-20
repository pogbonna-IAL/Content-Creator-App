# API URL Configuration Fix

## Issue: NEXT_PUBLIC_API_URL Configuration

The `.env` file shows:
```
NEXT_PUBLIC_API_URL=https://content-creator-app-beta.up.railway.app
```

## Important: Two Places to Configure

### 1. Local Development (`.env` file)
For running locally with `docker-compose` or `npm run dev`

### 2. Railway Deployment (Railway Dashboard)
For production deployment - **THIS IS WHAT RAILWAY USES**

## Step-by-Step Fix

### Step 1: Find Your Backend Railway URL

1. Go to **Railway Dashboard** → **Backend Service**
2. Click on the service
3. Go to **Settings** tab
4. Find **"Public Domain"** or **"Networking"** section
5. Copy the **HTTPS URL** (should look like `https://xxx.up.railway.app`)

**Example:** `https://content-creator-app-beta.up.railway.app`

### Step 2: Update Railway Frontend Environment Variables

1. Go to **Railway Dashboard** → **Frontend Service**
2. Click **Variables** tab
3. Find or add `NEXT_PUBLIC_API_URL`
4. Set it to your backend URL:
   ```
   NEXT_PUBLIC_API_URL=https://content-creator-app-beta.up.railway.app
   ```
5. **Important:** 
   - ✅ Must be HTTPS (not HTTP)
   - ✅ No trailing slash
   - ✅ Must match backend URL exactly

### Step 3: Update Railway Backend CORS

1. Go to **Railway Dashboard** → **Backend Service**
2. Click **Variables** tab
3. Find or add `CORS_ORIGINS`
4. Set it to your frontend URL:
   ```
   CORS_ORIGINS=https://content-creator-user-app.up.railway.app
   ```
5. **Important:**
   - ✅ Must include frontend Railway URL
   - ✅ Use HTTPS
   - ✅ No trailing slash
   - ✅ Can add multiple URLs separated by commas

### Step 4: Update Local `.env` File (Optional)

For local development, update `.env`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note:** Use `http://localhost:8000` for local development, not the Railway URL.

### Step 5: Rebuild Frontend (If URL Changed)

If you changed `NEXT_PUBLIC_API_URL` in Railway:
1. Railway will automatically rebuild
2. Or manually trigger rebuild:
   - Railway Dashboard → Frontend Service
   - Deployments → Redeploy

## Verification

### Check Backend Health
```bash
curl https://content-creator-app-beta.up.railway.app/health
```

**Expected:**
```json
{"status": "healthy", "service": "content-creation-crew"}
```

### Check Frontend Can Connect
1. Open browser console (F12)
2. Visit your frontend URL
3. Check for CORS errors
4. Should see API calls to backend URL

## Common Issues

### Issue 1: Wrong Backend URL
**Symptoms:**
- 404 errors
- Connection refused

**Fix:**
- Verify backend URL in Railway Dashboard
- Update `NEXT_PUBLIC_API_URL` to match exactly

### Issue 2: CORS Errors
**Symptoms:**
- Browser console shows CORS errors
- API calls blocked

**Fix:**
- Add frontend URL to `CORS_ORIGINS` in backend service
- Ensure both URLs use HTTPS

### Issue 3: Using HTTP Instead of HTTPS
**Symptoms:**
- Mixed content errors
- API calls fail

**Fix:**
- Always use HTTPS for Railway URLs
- Never use HTTP for production

### Issue 4: Trailing Slash
**Symptoms:**
- 404 errors
- Double slashes in URL

**Fix:**
- Remove trailing slash from URLs
- Use `https://xxx.up.railway.app` not `https://xxx.up.railway.app/`

## Quick Checklist

- [ ] Found backend Railway URL
- [ ] Set `NEXT_PUBLIC_API_URL` in Railway Frontend Variables
- [ ] Set `CORS_ORIGINS` in Railway Backend Variables
- [ ] Both URLs use HTTPS
- [ ] No trailing slashes
- [ ] Frontend rebuilt after URL change
- [ ] Backend health check passes
- [ ] No CORS errors in browser console

## Next Steps

1. ✅ **Update Railway Variables** - Set `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS`
2. ✅ **Rebuild Frontend** - If URL changed
3. ✅ **Test Connection** - Check browser console for errors
4. ✅ **Verify Backend** - Health check should pass

The `.env` file is only for local development. Railway uses environment variables set in the Railway Dashboard!

