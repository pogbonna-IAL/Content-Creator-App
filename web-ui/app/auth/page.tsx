'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import AuthForm from '@/components/AuthForm'
import ContactForm from '@/components/ContactForm'

// Import validated API URL from env module
import { API_URL, getApiUrl } from '@/lib/env'

// Force dynamic rendering (no static generation) to prevent React Context errors
export const dynamic = 'force-dynamic'

export default function AuthPage() {
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { login, signup } = useAuth()
  const router = useRouter()

  const handleSubmit = async (email: string, password: string, fullName?: string) => {
    try {
      setError(null)
      console.log('Handle submit:', { isSignUp, email, hasPassword: !!password, hasFullName: !!fullName })
      
      if (isSignUp) {
        console.log('Calling signup...')
        await signup(email, password, fullName)
        console.log('Signup successful')
      } else {
        console.log('Calling login...')
        await login(email, password)
        console.log('Login successful')
      }
      
      // Wait a brief moment for cookies to be set by the backend
      // Backend sets httpOnly cookies, which need a moment to be available
      await new Promise(resolve => setTimeout(resolve, 200))
      
      // Verify auth status by checking /api/auth/me before redirecting
      // This ensures cookies are set and auth is working
      try {
        const verifyResponse = await fetch(getApiUrl('api/auth/me'), {
          method: 'GET',
          credentials: 'include',
        })
        
        if (verifyResponse.ok) {
          const userData = await verifyResponse.json()
          console.log('Auth verified successfully, redirecting to dashboard...', userData.email)
          // Use window.location.href for a hard redirect to ensure auth state is refreshed
          // This forces a full page reload, which will properly check auth cookies
          window.location.href = '/'
        } else {
          const errorText = await verifyResponse.text()
          console.error('Auth verification failed after login:', verifyResponse.status, errorText)
          // Still redirect - the page will verify auth on load and show appropriate content
          // This handles edge cases where verification fails but cookies are actually set
          window.location.href = '/'
        }
      } catch (verifyError) {
        console.error('Error verifying auth after login:', verifyError)
        // Still redirect - the page will verify auth on load
        // This handles network errors or other issues
        window.location.href = '/'
      }
    } catch (err) {
      console.error('Authentication error:', err)
      let errorMessage = err instanceof Error ? err.message : 'Authentication failed'
      
      // Provide helpful error messages
      if (errorMessage.includes('Failed to fetch') || errorMessage.includes('Cannot connect')) {
        errorMessage = `Cannot connect to API server. Please make sure the backend server is running:
        
1. Open a terminal in the project directory
2. Run: uv run python api_server.py
3. Wait for "Application startup complete"
4. Try signing up again

The server should be running at: ${API_URL}`
      }
      
      console.error('Setting error:', errorMessage)
      setError(errorMessage)
    }
  }

  const handleOAuthLogin = (provider: 'google' | 'facebook' | 'github') => {
    window.location.href = getApiUrl(`api/auth/oauth/${provider}/login`)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 py-12">
      <div className="container mx-auto max-w-6xl w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Authentication Form */}
          <div className="glass-effect neon-border rounded-2xl p-8">
            <div className="mb-6 text-center">
              <button
                onClick={() => router.push('/')}
                className="flex items-center justify-center mx-auto mb-4 hover:opacity-80 transition-opacity cursor-pointer"
                aria-label="Go to home page"
              >
                <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center glow-text">
                  <span className="text-3xl font-bold">C</span>
                </div>
              </button>
              <h1 className="text-3xl font-bold text-gradient mb-2">
                {isSignUp ? 'Create Account' : 'Welcome Back'}
              </h1>
              <p className="text-gray-200">
                {isSignUp
                  ? 'Sign up to start creating content'
                  : 'Sign in to your account'}
              </p>
            </div>

            <AuthForm
              isSignUp={isSignUp}
              onSubmit={handleSubmit}
              error={error}
              onToggleMode={() => {
                setIsSignUp(!isSignUp)
                setError(null)
              }}
              onOAuthLogin={handleOAuthLogin}
            />
          </div>

          {/* Contact Form */}
          <div>
            <ContactForm />
          </div>
        </div>
      </div>
    </div>
  )
}

