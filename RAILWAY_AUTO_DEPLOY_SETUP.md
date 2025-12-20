# Railway Auto-Deploy Setup

## Issue: Backend Service Not Rebuilding Automatically

Railway should automatically rebuild when you push changes to your repository. If it's not, here's how to fix it.

## Step-by-Step Fix

### Step 1: Verify GitHub Connection

1. Go to Railway Dashboard → Your Project
2. Check if your service shows a GitHub icon/link
3. If not connected:
   - Click on your service
   - Go to **Settings** tab
   - Look for **"Source"** or **"Repository"** section
   - Connect your GitHub repository

### Step 2: Enable Auto-Deploy

1. Go to Railway Dashboard → **Backend Service**
2. Click **Settings** tab
3. Scroll to **"Deploy"** or **"Source"** section
4. Look for **"Auto Deploy"** or **"Automatic Deployments"**
5. **Enable** it (should be enabled by default)
6. Verify the branch is set correctly (usually `main` or `master`)

### Step 3: Check Service Settings

In Railway Dashboard → Backend Service → Settings:

**Verify:**
- ✅ **Source**: Connected to your GitHub repository
- ✅ **Branch**: Set to `main` (or your default branch)
- ✅ **Root Directory**: Set to `.` or empty (for backend)
- ✅ **Auto Deploy**: Enabled

### Step 4: Check Railway Project Settings

1. Go to Railway Dashboard → Your **Project** (not service)
2. Click **Settings**
3. Check **"Deploy Hooks"** or **"GitHub Integration"**
4. Verify GitHub is connected at project level

## Common Issues

### Issue 1: GitHub Not Connected

**Symptoms:**
- No GitHub icon on service
- Manual deployments only

**Fix:**
- Connect GitHub repository in service settings
- Or connect at project level

### Issue 2: Auto-Deploy Disabled

**Symptoms:**
- GitHub connected but no auto-deploy
- Need to manually trigger deployments

**Fix:**
- Enable "Auto Deploy" in service settings
- Verify branch is correct

### Issue 3: Wrong Branch

**Symptoms:**
- Pushing to wrong branch
- Auto-deploy watching different branch

**Fix:**
- Check which branch Railway is watching
- Push to that branch (usually `main` or `master`)
- Or change Railway to watch your branch

### Issue 4: Root Directory Wrong

**Symptoms:**
- Changes pushed but Railway doesn't detect them
- Builds from wrong directory

**Fix:**
- Set Root Directory to `.` (for backend)
- Or set to correct subdirectory

## Manual Deployment (Temporary Fix)

If auto-deploy isn't working, you can manually trigger:

1. Railway Dashboard → Backend Service
2. Click **"Deployments"** tab
3. Click **"Deploy"** or **"Redeploy"** button
4. Or click **"..."** menu → **"Redeploy"**

## Verification Steps

### Step 1: Check Service Connection

Railway Dashboard → Backend Service → Settings:
- Should show GitHub repository link
- Should show branch name
- Should show "Auto Deploy: Enabled"

### Step 2: Test Auto-Deploy

1. Make a small change (e.g., add a comment)
2. Commit and push to GitHub
3. Check Railway Dashboard
4. Should see new deployment starting automatically

### Step 3: Check Deployment History

Railway Dashboard → Backend Service → Deployments:
- Should show deployments triggered by git pushes
- Should show commit SHA and message
- Should show "Triggered by: GitHub" or similar

## Quick Checklist

- [ ] GitHub repository connected to Railway service
- [ ] Auto-deploy enabled in service settings
- [ ] Correct branch selected (usually `main`)
- [ ] Root Directory set correctly (`.` for backend)
- [ ] Pushing to the correct branch
- [ ] Railway has access to your GitHub repository

## Railway Configuration Files

The `railway.json` file doesn't control auto-deploy - that's done in Railway Dashboard settings. The `railway.json` file only configures:
- Build settings (Dockerfile path, etc.)
- Deploy settings (start command, health check, etc.)

## Next Steps

1. ✅ **Check Railway Dashboard** - Verify GitHub connection
2. ✅ **Enable Auto-Deploy** - In service settings
3. ✅ **Verify Branch** - Make sure it's watching correct branch
4. ✅ **Test** - Push a change and see if it auto-deploys

## If Still Not Working

1. **Disconnect and Reconnect GitHub:**
   - Railway Dashboard → Service → Settings
   - Disconnect GitHub
   - Reconnect GitHub repository
   - Enable auto-deploy

2. **Check GitHub Permissions:**
   - Railway needs access to your repository
   - Check Railway app permissions in GitHub settings

3. **Contact Railway Support:**
   - If auto-deploy still doesn't work
   - Share your service configuration
   - They can help troubleshoot

## Alternative: Use Railway CLI

You can also trigger deployments via CLI:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Deploy
railway up
```

But auto-deploy should work once configured correctly in the dashboard!

