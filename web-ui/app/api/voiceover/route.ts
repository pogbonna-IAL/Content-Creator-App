import { NextRequest, NextResponse } from 'next/server'

function getApiUrl(endpoint: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  return `${baseUrl}/${endpoint}`
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { job_id, narration_text, voice_id, speed, format } = body

    // Validate input
    if (!job_id && !narration_text) {
      return new Response(
        JSON.stringify({ error: 'Either job_id or narration_text is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Get auth token - try Authorization header first, then cookies
    // Check both lowercase and original case (Next.js may normalize headers)
    const authHeader = request.headers.get('authorization') || request.headers.get('Authorization')
    const cookieHeader = request.headers.get('cookie') || request.headers.get('Cookie') || ''
    let token: string | null = null

    console.log('Voiceover API - Auth header present:', !!authHeader)
    console.log('Voiceover API - Cookie header present:', !!cookieHeader)
    console.log('Voiceover API - Header names:', Array.from(request.headers.keys()))

    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.substring(7).trim()
      console.log('Voiceover API - Token from Authorization header, length:', token.length)
    } else if (authHeader) {
      console.log('Voiceover API - Auth header present but does not start with "Bearer ":', authHeader.substring(0, 20))
    }

    // Fallback to cookies if no Authorization header
    if (!token) {
      if (cookieHeader) {
        const cookies = cookieHeader.split(';').map(c => c.trim())
        for (const cookie of cookies) {
          if (cookie.startsWith('auth_token=')) {
            const value = cookie.substring('auth_token='.length).trim()
            try {
              token = decodeURIComponent(value)
            } catch {
              token = value
            }
            console.log('Voiceover API - Token from cookie, length:', token.length)
            break
          }
        }
      }

      // Also try Next.js cookies API
      if (!token) {
        const cookieToken = request.cookies.get('auth_token')?.value
        if (cookieToken) {
          token = cookieToken.trim()
          console.log('Voiceover API - Token from Next.js cookies, length:', token.length)
        }
      }
    }

    if (!token || token.length === 0) {
      console.error('Voiceover API - No token found. Auth header:', !!authHeader, 'Cookie header:', !!cookieHeader)
      console.error('Voiceover API - Auth header value (first 50 chars):', authHeader ? authHeader.substring(0, 50) : 'null')
      return new Response(
        JSON.stringify({ 
          error: 'Authentication required', 
          detail: 'Please log in to generate voiceover',
          hint: 'Token not found in Authorization header or cookies'
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log('Voiceover API - Token found (length:', token.length, '), forwarding to backend')

    // Prepare request body
    const requestBody: any = {}
    if (job_id) requestBody.job_id = job_id
    if (narration_text) requestBody.narration_text = narration_text
    if (voice_id) requestBody.voice_id = voice_id
    if (speed) requestBody.speed = speed
    if (format) requestBody.format = format

    // Call backend voiceover endpoint
    const backendUrl = getApiUrl('v1/content/voiceover')
    console.log('Calling voiceover endpoint:', backendUrl)
    console.log('Voiceover request body:', JSON.stringify(requestBody, null, 2))

    // Add timeout to prevent hanging requests (30 seconds)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000)

    let response: Response
    try {
      response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          ...(cookieHeader ? { 'Cookie': cookieHeader } : {})
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
    } catch (fetchError) {
      clearTimeout(timeoutId)
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        console.error('Voiceover request timed out after 30 seconds')
        return new Response(
          JSON.stringify({ 
            error: 'Request timeout', 
            detail: 'Voiceover request took too long. Please try again.',
            hint: 'The backend may be processing. Check backend logs for details.'
          }),
          { status: 504, headers: { 'Content-Type': 'application/json' } }
        )
      }
      throw fetchError
    }

    console.log('Voiceover API - Backend response status:', response.status, response.statusText)
    console.log('Voiceover API - Response headers:', Object.fromEntries(response.headers.entries()))

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Voiceover request failed:', response.status, errorText)
      
      // Try to parse the error response as JSON
      let errorData: any = { error: errorText || 'Unknown error' }
      try {
        errorData = JSON.parse(errorText)
      } catch {
        // If not JSON, keep the text as error
        errorData = { error: errorText || 'Unknown error', detail: errorText }
      }
      
      if (response.status === 401) {
        return new Response(
          JSON.stringify({ 
            error: 'Authentication failed', 
            detail: errorData.detail || 'Please log in again',
            hint: errorData.hint || 'Your session may have expired'
          }),
          { status: 401, headers: { 'Content-Type': 'application/json' } }
        )
      }

      // Forward the backend error details
      return new Response(
        JSON.stringify({ 
          error: errorData.error || 'Failed to start voiceover generation', 
          detail: errorData.detail || errorText,
          hint: errorData.hint,
          status: response.status
        }),
        { status: response.status, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const result = await response.json()
    console.log('Voiceover API - Backend response received:', {
      hasJobId: !!result.job_id,
      jobId: result.job_id,
      message: result.message,
      keys: Object.keys(result)
    })
    return NextResponse.json(result)

  } catch (error) {
    console.error('Voiceover API error:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error', 
        detail: error instanceof Error ? error.message : 'Unknown error' 
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
