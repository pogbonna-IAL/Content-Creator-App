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

# Ensure lib/env.ts and lib/api-client.ts exist - handle both build contexts
# First try to copy from web-ui/lib if we're building from root
# Then create missing files if needed
RUN mkdir -p ./lib && \
    if [ -d "web-ui" ] && [ -d "web-ui/lib" ]; then \
      cp -r web-ui/lib/* ./lib/ 2>/dev/null || true && \
      echo "✓ lib files copied from web-ui/lib/"; \
    fi && \
    if [ -f "lib/env.ts" ] && [ -f "lib/api-client.ts" ]; then \
      echo "✓ lib/env.ts and lib/api-client.ts exist"; \
    elif [ -f "lib/env.ts" ]; then \
      echo "⚠ lib/env.ts exists but lib/api-client.ts is missing - will create"; \
    elif [ -f "lib/api-client.ts" ]; then \
      echo "⚠ lib/api-client.ts exists but lib/env.ts is missing - will create"; \
    fi && \
    if [ ! -f "lib/env.ts" ]; then \
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
      echo "let apiUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// Normalize: trim whitespace and handle empty strings" >> ./lib/env.ts && \
      echo "if (apiUrl) {" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl.trim()" >> ./lib/env.ts && \
      echo "  // Remove trailing slashes" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl.replace(/\/+$/, '')" >> ./lib/env.ts && \
      echo "  // Handle case where API_URL is just '/' or empty after normalization" >> ./lib/env.ts && \
      echo "  if (apiUrl === '' || apiUrl === '/') {" >> ./lib/env.ts && \
      echo "    apiUrl = undefined" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// During Docker builds or build time, allow localhost/default (will be set at runtime)" >> ./lib/env.ts && \
      echo "if (isDockerBuild || isBuildTime) {" >> ./lib/env.ts && \
      echo "  // Use provided URL or default to localhost for Docker builds or during build" >> ./lib/env.ts && \
      echo "  apiUrl = apiUrl || \"http://localhost:8000\"" >> ./lib/env.ts && \
      echo "} else {" >> ./lib/env.ts && \
      echo "  // Runtime: In production, if API_URL is not set, use relative URLs (same origin)" >> ./lib/env.ts && \
      echo "  // This works when frontend and backend are on the same domain (e.g., Railway)" >> ./lib/env.ts && \
      echo "  if (isProduction && !apiUrl) {" >> ./lib/env.ts && \
      echo "    // Use empty string to signal getApiUrl() to use relative URLs" >> ./lib/env.ts && \
      echo "    apiUrl = ''" >> ./lib/env.ts && \
      echo "  } else if (!apiUrl) {" >> ./lib/env.ts && \
      echo "    // In development, default to localhost if not set" >> ./lib/env.ts && \
      echo "    apiUrl = \"http://localhost:8000\"" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// Final fallback: ensure API_URL is never undefined (but can be empty string for relative URLs)" >> ./lib/env.ts && \
      echo "if (apiUrl === undefined) {" >> ./lib/env.ts && \
      echo "  apiUrl = 'http://localhost:8000'" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "" >> ./lib/env.ts && \
      echo "// Log API URL for debugging (always log to help diagnose production issues)" >> ./lib/env.ts && \
      echo "if (typeof window !== 'undefined') {" >> ./lib/env.ts && \
      echo "  console.log('[env] API_URL:', apiUrl || '(empty/undefined)')" >> ./lib/env.ts && \
      echo "  console.log('[env] NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL || '(not set)')" >> ./lib/env.ts && \
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
      echo "  " >> ./lib/env.ts && \
      echo "  // Handle edge cases where API_URL might be empty, undefined, or just '/'" >> ./lib/env.ts && \
      echo "  if (!API_URL || API_URL.trim() === '' || API_URL === '/') {" >> ./lib/env.ts && \
      echo "    // Use relative URL (will use same origin as the frontend)" >> ./lib/env.ts && \
      echo "    // This works when frontend and backend are on the same domain" >> ./lib/env.ts && \
      echo "    const relativeUrl = \`/\${cleanPath}\`" >> ./lib/env.ts && \
      echo "    if (typeof window !== 'undefined') {" >> ./lib/env.ts && \
      echo "      console.log(\`[getApiUrl] API_URL is empty, using relative URL: \${relativeUrl}\`)" >> ./lib/env.ts && \
      echo "    }" >> ./lib/env.ts && \
      echo "    return relativeUrl" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "  " >> ./lib/env.ts && \
      echo "  // Normalize API_URL: trim and remove trailing slashes" >> ./lib/env.ts && \
      echo "  const normalizedApiUrl = API_URL.trim().replace(/\/+$/, '')" >> ./lib/env.ts && \
      echo "  " >> ./lib/env.ts && \
      echo "  // Construct URL ensuring no double slashes" >> ./lib/env.ts && \
      echo "  const fullUrl = \`\${normalizedApiUrl}/\${cleanPath}\`" >> ./lib/env.ts && \
      echo "  " >> ./lib/env.ts && \
      echo "  if (typeof window !== 'undefined') {" >> ./lib/env.ts && \
      echo "    console.log(\`[getApiUrl] Constructed URL: \${fullUrl} (from API_URL: \${normalizedApiUrl})\`)" >> ./lib/env.ts && \
      echo "  }" >> ./lib/env.ts && \
      echo "  " >> ./lib/env.ts && \
      echo "  return fullUrl" >> ./lib/env.ts && \
      echo "}" >> ./lib/env.ts && \
      echo "✓ lib/env.ts created"; \
    fi && \
    if [ -f "lib/api-client.ts" ]; then \
      echo "✓ lib/api-client.ts exists"; \
    else \
      echo "/**" > ./lib/api-client.ts && \
      echo " * API client helper with automatic Authorization header injection" >> ./lib/api-client.ts && \
      echo " * This handles cross-subdomain authentication by using Authorization headers" >> ./lib/api-client.ts && \
      echo " * instead of relying solely on cookies." >> ./lib/api-client.ts && \
      echo " */" >> ./lib/api-client.ts && \
      echo "" >> ./lib/api-client.ts && \
      echo "import { getApiUrl } from './env'" >> ./lib/api-client.ts && \
      echo "" >> ./lib/api-client.ts && \
      echo "/**" >> ./lib/api-client.ts && \
      echo " * Get the auth token from localStorage" >> ./lib/api-client.ts && \
      echo " */" >> ./lib/api-client.ts && \
      echo "export function getAuthToken(): string | null {" >> ./lib/api-client.ts && \
      echo "  if (typeof window === 'undefined') return null" >> ./lib/api-client.ts && \
      echo "  return localStorage.getItem('auth_token')" >> ./lib/api-client.ts && \
      echo "}" >> ./lib/api-client.ts && \
      echo "" >> ./lib/api-client.ts && \
      echo "/**" >> ./lib/api-client.ts && \
      echo " * Create fetch options with Authorization header if token is available" >> ./lib/api-client.ts && \
      echo " */" >> ./lib/api-client.ts && \
      echo "export function createAuthHeaders(additionalHeaders: HeadersInit = {}): HeadersInit {" >> ./lib/api-client.ts && \
      echo "  const token = getAuthToken()" >> ./lib/api-client.ts && \
      echo "  const headers: Record<string, string> = {}" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  // Convert additionalHeaders to a plain object if it's a Headers object" >> ./lib/api-client.ts && \
      echo "  if (additionalHeaders instanceof Headers) {" >> ./lib/api-client.ts && \
      echo "    additionalHeaders.forEach((value, key) => {" >> ./lib/api-client.ts && \
      echo "      headers[key] = value" >> ./lib/api-client.ts && \
      echo "    })" >> ./lib/api-client.ts && \
      echo "  } else if (Array.isArray(additionalHeaders)) {" >> ./lib/api-client.ts && \
      echo "    // Handle array of [key, value] pairs" >> ./lib/api-client.ts && \
      echo "    additionalHeaders.forEach(([key, value]) => {" >> ./lib/api-client.ts && \
      echo "      headers[key] = value" >> ./lib/api-client.ts && \
      echo "    })" >> ./lib/api-client.ts && \
      echo "  } else if (additionalHeaders) {" >> ./lib/api-client.ts && \
      echo "    // Handle plain object" >> ./lib/api-client.ts && \
      echo "    Object.assign(headers, additionalHeaders)" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  if (token) {" >> ./lib/api-client.ts && \
      echo "    headers['Authorization'] = \`Bearer \${token}\`" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  return headers" >> ./lib/api-client.ts && \
      echo "}" >> ./lib/api-client.ts && \
      echo "" >> ./lib/api-client.ts && \
      echo "/**" >> ./lib/api-client.ts && \
      echo " * Fetch wrapper that automatically adds Authorization header" >> ./lib/api-client.ts && \
      echo " */" >> ./lib/api-client.ts && \
      echo "export async function authFetch(" >> ./lib/api-client.ts && \
      echo "  url: string," >> ./lib/api-client.ts && \
      echo "  options: RequestInit = {}" >> ./lib/api-client.ts && \
      echo "): Promise<Response> {" >> ./lib/api-client.ts && \
      echo "  const headers = createAuthHeaders(options.headers)" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  // Log request details for debugging" >> ./lib/api-client.ts && \
      echo "  if (typeof window !== 'undefined') {" >> ./lib/api-client.ts && \
      echo "    const authHeader = (headers as Record<string, string>)['Authorization']" >> ./lib/api-client.ts && \
      echo "    console.log('[authFetch] Making request:', {" >> ./lib/api-client.ts && \
      echo "      url," >> ./lib/api-client.ts && \
      echo "      method: options.method || 'GET'," >> ./lib/api-client.ts && \
      echo "      hasAuth: !!authHeader," >> ./lib/api-client.ts && \
      echo "      credentials: 'include'," >> ./lib/api-client.ts && \
      echo "    })" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  try {" >> ./lib/api-client.ts && \
      echo "    const response = await fetch(url, {" >> ./lib/api-client.ts && \
      echo "      ...options," >> ./lib/api-client.ts && \
      echo "      headers," >> ./lib/api-client.ts && \
      echo "      credentials: 'include', // Still include cookies as fallback" >> ./lib/api-client.ts && \
      echo "    })" >> ./lib/api-client.ts && \
      echo "    " >> ./lib/api-client.ts && \
      echo "    if (typeof window !== 'undefined') {" >> ./lib/api-client.ts && \
      echo "      console.log('[authFetch] Response:', {" >> ./lib/api-client.ts && \
      echo "        url," >> ./lib/api-client.ts && \
      echo "        status: response.status," >> ./lib/api-client.ts && \
      echo "        statusText: response.statusText," >> ./lib/api-client.ts && \
      echo "        ok: response.ok," >> ./lib/api-client.ts && \
      echo "      })" >> ./lib/api-client.ts && \
      echo "    }" >> ./lib/api-client.ts && \
      echo "    " >> ./lib/api-client.ts && \
      echo "    return response" >> ./lib/api-client.ts && \
      echo "  } catch (error) {" >> ./lib/api-client.ts && \
      echo "    // Enhanced error logging" >> ./lib/api-client.ts && \
      echo "    if (typeof window !== 'undefined') {" >> ./lib/api-client.ts && \
      echo "      console.error('[authFetch] Fetch failed:', {" >> ./lib/api-client.ts && \
      echo "        url," >> ./lib/api-client.ts && \
      echo "        error: error instanceof Error ? error.message : String(error)," >> ./lib/api-client.ts && \
      echo "        errorType: error instanceof TypeError ? 'TypeError' : 'Unknown'," >> ./lib/api-client.ts && \
      echo "        isNetworkError: error instanceof TypeError && error.message.includes('fetch')," >> ./lib/api-client.ts && \
      echo "      })" >> ./lib/api-client.ts && \
      echo "    }" >> ./lib/api-client.ts && \
      echo "    " >> ./lib/api-client.ts && \
      echo "    // Re-throw with more context" >> ./lib/api-client.ts && \
      echo "    throw new Error(" >> ./lib/api-client.ts && \
      echo "      \`Failed to fetch \${url}: \${error instanceof Error ? error.message : String(error)}\`" >> ./lib/api-client.ts && \
      echo "    )" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "}" >> ./lib/api-client.ts && \
      echo "" >> ./lib/api-client.ts && \
      echo "/**" >> ./lib/api-client.ts && \
      echo " * Helper to make authenticated API calls" >> ./lib/api-client.ts && \
      echo " */" >> ./lib/api-client.ts && \
      echo "export async function apiCall(" >> ./lib/api-client.ts && \
      echo "  endpoint: string," >> ./lib/api-client.ts && \
      echo "  options: RequestInit = {}" >> ./lib/api-client.ts && \
      echo "): Promise<Response> {" >> ./lib/api-client.ts && \
      echo "  const url = getApiUrl(endpoint)" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  // Validate URL before making request" >> ./lib/api-client.ts && \
      echo "  if (!url || url.trim() === '') {" >> ./lib/api-client.ts && \
      echo "    throw new Error(\`Invalid API URL constructed from endpoint: \${endpoint}\`)" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  // Validate URL format" >> ./lib/api-client.ts && \
      echo "  let isValidUrl = false" >> ./lib/api-client.ts && \
      echo "  if (url.startsWith('http://') || url.startsWith('https://')) {" >> ./lib/api-client.ts && \
      echo "    try {" >> ./lib/api-client.ts && \
      echo "      new URL(url)" >> ./lib/api-client.ts && \
      echo "      isValidUrl = true" >> ./lib/api-client.ts && \
      echo "    } catch {" >> ./lib/api-client.ts && \
      echo "      // Invalid absolute URL" >> ./lib/api-client.ts && \
      echo "      console.error('[apiCall] Invalid absolute URL:', url)" >> ./lib/api-client.ts && \
      echo "      throw new Error(\`Invalid API URL: \${url}\`)" >> ./lib/api-client.ts && \
      echo "    }" >> ./lib/api-client.ts && \
      echo "  } else if (url.startsWith('/')) {" >> ./lib/api-client.ts && \
      echo "    // Relative URL is valid" >> ./lib/api-client.ts && \
      echo "    isValidUrl = true" >> ./lib/api-client.ts && \
      echo "  } else {" >> ./lib/api-client.ts && \
      echo "    console.warn('[apiCall] URL format might be invalid:', url)" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  // Log the full URL being called" >> ./lib/api-client.ts && \
      echo "  if (typeof window !== 'undefined') {" >> ./lib/api-client.ts && \
      echo "    console.log('[apiCall] Calling endpoint:', {" >> ./lib/api-client.ts && \
      echo "      endpoint," >> ./lib/api-client.ts && \
      echo "      fullUrl: url," >> ./lib/api-client.ts && \
      echo "      isValidUrl," >> ./lib/api-client.ts && \
      echo "    })" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "  " >> ./lib/api-client.ts && \
      echo "  try {" >> ./lib/api-client.ts && \
      echo "    return await authFetch(url, options)" >> ./lib/api-client.ts && \
      echo "  } catch (error) {" >> ./lib/api-client.ts && \
      echo "    // Provide more helpful error messages" >> ./lib/api-client.ts && \
      echo "    const errorMessage = error instanceof Error ? error.message : String(error)" >> ./lib/api-client.ts && \
      echo "    " >> ./lib/api-client.ts && \
      echo "    // Check if it's a network/CORS error" >> ./lib/api-client.ts && \
      echo "    if (errorMessage.includes('Failed to fetch') || error instanceof TypeError) {" >> ./lib/api-client.ts && \
      echo "      const apiUrl = typeof window !== 'undefined' " >> ./lib/api-client.ts && \
      echo "        ? (window as any).__API_URL__ || 'http://localhost:8000'" >> ./lib/api-client.ts && \
      echo "        : 'http://localhost:8000'" >> ./lib/api-client.ts && \
      echo "      " >> ./lib/api-client.ts && \
      echo "      const helpfulMessage = \`Network error: Cannot connect to API at \${url}. \` +" >> ./lib/api-client.ts && \
      echo "        \`Please ensure:\\n\` +" >> ./lib/api-client.ts && \
      echo "        \`1. The API server is running at \${apiUrl}\\n\` +" >> ./lib/api-client.ts && \
      echo "        \`2. CORS is properly configured on the API server\\n\` +" >> ./lib/api-client.ts && \
      echo "        \`3. The API URL is correct (check NEXT_PUBLIC_API_URL environment variable)\`" >> ./lib/api-client.ts && \
      echo "      " >> ./lib/api-client.ts && \
      echo "      console.error('[apiCall]', helpfulMessage)" >> ./lib/api-client.ts && \
      echo "      " >> ./lib/api-client.ts && \
      echo "      // Create a more informative error" >> ./lib/api-client.ts && \
      echo "      const enhancedError = new Error(helpfulMessage)" >> ./lib/api-client.ts && \
      echo "      ;(enhancedError as any).originalError = error" >> ./lib/api-client.ts && \
      echo "      ;(enhancedError as any).url = url" >> ./lib/api-client.ts && \
      echo "      ;(enhancedError as any).endpoint = endpoint" >> ./lib/api-client.ts && \
      echo "      throw enhancedError" >> ./lib/api-client.ts && \
      echo "    }" >> ./lib/api-client.ts && \
      echo "    " >> ./lib/api-client.ts && \
      echo "    // Re-throw other errors as-is" >> ./lib/api-client.ts && \
      echo "    throw error" >> ./lib/api-client.ts && \
      echo "  }" >> ./lib/api-client.ts && \
      echo "}" >> ./lib/api-client.ts && \
      echo "✓ lib/api-client.ts created"; \
    fi && \
    test -f lib/env.ts || (echo "ERROR: lib/env.ts still missing!" && exit 1) && \
    test -f lib/api-client.ts || (echo "ERROR: lib/api-client.ts still missing!" && exit 1)

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
