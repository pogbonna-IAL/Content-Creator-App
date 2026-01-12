# Voice Generation (TTS) Implementation

## Overview

This document describes the Text-to-Speech (TTS) voice generation feature implemented for the Content Creation Crew platform. The implementation follows an adapter pattern to support multiple TTS providers and includes full integration with the jobs-first persistence system and SSE streaming.

## Architecture

### TTS Provider Interface

**Location:** `src/content_creation_crew/services/tts_provider.py`

The `TTSProvider` abstract base class defines the interface for TTS providers:

```python
class TTSProvider(ABC):
    def synthesize(text, voice_id, speed, format) -> Tuple[bytes, Dict]
    def get_available_voices() -> List[str]
    def is_available() -> bool
```

### Implementations

1. **PiperTTSProvider** (Default)
   - Open-source TTS engine
   - Local runtime (no external API calls)
   - Supports WAV format
   - Configurable via `PIPER_BINARY` and `PIPER_MODEL_PATH` environment variables
   - Available voices: `en_US-lessac-medium`, `en_US-amy-medium`, `en_GB-alba-medium`, etc.

2. **CoquiXTTSProvider** (Optional, behind config flag)
   - Placeholder implementation
   - Enabled via `ENABLE_COQUI_TTS=true` environment variable
   - Requires TTS library installation

### Storage Provider Interface

**Location:** `src/content_creation_crew/services/storage_provider.py`

The `StorageProvider` abstract base class provides file storage abstraction:

```python
class StorageProvider(ABC):
    def put(key, data, content_type) -> str
    def get(key) -> Optional[bytes]
    def delete(key) -> bool
    def get_url(key) -> str
```

### Implementations

1. **LocalDiskStorageProvider** (Default for dev)
   - Stores files in local filesystem
   - Base path configurable via `STORAGE_PATH` (default: `./storage`)
   - Creates subdirectories: `voiceovers/`, `artifacts/`
   - Files served via FastAPI static file mount at `/v1/storage/`

2. **S3StorageProvider** (For production)
   - S3-compatible storage
   - Requires `S3_BUCKET_NAME` environment variable
   - Optional: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`
   - Uses boto3 library (optional dependency)

## Data Model

### ContentArtifact Extension

The `ContentArtifact` model already supports the `voiceover_audio` type:

- **type**: `'voiceover_audio'`
- **content_text**: First 500 characters of narration text (reference)
- **content_json**: Metadata including:
  - `voice_id`: Voice identifier used
  - `duration_sec`: Audio duration in seconds
  - `format`: Audio format (e.g., 'wav')
  - `sample_rate`: Audio sample rate
  - `text_hash`: SHA256 hash of input text (for deduplication)
  - `storage_key`: Storage provider key/path
  - `storage_url`: Public URL or path to audio file
  - `provider`: TTS provider name (e.g., 'piper')

## API Endpoints

### POST /v1/content/voiceover

Creates a voiceover (TTS) for a job's audio script or provided narration text.

**Request Body:**
```json
{
  "job_id": 123,  // Optional: Use audio_script from this job
  "narration_text": "Text to synthesize...",  // Optional: Direct text input
  "voice_id": "default",  // Optional: Voice identifier (default: "default")
  "speed": 1.0,  // Optional: Speech speed multiplier 0.5-2.0 (default: 1.0)
  "format": "wav"  // Optional: Output format (default: "wav")
}
```

**Response:**
```json
{
  "job_id": 123,
  "status": "processing",
  "message": "Voiceover generation started"
}
```

**Behavior:**
- If `job_id` provided: Uses `audio` artifact's `content_text` as narration
- If `narration_text` provided: Creates new job for standalone voiceover
- Returns immediately (202 Accepted) and processes asynchronously
- Progress streamed via SSE at `/v1/content/jobs/{job_id}/stream`

### GET /v1/content/jobs/{job_id}

Returns job details including `voiceover_audio` artifacts:

**Response includes:**
```json
{
  "id": 123,
  "artifacts": [
    {
      "id": 456,
      "type": "voiceover_audio",
      "created_at": "2024-01-01T12:00:00Z",
      "has_content": true,
      "metadata": {
        "voice_id": "default",
        "duration_sec": 45.2,
        "format": "wav",
        "sample_rate": 22050,
        "storage_key": "voiceovers/20240101_120000_abc123.wav",
        "storage_url": "/v1/storage/voiceovers/20240101_120000_abc123.wav"
      },
      "url": "/v1/storage/voiceovers/20240101_120000_abc123.wav"
    }
  ]
}
```

## SSE Events

The existing SSE stream (`GET /v1/content/jobs/{job_id}/stream`) now includes TTS-specific events:

### tts_started
```json
{
  "type": "tts_started",
  "job_id": 123,
  "voice_id": "default",
  "text_length": 500
}
```

### tts_progress
```json
{
  "type": "tts_progress",
  "job_id": 123,
  "message": "Synthesizing speech...",
  "progress": 25
}
```

### artifact_ready (for voiceover_audio)
```json
{
  "type": "artifact_ready",
  "job_id": 123,
  "artifact_type": "voiceover_audio",
  "artifact_id": 456,
  "metadata": {
    "voice_id": "default",
    "duration_sec": 45.2,
    "format": "wav",
    "storage_key": "voiceovers/20240101_120000_abc123.wav",
    "storage_url": "/v1/storage/voiceovers/20240101_120000_abc123.wav"
  },
  "url": "/v1/storage/voiceovers/20240101_120000_abc123.wav"
}
```

### tts_completed
```json
{
  "type": "tts_completed",
  "job_id": 123,
  "artifact_id": 456,
  "duration_sec": 45.2,
  "storage_url": "/v1/storage/voiceovers/20240101_120000_abc123.wav"
}
```

### tts_failed
```json
{
  "type": "tts_failed",
  "job_id": 123,
  "message": "Voiceover generation failed: ...",
  "error_type": "RuntimeError"
}
```

## Static File Serving

Audio files are served via FastAPI static file mount:

- **Endpoint:** `/v1/storage/{path}`
- **Location:** `api_server.py` (line ~232)
- **Directory:** `STORAGE_PATH` environment variable (default: `./storage`)
- **Access:** Public read access (authentication can be added if needed)

## Configuration

### Environment Variables

**TTS Provider:**
- `TTS_PROVIDER`: Provider name ('piper' or 'coqui', default: 'piper')
- `PIPER_BINARY`: Path to piper binary (default: 'piper')
- `PIPER_MODEL_PATH`: Path to Piper models directory (default: 'models/piper')
- `ENABLE_COQUI_TTS`: Enable Coqui TTS ('true' or 'false', default: 'false')

**Storage:**
- `STORAGE_PROVIDER`: Storage provider ('local' or 's3', default: 'local')
- `STORAGE_PATH`: Local storage directory (default: './storage')
- `S3_BUCKET_NAME`: S3 bucket name (required for S3 storage)
- `AWS_ACCESS_KEY_ID`: AWS access key (optional, can use env/credentials)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional)
- `S3_ENDPOINT_URL`: Custom S3 endpoint (for S3-compatible services)

## Usage Examples

### Generate Voiceover from Job

```bash
curl -X POST http://localhost:8000/v1/content/voiceover \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 123,
    "voice_id": "en_US-amy-medium",
    "speed": 1.0
  }'
