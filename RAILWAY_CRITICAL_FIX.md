# CRITICAL: Railway Build Context Fix

## The Error
```
ERROR: "/pyproject.toml": not found
```

## Root Cause
Railway's build context doesn't include `pyproject.toml`. This happens when:
1. **Root Directory** is set incorrectly in Railway dashboard
2. `pyproject.toml` is not committed to git
3. Railway is building from wrong directory

## IMMEDIATE FIX - Do These Steps:

### Step 1: Verify File is Committed to Git

```bash
# Check if pyproject.toml is tracked by git
git ls-files | grep pyproject.toml

# If not listed, add and commit it:
git add pyproject.toml
git commit -m "Add pyproject.toml for Railway build"
git push
```

### Step 2: Configure Railway Dashboard Settings

**CRITICAL: You MUST do this in Railway dashboard, not just in code!**

1. Go to **Railway Dashboard** → Your Project → **Backend Service**
2. Click **Settings** tab
3. Scroll to **"Build & Deploy"** section
4. Find **"Root Directory"** field
5. **Set it to:** `.` (dot) **OR leave it EMPTY**
6. Verify **"Dockerfile Path"** is: `Dockerfile`
7. **Save** settings
8. **Redeploy** the service

### Step 3: Verify Repository Structure

Your repository should look like this at the root:

```
your-repo/
├── Dockerfile          ← Must be here
├── pyproject.toml     ← Must be here (same level as Dockerfile)
├── api_server.py      ← Must be here
├── railway.json
└── src/
    └── content_creation_crew/
```

### Step 4: Check Railway Build Logs

After redeploying, check build logs. You should see:
- ✅ `COPY pyproject.toml ./` succeeds
- ❌ NOT see: `"/pyproject.toml": not found`

## Why This Happens

Railway needs to know:
- **Where your repository root is** (Root Directory)
- **Where your Dockerfile is** (Dockerfile Path)

If Root Directory is wrong, Railway looks in the wrong place for files.

## Common Mistakes

❌ **Wrong**: Root Directory = `src` or `backend`  
✅ **Correct**: Root Directory = `.` or empty

❌ **Wrong**: `pyproject.toml` not committed to git  
✅ **Correct**: File is tracked and committed

❌ **Wrong**: Building from subdirectory  
✅ **Correct**: Building from repository root

## Verification Checklist

- [ ] `pyproject.toml` exists in repository root
- [ ] `pyproject.toml` is committed to git (`git ls-files | grep pyproject.toml`)
- [ ] Root Directory in Railway = `.` or empty
- [ ] Dockerfile Path in Railway = `Dockerfile`
- [ ] Triggered new deployment after changing settings
- [ ] Build logs show `COPY pyproject.toml ./` succeeding

## Still Not Working?

1. **Check Railway Build Context**
   - Look at build logs for `context: ...`
   - This shows what directory Railway is building from

2. **Verify Git Repository**
   ```bash
   git status
   git ls-files pyproject.toml
   ```

3. **Test Locally**
   ```bash
   docker build -t test .
   ```
   If local build works, issue is Railway configuration

4. **Contact Railway Support**
   - Share build logs
   - Mention Root Directory setting

## Quick Fix Summary

1. ✅ Commit `pyproject.toml` to git
2. ✅ Set Root Directory = `.` in Railway dashboard
3. ✅ Redeploy service
4. ✅ Check build logs for success

