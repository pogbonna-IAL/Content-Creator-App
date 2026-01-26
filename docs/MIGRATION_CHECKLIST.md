# GPT-4o-mini Migration Checklist

## Pre-Migration

- [x] Code changes implemented
- [x] Configuration updated
- [x] Documentation updated
- [ ] OpenAI API key obtained
- [ ] API key added to environment variables

## Migration Steps

### 1. Get OpenAI API Key
- [ ] Sign up at https://platform.openai.com/
- [ ] Navigate to API Keys section
- [ ] Create new API key
- [ ] Copy key (starts with `sk-`)

### 2. Set Environment Variable

**For Railway:**
- [ ] Go to Railway dashboard
- [ ] Select backend service
- [ ] Go to Variables tab
- [ ] Add `OPENAI_API_KEY` = `sk-your-key-here`
- [ ] Save and redeploy

**For Local Development:**
- [ ] Add to `.env` file: `OPENAI_API_KEY=sk-your-key-here`
- [ ] Restart backend service

### 3. Verify Configuration

- [ ] Check logs for: `[LLM_INIT] Using provider: OpenAI`
- [ ] Visit `/health` endpoint
- [ ] Verify LLM status shows "OpenAI API accessible"

### 4. Test Content Generation

- [ ] Test blog content generation
- [ ] Test social media content generation
- [ ] Verify both complete successfully
- [ ] Check content quality meets expectations

### 5. Monitor

- [ ] Check OpenAI dashboard for API usage
- [ ] Set spending limits in OpenAI dashboard
- [ ] Monitor costs per generation
- [ ] Review logs for any errors

## Rollback Plan (if needed)

If issues occur:
- [ ] Remove `OPENAI_API_KEY` from environment
- [ ] Set `OLLAMA_BASE_URL` to Ollama instance
- [ ] Revert `tiers.yaml` to Ollama models
- [ ] Restart services

## Post-Migration

- [ ] Update team documentation
- [ ] Notify users of improved reliability
- [ ] Monitor costs and usage
- [ ] Optimize prompts if needed
