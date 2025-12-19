# Railway Build Context Fix

## Issue
Railway build failing with: `"/pyproject.toml": not found`

## Root Cause
Railway's build context might not be set correctly, causing Docker to look in the wrong directory for files.

## Solution

### Option 1: Configure Railway Service Settings (Recommended)

1. Go to your Railway project dashboard
2. Select your **backend service**
3. Go to **Settings** tab
4. Under **Build & Deploy**:
   - **Root Directory**: Leave empty (or set to `.`) - this means build from repository root
   - **Dockerfile Path**: `Dockerfile` (or `./Dockerfile`)
   - **Build Command**: Leave empty (Railway uses Dockerfile)
   - **Start Command**: `python api_server.py`

### Option 2: Verify Repository Structure

Ensure your repository structure looks like this:
```
your-repo/
├── Dockerfile          ← Backend Dockerfile
├── pyproject.toml      ← Must be in same directory as Dockerfile
├── api_server.py
├── src/
│   └── content_creation_crew/
├── web-ui/
│   └── Dockerfile      ← Frontend Dockerfile
└── railway.json
```

### Option 3: Check Railway Service Configuration

If deploying from a monorepo:

1. **Backend Service**:
   - Root Directory: `.` (or empty)
   - Dockerfile Path: `Dockerfile`

2. **Frontend Service**:
   - Root Directory: `web-ui`
   - Dockerfile Path: `Dockerfile`

## Verification

After updating settings:
1. Trigger a new deployment
2. Check build logs - should see `COPY pyproject.toml ./` succeed
3. Build should proceed to dependency installation

## Common Issues

**Issue**: "pyproject.toml not found"
- **Fix**: Ensure Root Directory is set correctly in Railway settings

**Issue**: Build context is wrong directory
- **Fix**: Set Root Directory to `.` (repository root) for backend service

**Issue**: Dockerfile can't find files
- **Fix**: Verify Dockerfile uses relative paths (e.g., `COPY pyproject.toml ./` not `/pyproject.toml`)

## Next Steps

1. ✅ Update Railway service settings (Root Directory)
2. ✅ Verify `pyproject.toml` exists in repository root
3. ✅ Redeploy service
4. ✅ Check build logs for success

