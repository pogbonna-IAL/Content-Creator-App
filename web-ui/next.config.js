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
    // Configure path aliases for webpack (matches tsconfig.json)
    // CRITICAL: Explicitly set @ alias to ensure @/lib/env resolves during Docker build
    // Next.js should auto-detect from tsconfig.json, but explicitly set for reliability
    const projectRoot = path.resolve(__dirname)
    
    // CRITICAL: Ensure @ alias is set to project root
    // This must be done before any other alias processing
    // Use Object.assign to ensure the alias is set even if Next.js/PWA plugin modifies it
    config.resolve = config.resolve || {}
    config.resolve.alias = Object.assign({}, config.resolve.alias || {}, {
      '@': projectRoot,
    })
    
    // Ensure proper module resolution - project root must be first
    if (!config.resolve.modules) {
      config.resolve.modules = []
    }
    // Remove projectRoot if it exists, then add it first
    config.resolve.modules = config.resolve.modules.filter(m => m !== projectRoot)
    config.resolve.modules.unshift(projectRoot)
    // Ensure node_modules is at the end
    if (!config.resolve.modules.includes('node_modules')) {
      config.resolve.modules.push('node_modules')
    }
    
    // Ensure extensions include TypeScript (order matters - check .ts before .js)
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else {
      // Ensure TypeScript extensions are present and in correct order
      const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
      extensions.forEach(ext => {
        if (!config.resolve.extensions.includes(ext)) {
          config.resolve.extensions.push(ext)
        }
      })
      // Reorder to ensure .ts comes before .js
      const ordered = ['.tsx', '.ts', '.jsx', '.js', '.json']
      config.resolve.extensions = [
        ...ordered.filter(ext => config.resolve.extensions.includes(ext)),
        ...config.resolve.extensions.filter(ext => !ordered.includes(ext))
      ]
    }
    
    // Debug logging (always log in Docker builds to help diagnose)
    const isDockerBuild = process.env.DOCKER_BUILD === 'true' || process.env.CI === 'true'
    if (dev || isDockerBuild) {
      console.log('Webpack resolve config:')
      console.log('  Project root:', projectRoot)
      console.log('  @ alias:', config.resolve.alias['@'])
      console.log('  Modules:', config.resolve.modules.slice(0, 3), '...')
      console.log('  Extensions:', config.resolve.extensions.slice(0, 5), '...')
    }
    
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

// Store original webpack function before PWA plugin wraps it
const originalWebpack = nextConfig.webpack

// Apply PWA plugin
const configWithPWA = withPWA(nextConfig)

// Store PWA's webpack function (if it modified it)
const pwaWebpack = configWithPWA.webpack

// CRITICAL: Re-apply webpack config after PWA plugin to ensure @ alias is set
// The PWA plugin might modify or wrap the webpack config, so we need to ensure
// our path alias configuration is applied correctly
configWithPWA.webpack = (config, options) => {
  const projectRoot = path.resolve(__dirname)
  
  // CRITICAL: Ensure @ alias is set to project root FIRST
  // This must happen before any other webpack processing
  if (!config.resolve) {
    config.resolve = {}
  }
  if (!config.resolve.alias) {
    config.resolve.alias = {}
  }
  
  // Force set @ alias - this is the key fix
  config.resolve.alias['@'] = projectRoot
  
  // Ensure proper module resolution - project root must be first
  if (!config.resolve.modules) {
    config.resolve.modules = []
  }
  // Remove projectRoot if it exists, then add it first
  config.resolve.modules = config.resolve.modules.filter(m => m !== projectRoot && typeof m === 'string')
  config.resolve.modules.unshift(projectRoot)
  // Ensure node_modules is at the end
  if (!config.resolve.modules.includes('node_modules')) {
    config.resolve.modules.push('node_modules')
  }
  
  // Ensure TypeScript extensions are included
  if (!config.resolve.extensions) {
    config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
  } else {
    // Ensure .ts and .tsx are present and before .js
    const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    extensions.forEach(ext => {
      if (!config.resolve.extensions.includes(ext)) {
        config.resolve.extensions.push(ext)
      }
    })
  }
  
  // Debug logging for Docker builds
  const isDockerBuild = process.env.DOCKER_BUILD === 'true' || process.env.CI === 'true'
  if (isDockerBuild || options.dev) {
    console.log('[Webpack Config] Project root:', projectRoot)
    console.log('[Webpack Config] @ alias:', config.resolve.alias['@'])
    console.log('[Webpack Config] Modules (first 3):', config.resolve.modules.slice(0, 3))
  }
  
  // Apply PWA's webpack config first (if it exists and is different from ours)
  if (pwaWebpack && pwaWebpack !== configWithPWA.webpack) {
    config = pwaWebpack(config, options) || config
    // Re-apply our alias after PWA (in case PWA modified it)
    config.resolve.alias['@'] = projectRoot
  }
  
  // Apply original webpack config if it exists (from nextConfig)
  if (originalWebpack) {
    config = originalWebpack(config, options) || config
    // Re-apply our alias after original (in case it modified it)
    config.resolve.alias['@'] = projectRoot
  }
  
  return config
}

module.exports = configWithPWA

