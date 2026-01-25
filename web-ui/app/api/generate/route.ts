import { NextRequest } from 'next/server'
import { API_URL, getApiUrl } from '@/lib/env'

// Increase timeout for this API route (30 minutes)
export const maxDuration = 1800 // 30 minutes in seconds
export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic } = body

    // Forward cookies from client request to backend
    // The auth_token cookie is set by the backend and needs to be forwarded
    const cookieHeader = request.headers.get('cookie') || ''
    
    // Extract token from Authorization header first (preferred for cross-subdomain)
    let token: string | null = null
    const authHeader = request.headers.get('authorization')
    if (authHeader && authHeader.startsWith('Bearer ')) {
      token = authHeader.substring(7).trim()
    }
    
    // Fallback: Extract auth_token from cookies if Authorization header not present
    // Handle both URL-encoded and plain cookies, and various cookie formats
    if (!token) {
    
    // Try multiple extraction methods
    // Method 1: Regex match from cookie header string
    const tokenMatch = cookieHeader.match(/auth_token=([^;,\s]+)/)
    if (tokenMatch && tokenMatch[1]) {
      try {
        // Try decoding URL-encoded value
        token = decodeURIComponent(tokenMatch[1].trim())
      } catch {
        // If decoding fails, use the raw value (might already be decoded)
        token = tokenMatch[1].trim()
      }
    }
    
    // Method 2: Try reading from Next.js cookies API (might work if same domain)
    if (!token) {
      const cookieToken = request.cookies.get('auth_token')?.value
      if (cookieToken) {
        token = cookieToken.trim()
      }
    }
    
    // Method 3: Try parsing all cookies manually
    if (!token && cookieHeader) {
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
    
    // Validate token format (JWT tokens have 3 parts separated by dots)
    if (token) {
      const parts = token.split('.')
      if (parts.length !== 3) {
        console.warn('Token format invalid - expected JWT format (3 parts), got:', parts.length, 'parts')
        console.warn('Token preview:', token.substring(0, 50) + '...')
        // Don't reject it, but log a warning - might be a different token format
      }
    }

    if (!token) {
      console.warn('No auth token found in cookies.')
      console.warn('Cookie header present:', !!cookieHeader)
      console.warn('Cookie header length:', cookieHeader.length)
      // Don't log the full cookie header for security, but log if it exists
      if (cookieHeader) {
        console.warn('Cookie header contains auth_token:', cookieHeader.includes('auth_token'))
      }
      return new Response(
        JSON.stringify({ 
          error: 'Authentication required', 
          detail: 'Please log in to generate content',
          hint: 'Make sure you are logged in and cookies are enabled'
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    console.log('Auth token found, length:', token.length)
    console.log('Auth token first 20 chars:', token.substring(0, 20) + '...')

    console.log('Next.js API route received topic:', topic)

    if (!topic || typeof topic !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Topic is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const backendUrl = getApiUrl('v1/content/generate')
    console.log('Step 1: Creating job at:', backendUrl)
    
    // Prepare headers with Authorization
    const authHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    }
    
    // Forward cookies to backend (in case backend also checks cookies)
    if (cookieHeader) {
      authHeaders['Cookie'] = cookieHeader
    }
    
    console.log('Request headers:', {
      'Content-Type': authHeaders['Content-Type'],
      'Authorization': `Bearer ${token.substring(0, 20)}...`,
      'Cookie': cookieHeader ? 'present' : 'missing',
    })

    // Step 1: Create the job first
    const createJobResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ topic }),
    })

    if (!createJobResponse.ok) {
      const errorText = await createJobResponse.text()
      console.error('Failed to create job:', createJobResponse.status, errorText)
      console.error('Response headers:', Object.fromEntries(createJobResponse.headers.entries()))
      
      // If it's a 401, the token might be invalid or missing
      if (createJobResponse.status === 401) {
        return new Response(
          JSON.stringify({ 
            error: 'Authentication failed', 
            detail: 'Please log in again',
            hint: 'The authentication token may have expired or is invalid'
          }),
          { status: 401, headers: { 'Content-Type': 'application/json' } }
        )
      }
      
      return new Response(
        JSON.stringify({ error: 'Failed to create generation job', detail: errorText }),
        { status: createJobResponse.status, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const jobData = await createJobResponse.json()
    const jobId = jobData.id
    console.log('Job created with ID:', jobId)

    // Step 2: Stream job progress
    console.log('Step 2: Streaming job progress at:', getApiUrl(`v1/content/jobs/${jobId}/stream`))

    // Create a streaming response that proxies the SSE stream from FastAPI
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(streamController) {
        try {
          // Create AbortController with extended timeout (30 minutes)
          const abortController = new AbortController()
          const timeoutId = setTimeout(() => {
            abortController.abort()
          }, 30 * 60 * 1000) // 30 minutes timeout

          // Configure fetch with extended timeout for streaming
          // Node.js fetch uses undici which has a default body timeout
          // We need to ensure the connection stays alive
          const streamHeaders: Record<string, string> = {
            'Connection': 'keep-alive',
            'Authorization': `Bearer ${token}`,
          }
          
          // Forward cookies to backend (in case backend also checks cookies)
          if (cookieHeader) {
            streamHeaders['Cookie'] = cookieHeader
          }
          
          console.log('Stream request headers:', {
            'Authorization': `Bearer ${token.substring(0, 20)}...`,
            'Cookie': cookieHeader ? 'present' : 'missing',
          })
          
          const fetchOptions: RequestInit = {
            method: 'GET',
            headers: streamHeaders,
            signal: abortController.signal,
          }

          // For Node.js, we can try to set keepalive
          if (typeof process !== 'undefined') {
            // @ts-ignore - Node.js specific fetch options
            fetchOptions.keepalive = true
          }

          const response = await fetch(getApiUrl(`v1/content/jobs/${jobId}/stream`), fetchOptions).finally(() => {
            clearTimeout(timeoutId)
          })

          if (!response.ok) {
            const errorText = await response.text()
            streamController.enqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'error', message: errorText })}\n\n`)
            )
            streamController.close()
            return
          }

          const reader = response.body?.getReader()
          const decoder = new TextDecoder()

          if (!reader) {
            streamController.enqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'No response body' })}\n\n`)
            )
            streamController.close()
            return
          }

          // Read stream with timeout handling and keep-alive
          const readStream = async () => {
            try {
              let lastActivity = Date.now()
              const keepAliveInterval = setInterval(() => {
                // Send keep-alive comment every 30 seconds to prevent timeout
                const now = Date.now()
                if (now - lastActivity > 30000) {
                  // Send SSE comment as keep-alive
                  streamController.enqueue(encoder.encode(': keep-alive\n\n'))
                }
              }, 30000)

              try {
                while (true) {
                  const { done, value } = await reader.read()
                  
                  if (done) {
                    clearInterval(keepAliveInterval)
                    streamController.close()
                    break
                  }

                  // Update last activity time
                  lastActivity = Date.now()

                  // Forward the SSE data to the client
                  const chunk = decoder.decode(value, { stream: true })
                  streamController.enqueue(encoder.encode(chunk))
                }
              } finally {
                clearInterval(keepAliveInterval)
              }
            } catch (readError) {
              if (readError instanceof Error && readError.name === 'AbortError') {
                streamController.enqueue(
                  encoder.encode(`data: ${JSON.stringify({ 
                    type: 'error', 
                    message: 'Request timeout - content generation took too long (30 minutes)' 
                  })}\n\n`)
                )
                streamController.close()
              } else {
                throw readError
              }
            }
          }
          
          await readStream()
        } catch (error) {
          console.error('Streaming error:', error)
          const errorMessage = error instanceof Error ? error.message : 'Unknown error'
          console.error('Error details:', errorMessage)
          
          // Check if it's a timeout error
          if (errorMessage.includes('UND_ERR_BODY_TIMEOUT') || errorMessage.includes('timeout')) {
            streamController.enqueue(
              encoder.encode(`data: ${JSON.stringify({ 
                type: 'error', 
                message: 'Request timeout - content generation is taking longer than expected. Please try again or check the FastAPI server logs.' 
              })}\n\n`)
            )
          } else {
            streamController.enqueue(
              encoder.encode(`data: ${JSON.stringify({ 
                type: 'error', 
                message: errorMessage 
              })}\n\n`)
            )
          }
          streamController.close()
        }
      },
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
  } catch (error) {
    console.error('Next.js API route error:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to connect to API server', 
        details: error instanceof Error ? error.message : 'Unknown error',
        hint: 'Make sure the FastAPI server is running on port 8000. Run: uv run python api_server.py'
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}

