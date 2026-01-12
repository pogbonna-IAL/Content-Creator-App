# Voiceover Testing Guide

## Setup Complete ✅

1. **Piper TTS Installed**: `piper-tts` Python package installed
2. **Voice Model Downloaded**: `en_US-lessac-medium` model downloaded to `models/piper/`
3. **Storage Directory Created**: `storage/voiceovers/` directory created
4. **TTS Provider Working**: Basic TTS synthesis test passed

## Test Results

### 1. TTS Provider Test ✅
```bash
python scripts/test_tts.py
```
**Result**: ✅ Success
- Piper TTS available
- Synthesis successful (2.71 seconds, 22050 Hz)
- Storage successful (119340 bytes saved)

### 2. Next Steps for Full Testing

To test the complete voiceover flow:

1. **Start the API server**:
   ```bash
   uv run python api_server.py
   ```

2. **Run the voiceover endpoint test**:
   ```bash
   python scripts/test_voiceover_endpoint.py
   ```

This will test:
- Job creation with audio content
- Voiceover generation endpoint
- SSE event streaming
- Artifact retrieval
- File download from `/v1/storage/`

## Manual Testing

### Test Voiceover Generation

```bash
# 1. Create a job with audio content
curl -X POST http://localhost:8000/v1/content/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Introduction to AI",
    "content_types": ["audio"]
  }'

# 2. Wait for job to complete, then generate voiceover
curl -X POST http://localhost:8000/v1/content/voiceover \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": <job_id>,
    "voice_id": "en_US-lessac-medium",
    "speed": 1.0
  }'

# 3. Stream SSE events
curl -N http://localhost:8000/v1/content/jobs/<job_id>/stream \
  -H "Authorization: Bearer <token>"

# 4. Get job details (includes voiceover artifact)
curl http://localhost:8000/v1/content/jobs/<job_id> \
  -H "Authorization: Bearer <token>"

# 5. Download audio file
curl http://localhost:8000/v1/storage/voiceovers/<filename>.wav \
  -H "Authorization: Bearer <token>" \
  --output voiceover.wav
```

## Environment Variables

Set these if needed:
```bash
export PIPER_MODEL_PATH=./models/piper
export STORAGE_PATH=./storage
export TTS_PROVIDER=piper
```

## Troubleshooting

1. **Model not found**: Ensure `models/piper/en_US-lessac-medium.onnx` exists
2. **Storage errors**: Check `storage/voiceovers/` directory permissions
3. **SSE not working**: Verify API server is running and CORS is configured
4. **File download fails**: Check static file mount in `api_server.py`

