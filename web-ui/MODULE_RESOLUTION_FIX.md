# Module Resolution Fix for @/lib/env

## Current Configuration

### ✅ tsconfig.json
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### ✅ next.config.js
- Webpack alias `@` → project root
- Explicit aliases: `@/lib`, `@/lib/env`, `@/contexts`, `@/components`
- Module resolution includes project root first
- TypeScript extensions configured

### ✅ Dockerfile
- Copies `next.config.js` ✅
- Copies `tsconfig.json` ✅
- Sets `DOCKER_BUILD=true` ✅

## Issue

Despite all configuration, webpack still can't resolve `@/lib/env` during Docker build.

## Potential Root Cause

Next.js 14 uses SWC compiler which processes TypeScript files before webpack. The SWC compiler might not be reading the `tsconfig.json` paths correctly in the Docker build environment.

## Solution Options

### Option 1: Use Relative Imports (Temporary Workaround)

If the alias resolution continues to fail, we can temporarily use relative imports:

```typescript
// Instead of: import { API_URL } from '@/lib/env'
// Use: import { API_URL } from '../../lib/env'
```

**Files to update:**
- `app/auth/callback/page.tsx`
- `app/auth/page.tsx`
- `app/billing/page.tsx`
- `app/pricing/page.tsx`
- `contexts/AuthContext.tsx`
- `app/api/generate/route.ts`

### Option 2: Verify tsconfig.json is Being Read

Add a test to verify Next.js is reading tsconfig.json:
- Check build logs for TypeScript compilation messages
- Verify `baseUrl` and `paths` are being applied

### Option 3: Check PWA Plugin Interference

The `next-pwa` plugin might be interfering with path resolution. Consider:
- Temporarily disabling PWA to test if it's the cause
- Updating `next-pwa` to latest version
- Checking if PWA plugin has known issues with path aliases

## Current Status

✅ All webpack aliases configured
✅ tsconfig.json paths configured correctly
✅ Dockerfile copies necessary config files
❌ Module resolution still failing

## Next Steps

1. Check Railway build logs for webpack debug output
2. Verify which aliases are being set
3. If aliases are set but still failing, consider Option 1 (relative imports) as temporary workaround
4. Investigate if PWA plugin is the root cause
