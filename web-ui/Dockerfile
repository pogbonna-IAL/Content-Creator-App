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
# CRITICAL: Explicitly copy lib/ directory FIRST to ensure it's included
# The root .dockerignore excludes lib/, so we must copy it explicitly
COPY lib/ ./lib/
COPY app/ ./app/
COPY contexts/ ./contexts/
COPY public/ ./public/
# Copy optional directories if they exist
COPY components/ ./components/ 2>/dev/null || mkdir -p ./components
# Copy all config and source files
COPY *.json ./
COPY *.js ./
COPY *.ts ./
COPY *.config.* ./

# Diagnostic: List build context to understand what files are available
# #region agent log
RUN echo "=== Build Context Diagnostic ===" && \
    echo "Current directory:" && pwd && \
    echo "Contents of root:" && ls -la /app/ | head -30 && \
    echo "" && \
    echo "Directories in root:" && find /app -maxdepth 1 -type d | head -20 && \
    echo "" && \
    echo "Looking for lib/env.ts:" && (test -f lib/env.ts && echo "✓ lib/env.ts found!" || echo "✗ lib/env.ts NOT found!") && \
    echo "Contents of lib/ directory:" && (ls -la lib/ 2>/dev/null || echo "lib/ directory does not exist!") && \
    echo "" && \
    echo "Checking for web-ui/lib/env.ts (if building from repo root):" && (test -f web-ui/lib/env.ts && echo "✓ web-ui/lib/env.ts found!" || echo "✗ web-ui/lib/env.ts NOT found!") && \
    echo "Contents of web-ui/lib/ directory:" && (ls -la web-ui/lib/ 2>/dev/null || echo "web-ui/lib/ directory does not exist!") && \
    echo "" && \
    echo "Searching for env.ts files:" && find /app -name "env.ts" -type f 2>/dev/null | head -10 && \
    echo "=== End Diagnostic ==="
# #endregion

# Verify critical files exist (this will fail the build if lib/env.ts is missing)
# Try both possible locations (if building from web-ui/ or from repo root)
RUN (test -f lib/env.ts || test -f web-ui/lib/env.ts) || \
    (echo "ERROR: lib/env.ts not found in build context!" && \
     echo "Searched locations: /app/lib/env.ts, /app/web-ui/lib/env.ts" && \
     ls -la lib/ 2>/dev/null || echo "lib/ directory does not exist!" && \
     ls -la web-ui/lib/ 2>/dev/null || echo "web-ui/lib/ directory does not exist!" && \
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
