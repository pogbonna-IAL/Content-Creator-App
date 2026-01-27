import { NextRequest, NextResponse } from 'next/server'

// Handle GET requests (e.g., browser refresh) gracefully
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ jobId: string }> }
) {
  return NextResponse.json(
    { error: 'Method not allowed', detail: 'Use POST to cancel a job' },
    { status: 405 }
  )
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ jobId: string }> }
) {
  try {
    // Safely await params promise (Next.js 15+ requirement)
    let jobId: string | undefined
    try {
      const params = await context.params
      jobId = params?.jobId
    } catch (paramsError) {
      console.error('Error reading params:', paramsError)
      return NextResponse.json(
        { error: 'Invalid request parameters', detail: 'Failed to read route parameters' },
        { status: 400 }
      )
    }

    if (!jobId || jobId === 'undefined' || jobId === 'null' || isNaN(Number(jobId))) {
      return NextResponse.json(
        { error: 'Invalid job ID', detail: `Job ID is required. Received: ${jobId || 'undefined'}` },
        { status: 400 }
      )
    }

    // Get auth token from localStorage (via Authorization header)
    const authHeader = request.headers.get('authorization')
    let token: string | null = null

    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.substring(7).trim()
    }

    // Fallback to cookies if no Authorization header
    if (!token) {
      const cookieHeader = request.headers.get('cookie') || ''
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
    }

    if (!token || token.length < 10) {
      return NextResponse.json(
        { error: 'Authentication required', detail: 'Please log in to cancel jobs' },
        { status: 401 }
      )
    }

    // Forward request to backend
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'https://content-creator-app-api-staging.up.railway.app'
    const response = await fetch(`${backendUrl}/v1/content/jobs/${jobId}/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(request.headers.get('cookie') ? { 'Cookie': request.headers.get('cookie')! } : {})
      },
      credentials: 'include',
    })

    if (!response.ok) {
      const errorText = await response.text()
      let errorData: any = {}
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { error: errorText || 'Unknown error' }
      }

      return NextResponse.json(
        { error: errorData.error || 'Failed to cancel job', detail: errorData.detail },
        { status: response.status }
      )
    }

    const result = await response.json()
    return NextResponse.json(result)

  } catch (error) {
    console.error('Error cancelling job:', error)
    return NextResponse.json(
      { error: 'Failed to cancel job', detail: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
