# Ollama Model Management Guide

## Overview

Content Creation Crew uses **Ollama** for local LLM inference. This document explains model configuration, download procedures, and lifecycle management.

## Table of Contents

1. [Model Configuration by Tier](#model-configuration-by-tier)
2. [Model Download Automation](#model-download-automation)
3. [Model Storage and Disk Requirements](#model-storage-and-disk-requirements)
4. [Changing Models Safely](#changing-models-safely)
5. [Troubleshooting](#troubleshooting)

---

## Model Configuration by Tier

Models are configured in `src/content_creation_crew/config/tiers.yaml`:

| Tier | Model | Size | Speed | Quality | Use Case |
|------|-------|------|-------|---------|----------|
| **Free** | `llama3.2:1b` | ~1.3 GB | ⚡ Fastest | Basic | Quick content generation |
| **Basic** | `llama3.2:3b` | ~2.0 GB | ⚡ Fast | Good | Balanced quality/speed |
| **Pro** | `llama3.1:8b` | ~4.7 GB | ⚡ Moderate | High | High-quality content |
| **Enterprise** | `llama3.1:70b` | ~40 GB | ⚡ Slower | Best | Premium quality content |

### Model Selection Logic

Models are automatically selected based on user subscription tier:

```python
# In src/content_creation_crew/crew.py
def _get_model_for_tier(self, tier: str) -> str:
    tier_config = self.tier_config.get(tier, {})
    model = tier_config.get('model', 'ollama/llama3.2:1b')
    return model
```

**Default Model:** If tier is not found, defaults to `llama3.2:1b` (free tier model).

---

## Model Download Automation

### Quick Start

**Download all required models:**
```bash
make models-pull
```

This command:
1. Detects if Ollama is running (Docker or local)
2. Extracts models from `tiers.yaml` or uses `MODEL_NAMES` env var
3. Downloads each model
4. Verifies model availability

### Manual Download

**Using Ollama CLI:**
```bash
# Download individual models
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama pull llama3.1:70b  # Enterprise tier only
```

**Using Docker:**
```bash
# If Ollama is running in Docker
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull llama3.1:8b
```

### Using Pull Scripts

**Bash Script (Linux/Mac):**
```bash
bash infra/scripts/pull-models.sh
```

**Python Script (Cross-platform):**
```bash
python3 infra/scripts/pull-models.py
# Or with uv
uv run python infra/scripts/pull-models.py
```

**With Custom Models:**
```bash
MODEL_NAMES="llama3.2:1b,llama3.2:3b,llama3.1:8b" make models-pull
```

### Environment Variable Configuration

Set `MODEL_NAMES` in your `.env` file:

```bash
# .env
MODEL_NAMES=llama3.2:1b,llama3.2:3b,llama3.1:8b
```

**Note:** Models are comma-separated. The `ollama/` prefix is optional and will be stripped automatically.

---

## Model Storage and Disk Requirements

### Storage Location

**Local Installation:**
- **Linux/Mac:** `~/.ollama/models/`
- **Windows:** `C:\Users\<username>\.ollama\models\`

**Docker Installation:**
- Volume: `ollama_data:/root/.ollama`
- Location: Docker volume (managed by Docker)

### Disk Space Requirements

| Model | Size | Total Space Needed |
|-------|------|-------------------|
| `llama3.2:1b` | ~1.3 GB | 1.3 GB |
| `llama3.2:3b` | ~2.0 GB | 2.0 GB |
| `llama3.1:8b` | ~4.7 GB | 4.7 GB |
| `llama3.1:70b` | ~40 GB | 40 GB |

**Minimum Requirements:**
- **Free/Basic tiers:** ~2 GB free space
- **Pro tier:** ~5 GB free space
- **Enterprise tier:** ~40 GB free space
- **All tiers:** ~48 GB free space

**Recommendation:** Keep at least 10 GB free space for model updates and temporary files.

### Checking Disk Usage

**Local:**
```bash
# Check Ollama storage
du -sh ~/.ollama/models/

# List downloaded models
ollama list
```

**Docker:**
```bash
# Check Docker volume size
docker system df

# List models in container
docker compose exec ollama ollama list
```

---

## Changing Models Safely

### When to Change Models

**Safe Scenarios:**
- ✅ Upgrading to a better model for a tier
- ✅ Testing new models in development
- ✅ Adjusting model for performance optimization

**Risky Scenarios:**
- ⚠️ Downgrading models (may affect content quality)
- ⚠️ Changing models in production without testing
- ⚠️ Removing models that are in use

### Step-by-Step Model Change Process

#### 1. **Update Configuration**

Edit `src/content_creation_crew/config/tiers.yaml`:

```yaml
tiers:
  pro:
    # ... other config ...
    model: "ollama/llama3.1:8b"  # Change this line
```

#### 2. **Download New Model**

```bash
# Download the new model
ollama pull llama3.1:8b

# Or use automation
make models-pull
```

#### 3. **Verify Model Availability**

```bash
# Check model exists
ollama list | grep llama3.1:8b

# Test model works
ollama run llama3.1:8b "Hello, how are you?"
```

#### 4. **Test in Development**

```bash
# Start application
make dev-api

# Test content generation with new model
# Verify quality and performance
```

#### 5. **Deploy to Staging**

- Deploy code changes
- Verify model is used correctly
- Monitor performance and quality

#### 6. **Deploy to Production**

- Deploy during low-traffic period
- Monitor application logs
- Verify content quality

### Removing Old Models

**Before removing a model:**
1. Ensure no active users are using it
2. Verify new model is working correctly
3. Keep old model for rollback if needed

**Remove model:**
```bash
# Remove model (frees disk space)
ollama rm llama3.2:1b
```

**Docker:**
```bash
docker compose exec ollama ollama rm llama3.2:1b
```

---

## Model Lifecycle

### Development Workflow

1. **Initial Setup:**
   ```bash
   # Start Ollama
   make up-ollama  # or: ollama serve
   
   # Download required models
   make models-pull
   ```

2. **During Development:**
   - Models are cached locally
   - No re-download needed unless model changes
   - Test with different models as needed

3. **Before Deployment:**
   - Verify all required models are downloaded
   - Check disk space availability
   - Test model availability

### Production Deployment

**Option 1: Pre-flight Model Download (Recommended)**

Create a deployment script that runs before application startup:

```bash
#!/bin/bash
# scripts/pre-deploy-models.sh

echo "Downloading required Ollama models..."

# Extract models from tiers.yaml or use MODEL_NAMES
MODELS="llama3.2:1b llama3.2:3b llama3.1:8b"

for model in $MODELS; do
    if ! ollama list | grep -q "$model"; then
        echo "Pulling $model..."
        ollama pull "$model"
    else
        echo "$model already exists"
    fi
done

echo "✓ All models ready"
```

**Option 2: Init Container (Kubernetes)**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: model-init
spec:
  initContainers:
  - name: pull-models
    image: ollama/ollama:latest
    command: ["/bin/sh", "-c"]
    args:
      - |
        ollama pull llama3.2:1b
        ollama pull llama3.2:3b
        ollama pull llama3.1:8b
    volumeMounts:
    - name: ollama-data
      mountPath: /root/.ollama
  containers:
  - name: app
    # ... your app container ...
```

**Option 3: Docker Compose Init**

Add to `docker-compose.yml`:

```yaml
services:
  model-init:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    command: >
      sh -c "
        ollama pull llama3.2:1b &&
        ollama pull llama3.2:3b &&
        ollama pull llama3.1:8b &&
        echo 'Models ready'
      "
    profiles:
      - init
    depends_on:
      - ollama
```

---

## Troubleshooting

### Model Not Found

**Error:** `Error: model 'llama3.2:1b' not found`

**Solution:**
```bash
# Download the model
ollama pull llama3.2:1b

# Verify it's available
ollama list
```

### Model Download Fails

**Error:** `Error: failed to pull model`

**Possible Causes:**
1. **Network issues:** Check internet connection
2. **Disk space:** Ensure sufficient free space
3. **Ollama service:** Verify Ollama is running

**Solution:**
```bash
# Check Ollama status
ollama list

# Check disk space
df -h ~/.ollama/models/

# Restart Ollama
ollama serve  # or: docker compose restart ollama
```

### Model Not Used Correctly

**Issue:** Application uses wrong model

**Check:**
1. Verify `tiers.yaml` configuration
2. Check user's subscription tier
3. Verify model name format (with/without `ollama/` prefix)

**Debug:**
```python
# In Python
from content_creation_crew.crew import ContentCreationCrew

crew = ContentCreationCrew(tier='pro')
print(crew._get_model_for_tier('pro'))  # Should print: ollama/llama3.1:8b
```

### Slow Model Performance

**Issue:** Model responses are slow

**Solutions:**
1. **Use smaller model:** Switch to `llama3.2:1b` or `llama3.2:3b`
2. **Check system resources:** Ensure sufficient CPU/RAM
3. **Optimize temperature:** Lower temperature = faster responses
4. **Use GPU:** Ollama supports GPU acceleration (if available)

### Docker Volume Full

**Error:** `no space left on device`

**Solution:**
```bash
# Check volume size
docker system df

# Remove unused models
docker compose exec ollama ollama rm <unused-model>

# Or clean up Docker system
docker system prune -a --volumes
```

---

## Best Practices

### ✅ DO

- ✅ Download models before deployment
- ✅ Verify model availability after download
- ✅ Test model changes in development first
- ✅ Monitor disk space usage
- ✅ Keep models for rollback if needed
- ✅ Document model changes in commit messages

### ❌ DON'T

- ❌ Don't download models during application startup
- ❌ Don't change models in production without testing
- ❌ Don't remove models that are actively used
- ❌ Don't ignore disk space warnings
- ❌ Don't use models that exceed system resources

---

## Related Documentation

- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Environment Configuration](./env-configuration-summary.md) - Environment variables
- [Architecture](../ARCHITECTURE.md) - System architecture

---

**Last Updated:** January 13, 2026  
**Ollama Version:** Latest  
**Status:** ✅ Production Ready

