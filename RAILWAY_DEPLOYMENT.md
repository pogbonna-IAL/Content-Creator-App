# Railway Deployment Guide

## Fixed Issues

### ModuleNotFoundError: No module named 'content_creation_crew'

This error has been fixed with the following changes:

1. **Dockerfile Updates**:
   - Added `PYTHONPATH=/app/src:/app` environment variable
   - Installs package in editable mode with `pip install -e .`
   - Includes fallback verification and debugging

2. **api_server.py Updates**:
   - Added automatic `src/` directory to Python path
   - Ensures package can be imported even if installation fails

3. **Package Configuration**:
   - Updated `pyproject.toml` with correct hatchling configuration
   - Added `setup.py` as fallback installation method

## Railway Configuration

The `railway.json` file has been created with:
- Dockerfile build configuration
- Health check endpoint (`/health`)
- Restart policy for reliability

## Environment Variables Required

Make sure to set these in Railway:

- `SECRET_KEY` - Strong random key (min 32 chars)
- `DATABASE_URL` - PostgreSQL connection string (Railway provides this)
- `OLLAMA_BASE_URL` - Your Ollama instance URL
- `NEXT_PUBLIC_API_URL` - Your Railway backend URL
- OAuth credentials (optional)

## Deployment Steps

1. **Connect Repository**: Connect your GitHub repo to Railway
2. **Set Environment Variables**: Add all required env vars in Railway dashboard
3. **Deploy**: Railway will automatically build and deploy using the Dockerfile
4. **Check Logs**: Monitor deployment logs for any issues

## Troubleshooting

If you still get `ModuleNotFoundError`:

1. Check Railway logs to see if package installation succeeded
2. Verify `PYTHONPATH` is set correctly (should be `/app/src:/app`)
3. Check that `src/content_creation_crew/` directory exists in the container
4. Verify all files are copied (check `.dockerignore` doesn't exclude needed files)

## Verification

After deployment, check:
- Health endpoint: `https://your-app.railway.app/health`
- API root: `https://your-app.railway.app/`
- Check logs for "✓ content_creation_crew imported successfully"

