'use client'

import { useEffect, useState } from 'react'

// Next.js 15: Force dynamic rendering for error pages
export const dynamic = 'force-dynamic'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const [mounted, setMounted] = useState(false)
  
  // Prevent hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true)
  }, [])
  
  // Get error message safely
  const errorMessage = error?.message || error?.toString() || 'An unexpected error occurred'
  
  // Show loading state during hydration to prevent mismatch
  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg">
      <div className="text-center px-4">
        <h1 className="text-6xl font-bold text-gradient mb-4">500</h1>
        <p className="text-xl text-gray-300 mb-4">Something went wrong!</p>
        <p className="text-gray-400 mb-8 break-words max-w-2xl mx-auto">
          {errorMessage}
        </p>
        {error?.digest && (
          <p className="text-xs text-gray-500 mb-4">
            Error ID: {error.digest}
          </p>
        )}
        <div className="flex gap-4 justify-center flex-wrap">
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
