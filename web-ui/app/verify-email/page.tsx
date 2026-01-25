'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { getApiUrl } from '@/lib/env'
import { createAuthHeaders } from '@/lib/api-client'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export const dynamic = 'force-dynamic'

function VerifyEmailContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, verifyAuthStatus } = useAuth()
  const [status, setStatus] = useState<'verifying' | 'success' | 'error' | 'expired'>('verifying')
  const [message, setMessage] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = searchParams.get('token')
    
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided. Please check your email for the verification link.')
      setLoading(false)
      return
    }

    // Verify email with token
    const verifyEmail = async () => {
      try {
        const response = await fetch(getApiUrl('api/auth/verify-email/confirm'), {
          method: 'POST',
          headers: createAuthHeaders({
            'Content-Type': 'application/json',
          }),
          credentials: 'include',
          body: JSON.stringify({ token }),
        })

        const data = await response.json()

        if (response.ok) {
          setStatus('success')
          setMessage('Your email has been verified successfully!')
          
          // Refresh auth status to get updated user data
          await verifyAuthStatus()
          
          // Redirect to dashboard after 2 seconds
          setTimeout(() => {
            router.push('/')
          }, 2000)
        } else {
          if (data.detail?.includes('expired')) {
            setStatus('expired')
            setMessage('This verification link has expired. Please request a new verification email.')
          } else {
            setStatus('error')
            setMessage(data.detail || 'Failed to verify email. The link may be invalid or already used.')
          }
        }
      } catch (error) {
        console.error('Email verification error:', error)
        setStatus('error')
        setMessage('An error occurred while verifying your email. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    verifyEmail()
  }, [searchParams, router, verifyAuthStatus])

  const handleResendEmail = async () => {
    try {
      setLoading(true)
      const response = await fetch(getApiUrl('api/auth/verify-email/request'), {
        method: 'POST',
        headers: createAuthHeaders(),
        credentials: 'include',
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('A new verification email has been sent to your email address.')
        setStatus('success')
      } else {
        setMessage(data.detail || 'Failed to send verification email. Please try again.')
        setStatus('error')
      }
    } catch (error) {
      console.error('Resend email error:', error)
      setMessage('An error occurred. Please try again.')
      setStatus('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <div className="flex-1 container mx-auto px-4 py-16 max-w-2xl">
        <div className="glass-effect neon-border rounded-2xl p-8 text-center">
          {loading && status === 'verifying' ? (
            <>
              <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4"></div>
              <h1 className="text-3xl font-bold text-gradient mb-4">Verifying Your Email</h1>
              <p className="text-gray-300">Please wait while we verify your email address...</p>
            </>
          ) : status === 'success' ? (
            <>
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gradient mb-4">Email Verified!</h1>
              <p className="text-gray-300 mb-6">{message}</p>
              <p className="text-sm text-gray-400">Redirecting to dashboard...</p>
            </>
          ) : status === 'expired' ? (
            <>
              <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gradient mb-4">Link Expired</h1>
              <p className="text-gray-300 mb-6">{message}</p>
              <button
                onClick={handleResendEmail}
                disabled={loading}
                className="px-6 py-3 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Sending...' : 'Resend Verification Email'}
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gradient mb-4">Verification Failed</h1>
              <p className="text-gray-300 mb-6">{message}</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={handleResendEmail}
                  disabled={loading}
                  className="px-6 py-3 bg-neon-cyan text-dark-bg rounded-lg font-semibold hover:bg-neon-cyan/80 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Sending...' : 'Resend Verification Email'}
                </button>
                <button
                  onClick={() => router.push('/')}
                  className="px-6 py-3 border-2 border-neon-cyan rounded-lg font-semibold hover:bg-neon-cyan/10 transition-colors"
                >
                  Go to Dashboard
                </button>
              </div>
            </>
          )}
        </div>
      </div>
      <Footer />
    </main>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center">
          <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
        </main>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  )
}
