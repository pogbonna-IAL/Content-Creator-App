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
const SAVED_PASSWORD_KEY = 'saved_password'

// Simple obfuscation (NOT true encryption - for convenience only)
// WARNING: This is not secure. Passwords stored client-side are vulnerable.
// This is for convenience only and should not be used for sensitive accounts.
function obfuscatePassword(password: string): string {
  if (typeof window === 'undefined') return password
  // Simple base64 encoding with a simple transformation
  const encoded = btoa(password)
  // Reverse and add a simple prefix to make it less obvious
  return 'cc_' + encoded.split('').reverse().join('')
}

function deobfuscatePassword(obfuscated: string): string {
  if (typeof window === 'undefined') return obfuscated
  try {
    // Remove prefix and reverse
    const withoutPrefix = obfuscated.replace('cc_', '')
    const reversed = withoutPrefix.split('').reverse().join('')
    // Decode base64
    return atob(reversed)
  } catch (e) {
    console.error('Error deobfuscating password:', e)
    return ''
  }
}

export default function AuthForm({
  isSignUp,
  onSubmit,
  error,
  onToggleMode,
  onOAuthLogin,
}: AuthFormProps) {
  // Load saved email and password from localStorage on mount
  const [email, setEmail] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedEmail = localStorage.getItem(SAVED_EMAIL_KEY)
      return savedEmail || ''
    }
    return ''
  })
  const [password, setPassword] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedPassword = localStorage.getItem(SAVED_PASSWORD_KEY)
      if (savedPassword) {
        try {
          return deobfuscatePassword(savedPassword)
        } catch (e) {
          console.error('Error loading saved password:', e)
          return ''
        }
      }
    }
    return ''
  })
  const [fullName, setFullName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(REMEMBER_ME_KEY) === 'true'
    }
    return false
  })

  // Load saved email and password when component mounts or when switching between sign in/up
  useEffect(() => {
    if (!isSignUp && typeof window !== 'undefined') {
      const savedEmail = localStorage.getItem(SAVED_EMAIL_KEY)
      const savedPassword = localStorage.getItem(SAVED_PASSWORD_KEY)
      
      if (savedEmail) {
        setEmail(savedEmail)
      }
      
      if (savedPassword && rememberMe) {
        try {
          const deobfuscated = deobfuscatePassword(savedPassword)
          if (deobfuscated) {
            setPassword(deobfuscated)
          }
        } catch (e) {
          console.error('Error loading saved password:', e)
        }
      }
    }
  }, [isSignUp, rememberMe])

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
      
      // Save email and password to localStorage after successful authentication
      // The "Remember me" checkbox controls whether to keep it after logout
      if (typeof window !== 'undefined') {
        localStorage.setItem(SAVED_EMAIL_KEY, email)
        localStorage.setItem(REMEMBER_ME_KEY, rememberMe.toString())
        
        // Only save password if "Remember me" is checked
        if (rememberMe && password) {
          try {
            const obfuscated = obfuscatePassword(password)
            localStorage.setItem(SAVED_PASSWORD_KEY, obfuscated)
          } catch (e) {
            console.error('Error saving password:', e)
            // Don't fail the login if password saving fails
          }
        } else {
          // Clear saved password if "Remember me" is unchecked
          localStorage.removeItem(SAVED_PASSWORD_KEY)
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
    <div>
      {/* OAuth Buttons */}
      <div className="space-y-3 mb-6">
        <button
          onClick={() => onOAuthLogin('google')}
          className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg
                   text-white hover:bg-white/20 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span>Continue with Google</span>
        </button>

        <button
          onClick={() => onOAuthLogin('facebook')}
          className="w-full px-4 py-3 bg-blue-600/20 border border-blue-500/50 rounded-lg
                   text-blue-400 hover:bg-blue-600/30 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
          <span>Continue with Facebook</span>
        </button>

        <button
          onClick={() => onOAuthLogin('github')}
          className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg
                   text-gray-300 hover:bg-gray-800/70 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
          <span>Continue with GitHub</span>
        </button>
      </div>

      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-dark-border"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-dark-bg text-gray-400">Or continue with email</span>
        </div>
      </div>

      {/* Email/Password Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {isSignUp && (
          <div>
            <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-2">
              Full Name
            </label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-dark-card border border-dark-border
                       focus:ring-2 focus:ring-neon-cyan focus:border-transparent outline-none
                       text-white placeholder-gray-500"
              placeholder="John Doe"
            />
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-3 rounded-lg bg-dark-card border border-dark-border
                     focus:ring-2 focus:ring-neon-cyan focus:border-transparent outline-none
                     text-white placeholder-gray-500"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full px-4 py-3 rounded-lg bg-dark-card border border-dark-border
                     focus:ring-2 focus:ring-neon-cyan focus:border-transparent outline-none
                     text-white placeholder-gray-500"
            placeholder="••••••••"
          />
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Remember Me Checkbox - show for both sign in and sign up */}
        <div className="flex items-start">
          <input
            type="checkbox"
            id="rememberMe"
            checked={rememberMe}
            onChange={(e) => {
              setRememberMe(e.target.checked)
              // Clear password if unchecking "Remember me"
              if (!e.target.checked && typeof window !== 'undefined') {
                localStorage.removeItem(SAVED_PASSWORD_KEY)
                setPassword('')
              }
            }}
            className="w-4 h-4 rounded bg-dark-card border-dark-border 
                     text-neon-cyan focus:ring-neon-cyan focus:ring-2 cursor-pointer mt-0.5"
          />
          <div className="ml-2 flex-1">
            <label htmlFor="rememberMe" className="text-sm text-gray-300 cursor-pointer block">
              Remember me
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Your email and password will be saved locally for convenience. 
              Not recommended for shared devices.
            </p>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full px-4 py-3 bg-gradient-to-r from-neon-cyan to-neon-purple
                   rounded-lg font-semibold hover:opacity-90 transition-opacity
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading
            ? 'Please wait...'
            : isSignUp
            ? 'Create Account'
            : 'Sign In'}
        </button>
      </form>

      <div className="mt-6 text-center">
        <button
          onClick={onToggleMode}
          className="text-gray-400 hover:text-neon-cyan transition-colors text-sm"
        >
          {isSignUp
            ? 'Already have an account? Sign in'
            : "Don't have an account? Sign up"}
        </button>
      </div>
    </div>
  )
}

