'use client'

// Next.js 15: Force dynamic rendering for error pages
export const dynamic = 'force-dynamic'

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gradient mb-4">404</h1>
        <p className="text-xl text-gray-300 mb-8">Page not found</p>
        <a
          href="/"
          className="px-6 py-3 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-cyan/50 transition-all"
        >
          Go Home
        </a>
      </div>
    </div>
  )
}
