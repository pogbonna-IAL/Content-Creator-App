'use client'

import { useState, FormEvent, useEffect } from 'react'

interface AuthFormProps {
  isSignUp: boolean
  onSubmit: (email: string, password: string, fullName?: string) => void
  error: string | null
  onToggleMode: () => void
  onOAuthLogin: (provider: 'google' | 'facebook' | 'github') => void
}

const SAVED_EMAIL_KEY = 'saved_email'
const REMEMBER_ME_KEY = 'remember_me'

// SECURITY NOTE: Passwords are NEVER stored in localStorage/sessionStorage
// Only email is saved for "Remember Me" functionality
// Authentication tokens are stored in httpOnly cookies by the backend

export default function AuthForm({
  isSignUp,
  onSubmit,
  error,
  onToggleMode,
  onOAuthLogin,
}: AuthFormProps) {
  // Load saved email from localStorage on mount
  const [email, setEmail] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedEmail = localStorage.getItem(SAVED_EMAIL_KEY)
      return savedEmail || ''
    }
    return ''
  })
  
  // Password is NEVER loaded from storage - always starts empty
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [fullName, setFullName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(REMEMBER_ME_KEY) === 'true'
    }
    return false
  })

  // Load saved email when switching between sign in/up
  useEffect(() => {
    if (!isSignUp && typeof window !== 'undefined') {
      const savedEmail = localStorage.getItem(SAVED_EMAIL_KEY)
      if (savedEmail) {
        setEmail(savedEmail)
      }
    }
  }, [isSignUp])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    // Basic validation
    if (!email || !password) {
      return // Let HTML5 validation handle this
    }
    
    if (isSignUp && password.length < 8) {
      // This will be caught by the onSubmit error handler
      return
    }
    
    setIsLoading(true)
    try {
      console.log('AuthForm: Submitting form', { isSignUp, email, hasPassword: !!password })
      await onSubmit(email, password, isSignUp ? fullName : undefined)
      console.log('AuthForm: Submit successful')
      
      // Save email to localStorage after successful authentication
      // The "Remember me" checkbox controls whether to keep it after logout
      if (typeof window !== 'undefined') {
        if (rememberMe) {
          localStorage.setItem(SAVED_EMAIL_KEY, email)
          localStorage.setItem(REMEMBER_ME_KEY, 'true')
        } else {
          // Clear saved email if "Remember me" is unchecked
          localStorage.removeItem(SAVED_EMAIL_KEY)
          localStorage.removeItem(REMEMBER_ME_KEY)
        }
      }
    } catch (err) {
      console.error('AuthForm: Submit error', err)
      // Error is handled by parent component via onError prop
      throw err // Re-throw so parent can handle it
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {isSignUp && (
        <div>
          <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">
            Full Name (Optional)
          </label>
          <input
            type="text"
            id="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            placeholder="John Doe"
          />
        </div>
      )}
      
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="you@example.com"
        />
      </div>
      
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <div className="relative mt-1">
          <input
            type={showPassword ? "text" : "password"}
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={isSignUp ? 8 : undefined}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
            placeholder={isSignUp ? "Minimum 8 characters" : "Your password"}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
        </div>
        {isSignUp && (
          <div className="mt-2 text-xs text-gray-600 space-y-1">
            <p className="font-medium">Password must contain:</p>
            <ul className="list-disc list-inside space-y-0.5 ml-2">
              <li>At least 8 characters</li>
              <li>One uppercase letter (A-Z)</li>
              <li>One lowercase letter (a-z)</li>
              <li>One number (0-9)</li>
              <li>One special character (!@#$%^&* etc.)</li>
            </ul>
            <p className="text-gray-500 italic mt-1">Example: MyP@ssw0rd123</p>
          </div>
        )}
      </div>

      {!isSignUp && (
        <div className="flex items-center">
          <input
            type="checkbox"
            id="rememberMe"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="rememberMe" className="ml-2 block text-sm text-gray-700">
            Remember my email
          </label>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                {error}
              </h3>
            </div>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <span className="flex items-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {isSignUp ? 'Creating account...' : 'Signing in...'}
          </span>
        ) : (
          isSignUp ? 'Sign up' : 'Sign in'
        )}
      </button>

      <div className="mt-4">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Or continue with</span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => onOAuthLogin('google')}
            className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          >
            Google
          </button>
          <button
            type="button"
            onClick={() => onOAuthLogin('facebook')}
            className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          >
            Facebook
          </button>
          <button
            type="button"
            onClick={() => onOAuthLogin('github')}
            className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          >
            GitHub
          </button>
        </div>
      </div>

      <div className="text-center text-sm">
        <button
          type="button"
          onClick={onToggleMode}
          className="font-medium text-blue-600 hover:text-blue-500"
        >
          {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
        </button>
      </div>
    </form>
  )
}
