# Web File Structure and Docker Image Review

**Date:** 2026-01-23  
**Project:** Content Creation Crew - Frontend Service  
**Status:** ✅ Structure Reviewed | ⚠️ Module Resolution Issue Identified

---

## 📁 File Structure Overview

### ✅ Core Application Structure

```
web-ui/
├── app/                          # Next.js App Router pages
│   ├── api/                      # API routes
│   │   ├── contact/
│   │   ├── devtools-config/
│   │   └── generate/
│   ├── auth/                     # Authentication pages
│   │   ├── callback/
│   │   └── page.tsx
│   ├── billing/                  # Billing page
│   ├── cookies/                  # Cookie policy
│   ├── docs/                     # Documentation
│   ├── documentation/            # Additional docs
│   ├── offline/                  # Offline fallback (PWA)
│   ├── pricing/                 # Pricing page
│   ├── privacy/                  # Privacy policy
│   ├── terms/                   # Terms of service
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Home page
│   └── globals.css              # Global styles
├── components/                   # React components
│   ├── AboutModal.tsx
│   ├── AudioPanel.tsx
│   ├── AuthForm.tsx
│   ├── ContactForm.tsx
│   ├── ContactModal.tsx
│   ├── DevToolsSuppress.tsx
│   ├── FeaturesDropdown.tsx
│   ├── Footer.tsx
│   ├── InputPanel.tsx
│   ├── Navbar.tsx
│   ├── OutputPanel.tsx
│   ├── SocialMediaPanel.tsx
│   └── VideoPanel.tsx
├── contexts/                     # React contexts
│   └── AuthContext.tsx
├── lib/                          # Utility libraries
│   ├── api.ts                   # API client functions
│   └── env.ts                   # Environment configuration ⚠️ CRITICAL
├── models/                       # Data models
│   └── piper/                   # Piper TTS models
├── public/                       # Static assets
│   ├── favicon.svg
│   ├── icon.svg
│   ├── manifest.json            # PWA manifest
│   └── mockServiceWorker.js     # MSW for testing
├── scripts/                      # Build scripts
│   └── generate-icons.js
├── storage/                      # File storage (local dev)
│   └── voiceovers/
├── types/                        # TypeScript type definitions
│   └── global.d.ts
└── [config files]               # See Configuration Files section
```

### ✅ Configuration Files

| File | Status | Purpose |
|------|--------|---------|
| `package.json` | ✅ Correct | Dependencies and scripts |
| `package-lock.json` | ✅ Present | Locked dependency versions |
| `tsconfig.json` | ✅ Configured | TypeScript configuration with path aliases |
| `next.config.js` | ✅ Configured | Next.js config with PWA and webpack aliases |
| `tailwind.config.js` | ✅ Present | Tailwind CSS configuration |
| `postcss.config.js` | ✅ Present | PostCSS configuration |
| `railway.json` | ✅ Present | Railway deployment configuration |
| `.dockerignore` | ✅ Present | Docker build exclusions |
| `.gitignore` | ✅ Present | Git exclusions |
| `Dockerfile` | ✅ Present | Multi-stage Docker build |

---

## 🐳 Docker Configuration Review

### ✅ Dockerfile Analysis

**Location:** `web-ui/Dockerfile`

**Structure:** Multi-stage build (optimized for production)

#### Stage 1: Builder
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps
COPY . .
ENV DOCKER_BUILD=true
ENV CI=true
ENV NODE_ENV=production
RUN npm run build
```

**✅ Strengths:**
- Uses Alpine Linux (smaller image size)
- Copies package files first (better layer caching)
- Sets `DOCKER_BUILD=true` to skip strict env validation
- Uses `--legacy-peer-deps` to handle peer dependency conflicts

**⚠️ Considerations:**
- `npm ci` may fail with peer dependency conflicts → fallback to `npm install` ✅
- Build-time environment variables are set correctly ✅

#### Stage 2: Runner
```dockerfile
FROM node:20-alpine AS runner
WORKDIR /app
RUN apk add --no-cache wget
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/next.config.js ./next.config.js
COPY --from=builder /app/tsconfig.json ./tsconfig.json
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3000}/ || exit 1
CMD [startup script with fallbacks]
```

**✅ Strengths:**
- Copies standalone build (smaller, optimized)
- Includes `next.config.js` and `tsconfig.json` for module resolution ✅
- Health check configured with proper start period
- Fallback startup logic (standalone → npm start)
- Uses Railway's `PORT` environment variable

**⚠️ Considerations:**
- Copies `node_modules` as fallback (increases image size, but necessary for fallback) ✅
- Health check uses `wget` (installed in runner stage) ✅

### ✅ .dockerignore Analysis

**Location:** `web-ui/.dockerignore`

**✅ Properly Excludes:**
- `node_modules/` (will be installed in builder)
- `.next/` (will be built fresh)
- `.env*.local` (sensitive files)
- `*.md` (documentation, except README.md)
- Test files
- IDE files
- Git files

**✅ Correctly Includes:**
- Source code (`app/`, `components/`, `lib/`, etc.)
- Configuration files (`package.json`, `tsconfig.json`, `next.config.js`)
- Public assets (`public/`)

---

## ⚙️ Configuration Files Review

### ✅ package.json

**Dependencies:**
- ✅ `next@^14.2.35` - Next.js framework
- ✅ `react@^18.3.0` - React library
- ✅ `react-dom@^18.3.0` - React DOM
- ✅ `next-pwa@^5.6.0` - PWA support
- ✅ `js-cookie@^3.0.5` - Cookie management
- ✅ `nodemailer@^7.0.11` - Email functionality

**Scripts:**
- ✅ `dev` - Development server
- ✅ `build` - Production build
- ✅ `start` - Production server
- ✅ `lint` - Linting

**Status:** ✅ All dependencies are appropriate and up-to-date

### ✅ tsconfig.json

**Configuration:**
```json
{
  "compilerOptions": {
    "baseUrl": ".",                    // ✅ Set correctly
    "moduleResolution": "node",         // ✅ Correct for Next.js 14
    "paths": {
      "@/*": ["./*"],                  // ✅ Base alias
      "@/lib/*": ["./lib/*"],          // ✅ Explicit lib alias
      "@/contexts/*": ["./contexts/*"], // ✅ Explicit contexts alias
      "@/components/*": ["./components/*"] // ✅ Explicit components alias
    }
  }
}
```

**Status:** ✅ Path aliases are correctly configured

### ✅ next.config.js

**Key Features:**
1. ✅ PWA plugin configured with proper caching strategies
2. ✅ Standalone output enabled (`output: 'standalone'`)
3. ✅ Webpack alias configuration for `@` paths
4. ✅ Environment validation (skips during Docker builds)
5. ✅ Module resolution configured to prioritize project root
6. ✅ TypeScript extensions ordered correctly
7. ✅ Webpack config preserved after PWA plugin processing

**Status:** ✅ Configuration is comprehensive and correct

### ✅ railway.json

**Configuration:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Status:** ✅ Correctly configured for Railway deployment

---

## ⚠️ Identified Issues

### 🔴 Critical Issue: Module Resolution

**Problem:** `Module not found: Can't resolve '@/lib/env'` during Docker build

