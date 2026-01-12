# Railway: Link PostgreSQL to Backend Service

## Problem

Your backend is trying to connect to database hostname `"db"`, which is a Docker Compose service name. This only works in Docker Compose, **not on Railway**.

## Solution: Link PostgreSQL Service to Backend

Railway automatically provides `DATABASE_URL` when you link services. Follow these steps:

### Step 1: Open Railway Dashboard

1. Go to [Railway Dashboard](https://railway.app)
2. Select your project
3. You should see your services listed (Backend, Frontend, PostgreSQL)

### Step 2: Link PostgreSQL to Backend

**Option A: From PostgreSQL Service (Recommended)**

1. Click on your **PostgreSQL service**
2. Look for a **"Connect"** or **"Add Service"** button (usually in the top right or in settings)
3. Click it
4. Select your **Backend service** from the dropdown
5. Railway will automatically add `DATABASE_URL` to your Backend service

**Option B: From Backend Service**

1. Click on your **Backend service**
2. Go to **"Variables"** tab
3. Check if `DATABASE_URL` exists
4. If it shows `postgresql://...@db:5432/...` (with `db` hostname):
   - **Delete this variable** (it's incorrect)
   - Go back to PostgreSQL service
   - Use Option A to link properly

### Step 3: Verify DATABASE_URL

1. Go to **Backend service** → **Variables** tab
2. Look for `DATABASE_URL`
3. It should look like:
   ```
   postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
   ```
4. **NOT** like:
   ```
   postgresql://user:pass@db:5432/database  ❌ (Docker Compose format)
   ```

### Step 4: Redeploy Backend

After linking:
1. Railway will **automatically redeploy** your Backend service
2. Or manually trigger: **Backend service** → **Deployments** → **Redeploy**

### Step 5: Check Deploy Logs

After redeploy, check logs for:
```
DATABASE_URL configured for PostgreSQL (host: containers-us-west-xxx.railway.app)
Testing database connection...
✓ Database connection test successful
```

## Visual Guide

### Railway Dashboard Layout

```
┌─────────────────────────────────────┐
│  Your Project                        │
├─────────────────────────────────────┤
│  📦 PostgreSQL Service               │
│     └─ [Connect] button              │
│                                      │
│  🚀 Backend Service                  │
│     └─ Variables tab                 │
│        └─ DATABASE_URL (auto-set)    │
│                                      │
│  🌐 Frontend Service                 │
└─────────────────────────────────────┘
```

### Linking Process

1. **PostgreSQL Service** → Click **"Connect"**
2. Select **Backend Service** from dropdown
3. Railway automatically:
   - Creates `DATABASE_URL` variable in Backend
   - Sets correct hostname (Railway's internal hostname)
   - Backend can now connect to PostgreSQL

## Troubleshooting

### Issue 1: Can't Find "Connect" Button

**Solution:**
- Look in PostgreSQL service settings/configuration
- Some Railway interfaces show it as "Add Service" or "Link Service"
- Check the service's "Settings" or "Configuration" tab

### Issue 2: DATABASE_URL Still Shows "db"

**Solution:**
1. Go to Backend service → Variables
2. **Delete** the incorrect `DATABASE_URL` variable
3. Re-link PostgreSQL service (Step 2)
4. Railway will create correct `DATABASE_URL`

### Issue 3: Multiple DATABASE_URL Variables

**Solution:**
1. Backend service → Variables
2. Delete **all** `DATABASE_URL` entries
3. Re-link PostgreSQL service
4. Railway will create one correct `DATABASE_URL`

### Issue 4: PostgreSQL Service Not Visible

**Solution:**
1. Check if PostgreSQL service exists in your project
2. If not, create it:
   - Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
3. Then link it to Backend (Step 2)

## Verification Checklist

After linking, verify:

- [ ] PostgreSQL service exists in Railway project
- [ ] Backend service shows PostgreSQL as dependency/linked service
- [ ] `DATABASE_URL` exists in Backend Variables
- [ ] `DATABASE_URL` uses Railway hostname (NOT `db`)
- [ ] Backend service redeployed after linking
- [ ] Deploy logs show successful database connection

## Expected DATABASE_URL Format

**Correct (Railway):**
```
postgresql://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

**Incorrect (Docker Compose):**
```
postgresql://user:pass@db:5432/database  ❌
```

## After Linking

Once linked correctly:
1. ✅ Railway sets `DATABASE_URL` automatically
2. ✅ Backend connects to PostgreSQL successfully
3. ✅ No more "db" hostname errors
4. ✅ Database features work correctly

## Summary

**The Fix:**
1. Link PostgreSQL service to Backend service in Railway
2. Railway automatically sets correct `DATABASE_URL`
3. Backend connects successfully

**Key Point:**
- Railway manages `DATABASE_URL` automatically
- Don't set it manually
- Link services, don't copy Docker Compose values

Your backend should now connect to PostgreSQL successfully! 🎉




