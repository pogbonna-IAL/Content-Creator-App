# Debugging Streaming Issues

## Steps to Debug

1. **Check API Server Logs**
   - Look for "Sent initial status", "Content extracted successfully", etc.
   - Check if content length is > 0

2. **Check Browser Console**
   - Open DevTools (F12)
   - Look for console.log messages:
     - "Starting to read stream..."
     - "Received chunk: ..."
     - "Parsed SSE data: ..."
     - "Final accumulatedContent length: ..."

3. **Test Direct API Call**
   ```bash
   python test_streaming.py
   ```
   This will show if the FastAPI server is streaming correctly.

4. **Check Network Tab**
   - Open DevTools → Network tab
   - Look for `/api/generate` request
   - Check if it's showing as "EventStream" type
   - Click on it and check "Preview" or "Response" tab

5. **Common Issues**
   - Content extraction failing (check content_output.md exists)
   - SSE format issues (should be `data: {...}\n\n`)
   - Buffer not being flushed
   - CORS issues (check browser console for CORS errors)

## Quick Test

Run this in browser console while on the page:
```javascript
fetch('/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ topic: 'test' })
}).then(r => {
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  function read() {
    reader.read().then(({done, value}) => {
      if (done) return;
      console.log('Chunk:', decoder.decode(value));
      read();
    });
  }
  read();
});
```

