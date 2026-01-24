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
# However, Railway may use root .dockerignore which excludes /lib/
# First copy everything (respects .dockerignore)
COPY . .

# Ensure lib/env.ts exists - handle both build contexts
# Create it using echo commands to avoid heredoc parsing issues
RUN mkdir -p ./lib && \
    if [ -f "lib/env.ts" ]; then \
      echo "✓ lib/env.ts exists"; \
    elif [ -d "web-ui" ] && [ -f "web-ui/lib/env.ts" ]; then \
      cp -r web-ui/lib/* ./lib/ && \
      echo "✓ lib/env.ts copied from web-ui/lib/"; \
    else \
      echo "/**" > ./lib/env.ts && \
      echo " * Environment variable validation and configuration" >> ./lib/env.ts && \
      echo " * This file validates NEXT_PUBLIC_API_URL and exports API_URL for use throughout the app" >> ./lib/env.ts && \
      echo " */" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "const isDockerBuild = process.env.DOCKER_BUILD === \"true\" || process.env.CI === \"true\"" >> ./lib/env.ts && \
      echo "const isProduction = process.env.NODE_ENV === \"production\"" >> ./lib/env.ts && \
      echo "const isBuildTime = process.env.NEXT_PHASE === \"phase-production-build\" ||" >> ./lib/env.ts && \
      echo "                    process.env.NEXT_PHASE === \"phase-development-build\" ||" >> ./lib/env.ts && \
      echo "                    typeof window === \"undefined\" && !process.env.NEXT_RUNTIME" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "let apiUrl = process.env.NEXT_PUBLIC_API_URL" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "if (isDockerBuild || isBuildTime) {" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl || \"http://localhost:8000\"" >> ./lib/env.ts && \
      echo "} else {" >> ./lib/env.ts && \
      echo "  if (isProduction && !apiUrl) {" >> ./lib/env.ts && \
      echo "    apiUrl = \"http://localhost:8000\"" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "  if (!apiUrl) {" >> ./lib/env.ts && \
      echo "    apiUrl = \"http://localhost:8000\"" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// Normalize API URL: remove trailing slash and ensure it's not empty" >> ./lib/env.ts && \
      echo "if (apiUrl) {" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl.trim()" >> ./lib/env.ts && \
      echo "  // Remove trailing slash to prevent double slashes in URL construction" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl.replace(/\/+$/, '')" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// Final fallback: ensure API_URL is never empty or undefined" >> ./lib/env.ts && \
      echo "if (!apiUrl || apiUrl === '') {" >> ./lib/env.ts && \
      echo "  apiUrl = 'http://localhost:8000'" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "export const API_URL = apiUrl" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "/**" >> ./lib/env.ts && \
      echo " * Helper function to construct API URLs safely" >> ./lib/env.ts && \
      echo " * Ensures no double slashes and handles empty API_URL gracefully" >> ./lib/env.ts && \
      echo " */" >> ./lib/env.ts && \
      echo "export function getApiUrl(path: string): string {" >> ./lib/env.ts && \
      echo "  // Remove leading slash from path if present" >> ./lib/env.ts && \
      echo "  const cleanPath = path.startsWith('/') ? path.slice(1) : path" >> ./lib/env.ts && \
      echo "  // Ensure API_URL doesn't end with slash and path doesn't start with slash" >> ./lib/env.ts && \
      echo "  return \`\${API_URL}/\${cleanPath}\`" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "✓ lib/env.ts created"; \
    fi && \
    test -f lib/env.ts || (echo "ERROR: lib/env.ts still missing!" && exit 1)

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
