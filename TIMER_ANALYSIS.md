# Timer Analysis: Blog vs Audio Artifact Streaming

## Executive Summary

After reviewing the blog content artifact streaming timers and audio content artifact timers, I've identified **3 critical issues** that are causing audio artifact streaming to fail most of the time:

1. **Polling interval too slow for completed jobs** - Audio artifacts are detected with 2-second delay
2. **Race condition between database commit and SSE store events** - Artifacts may be detected before events are added
3. **Missing immediate event delivery for audio artifacts** - Unlike blog content, audio artifacts aren't streamed immediately

---

## Blog Content Artifact Streaming (Working)

### Flow:
1. **Immediate Streaming** (lines 2443-2470):
   - Content is streamed in 500-character chunks **BEFORE** database commit
   - Uses `sse_store.add_event()` to send content events synchronously
   - No polling needed - content is streamed during generation

### Timers:
- **No polling delay** - Content is streamed immediately during generation
- **Keep-alive**: 5 seconds (line 826)
- **Chunk size**: 500 characters

### Why It Works:
- Content is available immediately during generation
- No database polling required
- Events are sent synchronously before database commit

---

## Audio Content Artifact Streaming (Failing)

### Flow:
1. **TTS Generation** (lines 3519-3819):
   - TTS synthesis completes
   - Audio file is saved to storage
   - **Database commit** happens (line 3770)
   - **THEN** `artifact_ready` and `tts_completed` events are added to SSE store (lines 3782-3811)

2. **Polling Detection** (lines 1309-1443):
   - `stream_job_progress` polls database and SSE store
   - Checks SSE store events FIRST (lines 1309-1331)
   - Checks database artifacts SECOND (lines 1332-1400)
   - Uses adaptive polling intervals

### Timers:
- **Adaptive Polling Intervals** (lines 1426-1438):
  - `pending`: 1.0 seconds
  - `running` (< 30s): 0.3 seconds
  - `running` (30-120s): 0.5 seconds
  - `running` (> 120s): 1.0 seconds
  - **`completed`/`failed`: 2.0 seconds** ⚠️ **ISSUE #1**
- **Keep-alive**: 5 seconds (line 826)

### Why It Fails:

#### Issue #1: Polling Interval Too Slow for Completed Jobs
**Location**: Line 1438
```python
else:
    return 2.0  # Slow polling for completed/failed jobs
```

**Problem**: 
- When audio generation completes, the job status may be `completed` or `running` (if job hasn't been updated yet)
- If status is `completed`, polling interval is **2.0 seconds**
- This means `tts_completed` event can take up to **2 seconds** to be detected and sent
- Frontend timeout is only **2 seconds** (AudioPanel.tsx line 375), creating a race condition

**Impact**: 
- High probability of timeout before event is detected
- Frontend may complete progress before backend sends `tts_completed`

#### Issue #2: Race Condition Between Database Commit and SSE Store Events
**Location**: Lines 3770-3811

**Problem**:
- Database commit happens at line 3770
- SSE store events are added AFTER commit (lines 3782-3811)
- Polling loop checks SSE store FIRST (lines 1309-1331), then database artifacts (lines 1332-1400)
- If polling happens between commit and SSE store event addition:
  - Database artifact is detected first
  - `artifact_ready` event is sent from database (line 1357)
  - This updates `last_sent_event_id` (line 1371)
  - When SSE store events are checked, they may be skipped if `event_id <= last_sent_event_id` (line 1412)

**Impact**:
- `tts_completed` event may be skipped if `artifact_ready` from database has higher event ID
- Frontend never receives `tts_completed`, progress stuck at 90%

#### Issue #3: Missing Immediate Event Delivery
**Location**: Lines 3770-3811

**Problem**:
- Unlike blog content, audio artifacts are NOT streamed immediately
- Events are added to SSE store AFTER database commit
- Relies on polling loop to detect and send events
- No immediate flush/notification mechanism

**Impact**:
- Delayed event delivery
- Higher chance of timeout
- Less reliable than blog content streaming

---

## Recommended Fixes

### Fix #1: Reduce Polling Interval for Completed Jobs
**Priority**: HIGH
**Location**: Line 1438

**Change**:
```python
else:
    # For completed/failed jobs, use faster polling to catch final events quickly
    # Audio artifacts may be created just before job completion
    return 0.5  # Faster polling for completed jobs (was 2.0)
```

**Rationale**: 
- Completed jobs may still have pending events (like `tts_completed`)
- 0.5s polling ensures events are detected within 0.5s instead of 2s
- Reduces timeout race condition

### Fix #2: Add Immediate Event Notification
**Priority**: HIGH
**Location**: Lines 3782-3811

**Change**: Add immediate event yield/flush after adding to SSE store:
```python
# After adding events to SSE store, immediately notify polling loop
# This ensures events are detected on next poll cycle
# Note: We can't yield directly from async task, but we can ensure events are ready
logger.info(f"[VOICEOVER_ASYNC] Events added to SSE store, ready for polling")
```

**Better Solution**: Add a notification mechanism or reduce polling interval when events are detected.

### Fix #3: Ensure SSE Store Events Are Added Before Database Commit
**Priority**: MEDIUM
**Location**: Lines 3770-3811

**Change**: Reorder operations:
1. Add SSE store events FIRST
2. Then commit database
3. This ensures events are available when polling detects database artifacts

**Rationale**: 
- Prevents race condition where database artifact is detected before SSE events
- Ensures proper event ordering

### Fix #4: Add Dedicated Fast Polling for Voiceover Jobs
**Priority**: MEDIUM
**Location**: Lines 1426-1438

**Change**: Detect voiceover jobs and use faster polling:
```python
def get_poll_interval(job_status: str, elapsed_time: float, has_voiceover: bool = False) -> float:
    """Get optimal polling interval based on job stage"""
    # Use faster polling for voiceover jobs to catch tts_completed events quickly
    if has_voiceover and job_status in ['running', 'completed']:
        return 0.2  # Very fast polling for voiceover jobs
    
    if job_status == 'pending':
        return 1.0
    elif job_status == 'running':
        if elapsed_time < 30:
            return 0.3
        elif elapsed_time < 120:
            return 0.5
        else:
            return 1.0
    else:
        return 0.5  # Faster polling for completed jobs (was 2.0)
```

**Rationale**:
- Voiceover jobs need faster polling to catch `tts_completed` events
- Reduces timeout failures

---

## Comparison Table

| Aspect | Blog Content | Audio Content | Issue |
|--------|-------------|---------------|-------|
| **Streaming Method** | Immediate (during generation) | Polling-based (after generation) | Audio relies on polling |
| **Database Commit** | After streaming | Before event addition | Race condition |
| **Polling Interval** | N/A (no polling) | 0.3s - 2.0s | Too slow for completed jobs |
| **Event Delivery** | Synchronous | Asynchronous (polling) | Delayed delivery |
| **Timeout Risk** | Low | High (2s polling + 2s frontend timeout) | Race condition |

---

## Conclusion

The root cause of audio artifact streaming failures is the **combination of slow polling intervals for completed jobs and a race condition between database commit and SSE store event addition**. Unlike blog content which streams immediately, audio artifacts rely on polling which introduces delays and timing issues.

**Recommended Priority**:
1. **Fix #1** (Reduce polling interval) - Quick fix, high impact
2. **Fix #3** (Reorder operations) - Prevents race condition
3. **Fix #2** (Immediate notification) - Improves reliability
4. **Fix #4** (Dedicated fast polling) - Long-term improvement
