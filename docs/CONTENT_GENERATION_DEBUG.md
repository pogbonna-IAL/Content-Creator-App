# Content Generation Debugging Guide

## Issue Analysis from HTTP Log

### HTTP Log Entry Analysis
```
requestId: "axEpZcT9QR-GU9t8w9P4nw"
method: "POST"
path: "/v1/content/generate"
httpStatus: 201
totalDuration: 6453ms (6.4 seconds)
upstreamRqDuration: 6305ms
txBytes: 322
rxBytes: 876
```

### Findings

1. **Job Creation Succeeded** ✅
   - HTTP 201 status indicates job was created successfully
   - Response size (322 bytes) matches expected job creation response
   - Duration (6.4s) is reasonable for job creation

2. **Missing Stream Request** ❌
   - **No HTTP log entry for `GET /v1/content/jobs/{jobId}/stream`**
   - This suggests the frontend is NOT calling the streaming endpoint
   - OR the stream request is failing before it can be logged

3. **Potential Issues**

   **A. Frontend Not Calling Stream Endpoint**
   - The Next.js API route (`/api/generate`) creates the job
   - It should then call `/v1/content/jobs/{jobId}/stream`
   - Check browser console for errors
   - Check Next.js server logs for stream request

   **B. Async Task Failing Silently**
   - The async generation task is created with `asyncio.create_task()`
   - If it fails immediately, errors might not be logged
   - **FIXED**: Added comprehensive error handling and logging

   **C. Job Status Not Updating**
   - Job might be stuck in "pending" status
   - Async task might not be running
   - **FIXED**: Added logging to track async task execution

## Diagnostic Steps

### 1. Check Application Logs

Look for these log entries in Railway logs:

**Job Creation:**
```
[JOB_START] Job {job_id}: Starting content generation
[ASYNC_TASK] Created async task for job {job_id}
```

**Async Task Execution:**
```
[ASYNC_TASK] Starting async generation task for job {job_id}
[LLM_INIT] Initializing LLM for tier...
[CREW_INIT] Job {job_id}: Initializing ContentCreationCrew...
[LLM_EXEC] Job {job_id}: Starting CrewAI kickoff...
```

**Streaming:**
```
[STREAM_START] Starting SSE stream for job {job_id}
[STREAM_POLL] Starting polling loop for job {job_id}
```

**Errors:**
```
[ASYNC_TASK] Async generation task FAILED for job {job_id}
[JOB_FAILED] Job {job_id}: FAILED after...
```

### 2. Check Job Status

Query the database or use the API:
```bash
GET /v1/content/jobs/{job_id}
```

Check if:
- Status is "pending" (task not started)
- Status is "running" (task started but not completing)
- Status is "failed" (task failed - check logs)
- Status is "completed" (task succeeded - check artifacts)

### 3. Check Frontend Console

In browser DevTools, check:
- Network tab: Is `/api/generate` returning a stream?
- Console: Any errors about SSE/EventSource?
- Is the stream connection being established?

### 4. Check Next.js Logs

Look for:
- "Step 1: Creating job at..."
- "Job created with ID: {jobId}"
- "Step 2: Streaming job progress at..."
- Any errors in the Next.js API route

## Common Issues and Solutions

### Issue 1: Async Task Not Running

**Symptoms:**
- Job stays in "pending" status
- No logs from async task
- No LLM execution logs

**Possible Causes:**
- Event loop not running the task
- Task being garbage collected
- Exception in task creation

**Solution:**
- ✅ Added error handling wrapper
- ✅ Added task completion callback
- ✅ Added comprehensive logging

### Issue 2: Stream Endpoint Not Called

**Symptoms:**
- No HTTP log for stream endpoint
- Frontend shows "generating" but no progress
- No SSE events received

**Possible Causes:**
- Frontend not calling stream endpoint
- CORS issue preventing stream request
- Network timeout

**Solution:**
- Check browser network tab
- Check Next.js API route logs
- Verify CORS configuration

### Issue 3: LLM Execution Failing

**Symptoms:**
- Job status changes to "running" then "failed"
- Error logs show LLM/ Ollama connection issues
- Timeout errors

**Possible Causes:**
- Ollama not accessible
- Model not available
- Network timeout
- LLM execution timeout

**Solution:**
- Check Ollama health: `GET {OLLAMA_BASE_URL}/api/tags`
- Verify model is pulled: `ollama list`
- Check network connectivity
- Review timeout settings (currently 180s)

### Issue 4: Job Completing But No Content

**Symptoms:**
- Job status is "completed"
- No artifacts created
- No content in response

**Possible Causes:**
- Content extraction failing
- Validation failing
- Artifact creation failing

**Solution:**
- Check extraction logs: `[EXTRACTION]`
- Check validation logs: `[VALIDATION]`
- Check artifact creation logs: `[ARTIFACT]`

## Enhanced Logging Added

### Async Task Logging
- `[ASYNC_TASK]` - Task creation and execution
- `[JOB_START]` - Job initialization
- `[LLM_INIT]` - LLM configuration
- `[CREW_INIT]` - Crew initialization
- `[LLM_EXEC]` - LLM execution timing
- `[JOB_COMPLETE]` - Job completion
- `[JOB_FAILED]` - Job failure with details

### Streaming Logging
- `[STREAM_START]` - Stream endpoint called
- `[STREAM_POLL]` - Polling progress (every 10s)
- `[STREAM_COMPLETE]` - Stream completion

### Content Processing Logging
- `[EXTRACTION]` - Content extraction
- `[VALIDATION]` - Content validation
- `[MODERATION]` - Content moderation
- `[ARTIFACT]` - Artifact creation

## Next Steps

1. **Deploy the enhanced logging** - The new logging will help identify where the issue occurs

2. **Check Railway logs** for the request ID `axEpZcT9QR-GU9t8w9P4nw`:
   - Look for `[ASYNC_TASK]` logs
   - Look for `[STREAM_START]` logs
   - Look for `[LLM_EXEC]` logs
   - Look for any error logs

3. **Check job status** using the job ID from the 201 response

4. **Monitor new requests** - The enhanced logging will provide detailed visibility into the entire flow

## Query Logs by Request ID

To find all logs for a specific request:
```
@requestId = "axEpZcT9QR-GU9t8w9P4nw"
```

Or search for job-specific logs:
```
[ASYNC_TASK] OR [STREAM_START] OR [LLM_EXEC] AND job_id
```
