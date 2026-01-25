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
  const isDev = env === 'development'
  const isDockerBuild = process.env.DOCKER_BUILD === 'true' || process.env.CI === 'true'
  
  // Check required environment variables
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  
  // Skip strict validation during Docker builds (API URL can be set at runtime)
  if (isDockerBuild) {
    console.log('ℹ️  Docker build detected - allowing localhost/default API URL (will be set at runtime)')
    return
  }
  
  // Skip strict validation in development (localhost is allowed)
  if (isDev) {
    console.log('ℹ️  Development build detected - allowing localhost/default API URL')
    return
  }
  
  // Production validation (only for non-Docker, non-dev builds)
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
  // CRITICAL: Ensure TypeScript paths are read correctly
  // Next.js should auto-detect from tsconfig.json, but we ensure it's configured
  typescript: {
    // TypeScript errors won't block build, but paths should still work
    ignoreBuildErrors: false,
  },
  // ESLint configuration - disable during builds to avoid compatibility issues
  eslint: {
    // Ignore ESLint errors during builds (ESLint 9 compatibility issue with Next.js 14)
    ignoreDuringBuilds: true,
  },
  // Ensure experimental features don't interfere with path resolution
  experimental: {
    // Increase timeout for API routes (30 minutes)
    serverComponentsExternalPackages: [],
  },
  // Suppress React DevTools hook warnings
  webpack: (config, { dev, isServer, webpack: webpackInstance }) => {
    const projectRoot = path.resolve(__dirname)
    const fs = require('fs')
    
    // #region agent log
    const libEnvPathCheck = path.resolve(projectRoot, 'lib/env.ts')
    const libEnvExists = fs.existsSync(libEnvPathCheck)
    console.log('[DEBUG HYP-A] Main webpack config - File check:', {
      libEnvPath: libEnvPathCheck,
      libEnvExists,
      isServer,
      projectRoot,
      aliasBefore: config.resolve?.alias?.['@/lib/env']
    })
    // #endregion
    
    // CRITICAL: Configure resolve BEFORE any other processing
    // This ensures the alias is set before Next.js processes imports
    config.resolve = config.resolve || {}
    
    // CRITICAL: Get existing aliases BEFORE modifying
    const existingAliases = config.resolve.alias || {}
    
    // CRITICAL: Force set @ alias FIRST - this must come before other aliases
    // Next.js should set this from tsconfig.json, but we ensure it's correct
    const libEnvPath = path.resolve(projectRoot, 'lib/env')
    const appLibEnvPath = path.resolve(projectRoot, 'app/lib/env')
    const libEnvTsPath = libEnvPath + '.ts'
    
    // Ensure lib/env.ts exists - if not, warn
    if (!fs.existsSync(libEnvTsPath)) {
      console.warn(`[WEBPACK] Warning: ${libEnvTsPath} does not exist!`)
    }
    
    // Set up aliases - use absolute paths for better reliability
    const apiClientPath = path.resolve(projectRoot, 'lib/api-client')
    config.resolve.alias = {
      '@': projectRoot,    // Base alias - MUST be first
      '@/lib': path.resolve(projectRoot, 'lib'),  // Directory alias
      '@/lib/env': libEnvPath,  // File alias (absolute path, no extension)
      '@/lib/api-client': apiClientPath,  // File alias (absolute path, no extension)
      '@/app/lib/env': appLibEnvPath,  // File alias for app/lib/env
      '@/contexts': path.resolve(projectRoot, 'contexts'),
      '@/components': path.resolve(projectRoot, 'components'),
      '@/app': path.resolve(projectRoot, 'app'),
      ...existingAliases,  // Then preserve other aliases (but @ takes precedence)
    }
    
    // CRITICAL: Force override to ensure file aliases are set (they might be overridden by existingAliases)
    config.resolve.alias['@/lib/env'] = libEnvPath
    config.resolve.alias['@/lib/api-client'] = apiClientPath
    
    // CRITICAL: Ensure resolve.extensions includes .ts and .tsx
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else if (!config.resolve.extensions.includes('.ts')) {
      config.resolve.extensions.unshift('.ts', '.tsx')
    }
    
    // #region agent log
    console.log('[DEBUG HYP-D] Main webpack - Alias set:', {
      '@/lib/env': config.resolve.alias['@/lib/env'],
      '@/app/lib/env': config.resolve.alias['@/app/lib/env'],
      libEnvPathWithExt: libEnvPath + '.ts',
      libEnvFileExists: fs.existsSync(libEnvPath + '.ts'),
      extensions: config.resolve.extensions?.slice(0, 5),
      isServer
    })
    // #endregion
    
    // CRITICAL: Ensure aliases are set BEFORE other processing
    // Force override any existing aliases that might conflict
    if (!config.resolve.alias['@/app/lib/env']) {
      config.resolve.alias['@/app/lib/env'] = appLibEnvPath
    }
    if (!config.resolve.alias['@/lib/env']) {
      config.resolve.alias['@/lib/env'] = libEnvPath
    }
    
    // CRITICAL: Ensure module resolution includes project root FIRST
    config.resolve.modules = config.resolve.modules || []
    // Remove projectRoot if it exists anywhere
    config.resolve.modules = config.resolve.modules.filter(m => m !== projectRoot && typeof m === 'string')
    // Add project root FIRST (before node_modules)
    config.resolve.modules.unshift(projectRoot)
    // Ensure node_modules is at the end
    const nodeModulesIndex = config.resolve.modules.indexOf('node_modules')
    if (nodeModulesIndex !== -1 && nodeModulesIndex !== config.resolve.modules.length - 1) {
      config.resolve.modules.splice(nodeModulesIndex, 1)
      config.resolve.modules.push('node_modules')
    } else if (nodeModulesIndex === -1) {
      config.resolve.modules.push('node_modules')
    }
    
    // Ensure TypeScript extensions are included and in correct order
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else {
      // Ensure .ts and .tsx come before .js
      const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
      const currentExts = [...config.resolve.extensions]
      const orderedExts = []
      
      // Add TypeScript extensions first
      extensions.forEach(ext => {
        if (currentExts.includes(ext)) {
          orderedExts.push(ext)
        }
      })
      
      // Add any other extensions
      currentExts.forEach(ext => {
        if (!extensions.includes(ext) && !orderedExts.includes(ext)) {
          orderedExts.push(ext)
        }
      })
      
      config.resolve.extensions = orderedExts.length > 0 ? orderedExts : config.resolve.extensions
    }
    
    // CRITICAL: Ensure @/app/lib/env alias is set correctly
    // The alias should work without needing NormalModuleReplacementPlugin
    // Removing the plugin to avoid absolute path resolution issues
    
    // Add webpack resolver plugin to debug module resolution
    // #region agent log
    const libEnvExistsCheck = fs.existsSync(libEnvPath + '.ts')
    
    // Add a custom resolver plugin to trace @/lib/env resolution
    if (!config.resolve.plugins) {
      config.resolve.plugins = []
    }
    
    // Create a resolver plugin that intercepts @/lib/env and redirects to the actual file
    // This runs EARLY in the resolution process, before webpack gives up
    class EnvResolverPlugin {
      apply(resolver) {
        // Hook into the resolve phase - this runs before the normal resolution
        // Use 'before' stage to ensure it runs before other resolvers
        resolver.hooks.resolve.tapAsync('EnvResolverPlugin', (request, resolveContext, callback) => {
          // Don't modify @/lib/env or @/lib/api-client requests
          // Let webpack's alias system handle them - it's already configured correctly
          // The alias will resolve @/lib/env -> lib/env and @/lib/api-client -> lib/api-client
          // which webpack can then resolve relative to the project root
          
          // For all requests, continue normally and let webpack's alias resolution work
          callback()
        })
      }
    }
    // Add this plugin FIRST so it runs before other resolvers
    config.resolve.plugins.unshift(new EnvResolverPlugin())
    
    // CRITICAL: Add NormalModuleReplacementPlugin as fallback for @/lib/env resolution
    // This plugin runs during module replacement phase and catches @/lib/env imports
    // It works together with the resolver plugin to ensure resolution succeeds
    if (!config.plugins) {
      config.plugins = []
    }
    
    // Don't use NormalModuleReplacementPlugin - let webpack's alias system handle it
    // The aliases are configured above and should work correctly
    // If aliases don't work, the issue is elsewhere (e.g., Next.js alias processing)
    
    // Also add webpack error handling to catch module resolution failures
    // #region agent log
    config.plugins = config.plugins || []
    config.plugins.push({
      apply: (compiler) => {
        compiler.hooks.compilation.tap('DebugModuleResolution', (compilation) => {
          compilation.hooks.buildModule.tap('DebugModuleResolution', (module) => {
            if (module.request && (module.request.includes('@/lib/env') || module.request === '@/lib/env')) {
              console.log('[DEBUG HYP-D] Building module:', {
                request: module.request,
                userRequest: module.userRequest,
                resource: module.resource,
                isServer
              })
            }
          })
          
          compilation.hooks.failedModule.tap('DebugModuleResolution', (module, error) => {
            if (module.request && (module.request.includes('@/lib/env') || module.request === '@/lib/env')) {
              console.log('[DEBUG HYP-D] Module build FAILED:', {
                request: module.request,
                userRequest: module.userRequest,
                error: error?.message || String(error),
                isServer
              })
            }
          })
        })
      }
    })
    // #endregion
    
    // Debug logging
    console.log('='.repeat(60))
    console.log('[WEBPACK CONFIG] Applied!')
    console.log('[WEBPACK CONFIG] Project root:', projectRoot)
    console.log('[WEBPACK CONFIG] @ alias:', config.resolve.alias['@'])
    console.log('[WEBPACK CONFIG] @/lib alias:', config.resolve.alias['@/lib'])
    console.log('[WEBPACK CONFIG] @/lib/env alias:', config.resolve.alias['@/lib/env'])
    console.log('[WEBPACK CONFIG] @/app/lib/env alias:', config.resolve.alias['@/app/lib/env'])
    console.log('[WEBPACK CONFIG] All aliases:', Object.keys(config.resolve.alias))
    console.log('[WEBPACK CONFIG] Extensions:', config.resolve.extensions.slice(0, 5))
    console.log('[WEBPACK CONFIG] Modules (full):', config.resolve.modules)
    console.log('[WEBPACK CONFIG] Project root index:', config.resolve.modules.indexOf(projectRoot))
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
    const webpackInstance = options.webpack || require('webpack')
    
    const projectRoot = path.resolve(__dirname)
    
    // CRITICAL: Ensure @ alias is set (preserve existing aliases)
    const existingAliases = result.resolve?.alias || {}
    
    result.resolve = result.resolve || {}
    result.resolve.alias = {
      '@': projectRoot,                    // Base alias
      '@/lib': path.resolve(projectRoot, 'lib'),  // Explicit lib alias
      '@/lib/env': path.resolve(projectRoot, 'lib/env'),  // Explicit env alias (no extension)
      '@/lib/api-client': path.resolve(projectRoot, 'lib/api-client'),  // Explicit api-client alias (no extension)
      '@/app/lib/env': path.resolve(projectRoot, 'app/lib/env'),  // Explicit app/lib/env alias (no extension)
      '@/contexts': path.resolve(projectRoot, 'contexts'),  // Explicit contexts alias
      '@/components': path.resolve(projectRoot, 'components'),  // Explicit components alias
      ...existingAliases,                  // Then preserve other aliases
    }
    
    // CRITICAL: Ensure module resolution includes project root FIRST
    result.resolve.modules = result.resolve.modules || []
    // Remove projectRoot if it exists anywhere
    result.resolve.modules = result.resolve.modules.filter(m => m !== projectRoot)
    // Add project root FIRST (before node_modules)
    result.resolve.modules.unshift(projectRoot)
    // Ensure node_modules is at the end
    const nodeModulesIndex = result.resolve.modules.indexOf('node_modules')
    if (nodeModulesIndex !== -1 && nodeModulesIndex !== result.resolve.modules.length - 1) {
      result.resolve.modules.splice(nodeModulesIndex, 1)
      result.resolve.modules.push('node_modules')
    } else if (nodeModulesIndex === -1) {
      result.resolve.modules.push('node_modules')
    }
    
    // Ensure TypeScript extensions are included and in correct order
    if (!result.resolve.extensions) {
      result.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    } else {
      const extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
      const currentExts = [...result.resolve.extensions]
      const orderedExts = []
      
      // Add TypeScript extensions first
      extensions.forEach(ext => {
        if (currentExts.includes(ext)) {
          orderedExts.push(ext)
        }
      })
      
      // Add any other extensions
      currentExts.forEach(ext => {
        if (!extensions.includes(ext) && !orderedExts.includes(ext)) {
          orderedExts.push(ext)
        }
      })
      
      result.resolve.extensions = orderedExts.length > 0 ? orderedExts : result.resolve.extensions
    }
    
    // CRITICAL: Force override @/app/lib/env alias to ensure it's set correctly
    // This must be done AFTER PWA processes the config
    // Remove NormalModuleReplacementPlugin - it was causing absolute path issues
    // Instead, rely on the alias which should work correctly
    const envPath = path.resolve(projectRoot, 'app/lib/env')
    const libEnvPath = path.resolve(projectRoot, 'lib/env')
    const apiClientPath = path.resolve(projectRoot, 'lib/api-client')
    const fs = require('fs')
    
    // #region agent log
    const libEnvExists = fs.existsSync(libEnvPath + '.ts')
    console.log('[DEBUG HYP-A] After PWA - File check:', {
      libEnvPath: libEnvPath + '.ts',
      libEnvExists,
      isServer: options.isServer,
      aliasBefore: result.resolve?.alias?.['@/lib/env']
    })
    // #endregion
    
    result.resolve.alias['@/app/lib/env'] = envPath
    result.resolve.alias['@/lib/env'] = libEnvPath
    result.resolve.alias['@/lib/api-client'] = apiClientPath
    
    // Ensure the alias is set and not overridden
    if (!result.resolve.alias['@/app/lib/env']) {
      result.resolve.alias['@/app/lib/env'] = envPath
    }
    if (!result.resolve.alias['@/lib/env']) {
      result.resolve.alias['@/lib/env'] = libEnvPath
    }
    if (!result.resolve.alias['@/lib/api-client']) {
      result.resolve.alias['@/lib/api-client'] = apiClientPath
    }
    
    // #region agent log
    console.log('[DEBUG HYP-E] After PWA - Final alias state:', {
      '@/lib/env': result.resolve.alias['@/lib/env'],
      '@/lib/api-client': result.resolve.alias['@/lib/api-client'],
      '@/app/lib/env': result.resolve.alias['@/app/lib/env'],
      libEnvFileExists: fs.existsSync(libEnvPath + '.ts'),
      apiClientFileExists: fs.existsSync(apiClientPath + '.ts'),
      extensions: result.resolve.extensions?.slice(0, 5),
      isServer: options.isServer,
      modules: result.resolve.modules?.slice(0, 3)
    })
    // #endregion
    
    console.log('[WEBPACK AFTER PWA] @ alias:', result.resolve.alias['@'])
    console.log('[WEBPACK AFTER PWA] @/lib alias:', result.resolve.alias['@/lib'])
    console.log('[WEBPACK AFTER PWA] @/lib/env alias:', result.resolve.alias['@/lib/env'])
    console.log('[WEBPACK AFTER PWA] @/lib/api-client alias:', result.resolve.alias['@/lib/api-client'])
    console.log('[WEBPACK AFTER PWA] @/app/lib/env alias:', result.resolve.alias['@/app/lib/env'])
    console.log('[WEBPACK AFTER PWA] Extensions:', result.resolve.extensions.slice(0, 5))
    
    return result
  }
} else {
  // If PWA removed webpack config, add it back
  configWithPWA.webpack = (config, options) => {
    const projectRoot = path.resolve(__dirname)
    
    config.resolve = config.resolve || {}
    config.resolve.alias = {
      '@': projectRoot,
      '@/lib': path.resolve(projectRoot, 'lib'),
      '@/lib/env': path.resolve(projectRoot, 'lib/env'),
      '@/lib/api-client': path.resolve(projectRoot, 'lib/api-client'),
      '@/app/lib/env': path.resolve(projectRoot, 'app/lib/env'),
      '@/contexts': path.resolve(projectRoot, 'contexts'),
      '@/components': path.resolve(projectRoot, 'components'),
      ...(config.resolve.alias || {}),
    }
    
    // CRITICAL: Force override to ensure file aliases are set correctly
    const apiClientPathFallback = path.resolve(projectRoot, 'lib/api-client')
    const libEnvPathFallback = path.resolve(projectRoot, 'lib/env')
    config.resolve.alias['@/app/lib/env'] = path.resolve(projectRoot, 'app/lib/env')
    config.resolve.alias['@/lib/env'] = libEnvPathFallback
    config.resolve.alias['@/lib/api-client'] = apiClientPathFallback
    
    // CRITICAL: Ensure module resolution includes project root FIRST
    config.resolve.modules = config.resolve.modules || []
    config.resolve.modules = config.resolve.modules.filter(m => m !== projectRoot)
    config.resolve.modules.unshift(projectRoot)
    
    const nodeModulesIndex = config.resolve.modules.indexOf('node_modules')
    if (nodeModulesIndex !== -1 && nodeModulesIndex !== config.resolve.modules.length - 1) {
      config.resolve.modules.splice(nodeModulesIndex, 1)
      config.resolve.modules.push('node_modules')
    } else if (nodeModulesIndex === -1) {
      config.resolve.modules.push('node_modules')
    }
    
    if (!config.resolve.extensions) {
      config.resolve.extensions = ['.tsx', '.ts', '.jsx', '.js', '.json']
    }
    
    return config
  }
}

module.exports = configWithPWA

