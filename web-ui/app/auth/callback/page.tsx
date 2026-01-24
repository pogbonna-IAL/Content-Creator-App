'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { API_URL, getApiUrl } from '@/lib/env'

// Force dynamic rendering (no static generation) to prevent React Context errors
export const dynamic = 'force-dynamic'

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setAuthToken } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const provider = searchParams.get('provider')

    if (token) {
      // Backend sets httpOnly cookie automatically via OAuth callback
      // Verify auth status (cookies sent automatically)
      fetch(getApiUrl('api/auth/me'), {
        method: 'GET',
        credentials: 'include',  // Include cookies
      })
        .then((res) => {
          if (!res.ok) {
            throw new Error('Authentication failed')
          }
          return res.json()
        })
        .then((user) => {
          // setAuthToken is deprecated but kept for compatibility
          // Backend already set httpOnly cookie
          setAuthToken(token, user)
          // Use window.location.href for a hard redirect to ensure auth state is refreshed
          window.location.href = '/'
        })
        .catch((err) => {
          console.error('Error fetching user info:', err)
          setError('Failed to complete authentication')
        })
    } else {
      // No token in URL - check if cookies are already set (direct visit)
      fetch(getApiUrl('api/auth/me'), {
        method: 'GET',
        credentials: 'include',
      })
        .then((res) => {
          if (res.ok) {
            return res.json()
          }
          throw new Error('Not authenticated')
        })
        .then((user) => {
          setAuthToken('', user)  // Token in cookie
          // Use window.location.href for a hard redirect to ensure auth state is refreshed
          window.location.href = '/'
        })
        .catch(() => {
          setError('No token received from OAuth provider')
        })
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

