'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setAuthToken } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const provider = searchParams.get('provider')

    if (token) {
      // Get user info from token
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.json())
        .then((user) => {
          setAuthToken(token, user)
          router.push('/')
        })
        .catch((err) => {
          console.error('Error fetching user info:', err)
          setError('Failed to complete authentication')
        })
    } else {
      setError('No token received from OAuth provider')
    }
  }, [searchParams, setAuthToken, router])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-effect neon-border rounded-2xl p-8 max-w-md">
          <h1 className="text-2xl font-bold text-gradient mb-4">Authentication Error</h1>
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg
                     text-neon-purple hover:bg-neon-purple/30 transition-colors"
          >
            Go to Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="glass-effect neon-border rounded-2xl p-8">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
          <p className="text-neon-cyan">Completing authentication...</p>
        </div>
      </div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="glass-effect neon-border rounded-2xl p-8">
            <div className="flex flex-col items-center space-y-4">
              <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
              <p className="text-neon-cyan">Loading...</p>
            </div>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  )
}

