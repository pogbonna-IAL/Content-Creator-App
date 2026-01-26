# Email Verification 404 Error Fix

## Problem

Email verification links were returning 404 errors because:
1. `FRONTEND_URL` environment variable was incorrectly configured
2. Verification links were pointing to the backend API server instead of the frontend
3. The path `/auth/callback/verify-email` suggests `FRONTEND_URL` included `/auth/callback`

## Root Cause

The error log showed:
- **Host**: `content-creator-app-api-staging.up.railway.app` (backend API server)
- **Path**: `/auth/callback/verify-email`
- **Status**: 404

This indicates `FRONTEND_URL` was set to something like:
```
https://content-creator-app-api-staging.up.railway.app/auth/callback
```

Instead of the correct frontend URL:
```
https://content-creator-app-staging.up.railway.app
```

## Solution Implemented

### 1. Added URL Validation and Auto-Fix

The backend now:
- Detects if `FRONTEND_URL` contains `/auth/callback` and removes it
- Detects if `FRONTEND_URL` points to the API server and attempts to fix it
- Logs warnings when misconfiguration is detected
- Logs the generated verification URL for debugging

### 2. Created Next.js API Proxy Routes

Created proxy routes in Next.js to ensure requests work even if `NEXT_PUBLIC_API_URL` is not set:
- `/api/auth/verify-email/confirm` - Proxies to backend for email verification
- `/api/auth/verify-email/request` - Proxies to backend for resending verification emails

### 3. Updated Frontend Calls

Updated frontend to use Next.js API routes:
- Changed from `api/auth/verify-email/confirm` to `/api/auth/verify-email/confirm`
- This ensures requests go through Next.js proxy even if backend URL is not configured

## Required Environment Variables

### Backend (FastAPI)

Set `FRONTEND_URL` to point to your **frontend** domain:

```bash
# Correct - Points to frontend
FRONTEND_URL=https://content-creator-app-staging.up.railway.app

# Wrong - Points to API server
FRONTEND_URL=https://content-creator-app-api-staging.up.railway.app

# Wrong - Includes /auth/callback
FRONTEND_URL=https://content-creator-app-staging.up.railway.app/auth/callback
```

### Frontend (Next.js)

Set `NEXT_PUBLIC_API_URL` to point to your **backend** domain:

```bash
# Points to backend API server
NEXT_PUBLIC_API_URL=https://content-creator-app-api-staging.up.railway.app
```

## Verification

After setting environment variables correctly:

1. **Check Backend Logs** - Look for:
   ```
   Generated verification URL: https://content-creator-app-staging.up.railway.app/verify-email?token=...
   ```

2. **Check Email** - The verification link should point to:
   ```
   https://content-creator-app-staging.up.railway.app/verify-email?token=...
   ```

3. **Test Verification** - Click the link and verify it works

## Common Mistakes

1. **Using FRONTEND_CALLBACK_URL instead of FRONTEND_URL**
   - `FRONTEND_CALLBACK_URL` is for OAuth callbacks: `https://domain.com/auth/callback`
   - `FRONTEND_URL` is for email links: `https://domain.com`

2. **Pointing FRONTEND_URL to API server**
   - Wrong: `https://api-staging.up.railway.app`
   - Correct: `https://staging.up.railway.app` (or your frontend domain)

3. **Including paths in FRONTEND_URL**
   - Wrong: `https://domain.com/auth/callback`
   - Correct: `https://domain.com`

## Auto-Fix Behavior

The backend now automatically:
- Removes `/auth/callback` from `FRONTEND_URL` if present
- Attempts to fix API server URLs by replacing `api-staging` with `staging`
- Logs warnings when misconfiguration is detected

However, **you should still set `FRONTEND_URL` correctly** in your environment variables.

## Testing

1. Sign up a new user
2. Check the verification email
3. Verify the link points to the frontend domain (not API domain)
4. Click the link and verify it works
5. Check backend logs for any warnings about `FRONTEND_URL`

---

**Last Updated**: 2026-01-26  
**Status**: Fixed with validation and auto-fix
