# Fix .env File - API URL Configuration

## Issue

Your `.env` file currently has:
```
NEXT_PUBLIC_API_URL=https://content-creator-app-beta.up.railway.app
```

This is the **Railway production URL**, but for **local development**, it should be:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Quick Fix

### Option 1: Manual Edit (Recommended)

1. Open `content_creation_crew/.env` file
2. Find line with `NEXT_PUBLIC_API_URL`
3. Change it to:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. Save the file

### Option 2: PowerShell Command

Run this command in PowerShell from the project root:

```powershell
cd content_creation_crew
(Get-Content .env) -replace 'NEXT_PUBLIC_API_URL=https://content-creator-app-beta.up.railway.app', 'NEXT_PUBLIC_API_URL=http://localhost:8000' | Set-Content .env
```

## Important: Two Different Configurations

### 1. Local Development (`.env` file)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
- Used when running `npm run dev` locally
- Used with `docker-compose` for local development
- **NOT used by Railway**

### 2. Railway Production (Railway Dashboard)
```
NEXT_PUBLIC_API_URL=https://content-creator-app-beta.up.railway.app
```
- Set in **Railway Dashboard** → Frontend Service → Variables
- Used when Railway builds and deploys your frontend
- **NOT in `.env` file**

## Verification

After fixing the `.env` file:

1. **For Local Development:**
   ```bash
   # Start backend
   cd content_creation_crew
   python api_server.py
   
   # In another terminal, start frontend
   cd content_creation_crew/web-ui
   npm run dev
   ```
   - Frontend should connect to `http://localhost:8000`

2. **For Railway:**
   - Check Railway Dashboard → Frontend Service → Variables
   - Ensure `NEXT_PUBLIC_API_URL` is set to your backend Railway URL
   - Railway will use this, not the `.env` file

## Summary

- ✅ **`.env` file** → Use `http://localhost:8000` for local dev
- ✅ **Railway Variables** → Use `https://content-creator-app-beta.up.railway.app` for production

Both are needed, but for different environments!

