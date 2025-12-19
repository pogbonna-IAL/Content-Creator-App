# Authentication Setup Guide

This guide explains how to set up authentication for the Content Creator application.

## Features

- **Email/Password Authentication**: Users can sign up and sign in with email and password
- **OAuth Providers**: Support for Google, Facebook, and GitHub authentication
- **JWT Tokens**: Secure token-based authentication
- **Protected Routes**: API endpoints and frontend routes require authentication

## Backend Setup

### 1. Install Dependencies

The authentication dependencies are already included in `pyproject.toml`. Install them with:

```bash
uv sync
```

### 2. Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Secret key for JWT tokens (generate a secure random string)
SECRET_KEY=your-secret-key-change-in-production-min-32-chars-long

# OAuth redirect URL
REDIRECT_URL=http://localhost:3000/auth/callback

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Facebook OAuth (optional)
FACEBOOK_CLIENT_ID=your-facebook-app-id
FACEBOOK_CLIENT_SECRET=your-facebook-app-secret

# GitHub OAuth (optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### 3. Database Initialization

The database is automatically initialized when the API server starts. The SQLite database file `content_crew.db` will be created in the project root.

### 4. Start the API Server

```bash
uv run python api_server.py
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd web-ui
npm install
```

### 2. Environment Variables

Create a `.env.local` file in the `web-ui` directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start the Development Server

```bash
npm run dev
```

## OAuth Provider Setup

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Set authorized redirect URIs to: `http://localhost:8000/api/auth/oauth/google/callback`
6. Copy the Client ID and Client Secret to your `.env` file

### Facebook OAuth

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add "Facebook Login" product
4. Set valid OAuth redirect URIs to: `http://localhost:8000/api/auth/oauth/facebook/callback`
5. Copy the App ID and App Secret to your `.env` file

### GitHub OAuth

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Set Authorization callback URL to: `http://localhost:8000/api/auth/oauth/github/callback`
4. Copy the Client ID and Client Secret to your `.env` file

## Usage

### Sign Up

1. Navigate to `/auth`
2. Click "Sign up" or use an OAuth provider
3. Fill in email, password, and optional full name
4. You'll be redirected to the main application

### Sign In

1. Navigate to `/auth`
2. Enter your email and password, or use an OAuth provider
3. You'll be redirected to the main application

### Protected Routes

- `/` - Main application (requires authentication)
- `/api/generate` - Content generation endpoint (requires authentication)

### API Endpoints

- `POST /api/auth/signup` - Register a new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout (client-side token removal)
- `GET /api/auth/oauth/{provider}/login` - Initiate OAuth login
- `GET /api/auth/oauth/{provider}/callback` - OAuth callback handler

## Security Notes

1. **SECRET_KEY**: Use a strong, random secret key in production (minimum 32 characters)
2. **HTTPS**: Always use HTTPS in production
3. **CORS**: Update CORS settings for production domain
4. **Database**: Consider using PostgreSQL instead of SQLite for production
5. **Token Expiration**: Tokens expire after 7 days (configurable in `auth.py`)

## Troubleshooting

### OAuth Not Working

- Ensure redirect URIs match exactly in OAuth provider settings
- Check that environment variables are set correctly
- Verify the OAuth provider credentials are correct

### Database Errors

- Delete `content_crew.db` and restart the server to recreate the database
- Ensure write permissions in the project directory

### Token Issues

- Clear browser cookies and try again
- Check that the SECRET_KEY hasn't changed (this invalidates all tokens)

