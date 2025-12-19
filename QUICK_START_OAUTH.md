# Quick Start: Setting Up Google OAuth

The error "Google OAuth is not configured" means you need to set up Google OAuth credentials.

## Quick Setup (5 minutes)

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google+ API**:
   - Go to "APIs & Services" > "Library"
   - Search "Google+ API" > Enable
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/api/auth/oauth/google/callback`
   - **Important**: Must point to your BACKEND API (port 8000), not the frontend!
   - Click "Create"
5. Copy **Client ID** and **Client Secret**

### 2. Create `.env` File

Create a `.env` file in the project root (`content_creation_crew/.env`):

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
FRONTEND_CALLBACK_URL=http://localhost:3000/auth/callback
API_BASE_URL=http://localhost:8000
```

### 3. Restart the Server

```bash
# Stop the current server (Ctrl+C)
# Then restart:
uv run python api_server.py
```

### 4. Test

Try clicking "Continue with Google" - it should work now!

## Alternative: Use Email/Password

If you don't want to set up OAuth, you can use email/password authentication instead. The OAuth buttons will show an error, but email/password login works without any OAuth configuration.

## Need Help?

See `OAUTH_SETUP.md` for detailed instructions for Google, Facebook, and GitHub OAuth setup.