**Affected Files:**
- `web-ui/app/auth/callback/page.tsx`
- `web-ui/app/auth/page.tsx`
- `web-ui/app/billing/page.tsx`
- `web-ui/app/pricing/page.tsx`
- `web-ui/contexts/AuthContext.tsx`
- `web-ui/app/api/generate/route.ts`

**Root Cause Analysis:**
1. ✅ `lib/env.ts` exists at correct location
2. ✅ `tsconfig.json` has correct path aliases
3. ✅ `next.config.js` has webpack alias configuration
4. ⚠️ **Issue:** Webpack may not be resolving aliases correctly during Docker build, despite configuration

**Possible Causes:**
- Webpack alias resolution order in Docker environment
- Next.js standalone build may not preserve webpack config correctly
- PWA plugin may interfere with webpack alias resolution
- Module resolution cache issues

**Current Mitigations:**
- ✅ Explicit aliases for `@/lib`, `@/lib/env`, `@/contexts`, `@/components`
- ✅ Module resolution includes project root first
- ✅ TypeScript extensions ordered correctly
- ✅ Webpack config re-applied after PWA plugin

**Recommended Next Steps:**
1. Verify `lib/env.ts` is copied to Docker image (check Dockerfile COPY commands)
2. Test webpack alias resolution in Docker build locally
3. Consider using relative imports as temporary workaround
4. Check Next.js standalone build output for module resolution issues

---

## ✅ Strengths

1. **Multi-stage Docker Build:** Optimized for production with minimal image size
2. **Standalone Output:** Next.js standalone mode reduces dependencies
3. **Health Checks:** Proper health check configuration for Railway
4. **Environment Handling:** Docker build detection prevents strict validation during builds
5. **Fallback Logic:** Startup script has multiple fallback options
6. **PWA Support:** Properly configured with appropriate caching strategies
7. **Path Aliases:** Comprehensive TypeScript and webpack alias configuration
8. **Railway Integration:** Properly configured for Railway deployment

---

## 📋 Recommendations

### High Priority

1. **Fix Module Resolution Issue:**
   - Verify `lib/env.ts` is accessible in Docker build context
   - Test webpack alias resolution in Docker build
   - Consider adding explicit file extension in imports: `@/lib/env.ts` instead of `@/lib/env`

2. **Verify Docker Build:**
   - Test Docker build locally: `docker build -t web-ui-test ./web-ui`
   - Check if module resolution works in local Docker build
   - Compare local build vs Railway build logs

### Medium Priority

1. **Optimize Docker Image Size:**
   - Consider removing `node_modules` copy if standalone build works reliably
   - Use multi-stage build more aggressively (only copy necessary files)

2. **Add Build Verification:**
   - Add build-time checks to verify module resolution
   - Add logging to webpack config to debug alias resolution

### Low Priority

1. **Documentation:**
   - Add Docker build instructions to README
   - Document environment variable requirements
   - Add troubleshooting guide for module resolution issues

---

## 🔍 File Verification Checklist

- [x] `lib/env.ts` exists
- [x] `lib/api.ts` exists
- [x] `tsconfig.json` has correct path aliases
- [x] `next.config.js` has webpack alias configuration
- [x] `Dockerfile` copies necessary files
- [x] `.dockerignore` excludes unnecessary files
- [x] `railway.json` is correctly configured
- [x] All imports use `@/lib/env` path alias
- [ ] Module resolution works in Docker build (⚠️ Needs verification)

---

## 📊 Summary

**Overall Status:** ✅ Structure is well-organized and Docker configuration is correct

**Critical Issue:** ⚠️ Module resolution during Docker build needs investigation

**Recommendation:** Test Docker build locally and verify module resolution. If issue persists, consider:
1. Using explicit file extensions in imports
2. Adding debug logging to webpack config
3. Verifying file paths in Docker build context

**Next Steps:**
1. Test Docker build locally
2. Verify `lib/env.ts` is accessible in Docker image
3. Check webpack alias resolution in build logs
4. Consider alternative import strategies if needed

---

**Review Completed:** 2026-01-23  
**Reviewed By:** AI Assistant  
**Status:** ⚠️ Requires Docker Build Testing
