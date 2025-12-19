# Railway Deployment Checklist

Quick reference for deploying both backend and frontend to Railway.

## Backend Deployment ✅

### 1. Deploy Backend Service
- [x] Create new Railway service
- [x] Connect GitHub repository
- [x] Set root directory (if needed)
- [x] Railway detects `Dockerfile` automatically

### 2. Set Backend Environment Variables

In Railway → Backend Service → Variables:

```
SECRET_KEY=your-strong-secret-key-here-min-32-chars
DATABASE_URL=postgresql://... (if using PostgreSQL, Railway provides this)
OLLAMA_BASE_URL=http://your-ollama-instance:11434
CORS_ORIGINS=https://your-frontend.up.railway.app,https://your-frontend-2.up.railway.app
```

**Important:**
- `SECRET_KEY`: Generate a strong random key (min 32 characters)
- `DATABASE_URL`: Railway provides this if you add PostgreSQL service
- `OLLAMA_BASE_URL`: Your Ollama instance URL
- `CORS_ORIGINS`: Add your frontend Railway URL(s) here (comma-separated)

### 3. Get Backend URL

After deployment:
- Go to Backend Service → Settings → Networking
- Copy the public domain: `https://your-backend.up.railway.app`
- Save this URL for frontend configuration

## Frontend Deployment ✅

### 1. Deploy Frontend Service

**Option A: Separate Service (Recommended)**
1. In Railway project, click **"+ New"** → **"GitHub Repo"**
2. Select same repository
3. Configure:
   - **Service Name**: `frontend` or `web-ui`
   - **Root Directory**: `web-ui`
   - **Dockerfile Path**: `web-ui/Dockerfile`

**Option B: From Monorepo**
- Railway will detect `web-ui/Dockerfile` automatically
- Set root directory to `web-ui` if needed

### 2. Set Frontend Environment Variables

**CRITICAL: Set this BEFORE first build**

In Railway → Frontend Service → Variables:

```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

**Replace `your-backend.up.railway.app` with your actual backend URL from step 3 above.**

**Optional:**
```
PORT=3000  # Railway sets this automatically
NODE_ENV=production
```

### 3. Deploy Frontend

1. Railway will automatically build using `web-ui/Dockerfile`
2. Monitor build logs
3. Once deployed, Railway provides frontend URL

### 4. Update Backend CORS

After frontend is deployed:

1. Get frontend URL: `https://your-frontend.up.railway.app`
2. Go to Backend Service → Variables
3. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://your-frontend.up.railway.app
   ```
4. Redeploy backend (or restart service)

## Verification Steps

### Backend Health Check
```bash
curl https://your-backend.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "content-creation-crew"}
```

### Frontend Connection Test

1. Open frontend URL in browser
2. Open DevTools → Console
3. Check for API calls to backend URL
4. Test login/signup functionality

### Common Issues

**CORS Errors:**
- ✅ Verify `CORS_ORIGINS` includes frontend URL
- ✅ Use HTTPS URLs (Railway uses HTTPS)
- ✅ No trailing slashes in URLs

**Frontend Can't Connect:**
- ✅ Verify `NEXT_PUBLIC_API_URL` is set correctly
- ✅ Must be set BEFORE build (rebuild if changed)
- ✅ Use HTTPS, not HTTP

**Build Failures:**
- ✅ Check build logs for errors
- ✅ Verify all dependencies in `package.json`
- ✅ Check TypeScript errors

## Quick Reference

### Backend Service
- **Dockerfile**: `Dockerfile` (root)
- **Start Command**: `python api_server.py`
- **Port**: Uses `PORT` env var (Railway sets automatically)
- **Health Check**: `/health`

### Frontend Service
- **Dockerfile**: `web-ui/Dockerfile`
- **Root Directory**: `web-ui`
- **Port**: Uses `PORT` env var (defaults to 3000)
- **Health Check**: `/`

### Environment Variables Summary

**Backend:**
```
SECRET_KEY=...
DATABASE_URL=... (if using PostgreSQL)
OLLAMA_BASE_URL=...
CORS_ORIGINS=https://your-frontend.up.railway.app
```

**Frontend:**
```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Railway Project                     │
├─────────────────┬───────────────────────────────┤
│   Backend       │        Frontend                │
│   Service      │        Service                  │
│                 │                                │
│  Port: Dynamic │  Port: Dynamic (default 3000)  │
│  URL: backend   │  URL: frontend                 │
│  .railway.app   │  .railway.app                  │
└────────┬────────┴───────────────┬────────────────┘
         │                        │
         │  HTTPS API Calls       │
         └────────────────────────┘
```

## Next Steps After Deployment

1. ✅ Test authentication flow
2. ✅ Test content generation
3. ✅ Set up custom domains (optional)
4. ✅ Configure monitoring/alerts
5. ✅ Share your frontend URL with users

## Support

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Project Issues**: Check GitHub issues

