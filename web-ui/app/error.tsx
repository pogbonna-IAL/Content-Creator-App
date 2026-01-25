'use client'

// Next.js 15: Force dynamic rendering for error pages
export const dynamic = 'force-dynamic'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gradient mb-4">500</h1>
        <p className="text-xl text-gray-300 mb-4">Something went wrong!</p>
        <p className="text-gray-400 mb-8">{error.message}</p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={reset}
            className="px-6 py-3 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-cyan/50 transition-all"
          >
            Try again
          </button>
          <a
            href="/"
            className="px-6 py-3 border-2 border-neon-cyan rounded-lg font-semibold hover:bg-neon-cyan/10 transition-all"
          >
            Go Home
          </a>
        </div>
      </div>
    </div>
  )
}
