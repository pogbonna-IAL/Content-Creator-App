# Stream Connection Error Fixes

## Problem Analysis

Based on the logs provided, the content generation was failing due to premature stream connection closure:

```
"Stream controller closed by client"
"Streaming error: [TypeError: terminated]"
"Error [SocketError]: other side closed"
"UND_ERR_SOCKET"
```

### Root Causes Identified

1. **Backend Closing Connection Prematurely**
   - Database session errors during `db.refresh(job)` could cause the stream to crash
   - Unhandled exceptions in the polling loop would terminate the stream
   - Database connection issues weren't being caught and handled gracefully

2. **Frontend Not Handling Socket Errors**
   - The Next.js API route only handled timeout errors (`UND_ERR_BODY_TIMEOUT`)
   - Socket closure errors (`UND_ERR_SOCKET`) weren't being detected or handled
   - Users saw generic "terminated" errors without context

3. **Missing Error Recovery**
   - When database errors occurred, the stream would just die
   - No attempt to recover or send error events to the client
   - No logging to help diagnose the issue

## Fixes Implemented

### 1. Enhanced Backend Error Handling (`content_routes.py`)

**Database Refresh Error Handling:**
- Wrapped `db.refresh(job)` in try-catch
- If refresh fails, attempts to get a fresh job from the database
- If job not found, sends error event and exits gracefully
- Logs all database errors with full context

**Polling Loop Error Handling:**
- Wrapped entire polling loop in try-catch
- Individual operations (artifact queries, status checks) have their own error handling
- Errors during polling send error events but continue polling (allows client to reconnect)
- Fatal errors send final error event before exiting

**Stream Generator Error Handling:**
- Top-level try-catch around entire stream generator
- Attempts to send final error event if stream fails
- Comprehensive logging with `[STREAM_ERROR]` tags

**Key Changes:**
```python
# Database refresh with recovery
try:
    db.refresh(job)
except Exception as db_error:
    # Try to get fresh job
    fresh_job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
    if fresh_job:
        job = fresh_job
    else:
        # Send error and exit
        yield error_event
        break

# Polling loop with error recovery
try:
    # Polling operations...
except Exception as poll_error:
    # Send error event but continue polling
    yield error_event
    await asyncio.sleep(0.5)  # Retry
```

### 2. Enhanced Frontend Error Handling (`web-ui/app/api/generate/route.ts`)

**Socket Error Detection:**
- Added detection for `UND_ERR_SOCKET` errors
- Detects "terminated" and "other side closed" errors
- Provides specific error messages for socket closure

**Error Messages:**
- **Timeout Error**: "Stream timeout - content generation is taking longer than expected..."
- **Socket Error**: "Connection closed by server. The backend may have encountered an error..."
- **Generic Error**: Includes error code and details

**Key Changes:**
```typescript
const isSocketError = errorMessage.includes('terminated') ||
    errorMessage.includes('SocketError') ||
    errorMessage.includes('other side closed') ||
    errorCode === 'UND_ERR_SOCKET'

if (isSocketError) {
  safeEnqueue(encoder.encode(`data: ${JSON.stringify({ 
    type: 'error', 
    message: 'Connection closed by server...',
    error_code: 'STREAM_CLOSED'
  })}\n\n`))
}
```

### 3. Enhanced Logging

**Backend Logging:**
- `[STREAM_ERROR]` - All stream-related errors
- `[STREAM_POLL]` - Polling progress (every 10 seconds)
- `[STREAM_COMPLETE]` - Stream completion with summary
- Database errors logged with full stack traces

**Error Context:**
- Job ID included in all error logs
- Error type and message logged
- Stack traces for debugging
- Artifact counts and status included

## Expected Behavior After Fixes

### Normal Flow:
1. Job created → Status: `pending`
2. Async task starts → Status: `running`
3. Stream connects → `[STREAM_START]` logged
4. Polling begins → `[STREAM_POLL]` every 10s
5. Content generated → Artifacts created
6. Status changes → `[STREAM_COMPLETE]` logged
7. Stream ends → Client receives completion event

### Error Recovery:
1. **Database Error During Polling:**
   - Error logged with `[STREAM_ERROR]`
   - Attempts to get fresh job from database
   - If successful, continues polling
   - If failed, sends error event and exits

2. **Socket Closure:**
   - Backend logs error with `[STREAM_ERROR]`
   - Frontend detects `UND_ERR_SOCKET`
   - User sees: "Connection closed by server..."
   - User can retry the request

3. **Fatal Stream Error:**
   - Error logged with full stack trace
   - Attempts to send final error event
   - Stream closes gracefully
   - Client receives error event

## Testing Recommendations

1. **Test Normal Flow:**
   - Generate content with a simple topic
   - Verify stream stays connected
   - Verify completion event received

2. **Test Database Errors:**
   - Simulate database connection issues
   - Verify error events are sent
   - Verify logging includes `[STREAM_ERROR]`

3. **Test Socket Closure:**
   - Kill backend during streaming
   - Verify frontend detects socket error
   - Verify user sees helpful error message

4. **Monitor Logs:**
   - Check for `[STREAM_ERROR]` entries
   - Verify error context is logged
   - Check error recovery attempts

## Monitoring

### Key Log Patterns to Watch:

**Successful Streams:**
```
[STREAM_START] Starting SSE stream for job {id}
[STREAM_POLL] Job {id}: Poll #20, status=running...
[STREAM_COMPLETE] Job {id}: Status changed to completed...
```

**Errors:**
```
[STREAM_ERROR] Job {id}: Database refresh failed...
[STREAM_ERROR] Job {id}: Error during poll #X...
[STREAM_ERROR] Job {id}: Fatal error in stream generator...
```

**Frontend Errors:**
```
Streaming error: [TypeError: terminated]
Error [SocketError]: other side closed
UND_ERR_SOCKET
```

## Next Steps

1. **Deploy fixes** to staging/production
2. **Monitor logs** for `[STREAM_ERROR]` entries
3. **Track error rates** - should decrease significantly
4. **User feedback** - verify error messages are helpful
5. **Performance** - ensure error handling doesn't impact performance

## Related Issues

- Database connection pooling may need tuning for long-running streams
- Consider implementing connection retry logic
- May need to adjust database session timeout settings