```

### Generate Standalone Voiceover

```bash
curl -X POST http://localhost:8000/v1/content/voiceover \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "narration_text": "Hello, this is a test voiceover.",
    "voice_id": "default",
    "speed": 1.2
  }'
```

### Stream Progress via SSE

```bash
curl -N http://localhost:8000/v1/content/jobs/123/stream \
  -H "Authorization: Bearer <token>"
```

### Download Generated Audio

```bash
curl http://localhost:8000/v1/storage/voiceovers/20240101_120000_abc123.wav \
  -H "Authorization: Bearer <token>" \
  --output voiceover.wav
```

## Integration with Existing System

### Preserves Existing Functionality

- ✅ Script generation (`audio` artifact type) remains unchanged
- ✅ Existing `/api/generate/stream` contract unchanged
- ✅ Voiceover uses `audio_script` narration when `job_id` provided
- ✅ All artifacts stored in same `ContentArtifact` table

### New Capabilities

- ✅ Real voice generation (not just scripts)
- ✅ Multiple TTS providers via adapter pattern
- ✅ Flexible storage (local filesystem or S3)
- ✅ Full SSE integration for real-time progress
- ✅ Standalone voiceover generation (without prior job)

## Testing

### Local Development

1. **Install Piper TTS:**
   ```bash
   # Install piper-tts (varies by OS)
   # Example for Linux:
   wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
   tar -xzf piper_amd64.tar.gz
   export PIPER_BINARY=$(pwd)/piper/piper
   ```

2. **Download Piper Models:**
   ```bash
   mkdir -p models/piper
   # Download models from https://huggingface.co/rhasspy/piper-voices
   # Example: en_US-lessac-medium.onnx
   ```

3. **Set Environment Variables:**
   ```bash
   export TTS_PROVIDER=piper
   export PIPER_BINARY=/path/to/piper
   export PIPER_MODEL_PATH=./models/piper
   export STORAGE_PATH=./storage
   ```

4. **Test Voiceover Generation:**
   ```bash
   # Create a job with audio content first
   curl -X POST http://localhost:8000/v1/content/generate \
     -H "Authorization: Bearer <token>" \
     -d '{"topic": "Test topic", "content_types": ["audio"]}'
   
   # Then generate voiceover
   curl -X POST http://localhost:8000/v1/content/voiceover \
     -H "Authorization: Bearer <token>" \
     -d '{"job_id": 123}'
   ```

## Acceptance Criteria Status

- ✅ TTS provider interface with adapter pattern
- ✅ PiperTTSProvider as default implementation
- ✅ Storage provider abstraction (local + S3)
- ✅ ContentArtifact supports `voiceover_audio` type
- ✅ POST /v1/content/voiceover endpoint
- ✅ GET /v1/content/jobs/{id} includes voiceover artifacts
- ✅ SSE events: tts_started, tts_progress, artifact_ready, tts_completed, tts_failed
- ✅ Works locally with docker compose + Postgres + Redis
- ✅ Preserves existing script generation
- ✅ Voiceover uses audio_script narration when available

## Future Enhancements

1. **Additional TTS Providers:**
   - Google Cloud Text-to-Speech
   - Amazon Polly
   - Azure Cognitive Services

2. **Audio Format Support:**
   - MP3 encoding
   - OGG Vorbis
   - FLAC (lossless)

3. **Voice Cloning:**
   - Custom voice training
   - Voice import from audio samples

4. **Batch Processing:**
   - Multiple voiceovers in parallel
   - Queue-based processing for high volume

5. **Caching:**
   - Cache generated audio by text_hash
   - Reuse existing voiceovers for identical text

