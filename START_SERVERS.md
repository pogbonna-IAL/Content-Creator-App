# Starting the Application Servers

## Quick Start

You need to run **two servers** for the application to work:

### 1. Backend API Server (FastAPI)

**Terminal 1:**
```bash
cd content_creation_crew
uv run python api_server.py
```

The server should start on `http://localhost:8000`

**Verify it's running:**
- Open `http://localhost:8000/health` in your browser
- Should return: `{"status": "healthy"}`

### 2. Frontend Web Server (Next.js)

**Terminal 2:**
```bash
cd content_creation_crew/web-ui
npm run dev
```

The frontend should start on `http://localhost:3000`

## Troubleshooting "Failed to fetch" Error

If you see "Failed to fetch" when trying to sign up:

1. **Check if API server is running:**
   ```bash
   python check_api_server.py
   ```

2. **Make sure both servers are running:**
   - Backend: `http://localhost:8000` (FastAPI)
   - Frontend: `http://localhost:3000` (Next.js)

3. **Check browser console** (F12) for detailed error messages

4. **Verify API URL** - The frontend uses `NEXT_PUBLIC_API_URL` environment variable
   - Default: `http://localhost:8000`
   - Create `.env.local` in `web-ui/` if you need to change it:
     ```
     NEXT_PUBLIC_API_URL=http://localhost:8000
     ```

5. **Check CORS** - Make sure backend CORS allows `http://localhost:3000`

## Common Issues

### Issue: "Cannot connect to API server"
**Solution:** Start the backend server first:
```bash
uv run python api_server.py
```

### Issue: Port 8000 already in use
**Solution:** 
- Find what's using port 8000: `netstat -ano | findstr :8000`
- Kill the process or change the port in `api_server.py`

### Issue: Port 3000 already in use
**Solution:**
- Kill the process or change the port: `npm run dev -- -p 3001`

### Issue: Database errors
**Solution:**
- Run migrations: `uv run alembic upgrade head`
- Or delete `content_crew.db` and restart (will auto-create)

## Startup Checklist

- [ ] Backend API server running on port 8000
- [ ] Frontend dev server running on port 3000
- [ ] Database initialized (migrations run)
- [ ] No port conflicts
- [ ] CORS configured correctly
- [ ] Environment variables set (if needed)

## Testing the Connection

Run the check script:
```bash
python check_api_server.py
```

Or manually test:
```bash
curl http://localhost:8000/health
```

Should return: `{"status": "healthy"}`

