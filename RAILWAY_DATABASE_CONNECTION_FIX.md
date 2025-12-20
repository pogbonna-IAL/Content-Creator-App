# Railway Database Connection Fix

## Error: `could not translate host name "db" to address: Name or service not known`

This error occurs when the backend service tries to connect to a database using the hostname `"db"`, which is a Docker Compose service name. This hostname only works in Docker Compose, **not on Railway**.

## Root Cause

The `DATABASE_URL` environment variable is either:
1. **Not set** on Railway (PostgreSQL service not linked)
2. **Set incorrectly** (using Docker Compose format with `db` hostname)
3. **Missing** from Railway Variables

## Solution

### Step 1: Verify PostgreSQL Service Exists

1. Go to Railway Dashboard
2. Check if you have a PostgreSQL service
3. If not, create one:
   - Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**

### Step 2: Link PostgreSQL to Backend Service

**Option A: From PostgreSQL Service**
1. Go to your **PostgreSQL service** in Railway
2. Click **"Connect"** or **"Add Service"** button
3. Select your **Backend service**
4. Railway will automatically add `DATABASE_URL` to your Backend service

**Option B: From Backend Service**
1. Go to your **Backend service** in Railway
2. Click **"Variables"** tab
3. Check if `DATABASE_URL` exists
4. If missing:
   - Click **"+ New Variable"**
   - But **DON'T** create it manually!
   - Instead, go back and link the PostgreSQL service (Option A)

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

After linking the PostgreSQL service:
1. Railway will automatically redeploy the backend
2. Or manually trigger a redeploy:
   - Go to Backend service → **"Deployments"** → **"Redeploy"**

### Step 5: Check Deploy Logs

After redeploy, check logs for:
```
✓ DATABASE_URL configured for PostgreSQL (host: containers-us-west-xxx.railway.app)
✓ Database connection test successful
```

**If you see:**
```
❌ DATABASE_URL uses 'db' hostname (Docker Compose) - this won't work on Railway!
```
→ PostgreSQL service is not linked correctly

## Common Issues

### Issue 1: DATABASE_URL Not Set

**Symptoms:**
- Error: `could not translate host name "db"`
- `DATABASE_URL` missing from Variables

**Fix:**
- Link PostgreSQL service to Backend service (see Step 2)

### Issue 2: DATABASE_URL Uses "db" Hostname

**Symptoms:**
- Error: `could not translate host name "db"`
- `DATABASE_URL` contains `@db:5432`

**Fix:**
- Remove the incorrect `DATABASE_URL` variable
- Link PostgreSQL service properly (Railway will set it automatically)

### Issue 3: Multiple DATABASE_URL Variables

**Symptoms:**
- Conflicting `DATABASE_URL` values
- Wrong one being used

**Fix:**
1. Go to Backend service → Variables
2. Delete all `DATABASE_URL` entries
3. Link PostgreSQL service (Railway will create correct one)

## Verification

### Check Backend Logs

After redeploy, you should see:
```
DATABASE_URL configured for PostgreSQL (host: containers-us-west-xxx.railway.app)
Testing database connection...
✓ Database connection test successful
```

### Test Database Connection

The backend will automatically test the connection on startup. If successful, you'll see:
- `✓ Database connection test successful`
- No `_do_get()` errors
- Health check endpoint returns 200

## Railway-Specific Notes

### Automatic DATABASE_URL

Railway automatically provides `DATABASE_URL` when:
- PostgreSQL service is linked to Backend service
- Format: `postgresql://user:password@hostname:port/database`
- Hostname is Railway's internal hostname (not `db`)

### Don't Set DATABASE_URL Manually

**Don't:**
- Manually create `DATABASE_URL` variable
- Copy `DATABASE_URL` from Docker Compose
- Use `db` as hostname

**Do:**
- Let Railway set it automatically by linking services
- Use Railway's provided `DATABASE_URL`

## Troubleshooting

### Still Getting "db" Hostname Error?

1. **Check Variables:**
   - Backend service → Variables → Look for `DATABASE_URL`
   - If it contains `@db:`, delete it

2. **Re-link PostgreSQL:**
   - PostgreSQL service → Connect → Select Backend
   - Or Backend service → Variables → Check source

3. **Check Service Dependencies:**
   - Backend service → Settings → Dependencies
   - PostgreSQL should be listed

4. **Redeploy:**
   - Backend service → Deployments → Redeploy

### Connection Still Failing?

1. **Check PostgreSQL Status:**
   - PostgreSQL service → Logs
   - Should see: `database system is ready to accept connections`

2. **Check Network:**
   - Both services should be in same Railway project
   - Railway handles networking automatically

3. **Check Credentials:**
   - Railway manages credentials automatically
   - Don't manually set `POSTGRES_USER` or `POSTGRES_PASSWORD`

## Summary

**The Fix:**
1. ✅ Link PostgreSQL service to Backend service in Railway
2. ✅ Railway automatically sets `DATABASE_URL`
3. ✅ Backend redeploys and connects successfully

**Key Point:**
- Railway provides `DATABASE_URL` automatically
- Don't use Docker Compose `DATABASE_URL` format
- Link services, don't set variables manually

The error should be resolved after linking the PostgreSQL service!

