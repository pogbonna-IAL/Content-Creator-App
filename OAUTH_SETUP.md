# OAuth Setup Guide

This guide explains how to configure OAuth authentication (Google, Facebook, GitHub) for the Content Creation Crew application.

## Overview

OAuth allows users to sign in using their Google, Facebook, or GitHub accounts without creating a separate account. Each provider requires:
1. Creating an OAuth application
2. Getting Client ID and Client Secret
3. Setting environment variables

## Google OAuth Setup

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google+ API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:8000/api/auth/oauth/google/callback` (for local development)
     - `https://yourdomain.com/api/auth/oauth/google/callback` (for production)
   - **Important**: The redirect URI must point to your BACKEND API, not the frontend!
   - Click "Create"
5. Copy the **Client ID** and **Client Secret**

### Step 2: Set Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Facebook OAuth Setup

### Step 1: Create Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "My Apps" > "Create App"
3. Choose "Consumer" or "Business" app type
4. Fill in app details
5. Add Facebook Login product:
   - Go to "Products" > "Facebook Login" > "Set Up"
   - Choose "Web" platform
6. Configure OAuth redirect URIs:
   - Go to "Settings" > "Basic"
   - Add "Valid OAuth Redirect URIs":
     - `http://localhost:8000/api/auth/oauth/facebook/callback` (for local development)
     - `https://yourdomain.com/api/auth/oauth/facebook/callback` (for production)
   - **Important**: The redirect URI must point to your BACKEND API, not the frontend!
7. Copy **App ID** and **App Secret**

### Step 2: Set Environment Variables

```bash
FACEBOOK_CLIENT_ID=your-facebook-app-id
FACEBOOK_CLIENT_SECRET=your-facebook-app-secret
```

## GitHub OAuth Setup

### Step 1: Create GitHub OAuth App

1. Go to GitHub Settings > [Developer settings](https://github.com/settings/developers)
2. Click "OAuth Apps" > "New OAuth App"
3. Fill in:
   - **Application name**: Content Creation Crew
   - **Homepage URL**: `http://localhost:3000` (or your production URL)
   - **Authorization callback URL**: `http://localhost:8000/api/auth/oauth/github/callback` (for local development)
   - For production: `https://yourdomain.com/api/auth/oauth/github/callback`
   - **Important**: The callback URL must point to your BACKEND API, not the frontend!
4. Click "Register application"
5. Copy **Client ID** and generate a **Client Secret**

### Step 2: Set Environment Variables

```bash
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## Environment Variables Summary

Create a `.env` file in the project root with:

```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

FACEBOOK_CLIENT_ID=your-facebook-app-id
FACEBOOK_CLIENT_SECRET=your-facebook-app-secret

GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Frontend callback URL (where backend redirects after OAuth processing)
FRONTEND_CALLBACK_URL=http://localhost:3000/auth/callback

# Backend API base URL (where OAuth providers redirect to)
API_BASE_URL=http://localhost:8000

# Other environment variables
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
```

## Loading Environment Variables

### Option 1: Using `.env` file (Recommended)

Install `python-dotenv`:
```bash
uv add python-dotenv
```

Then load it in `api_server.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Option 2: Set environment variables directly

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CLIENT_ID="your-client-id"
$env:GOOGLE_CLIENT_SECRET="your-client-secret"
```

**Linux/Mac:**
```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

## Testing OAuth

1. Start the API server:
   ```bash
   uv run python api_server.py
   ```

2. Start the frontend:
   ```bash
   cd web-ui
   npm run dev
   ```

3. Try signing in with OAuth - the buttons should work if configured correctly

## Troubleshooting

### "OAuth is not configured" Error

- Make sure environment variables are set correctly
- Restart the API server after setting environment variables
- Check that the redirect URIs match exactly (including http/https and port)

### Redirect URI Mismatch

- Ensure the redirect URI in your OAuth app settings matches exactly:
  - Format: `http://localhost:3000/auth/callback/{provider}`
  - Case-sensitive
  - Must include protocol (http/https)

### Local Development

For local development, you may need to:
- Use `http://localhost` (not `127.0.0.1`)
- Some providers require HTTPS even for localhost (use ngrok or similar)

## Security Notes

- **Never commit** `.env` files or credentials to version control
- Use different OAuth apps for development and production
- Rotate secrets regularly
- Use environment variables or secure secret management in production

## Optional: Disable OAuth Buttons

If you don't want to use OAuth, the buttons will automatically be disabled when the environment variables are not set. The error message will guide users to use email/password authentication instead.

