# Railway Root Directory Configuration - CRITICAL FIX

## The Problem
Railway error: `"/pyproject.toml": not found`

This means Railway is building from the wrong directory and can't find your files.

## The Solution: Configure Root Directory in Railway Dashboard

**You MUST configure this in the Railway dashboard - railway.json alone is not enough!**

### Step-by-Step Instructions:

1. **Go to Railway Dashboard**
   - Open https://railway.app
   - Navigate to your project
   - Click on your **backend service** (the one that's failing)

2. **Open Settings**
   - Click the **Settings** tab (gear icon)

3. **Find "Root Directory" Setting**
   - Scroll down to **"Build & Deploy"** section
   - Look for **"Root Directory"** field

4. **Set Root Directory**
   - **Option A**: Leave it **EMPTY** (recommended)
   - **Option B**: Set it to `.` (dot)
   - **Option C**: Set it to `/` (if Railway requires a value)

5. **Verify Dockerfile Path**
   - **Dockerfile Path**: Should be `Dockerfile` (or `./Dockerfile`)
   - This tells Railway where your Dockerfile is relative to Root Directory

6. **Save Settings**
   - Click **Save** or the changes auto-save

7. **Redeploy**
   - Go to **Deployments** tab
   - Click **"Redeploy"** or trigger a new deployment
   - Railway will rebuild with the correct context

## Visual Guide

```
Railway Service Settings:
┌─────────────────────────────────────┐
│ Settings Tab                        │
├─────────────────────────────────────┤
│ Build & Deploy                      │
│                                     │
│ Root Directory: [empty or "."]  ←───┼─── SET THIS!
│                                     │
│ Dockerfile Path: [Dockerfile]      │
│                                     │
│ Start Command: [python api_server.py]│
└─────────────────────────────────────┘
```

## Why This Happens

Railway needs to know:
1. **Where to start building from** (Root Directory)
2. **Where the Dockerfile is** (Dockerfile Path)

If Root Directory is wrong, Railway looks in the wrong place for files like `pyproject.toml`.

## Repository Structure

Your repository should look like this:
```
your-repo/                    ← Root Directory should point here
├── Dockerfile               ← Backend Dockerfile
├── pyproject.toml           ← Must be here!
├── api_server.py
├── railway.json
├── src/
│   └── content_creation_crew/
└── web-ui/
    └── Dockerfile           ← Frontend Dockerfile (different service)
```

## Verification

After setting Root Directory:

1. **Check Build Logs**
   - Should see: `COPY pyproject.toml ./` succeed
   - Should NOT see: `"/pyproject.toml": not found`

2. **Build Should Progress**
   - Step 1: System dependencies
   - Step 2: Install UV
   - Step 3: Copy pyproject.toml ✅
   - Step 4: Install dependencies

## Common Mistakes

❌ **Wrong**: Root Directory = `src` or `backend` or `content_creation_crew`
✅ **Correct**: Root Directory = `.` or empty

❌ **Wrong**: Dockerfile Path = `./Dockerfile` when Root Directory is wrong
✅ **Correct**: Dockerfile Path = `Dockerfile` when Root Directory = `.`

## Still Having Issues?

1. **Check Railway Logs**
   - Look for the exact error message
   - Check which directory Railway is building from

2. **Verify File Exists**
   - Ensure `pyproject.toml` is committed to git
   - Check it's in the repository root (same level as Dockerfile)

3. **Try Manual Build**
   - Test locally: `docker build -t test .`
   - If local build works, issue is Railway configuration

4. **Contact Railway Support**
   - If settings are correct but still failing
   - Share build logs with Railway support

## Quick Checklist

- [ ] Root Directory is set to `.` or empty in Railway dashboard
- [ ] Dockerfile Path is `Dockerfile` (or `./Dockerfile`)
- [ ] `pyproject.toml` exists in repository root
- [ ] `Dockerfile` exists in repository root
- [ ] Both files are committed to git
- [ ] Triggered new deployment after changing settings

