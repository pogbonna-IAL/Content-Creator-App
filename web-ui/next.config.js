const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    // Network-first strategy for API routes (never cache)
    {
      urlPattern: /^https?:\/\/.*\/api\/.*/,
      handler: 'NetworkOnly',
      options: {
        cacheName: 'api-cache',
        networkTimeoutSeconds: 10,
      },
    },
    // Network-first strategy for auth routes (never cache)
    {
      urlPattern: /^https?:\/\/.*\/auth\/.*/,
      handler: 'NetworkOnly',
      options: {
        cacheName: 'auth-cache',
        networkTimeoutSeconds: 10,
      },
    },
    // Cache static assets
    {
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico|woff|woff2|ttf|eot)$/,
      handler: 'CacheFirst',
      options: {
        cacheName: 'static-assets',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
        },
      },
    },
    // Network-first for pages (with fallback)
    {
      urlPattern: /^https?:\/\/.*/,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'pages-cache',
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 24 * 60 * 60, // 24 hours
        },
        networkTimeoutSeconds: 10,
      },
    },
  ],
  // Exclude auth and API routes from precaching
  publicExcludes: ['!**/auth/**', '!**/api/**'],
  buildExcludes: [/middleware-manifest\.json$/],
  // Don't precache auth callbacks and private API responses
  exclude: [
    /\/auth\/callback/,
    /\/api\/generate/,
    /\/api\/auth/,
    /\/api\/.*/,
  ],
  fallbacks: {
    document: '/offline',
  },
})

/**
 * Validate required environment variables at build time
 * This runs before the build starts
 */
function validateBuildEnv() {
  const env = process.env.NODE_ENV || 'development'
  const isProd = env === 'production'
  
  // Check required environment variables
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  
  if (isProd && !apiUrl) {
    console.error('❌ Build failed: NEXT_PUBLIC_API_URL is required in production')
    console.error('   Set it as an environment variable:')
    console.error('   NEXT_PUBLIC_API_URL=https://api.yourdomain.com npm run build')
    process.exit(1)
  }
  
  if (isProd && apiUrl && !apiUrl.startsWith('https://')) {
    console.error('❌ Build failed: NEXT_PUBLIC_API_URL must use HTTPS in production')
    console.error(`   Current value: ${apiUrl}`)
    process.exit(1)
  }
  
  if (isProd && apiUrl && (apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1'))) {
    console.error('❌ Build failed: NEXT_PUBLIC_API_URL cannot point to localhost in production')
    console.error(`   Current value: ${apiUrl}`)
    process.exit(1)
  }
}

// Validate environment before build
validateBuildEnv()

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Enable standalone output for Docker
  output: 'standalone',
  // Suppress React DevTools hook warnings
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Suppress installhook.js errors in development
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      }
    }
    return config
  },
  // Disable React DevTools hook warnings
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Ignore mockServiceWorker.js 404 errors and Chrome DevTools requests
  async rewrites() {
    return [
      {
        source: '/mockServiceWorker.js',
        destination: '/mockServiceWorker.js',
      },
      {
        source: '/.well-known/appspecific/com.chrome.devtools.json',
        destination: '/api/devtools-config',
      },
    ]
  },
  // Increase API route timeout for long-running requests
  experimental: {
    // Increase timeout for API routes (30 minutes)
    serverComponentsExternalPackages: [],
  },
}

module.exports = withPWA(nextConfig)

