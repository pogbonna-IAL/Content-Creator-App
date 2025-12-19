# Frontend Railway Deployment Guide

This guide explains how to deploy the frontend to Railway to access your backend API.

## Prerequisites

1. **Backend deployed on Railway** - You should have your backend running and know its URL
   - Example: `https://your-backend.up.railway.app`
2. **Railway account** - Sign up at [railway.app](https://railway.app)

## Step-by-Step Deployment

### Option 1: Deploy Frontend as Separate Service (Recommended)

#### 1. Create New Service in Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"GitHub Repo"** (or **"Empty Service"**)
3. If using GitHub:
   - Select your repository
   - Railway will detect the Dockerfile automatically
4. If using Empty Service:
   - Connect your GitHub repo later
   - Or use Railway CLI

#### 2. Configure Service Settings

1. **Service Name**: Name it `frontend` or `web-ui`
2. **Root Directory**: Set to `web-ui` (if deploying from monorepo)
3. **Dockerfile Path**: `web-ui/Dockerfile`

#### 3. Set Environment Variables

In Railway dashboard → Your Frontend Service → Variables:

**Required:**
```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

**Optional (Railway sets these automatically):**
```
PORT=3000  # Railway will set this automatically
NODE_ENV=production
```

**Important Notes:**
- `NEXT_PUBLIC_API_URL` must be set **before building** (it's used at build time)
- Replace `your-backend.up.railway.app` with your actual backend URL
- Use `https://` not `http://` (Railway uses HTTPS)

#### 4. Deploy

1. Railway will automatically detect the Dockerfile and start building
2. Monitor the build logs
3. Once deployed, Railway will provide a public URL

#### 5. Verify Deployment

1. Visit your frontend URL (e.g., `https://your-frontend.up.railway.app`)
2. Check browser console for any API connection errors
3. Test authentication and content generation

### Option 2: Deploy from Monorepo Root

If your Railway project is at the repository root:

1. **Set Root Directory**: Leave empty (or set to `.`)
2. **Set Dockerfile Path**: `web-ui/Dockerfile`
3. **Set Build Context**: Railway should detect it automatically
4. **Environment Variables**: Same as above

### Option 3: Use Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy frontend
cd web-ui
railway up --service frontend
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (must be HTTPS) | `https://backend.up.railway.app` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `3000` (Railway sets automatically) |
| `NODE_ENV` | Environment | `production` |

## Troubleshooting

### Frontend Can't Connect to Backend

**Symptoms:**
- CORS errors in browser console
- "Cannot connect to API server" messages
- 401/403 errors

**Solutions:**

1. **Check Backend CORS Settings**
   - Verify backend allows requests from your frontend domain
   - Check `api_server.py` CORS configuration

2. **Verify Environment Variable**
   - Ensure `NEXT_PUBLIC_API_URL` is set correctly
   - Must be set **before build** (rebuild if you change it)
   - Use HTTPS URL, not HTTP

3. **Check Backend Health**
   ```bash
   curl https://your-backend.up.railway.app/health
   ```

4. **Rebuild Frontend**
   - If you changed `NEXT_PUBLIC_API_URL`, you need to rebuild
   - Railway will rebuild automatically on next deploy

### Build Failures

**Common Issues:**

1. **Missing Dependencies**
   - Check build logs for npm errors
   - Ensure `package.json` has all required dependencies

2. **TypeScript Errors**
   - Fix TypeScript errors before deploying
   - Check `tsconfig.json` configuration

3. **Memory Issues**
   - Next.js build can be memory-intensive
   - Railway provides adequate resources, but check logs

### Port Issues

- Railway automatically sets `PORT` environment variable
- The Dockerfile uses `PORT=${PORT:-3000}` as fallback
- No manual port configuration needed

## Connecting Frontend to Backend

### Step 1: Get Your Backend URL

1. Go to Railway dashboard
2. Select your backend service
3. Go to **Settings** → **Networking**
4. Copy the public domain (e.g., `https://content-crew-backend-production.up.railway.app`)

### Step 2: Set Frontend Environment Variable

1. Go to your frontend service in Railway
2. Go to **Variables** tab
3. Add:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.up.railway.app
   ```
4. **Important**: Redeploy after setting this variable (it's used at build time)

### Step 3: Verify Connection

1. Deploy frontend
2. Open frontend URL in browser
3. Open browser DevTools → Console
4. Look for API calls - they should go to your backend URL
5. Test login/signup to verify connection

## Architecture

```
┌─────────────────┐         HTTPS          ┌─────────────────┐
│                 │ ────────────────────> │                 │
│   Frontend      │                        │    Backend      │
│   (Railway)     │ <──────────────────── │   (Railway)     │
│                 │         HTTPS          │                 │
└─────────────────┘                        └─────────────────┘
     Port 3000                                  Port (dynamic)
```

## Custom Domain (Optional)

1. Go to Frontend Service → Settings → Networking
2. Click **"Add Domain"**
3. Enter your custom domain
4. Configure DNS as instructed
5. Railway will handle SSL certificates automatically

## Monitoring

- **Logs**: View real-time logs in Railway dashboard
- **Metrics**: Check service metrics for performance
- **Health Checks**: Railway automatically monitors `/` endpoint

## Next Steps

1. ✅ Deploy backend to Railway
2. ✅ Deploy frontend to Railway
3. ✅ Set `NEXT_PUBLIC_API_URL` environment variable
4. ✅ Test the connection
5. ✅ Share your frontend URL with users

## Quick Reference

**Backend URL Format:**
```
https://[service-name].up.railway.app
```

**Frontend URL Format:**
```
https://[service-name].up.railway.app
```

**Environment Variable:**
```bash
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

