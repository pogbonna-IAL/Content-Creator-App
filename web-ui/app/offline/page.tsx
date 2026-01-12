'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OfflinePage() {
  const router = useRouter()
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    // Check online status
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    setIsOnline(navigator.onLine)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    // Auto-redirect when back online
    if (isOnline) {
      const timer = setTimeout(() => {
        router.push('/')
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [isOnline, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4">
      <div className="glass-effect neon-border rounded-2xl p-8 max-w-md w-full text-center">
        <div className="mb-6">
          <svg
            className="w-24 h-24 mx-auto text-neon-cyan/50"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
            />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-gradient mb-4">
          {isOnline ? 'Back Online!' : 'You\'re Offline'}
        </h1>

        <p className="text-gray-300 mb-6">
          {isOnline
            ? 'Connection restored. Redirecting you back...'
            : 'It looks like you\'ve lost your internet connection. Some features may be limited while offline.'}
        </p>

        {!isOnline && (
          <div className="space-y-4">
            <div className="bg-dark-bg/50 rounded-lg p-4 text-left">
              <h2 className="text-neon-cyan font-semibold mb-2">What you can do offline:</h2>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• View previously generated content</li>
                <li>• Browse cached pages</li>
                <li>• Read documentation</li>
              </ul>
            </div>

            <button
              onClick={() => router.push('/')}
              className="w-full px-6 py-3 bg-neon-purple/20 border border-neon-purple/50 rounded-lg
                       text-neon-purple hover:bg-neon-purple/30 transition-colors font-semibold"
            >
              Go to Home
            </button>
          </div>
        )}

        {isOnline && (
          <div className="animate-pulse text-neon-cyan">
            <p>Redirecting...</p>
          </div>
        )}
      </div>
    </div>
  )
}

