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
COPY . .

# Set environment variable for build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js application
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
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Copy package.json for npm start fallback
COPY --from=builder /app/package.json ./package.json

# Copy node_modules for npm start fallback (if standalone doesn't work)
# Only copy production dependencies to keep image size small
COPY --from=builder /app/node_modules ./node_modules

# Expose port
EXPOSE 3000

# Health check (uses PORT env var with fallback)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3000} || exit 1

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
