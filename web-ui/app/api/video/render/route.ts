import { NextRequest, NextResponse } from 'next/server'
import { getApiUrl } from '@/lib/env'

export const dynamic = 'force-dynamic'
export const maxDuration = 600 // 10 minutes for video rendering

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { 
      job_id, 
      resolution, 
      fps, 
      background_type, 
      background_color, 
      background_image_path,
      include_narration, 
      renderer 
    } = body

    // Validate input
    if (!job_id) {
      return new NextResponse(
        JSON.stringify({ error: 'job_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Get auth token - try Authorization header first, then cookies
    const authHeader = request.headers.get('authorization') || request.headers.get('Authorization')
    const cookieHeader = request.headers.get('cookie') || request.headers.get('Cookie') || ''
    let token: string | null = null

    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.substring(7).trim()
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
            break
          }
        }
      }

      // Also try Next.js cookies API
      if (!token) {
        const cookieToken = request.cookies.get('auth_token')?.value
        if (cookieToken) {
          token = cookieToken.trim()
        }
      }
    }

    if (!token || token.length === 0) {
      return new NextResponse(
        JSON.stringify({ 
          error: 'Authentication required', 
          detail: 'Please log in to render video',
          hint: 'Token not found in Authorization header or cookies'
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Prepare request body with defaults
    const requestBody: any = {
      job_id,
      resolution: resolution || [1920, 1080],
      fps: fps || 30,
      background_type: background_type || 'solid',
      background_color: background_color || '#000000',
      include_narration: include_narration !== false,
      renderer: renderer || 'baseline'
    }

    if (background_image_path) {
      requestBody.background_image_path = background_image_path
    }

    // Call backend video render endpoint
    const backendUrl = getApiUrl('v1/content/video/render')
    console.log('Video Render API - Calling backend:', backendUrl)
    console.log('Video Render API - Request body:', JSON.stringify(requestBody, null, 2))

    // Add timeout to prevent hanging requests (60 seconds for initial response)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)

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
        console.error('Video render request timed out after 60 seconds')
        return new NextResponse(
          JSON.stringify({ 
            error: 'Request timeout', 
            detail: 'Video render request took too long. Please try again.',
            hint: 'The backend may be processing. Check backend logs for details.'
          }),
          { status: 504, headers: { 'Content-Type': 'application/json' } }
        )
      }
      throw fetchError
    }

    console.log('Video Render API - Backend response status:', response.status, response.statusText)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Video render request failed:', response.status, errorText)
      
      // Try to parse the error response as JSON
      let errorData: any = { error: errorText || 'Unknown error' }
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { error: errorText || 'Unknown error', detail: errorText }
      }
      
      if (response.status === 401) {
        return new NextResponse(
          JSON.stringify({ 
            error: 'Authentication failed', 
            detail: errorData.detail || 'Please log in again',
            hint: errorData.hint || 'Your session may have expired'
          }),
          { status: 401, headers: { 'Content-Type': 'application/json' } }
        )
      }

      // Forward the backend error details
      return new NextResponse(
        JSON.stringify({ 
          error: errorData.error || 'Failed to start video rendering', 
          detail: errorData.detail || errorText,
          hint: errorData.hint,
          status: response.status
        }),
        { status: response.status, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const result = await response.json()
    console.log('Video Render API - Backend response received:', {
      hasJobId: !!result.job_id,
      jobId: result.job_id,
      message: result.message,
      keys: Object.keys(result)
    })
    return NextResponse.json(result)

  } catch (error) {
    console.error('Video Render API error:', error)
    return new NextResponse(
      JSON.stringify({ 
        error: 'Internal server error', 
        detail: error instanceof Error ? error.message : 'Unknown error' 
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
