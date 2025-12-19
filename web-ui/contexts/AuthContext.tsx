'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import Cookies from 'js-cookie'

interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  provider: string | null
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  setAuthToken: (token: string, user: User) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const TOKEN_COOKIE = 'auth_token'
const USER_COOKIE = 'auth_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Load auth state from cookies on mount
    const savedToken = Cookies.get(TOKEN_COOKIE)
    const savedUser = Cookies.get(USER_COOKIE)

    if (savedToken && savedUser) {
      try {
        setToken(savedToken)
        setUser(JSON.parse(savedUser))
        // Verify token is still valid
        verifyToken(savedToken)
      } catch (error) {
        console.error('Error loading auth state:', error)
        logout()
      }
    }
    setIsLoading(false)
  }, [])

  const verifyToken = async (tokenToVerify: string) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${tokenToVerify}`,
        },
      })

      if (!response.ok) {
        // Extract error message if available
        let errorMessage = 'Token invalid'
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch {
          // Response is not JSON, use status text
          errorMessage = response.statusText || errorMessage
        }
        
        if (response.status === 401) {
          console.warn('Token verification failed - token expired or invalid:', errorMessage)
        } else {
          console.error('Token verification failed:', errorMessage)
        }
        logout()
        return
      }

      const userData = await response.json()
      setUser(userData)
      Cookies.set(USER_COOKIE, JSON.stringify(userData), { expires: 7 })
    } catch (error) {
      console.error('Token verification failed:', error)
      // Network error or other issue - clear auth state
      logout()
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const formData = new FormData()
      formData.append('username', email) // OAuth2PasswordRequestForm uses 'username'
      formData.append('password', password)

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
        credentials: 'omit',
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
      setAuthToken(data.access_token, data.user)
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
      console.log('API URL:', `${API_URL}/api/auth/signup`)
      
      const response = await fetch(`${API_URL}/api/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, full_name: fullName }),
        // Add mode and credentials for CORS
        mode: 'cors',
        credentials: 'omit', // Don't send cookies for signup
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
      setAuthToken(data.access_token, data.user)
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

  const logout = () => {
    setUser(null)
    setToken(null)
    Cookies.remove(TOKEN_COOKIE)
    Cookies.remove(USER_COOKIE)
    
    // Clear saved email and password if "Remember me" was not checked
    if (typeof window !== 'undefined') {
      const rememberMe = localStorage.getItem('remember_me')
      if (rememberMe !== 'true') {
        localStorage.removeItem('saved_email')
        localStorage.removeItem('saved_password')
        localStorage.removeItem('remember_me')
      }
      // If "Remember me" was checked, keep the email and password for next login
    }
  }

  const setAuthToken = (newToken: string, newUser: User) => {
    setToken(newToken)
    setUser(newUser)
    Cookies.set(TOKEN_COOKIE, newToken, { expires: 7 })
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

