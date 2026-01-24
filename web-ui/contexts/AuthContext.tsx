'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import Cookies from 'js-cookie'

interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  is_admin: boolean
  email_verified?: boolean
  provider: string | null
}

interface AuthContextType {
  user: User | null
  token: string | null  // Deprecated: kept for backward compatibility, always null now
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => Promise<void>
  setAuthToken: (token: string, user: User) => void  // Deprecated: cookies set by backend
  verifyAuthStatus: () => Promise<void>  // Verify and refresh auth status
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Import validated API URL from env module
import { API_URL, getApiUrl } from '@/lib/env'
const USER_COOKIE = 'auth_user'  // Non-httpOnly cookie for user display info

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Load auth state on mount
    // auth_token is httpOnly, so we can't read it from JavaScript
    // Instead, verify auth status via /api/auth/me (cookies sent automatically)
    const savedUser = Cookies.get(USER_COOKIE)
    
    if (savedUser) {
      try {
        // Load user info from non-httpOnly cookie for immediate display
        setUser(JSON.parse(savedUser))
      } catch (error) {
        console.error('Error loading user info:', error)
      }
    }
    
    // Verify auth status with backend (cookies sent automatically)
    verifyAuthStatus()
  }, [])

  const verifyAuthStatus = async () => {
    try {
      // Cookies (including httpOnly auth_token) are sent automatically
      const response = await fetch(getApiUrl('api/auth/me'), {
        method: 'GET',
        credentials: 'include',  // Include cookies
      })

      if (!response.ok) {
        // Extract error message if available
        let errorMessage = 'Authentication failed'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch {
          // Response is not JSON, use status text
          errorMessage = response.statusText || errorMessage
        }
        
        if (response.status === 401) {
          console.warn('Auth verification failed - not authenticated:', errorMessage)
        } else {
          console.error('Auth verification failed:', errorMessage)
        }
        // Clear local state
        setUser(null)
        setToken(null)
        Cookies.remove(USER_COOKIE)
        setIsLoading(false)
        return
      }

      const userData = await response.json()
      setUser(userData)
      // Update user cookie (non-httpOnly) for display
      Cookies.set(USER_COOKIE, JSON.stringify(userData), { expires: 7 })
      setIsLoading(false)
    } catch (error) {
      console.error('Auth verification failed:', error)
      // Network error or other issue - clear auth state
      setUser(null)
      setToken(null)
      Cookies.remove(USER_COOKIE)
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const formData = new FormData()
      formData.append('username', email) // OAuth2PasswordRequestForm uses 'username'
      formData.append('password', password)

      const response = await fetch(getApiUrl('api/auth/login'), {
        method: 'POST',
        body: formData,
        mode: 'cors',
        credentials: 'include',  // Include cookies to receive httpOnly auth_token
      }).catch((fetchError) => {
        console.error('Login fetch error:', fetchError)
        if (fetchError instanceof TypeError && fetchError.message.includes('fetch')) {
          throw new Error(
            `Cannot connect to API server at ${API_URL}. ` +
            `Please make sure the API server is running: uv run python api_server.py`
          )
        }
        throw fetchError
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Login failed')
      }

      const data = await response.json()
      // Backend sets httpOnly cookie automatically
      // Just update local user state
      setUser(data.user)
      setToken(null)  // Token is in httpOnly cookie, not accessible from JS
      Cookies.set(USER_COOKIE, JSON.stringify(data.user), { expires: 7 })
    } catch (error) {
      console.error('Login error:', error)
      if (error instanceof Error && error.message.includes('Failed to fetch')) {
        throw new Error(
          `Cannot connect to the API server. ` +
          `Make sure the server is running at ${API_URL}. ` +
          `Start it with: uv run python api_server.py`
        )
      }
      throw error
    }
  }

  const signup = async (email: string, password: string, fullName?: string) => {
    try {
      console.log('Signup attempt:', { email, hasPassword: !!password, hasFullName: !!fullName })
      console.log('API URL:', getApiUrl('api/auth/signup'))
      
      const response = await fetch(getApiUrl('api/auth/signup'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, full_name: fullName }),
        mode: 'cors',
        credentials: 'include',  // Include cookies to receive httpOnly auth_token
      }).catch((fetchError) => {
        // Handle network errors
        console.error('Fetch error:', fetchError)
        if (fetchError instanceof TypeError && fetchError.message.includes('fetch')) {
          throw new Error(
            `Cannot connect to API server at ${API_URL}. ` +
            `Please make sure the API server is running: uv run python api_server.py`
          )
        }
        throw fetchError
      })

      console.log('Signup response status:', response.status, response.statusText)

      if (!response.ok) {
        let error
        try {
          error = await response.json()
          console.error('Signup error response:', error)
        } catch (e) {
          const text = await response.text()
          console.error('Signup error (non-JSON):', text)
          throw new Error(`Signup failed: ${response.status} ${response.statusText}`)
        }
        throw new Error(error.detail || error.message || 'Signup failed')
      }

      const data = await response.json()
      console.log('Signup success:', { hasToken: !!data.access_token, hasUser: !!data.user })
      // Backend sets httpOnly cookie automatically
      // Just update local user state
      setUser(data.user)
      setToken(null)  // Token is in httpOnly cookie, not accessible from JS
      Cookies.set(USER_COOKIE, JSON.stringify(data.user), { expires: 7 })
    } catch (error) {
      console.error('Signup error:', error)
      // Provide more helpful error messages
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          throw new Error(
            `Cannot connect to the API server. ` +
            `Make sure the server is running at ${API_URL}. ` +
            `Start it with: uv run python api_server.py`
          )
        }
        throw error
      }
      throw new Error('An unexpected error occurred during signup')
    }
  }

  const logout = async () => {
    try {
      // Call backend logout endpoint to clear httpOnly cookies
      await fetch(getApiUrl('api/auth/logout'), {
        method: 'POST',
        credentials: 'include',  // Include cookies
      }).catch(() => {
        // Ignore errors - cookies will be cleared client-side anyway
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear local state
      setUser(null)
      setToken(null)
      Cookies.remove(USER_COOKIE)
      
      // Clear saved email if "Remember me" was not checked
      if (typeof window !== 'undefined') {
        const rememberMe = localStorage.getItem('remember_me')
        if (rememberMe !== 'true') {
          localStorage.removeItem('saved_email')
          localStorage.removeItem('remember_me')
        }
        // If "Remember me" was checked, keep the email only (passwords are NEVER stored)
      }
    }
  }

  const setAuthToken = (newToken: string, newUser: User) => {
    // Deprecated: Backend sets httpOnly cookies automatically
    // This function kept for backward compatibility (OAuth callback)
    setUser(newUser)
    setToken(null)  // Token is in httpOnly cookie, not accessible from JS
    Cookies.set(USER_COOKIE, JSON.stringify(newUser), { expires: 7 })
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        signup,
        logout,
        setAuthToken,
        verifyAuthStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

