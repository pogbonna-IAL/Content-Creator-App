# Signup Flow Debugging Guide

## Steps to Debug Signup Issues

### 1. Check Browser Console
Open your browser's developer console (F12) and look for:
- Network errors (CORS, connection refused)
- JavaScript errors
- Console.log messages from the signup flow

### 2. Check API Server Logs
Look at the terminal where `api_server.py` is running for:
- Request logs
- Error messages
- Database errors

### 3. Test the API Directly

Run the test script:
```bash
python test_signup.py
```

Or use curl:
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123","full_name":"Test User"}'
```

### 4. Common Issues

#### Issue: CORS Error
**Symptom**: Browser console shows CORS error
**Solution**: 
- Check that `http://localhost:3000` is in the CORS allowed origins
- Make sure API server is running on port 8000

#### Issue: Connection Refused
**Symptom**: "Failed to fetch" or connection error
**Solution**:
- Make sure API server is running: `uv run python api_server.py`
- Check that API_URL is correct in `.env.local`

#### Issue: Database Error
**Symptom**: Server logs show database errors
**Solution**:
- Delete `content_crew.db` and restart server (database will be recreated)
- Check file permissions in project directory

#### Issue: Password Too Short
**Symptom**: Error message "Password must be at least 8 characters long"
**Solution**: Use a password with at least 8 characters

#### Issue: Email Already Registered
**Symptom**: Error message "Email already registered"
**Solution**: Use a different email or delete the user from database

### 5. Enable Detailed Logging

The code now includes console.log statements. Check:
- Browser console for frontend logs
- Server terminal for backend logs

### 6. Verify Environment Variables

Create `.env.local` in `web-ui/` directory:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 7. Check Network Tab

In browser DevTools → Network tab:
- Look for the `/api/auth/signup` request
- Check request payload
- Check response status and body
- Look for any error responses

## Expected Flow

1. User fills form and clicks "Create Account"
2. Frontend sends POST to `http://localhost:8000/api/auth/signup`
3. Backend validates data and creates user
4. Backend returns JWT token and user data
5. Frontend stores token in cookies
6. User is redirected to main page

## Debugging Checklist

- [ ] API server is running on port 8000
- [ ] Next.js dev server is running on port 3000
- [ ] No CORS errors in browser console
- [ ] Network request shows correct URL and payload
- [ ] Server logs show the signup request
- [ ] Database file exists and is writable
- [ ] Password is at least 8 characters
- [ ] Email is valid format
- [ ] No duplicate email in database

