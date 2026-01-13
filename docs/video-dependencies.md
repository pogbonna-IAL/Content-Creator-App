# Video Rendering Dependencies

## Overview

Content Creation Crew supports video rendering using FFmpeg for encoding and processing. This document describes FFmpeg requirements, installation, and configuration.

## Table of Contents

1. [FFmpeg Requirements](#ffmpeg-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Startup Validation](#startup-validation)
5. [Troubleshooting](#troubleshooting)

---

## FFmpeg Requirements

### Minimum Version

- **FFmpeg 4.0+** (recommended: 5.0+)
- Must be available in system PATH
- Must support H.264 encoding (libx264)

### Required Features

- Video encoding (H.264/MP4)
- Audio encoding (AAC)
- Image processing (for frame generation)
- Subtitle/overlay support

### System Requirements

- **CPU:** Multi-core recommended for faster rendering
- **RAM:** 2GB+ free memory for video processing
- **Disk:** Sufficient space for temporary video files (typically 2-3x final video size)

---

## Installation

### Docker (Recommended)

FFmpeg is automatically included in the Docker image:

```dockerfile
# Dockerfile includes FFmpeg installation
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

**No additional setup required** - FFmpeg is pre-installed in the container.

### Local Development

#### Windows

**Option 1: Chocolatey (Recommended)**
```powershell
choco install ffmpeg
```

**Option 2: winget**
```powershell
winget install ffmpeg
```

**Option 3: Manual Installation**
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip file
3. Add the `bin` folder to your system PATH:
   - Open System Properties > Environment Variables
   - Edit PATH variable
   - Add: `C:\path\to\ffmpeg\bin`
4. Restart terminal/IDE

**Verify Installation:**
```powershell
ffmpeg -version
```

#### macOS

**Option 1: Homebrew (Recommended)**
```bash
brew install ffmpeg
```

**Option 2: MacPorts**
```bash
sudo port install ffmpeg
```

**Verify Installation:**
```bash
ffmpeg -version
```

#### Linux

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Fedora:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

**Verify Installation:**
```bash
ffmpeg -version
```

---

## Configuration

### Environment Variable

**`ENABLE_VIDEO_RENDERING`** - Enable/disable video rendering features

**Values:**
- `true` - Video rendering enabled (FFmpeg required)
- `false` - Video rendering disabled (FFmpeg optional)

**Default:** `false`

**Example (.env):**
```bash
# Enable video rendering (requires FFmpeg)
ENABLE_VIDEO_RENDERING=true

# Disable video rendering (FFmpeg not required)
ENABLE_VIDEO_RENDERING=false
```

### Startup Behavior

#### With `ENABLE_VIDEO_RENDERING=true`

- **FFmpeg Required:** Application will fail to start if FFmpeg is not available
- **Validation:** FFmpeg is checked at startup with 5-second timeout
- **Error:** RuntimeError raised if FFmpeg missing

**Example Error:**
```
RuntimeError: Video rendering is enabled (ENABLE_VIDEO_RENDERING=true) but FFmpeg is not available. 
FFmpeg is not installed or not in PATH. 
Install FFmpeg or set ENABLE_VIDEO_RENDERING=false to disable video features.
```

#### With `ENABLE_VIDEO_RENDERING=false`

- **FFmpeg Optional:** Application starts even if FFmpeg is missing
- **Warning:** Warning logged if FFmpeg is not available
- **Behavior:** Video rendering endpoints return errors if attempted

**Example Warning:**
```
⚠️  FFmpeg is not available. Video rendering features will be disabled. 
Set ENABLE_VIDEO_RENDERING=true and install FFmpeg to enable video rendering.
```

---

## Startup Validation

### Validation Process

1. **Check FFmpeg Availability:**
   - Runs `ffmpeg -version` command
   - Timeout: 5 seconds
   - Captures version information

2. **Behavior Based on Config:**
   - If `ENABLE_VIDEO_RENDERING=true`: Fail fast if FFmpeg missing
   - If `ENABLE_VIDEO_RENDERING=false`: Warn only if FFmpeg missing

3. **Environment-Specific Behavior:**
   - **Production/Staging:** Application exits if validation fails
   - **Development:** Warning logged, application continues

### Validation Code

**Location:** `src/content_creation_crew/services/ffmpeg_check.py`

**Function:** `validate_ffmpeg_startup(enable_video_rendering, timeout=5.0)`

**Called From:** `api_server.py` at startup

---

## Troubleshooting

### FFmpeg Not Found

**Error:**
```
FileNotFoundError: FFmpeg is not installed or not in PATH
```

**Solutions:**
1. **Install FFmpeg** (see Installation section above)
2. **Add to PATH:**
   - Windows: Add FFmpeg `bin` folder to system PATH
   - macOS/Linux: Ensure FFmpeg is in `/usr/local/bin` or add to PATH
3. **Verify Installation:**
   ```bash
   ffmpeg -version
   ```
4. **Restart Application:** After installing FFmpeg, restart the application

### FFmpeg Check Timeout

**Error:**
```
FFmpeg check timed out after 5 seconds
```

**Solutions:**
1. **Check System Load:** High CPU/memory usage may slow FFmpeg
2. **Increase Timeout:** Modify `timeout` parameter in `validate_ffmpeg_startup()`
3. **Check Permissions:** Ensure FFmpeg executable has proper permissions
4. **Verify Installation:** Run `ffmpeg -version` manually to test

### Video Rendering Fails Despite FFmpeg Installed

**Possible Causes:**
1. **Wrong FFmpeg Version:** Ensure FFmpeg 4.0+ is installed
2. **Missing Codecs:** Install additional codecs if needed
3. **Permissions:** Check file permissions for temporary directories
4. **Disk Space:** Ensure sufficient disk space for video processing

**Debug Steps:**
1. **Test FFmpeg Manually:**
   ```bash
   ffmpeg -version
   ffmpeg -codecs | grep h264
   ```
2. **Check Application Logs:** Look for FFmpeg-related errors
3. **Verify Configuration:** Ensure `ENABLE_VIDEO_RENDERING=true`
4. **Check Dependencies:** Verify PIL and MoviePy are installed

### Docker Container Issues

**FFmpeg Not Available in Container:**

1. **Rebuild Image:**
   ```bash
   docker-compose build --no-cache api
   ```
2. **Verify Dockerfile:** Ensure FFmpeg is installed in Dockerfile
3. **Check Container:**
   ```bash
   docker-compose exec api ffmpeg -version
   ```

**FFmpeg Works Locally but Not in Docker:**

1. **Check PATH:** Ensure FFmpeg is in container PATH
2. **Verify Installation:** Check if FFmpeg is installed in container
3. **Check Logs:** Review container startup logs

---

## Testing FFmpeg Installation

### Quick Test

```bash
# Check FFmpeg version
ffmpeg -version

# Test encoding (creates a test video)
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 test.mp4

# Verify test video
ls -lh test.mp4
```

### Using Check Script

**Location:** `scripts/check_ffmpeg.py`

**Usage:**
```bash
python scripts/check_ffmpeg.py
```

**Output:**
```
Checking FFmpeg installation...

[OK] FFmpeg is installed: ffmpeg version 5.1.2
[OK] FFmpeg is ready to use!
```

---

## Production Recommendations

### Docker Deployment

✅ **Recommended:** Use Docker image with FFmpeg pre-installed

**Benefits:**
- Consistent environment
- No manual installation required
- Version control via Dockerfile

### System Requirements

- **CPU:** 2+ cores recommended
- **RAM:** 4GB+ for video processing
- **Disk:** 10GB+ free space for temporary files

### Monitoring

- Monitor FFmpeg process CPU/memory usage
- Track video rendering success/failure rates
- Alert on FFmpeg unavailability

---

## Related Documentation

- [Video Rendering Implementation](./video-rendering-implementation.md) - Video rendering architecture
- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Health Checks](./health-checks-implementation.md) - Health endpoint documentation

---

## Quick Reference

### Enable Video Rendering

```bash
# .env
ENABLE_VIDEO_RENDERING=true
```

### Disable Video Rendering

```bash
# .env
ENABLE_VIDEO_RENDERING=false
```

### Check FFmpeg

```bash
ffmpeg -version
```

### Test Installation

```bash
python scripts/check_ffmpeg.py
```

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

