# Migration to GPT-4o-mini

## Overview

This document describes the migration from Ollama-based LLM models to OpenAI's `gpt-4o-mini` for content generation. This change addresses reliability issues with local Ollama instances and provides better performance and scalability.

## Changes Implemented

### 1. Configuration Updates (`src/content_creation_crew/config.py`)

- **Added**: `OPENAI_API_KEY` environment variable support
- **Updated**: LLM provider validation to accept either OpenAI or Ollama
- **Changed**: Made `OLLAMA_BASE_URL` optional when OpenAI is configured

### 2. Crew Initialization (`src/content_creation_crew/crew.py`)

- **Added**: Automatic provider detection (OpenAI vs Ollama)
- **Updated**: LLM initialization to conditionally use `base_url` (only for Ollama)
- **Changed**: Default model fallbacks from Ollama models to `gpt-4o-mini`
- **Enhanced**: Logging to show which provider is being used

### 3. Tier Configuration (`src/content_creation_crew/config/tiers.yaml`)

- **Updated**: All tier models changed from:
  - `ollama/llama3.2:1b` → `gpt-4o-mini`
  - `ollama/llama3.2:3b` → `gpt-4o-mini`
  - `ollama/llama3.1:8b` → `gpt-4o-mini`
  - `ollama/llama3.1:70b` → `gpt-4o-mini`

### 4. Plan Policy (`src/content_creation_crew/services/plan_policy.py`)

- **Updated**: Default model fallback from `ollama/llama3.2:1b` to `gpt-4o-mini`

### 5. Health Check (`src/content_creation_crew/services/health_check.py`)

- **Added**: OpenAI API connectivity check
- **Updated**: Prioritizes OpenAI check over Ollama
- **Enhanced**: Better error messages for OpenAI authentication/rate limit issues

### 6. Docker Compose (`docker-compose.yml`)

- **Added**: `OPENAI_API_KEY` environment variable support
- **Updated**: Made `OLLAMA_BASE_URL` optional

## Setup Instructions

### Step 1: Get OpenAI API Key

1. Sign up at [OpenAI Platform](https://platform.openai.com/)
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key (starts with `sk-`)

### Step 2: Set Environment Variable

**For Local Development:**
```bash
# Add to .env file
OPENAI_API_KEY=sk-your-api-key-here
```

**For Railway/Production:**
1. Go to Railway dashboard
2. Select your backend service
3. Go to Variables tab
4. Add new variable:
   - Key: `OPENAI_API_KEY`
   - Value: `sk-your-api-key-here`
5. Redeploy the service

### Step 3: Verify Configuration

After setting the API key, check the logs for:
```
[LLM_INIT] Using provider: OpenAI
[LLM_INIT] LLM instance created successfully for model 'gpt-4o-mini' using OpenAI
```

### Step 4: Test Content Generation

1. Start the application
2. Log in to the dashboard
3. Try generating blog content
4. Verify it completes successfully

## Benefits

1. **Reliability**: No dependency on local Ollama instance
2. **Performance**: Faster response times
3. **Quality**: Better content quality than small Ollama models
4. **Scalability**: No local resource constraints
5. **Cost-Effective**: gpt-4o-mini is very affordable (~$0.15/$0.60 per 1M tokens)

## Cost Estimation

- **Input**: ~$0.15 per 1M tokens
- **Output**: ~$0.60 per 1M tokens
- **Typical Blog Post**: 
  - Input: ~500-1000 tokens
  - Output: ~2000-3000 tokens
  - **Cost per post**: ~$0.002-0.003

## Rollback Plan

If you need to rollback to Ollama:

1. Remove `OPENAI_API_KEY` from environment variables
2. Set `OLLAMA_BASE_URL` to your Ollama instance
3. Revert `tiers.yaml` to Ollama models:
   ```yaml
   model: "ollama/llama3.2:1b"  # etc.
   ```
4. Restart services

## Troubleshooting

### Issue: "Either OPENAI_API_KEY or OLLAMA_BASE_URL must be set"

**Solution**: Set `OPENAI_API_KEY` environment variable

### Issue: "OpenAI API authentication failed"

**Solution**: 
- Verify API key is correct
- Check API key starts with `sk-`
- Ensure API key has sufficient credits

### Issue: "OpenAI API rate limit reached"

**Solution**:
- Wait for rate limit to reset
- Consider upgrading OpenAI plan
- Implement request throttling

### Issue: Content generation still using Ollama

**Solution**:
- Verify `OPENAI_API_KEY` is set correctly
- Check logs for `[LLM_INIT] Using provider: OpenAI`
- Restart the backend service

## Monitoring

### Key Log Patterns

**Successful OpenAI Initialization:**
```
[LLM_INIT] Using provider: OpenAI
[LLM_INIT] OpenAI API key configured (length: 51)
[LLM_INIT] LLM Configuration: model=gpt-4o-mini, temperature=0.2, max_tokens=1500, timeout=180.0s, provider=OpenAI
[LLM_INIT] LLM instance created successfully for model 'gpt-4o-mini' using OpenAI
```

**Health Check:**
```
OpenAI API accessible
provider: openai
gpt_models_available: X
```

## Next Steps

1. **Monitor Costs**: Track OpenAI API usage in OpenAI dashboard
2. **Set Usage Limits**: Configure spending limits in OpenAI dashboard
3. **Optimize Prompts**: Review and optimize prompts to reduce token usage
4. **Consider Tiered Models**: Use `gpt-4o` for enterprise tier if needed

## Support

For issues or questions:
- Check OpenAI API status: https://status.openai.com/
- Review OpenAI documentation: https://platform.openai.com/docs
- Check application logs for detailed error messages
