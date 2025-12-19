# Frontend Deployment Fix - Can't Access Landing Page

## Quick Diagnosis

If you can't access the frontend landing page, check these:

### Step 1: Is Frontend Deployed?

1. Go to **Railway Dashboard** → Your Project
2. Check if you have a **frontend service** (separate from backend)
3. If no frontend service exists, you need to deploy it first

### Step 2: Check Frontend Service Status

1. Go to Railway Dashboard → Frontend Service
2. Check **Deployments** tab
3. Look for:
   - ✅ Build succeeded
   - ✅ Deployment succeeded
   - ❌ Build failed
   - ❌ Deployment failed

### Step 3: Check Deploy Logs

1. Go to Frontend Service → Deployments → Latest
2. Click **"Deploy Logs"**
3. Look for:
   - "Starting server on port XXXX"
   - Error messages
   - Build failures

## Common Issues & Fixes

### Issue 1: Frontend Not Deployed Yet

**Symptoms:**
- Only see backend service in Railway
- No frontend URL available

**Fix: Deploy Frontend Service**

1. **Create New Service:**
   - Railway Dashboard → Your Project
   - Click **"+ New"** → **"GitHub Repo"** (or **"Empty Service"**)
   - Select your repository

2. **Configure Service:**
   - **Service Name**: `frontend` or `web-ui`
   - **Root Directory**: `web-ui` (if deploying from monorepo)
   - **Dockerfile Path**: `web-ui/Dockerfile`

3. **Set Environment Variable (CRITICAL!):**
   - Go to Frontend Service → **Variables**
   - Add: `NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app`
   - **Replace** `your-backend.up.railway.app` with your actual backend URL
   - **Must be HTTPS** (Railway uses HTTPS)
   - **Must be set BEFORE first build** (it's used at build time)

4. **Deploy:**
   - Railway will automatically build and deploy
   - Wait for build to complete
   - Get frontend URL from Railway

### Issue 2: Build Failing

**Symptoms:**
- Build logs show errors
- Deployment fails

**Common Build Errors:**

**Error: "NEXT_PUBLIC_API_URL not set"**
- Fix: Add `NEXT_PUBLIC_API_URL` to Railway Variables before building

**Error: "Module not found"**
- Fix: Check `package.json` has all dependencies
- Verify `npm ci` succeeds

**Error: "TypeScript errors"**
- Fix: Fix TypeScript errors before deploying
- Check `tsconfig.json` configuration

**Error: "Build failed"**
- Fix: Check build logs for specific error
- Common: Missing dependencies, TypeScript errors, memory issues

### Issue 3: Frontend Deployed But 502/404 Errors

**Symptoms:**
- Frontend service shows as deployed
- But can't access landing page
- Getting 502 or 404 errors

**Fix:**

1. **Check Deploy Logs:**
   - Look for "Starting server" message
   - Check for runtime errors
   - Verify port binding

2. **Check Environment Variables:**
   - Verify `NEXT_PUBLIC_API_URL` is set correctly
   - Must be HTTPS URL
   - Must match your backend Railway URL

3. **Check Port Configuration:**
   - Railway sets `PORT` automatically
   - Frontend should use `PORT` env var
   - Verify in deploy logs

4. **Test Health Check:**
   ```bash
   curl https://your-frontend.up.railway.app/
   ```
   - Should return HTML (not 502/404)

### Issue 4: Frontend Works But Can't Connect to Backend

**Symptoms:**
- Frontend loads but shows errors
- "Cannot connect to API" messages
- API calls failing

**Fix:**

1. **Verify NEXT_PUBLIC_API_URL:**
   - Must be set to backend URL: `https://your-backend.up.railway.app`
   - **Must rebuild** if you change it (it's used at build time)

2. **Check Backend CORS:**
   - Backend must allow frontend domain
   - In Backend Service → Variables:
     ```
     CORS_ORIGINS=https://your-frontend.up.railway.app
     ```

3. **Test Backend Health:**
   ```bash
   curl https://your-backend.up.railway.app/health
   ```
   - Should return: `{"status": "healthy"}`

## Step-by-Step Frontend Deployment

### 1. Deploy Frontend Service

**Option A: Separate Service (Recommended)**

1. Railway Dashboard → Your Project
2. Click **"+ New"** → **"GitHub Repo"**
3. Select your repository
4. Configure:
   - **Root Directory**: `web-ui`
   - **Dockerfile Path**: `web-ui/Dockerfile` (or Railway auto-detects)

**Option B: From Monorepo**

- Railway should detect `web-ui/Dockerfile`
- Set Root Directory to `web-ui` if needed

### 2. Set Environment Variables

**CRITICAL: Set this BEFORE first build!**

In Railway Dashboard → Frontend Service → Variables:

```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

**Important:**
- Use HTTPS (not HTTP)
- Use your actual backend Railway URL
- No trailing slash
- Must be set before build (Next.js uses it at build time)

### 3. Deploy

1. Railway will automatically build
2. Monitor build logs
3. Wait for deployment to complete
4. Get frontend URL from Railway

### 4. Update Backend CORS

After frontend is deployed:

1. Get frontend URL: `https://your-frontend.up.railway.app`
2. Go to Backend Service → Variables
3. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://your-frontend.up.railway.app
   ```
4. Redeploy backend (or restart)

## Verification Steps

### 1. Check Frontend Service Status

- ✅ Service exists in Railway
- ✅ Build succeeded
- ✅ Deployment succeeded
- ✅ Service shows as "Running"

### 2. Test Frontend URL

```bash
curl https://your-frontend.up.railway.app/
```

**Expected:**
- HTML response (not 502/404)
- Landing page content

### 3. Check Environment Variables

- ✅ `NEXT_PUBLIC_API_URL` is set
- ✅ Points to backend URL (HTTPS)
- ✅ No trailing slash

### 4. Test Backend Connection

Open browser console on frontend:
- Check for API connection errors
- Verify API calls go to correct backend URL

## Quick Checklist

- [ ] Frontend service exists in Railway
- [ ] Root Directory set to `web-ui` (if monorepo)
- [ ] Dockerfile Path is `web-ui/Dockerfile`
- [ ] `NEXT_PUBLIC_API_URL` environment variable set (HTTPS)
- [ ] Build succeeded
- [ ] Deployment succeeded
- [ ] Frontend URL accessible (not 502/404)
- [ ] Backend CORS includes frontend URL
- [ ] Landing page loads in browser

## Troubleshooting Commands

**Test Frontend:**
```bash
curl https://your-frontend.up.railway.app/
```

**Test Backend:**
```bash
curl https://your-backend.up.railway.app/health
```

**Check Environment Variables:**
- Railway Dashboard → Frontend Service → Variables
- Verify `NEXT_PUBLIC_API_URL` is set correctly

## Most Common Issues

1. **Frontend not deployed** - Need to create frontend service
2. **NEXT_PUBLIC_API_URL not set** - Must be set before build
3. **Wrong API URL** - Must be HTTPS, must match backend URL
4. **Build failed** - Check build logs for errors
5. **502 errors** - Check deploy logs, verify app starts

## Next Steps

1. ✅ **Check if frontend service exists** in Railway
2. ✅ **If not, deploy frontend service** (see steps above)
3. ✅ **Set NEXT_PUBLIC_API_URL** environment variable
4. ✅ **Verify build succeeds**
5. ✅ **Test frontend URL** in browser
6. ✅ **Update backend CORS** with frontend URL

If you share:
- Whether frontend service exists in Railway
- What you see in frontend deploy logs
- Any error messages

I can help you fix the specific issue!

