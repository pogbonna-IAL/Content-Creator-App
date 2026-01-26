import { NextRequest, NextResponse } from 'next/server'
import { getApiUrl } from '@/lib/env'

/**
 * Next.js API route that proxies email verification confirmation to the backend
 * This ensures the request goes to the FastAPI backend even if NEXT_PUBLIC_API_URL is not set
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { token } = body

    if (!token) {
      return NextResponse.json(
        { detail: 'Verification token is required' },
        { status: 400 }
      )
    }

    // Get backend API URL
    // In server-side context, we need an absolute URL for fetch
    let backendUrl = getApiUrl('api/auth/verify-email/confirm')
    
    // If getApiUrl returned a relative URL (starts with /), we need to construct absolute URL
    // Check if we're in a server environment and need to use the backend URL
    if (backendUrl.startsWith('/')) {
      // Try to get the backend URL from environment or use default
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000'
      backendUrl = `${apiUrl.replace(/\/+$/, '')}${backendUrl}`
    }
    
    console.log('[verify-email/confirm] Proxying to backend:', backendUrl)
    console.log('[verify-email/confirm] Token length:', token.length)

    // Extract auth token from cookies or Authorization header
    let authToken: string | null = null
    
    // Method 1: Try Authorization header
    const authHeader = request.headers.get('authorization')
    if (authHeader && authHeader.startsWith('Bearer ')) {
      authToken = authHeader.substring(7).trim()
    }
    
    // Method 2: Try reading from cookies
    if (!authToken) {
      const cookieToken = request.cookies.get('auth_token')?.value
      if (cookieToken) {
        authToken = cookieToken.trim()
      }
    }

    // Prepare headers for backend request
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    // Add Authorization header if token is available
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    
    // Forward cookies to backend
    const cookieHeader = request.headers.get('cookie')
    if (cookieHeader) {
      headers['Cookie'] = cookieHeader
    }

    console.log('[verify-email/confirm] Backend request headers:', {
      'Content-Type': headers['Content-Type'],
      'Authorization': authToken ? `Bearer ${authToken.substring(0, 20)}...` : 'missing',
      'Cookie': cookieHeader ? 'present' : 'missing',
    })

    // Proxy request to backend
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({ token }),
    })

    const responseData = await response.json().catch(() => ({
      detail: `Backend returned ${response.status} ${response.statusText}`
    }))

    console.log('[verify-email/confirm] Backend response:', {
      status: response.status,
      statusText: response.statusText,
      data: responseData,
    })

    // Return the backend response with the same status code
    return NextResponse.json(responseData, { status: response.status })
  } catch (error) {
    console.error('[verify-email/confirm] Proxy error:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json(
      { 
        detail: `Failed to verify email: ${errorMessage}`,
        error_code: 'PROXY_ERROR'
      },
      { status: 500 }
    )
  }
}
