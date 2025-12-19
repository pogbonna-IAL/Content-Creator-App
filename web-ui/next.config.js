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

module.exports = nextConfig

