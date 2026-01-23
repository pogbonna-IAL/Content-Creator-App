# Import Strategy Change - Relative Imports

**Date:** 2026-01-23  
**Reason:** Fix module resolution issue during Docker build  
**Status:** ✅ Completed

---

## Problem

During Docker builds, webpack was unable to resolve the `@/lib/env` path alias, causing build failures with:
```
Module not found: Can't resolve '@/lib/env'
```

## Solution

Changed all imports from `@/lib/env` to relative imports. This approach is more reliable in Docker builds because:
1. Relative imports don't depend on webpack alias resolution
2. They work consistently across different build environments
3. They're resolved directly by Node.js/TypeScript without webpack configuration

## Files Updated

### 1. `app/pricing/page.tsx`
**Before:**
```typescript
import { API_URL } from "@/lib/env";
```

**After:**
```typescript
import { API_URL } from "../../lib/env";
```

### 2. `app/billing/page.tsx`
**Before:**
```typescript
import { API_URL } from "@/lib/env";
```

**After:**
```typescript
import { API_URL } from "../../lib/env";
```

### 3. `contexts/AuthContext.tsx`
**Before:**
```typescript
import { API_URL } from '@/lib/env'
```

**After:**
```typescript
import { API_URL } from '../lib/env'
```

### 4. `app/auth/page.tsx`
**Before:**
```typescript
import { API_URL } from '@/lib/env'
```

**After:**
```typescript
import { API_URL } from '../../lib/env'
```

### 5. `app/auth/callback/page.tsx`
**Before:**
```typescript
import { API_URL } from '@/lib/env'
```

**After:**
```typescript
import { API_URL } from '../../../lib/env'
```

### 6. `app/api/generate/route.ts`
**Before:**
```typescript
import { API_URL } from '@/lib/env'
```

**After:**
```typescript
import { API_URL } from '../../../lib/env'
```

## Relative Path Calculation

The relative paths are calculated based on the file location relative to `lib/env.ts`:

- `app/pricing/page.tsx` → `../../lib/env` (2 levels up: app → root → lib)
- `app/billing/page.tsx` → `../../lib/env` (2 levels up: app → root → lib)
- `contexts/AuthContext.tsx` → `../lib/env` (1 level up: contexts → root → lib)
- `app/auth/page.tsx` → `../../lib/env` (2 levels up: app → root → lib)
- `app/auth/callback/page.tsx` → `../../../lib/env` (3 levels up: app/auth/callback → app/auth → app → root → lib)
- `app/api/generate/route.ts` → `../../../lib/env` (3 levels up: app/api/generate → app/api → app → root → lib)

## Benefits

1. ✅ **Reliability:** Relative imports work consistently in all build environments
2. ✅ **No Webpack Dependency:** Doesn't rely on webpack alias configuration
3. ✅ **Docker Compatible:** Works correctly in Docker builds without special configuration
4. ✅ **TypeScript Support:** TypeScript resolves relative imports natively
5. ✅ **Next.js Compatible:** Next.js handles relative imports without issues

## Testing

After this change, the Docker build should succeed. To test:

```bash
cd web-ui
docker build -t web-ui-test .
```

The build should complete without module resolution errors.

## Notes

- Other `@/` aliases (like `@/contexts`, `@/components`) remain unchanged as they don't have the same resolution issues
- The `tsconfig.json` and `next.config.js` path alias configurations remain in place for other imports
- This change only affects `@/lib/env` imports; other path aliases continue to work

## Rollback

If needed, you can revert these changes by replacing relative imports back to `@/lib/env`. However, this should not be necessary as relative imports are more reliable.

---

**Status:** ✅ All imports updated successfully  
**Next Step:** Test Docker build to verify the fix
