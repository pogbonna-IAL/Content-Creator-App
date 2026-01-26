'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { apiCall } from '@/lib/api-client'

export default function EmailVerificationBanner() {
  const { user } = useAuth()
  const router = useRouter()
  const [isResending, setIsResending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  // Don't show banner if user is verified or not logged in
  if (!user || user.email_verified === true) {
    return null
  }

  const handleResendEmail = async () => {
    setIsResending(true)
    setMessage(null)
    
    try {
      // Use Next.js API route that proxies to backend
      const response = await apiCall('/api/auth/verify-email/request', {
        method: 'POST',
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Verification email sent! Please check your inbox.')
        setTimeout(() => setMessage(null), 5000)
      } else {
        setMessage(data.detail || 'Failed to send verification email. Please try again.')
        setTimeout(() => setMessage(null), 5000)
      }
    } catch (error) {
      console.error('Resend email error:', error)
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      setMessage(errorMessage.includes('Failed to fetch') 
        ? 'Cannot connect to server. Please check your connection and try again.'
        : 'An error occurred. Please try again.')
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setIsResending(false)
    }
  }

  return (
    <div className="bg-yellow-500/20 border-b border-yellow-500/30 px-4 py-3">
      <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-yellow-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-sm font-medium text-yellow-400">
              Please verify your email address
            </p>
            <p className="text-xs text-yellow-300/80">
              {message || 'Check your inbox for the verification email we sent when you signed up.'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleResendEmail}
            disabled={isResending}
            className="px-4 py-1.5 text-sm bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 disabled:opacity-50 transition-colors border border-yellow-500/30"
          >
            {isResending ? 'Sending...' : 'Resend Email'}
          </button>
          <button
            onClick={() => router.push('/verify-email')}
            className="px-4 py-1.5 text-sm bg-yellow-500/30 text-yellow-300 rounded-lg hover:bg-yellow-500/40 transition-colors border border-yellow-500/40"
          >
            Verify Now
          </button>
        </div>
      </div>
    </div>
  )
}
