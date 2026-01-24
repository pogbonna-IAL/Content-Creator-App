# Frontend Dockerfile for Content Creation Crew
# Multi-stage build for optimal image size

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install ALL dependencies (including devDependencies needed for build)
# Use --legacy-peer-deps to handle peer dependency conflicts
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps

# Copy source code
# CRITICAL: Railway's buildContext: "." means it builds from web-ui/ directory
# So we copy directly from web-ui/ subdirectories (not web-ui/web-ui/)
# However, Railway may build from repo root, so we handle both cases with RUN commands
COPY . .

# Handle both build contexts: if building from repo root, move web-ui/ contents to root
# #region agent log
RUN echo "=== Build Context Detection ===" && \
    if [ -d "web-ui" ] && [ -f "web-ui/lib/env.ts" ]; then \
      echo "Building from repo root - moving web-ui/ contents to root" && \
      cp -r web-ui/lib/* ./lib/ 2>/dev/null || true && \
      cp -r web-ui/app/* ./app/ 2>/dev/null || true && \
      cp -r web-ui/contexts/* ./contexts/ 2>/dev/null || true && \
      cp -r web-ui/public/* ./public/ 2>/dev/null || true && \
      cp -r web-ui/components/* ./components/ 2>/dev/null || true && \
      echo "✓ Files moved from web-ui/ to root"; \
    elif [ -f "lib/env.ts" ]; then \
      echo "Building from web-ui/ directory - files already in root"; \
    else \
      echo "✗ ERROR: lib/env.ts not found!" && \
      find /app -name "env.ts" -type f 2>/dev/null | head -10 && \
      exit 1; \
    fi && \
    echo "Verifying lib/env.ts exists:" && \
    (test -f lib/env.ts && echo "✓ lib/env.ts verified!" || (echo "✗ lib/env.ts missing!" && exit 1)) && \
    echo "=== End Build Context Detection ==="
# #endregion

# Diagnostic: Check what was actually copied
# #region agent log
RUN echo "=== Build Context Diagnostic ===" && \
    echo "Current directory:" && pwd && \
    echo "Contents of /app:" && ls -la /app/ | head -30 && \
    echo "" && \
    echo "Checking for web-ui/ directory:" && \
    (test -d "web-ui" && echo "✓ web-ui/ exists" || echo "✗ web-ui/ does NOT exist") && \
    echo "" && \
    echo "Checking for web-ui/lib/ directory:" && \
    (test -d "web-ui/lib" && echo "✓ web-ui/lib/ exists" || echo "✗ web-ui/lib/ does NOT exist") && \
    echo "" && \
    echo "Checking for web-ui/lib/env.ts:" && \
    (test -f "web-ui/lib/env.ts" && echo "✓ web-ui/lib/env.ts found!" || echo "✗ web-ui/lib/env.ts NOT found!") && \
    echo "" && \
    echo "Contents of web-ui/lib/ (if exists):" && \
    (ls -la web-ui/lib/ 2>/dev/null || echo "web-ui/lib/ does not exist") && \
    echo "" && \
    echo "Checking for lib/env.ts:" && \
    (test -f "lib/env.ts" && echo "✓ lib/env.ts found!" || echo "✗ lib/env.ts NOT found!") && \
    echo "" && \
    echo "Searching for all env.ts files:" && \
    find /app -name "env.ts" -type f 2>/dev/null | head -10 && \
    echo "=== End Build Context Diagnostic ==="
# #endregion

# If building from repo root, copy web-ui/lib/ to lib/
# #region agent log
RUN echo "=== Copying lib/env.ts ===" && \
    if [ -f "web-ui/lib/env.ts" ]; then \
      echo "Found web-ui/lib/env.ts - copying to lib/" && \
      mkdir -p ./lib && \
      cp -r web-ui/lib/* ./lib/ && \
      echo "✓ lib/env.ts copied from web-ui/lib/" && \
      ls -la lib/; \
    elif [ -f "lib/env.ts" ]; then \
      echo "✓ lib/env.ts already exists in root"; \
    else \
      echo "✗ ERROR: lib/env.ts not found in either location!" && \
      echo "This means web-ui/lib/ was excluded by .dockerignore" && \
      exit 1; \
    fi && \
    echo "Verifying lib/env.ts exists:" && \
    (test -f lib/env.ts && echo "✓ lib/env.ts verified!" || (echo "✗ lib/env.ts still missing!" && exit 1)) && \
    echo "=== End Copying lib/env.ts ==="
# #endregion

# Verify critical files exist (this will fail the build if lib/env.ts is missing)
RUN test -f lib/env.ts || \
    (echo "ERROR: lib/env.ts not found in build context!" && \
     echo "Build context should be web-ui/ directory" && \
     echo "Current directory:" && pwd && \
     echo "Contents of /app:" && ls -la /app/ | head -20 && \
     echo "Searching for env.ts files:" && \
     find /app -name "env.ts" -type f 2>/dev/null && \
     exit 1)

# Set environment variables for build
# CRITICAL: Set DOCKER_BUILD=true to skip strict validation during Docker builds
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV DOCKER_BUILD=true
ENV CI=true
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js application
# This will create .next/standalone and .next/static directories
RUN npm run build

# Stage 2: Production
FROM node:20-alpine AS runner

WORKDIR /app

# Install wget for health checks
RUN apk add --no-cache wget

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Set environment variable
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy necessary files from builder
# For standalone output
COPY --from=builder /app/public ./public

# Copy standalone build (preferred method)
# Next.js standalone includes server.js and necessary dependencies
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# CRITICAL: Copy next.config.js and tsconfig.json for standalone build
# These are needed for proper module resolution and configuration
COPY --from=builder /app/next.config.js ./next.config.js
COPY --from=builder /app/tsconfig.json ./tsconfig.json

# Copy package.json for npm start fallback
COPY --from=builder /app/package.json ./package.json

# Copy node_modules ONLY for npm start fallback (if standalone doesn't work)
# Note: Next.js standalone includes necessary node_modules in .next/standalone/node_modules
# This copy is only used if the standalone server fails and we fall back to npm start
COPY --from=builder /app/node_modules ./node_modules

# Expose port
EXPOSE 3000

# Health check (uses PORT env var with fallback)
# Check the root endpoint to ensure Next.js is serving correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3000}/ || exit 1

# Start Next.js standalone server if available, otherwise use npm start
# Use Railway's PORT environment variable if available
# Next.js standalone creates server.js in the standalone directory
CMD if [ -f "./server.js" ]; then \
      echo "✓ Starting Next.js standalone server (./server.js)..." && \
      PORT=${PORT:-3000} HOSTNAME=0.0.0.0 node ./server.js; \
    elif [ -f "server.js" ]; then \
      echo "✓ Starting Next.js standalone server (server.js)..." && \
      PORT=${PORT:-3000} HOSTNAME=0.0.0.0 node server.js; \
    elif [ -d "./.next" ] && [ -f "./package.json" ]; then \
      echo "✓ Using npm start fallback..." && \
      PORT=${PORT:-3000} HOSTNAME=0.0.0.0 npm start; \
    else \
      echo "✗ Error: Cannot start server - missing files!" && \
      echo "Contents of /app:" && ls -la && \
      echo "Looking for server.js or .next directory..." && \
      find . -name "server.js" -o -name ".next" 2>/dev/null | head -10 && \
      exit 1; \
    fi
