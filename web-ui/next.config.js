const path = require('path')

const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  runtimeCaching: [
    // Network-only strategy for API routes (never cache, no timeout needed)
    {
      urlPattern: /^https?:\/\/.*\/api\/.*/,
      handler: 'NetworkOnly',
      options: {
        cacheName: 'api-cache',
      },
    },
    // Network-only strategy for auth routes (never cache, no timeout needed)
    {
      urlPattern: /^https?:\/\/.*\/auth\/.*/,
      handler: 'NetworkOnly',
      options: {
        cacheName: 'auth-cache',
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
  const isDockerBuild = process.env.DOCKER_BUILD === 'true' || process.env.CI === 'true'
  
  // Check required environment variables
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  
  if (isProd && !apiUrl) {
    console.error('❌ Build failed: NEXT_PUBLIC_API_URL is required in production')
    console.error('   Set it as an environment variable:')
    console.error('   NEXT_PUBLIC_API_URL=https://api.yourdomain.com npm run build')
    process.exit(1)
  }
  
  // Skip strict validation during Docker builds (API URL can be set at runtime)
  if (isDockerBuild) {
    console.log('ℹ️  Docker build detected - allowing localhost/default API URL (will be set at runtime)')
    return
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
  webpack: (config, { dev, isServer, webpack }) => {
    const projectRoot = path.resolve(__dirname)
    
    // CRITICAL: Set alias directly - this is the primary method
    // Next.js should read from tsconfig.json, but we ensure it's set
    config.resolve = config.resolve || {}
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@': projectRoot,
    }
    
    // Ensure module resolution includes project root
    config.resolve.modules = config.resolve.modules || []
    if (!config.resolve.modules.includes(projectRoot)) {
      config.resolve.modules.unshift(projectRoot)
    }
    
    // Ensure TypeScript extensions are included and in correct order
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else {
      // Ensure .ts and .tsx come before .js
      const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
      extensions.forEach(ext => {
        if (!config.resolve.extensions.includes(ext)) {
          config.resolve.extensions.push(ext)
        }
      })
    }
    
    // Debug logging
    console.log('='.repeat(60))
    console.log('[WEBPACK CONFIG] Applied!')
    console.log('[WEBPACK CONFIG] Project root:', projectRoot)
    console.log('[WEBPACK CONFIG] @ alias:', config.resolve.alias['@'])
    console.log('[WEBPACK CONFIG] Extensions:', config.resolve.extensions.slice(0, 5))
    console.log('[WEBPACK CONFIG] Modules:', config.resolve.modules.slice(0, 3))
    console.log('='.repeat(60))
    
    if (dev && !isServer) {
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

// Apply PWA plugin - it should preserve our webpack config
const configWithPWA = withPWA(nextConfig)

// CRITICAL: Ensure webpack config is preserved after PWA plugin
// The webpack config in nextConfig should already have the @ alias set
// But we'll override it again after PWA to ensure it's not modified
if (configWithPWA.webpack) {
  const pwaWebpack = configWithPWA.webpack
  configWithPWA.webpack = (config, options) => {
    // First apply PWA's webpack config
    const result = pwaWebpack(config, options) || config
    
    const projectRoot = path.resolve(__dirname)
    
    // CRITICAL: Ensure @ alias is set (preserve existing aliases)
    const existingAliases = result.resolve?.alias || {}
    
    result.resolve = result.resolve || {}
    result.resolve.alias = {
      ...existingAliases,
      '@': projectRoot,
    }
    
    // Ensure module resolution includes project root
    result.resolve.modules = result.resolve.modules || []
    if (!result.resolve.modules.includes(projectRoot)) {
      result.resolve.modules.unshift(projectRoot)
    }
    
    // Ensure TypeScript extensions are included
    if (!result.resolve.extensions) {
      result.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else {
      const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
      extensions.forEach(ext => {
        if (!result.resolve.extensions.includes(ext)) {
          result.resolve.extensions.push(ext)
        }
      })
    }
    
    console.log('[WEBPACK AFTER PWA] @ alias:', result.resolve.alias['@'])
    console.log('[WEBPACK AFTER PWA] Extensions:', result.resolve.extensions.slice(0, 5))
    
    return result
  }
} else {
  // If PWA removed webpack config, add it back
  configWithPWA.webpack = (config, options) => {
    const projectRoot = path.resolve(__dirname)
    
    config.resolve = config.resolve || {}
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@': projectRoot,
    }
    
    config.resolve.modules = config.resolve.modules || []
    if (!config.resolve.modules.includes(projectRoot)) {
      config.resolve.modules.unshift(projectRoot)
    }
    
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    }
    
    return config
  }
}

module.exports = configWithPWA

