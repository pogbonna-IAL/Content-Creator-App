import { NextRequest, NextResponse } from 'next/server'

export async function POST(
  request: NextRequest,
  { params }: { params: { jobId: string } }
) {
  try {
    const jobId = params.jobId

    if (!jobId || isNaN(Number(jobId))) {
      return NextResponse.json(
        { error: 'Invalid job ID' },
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
