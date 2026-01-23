import { NextRequest } from 'next/server'
import { API_URL } from '../../../lib/env'

// Increase timeout for this API route (30 minutes)
export const maxDuration = 1800 // 30 minutes in seconds
export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic } = body

    // Get auth token from cookies
    const token = request.cookies.get('auth_token')?.value

    if (!token) {
      return new Response(
        JSON.stringify({ error: 'Authentication required' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log('Next.js API route received topic:', topic)

    if (!topic || typeof topic !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Topic is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    console.log('Calling FastAPI streaming endpoint at:', `${API_URL}/api/generate`)

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
          const fetchOptions: RequestInit = {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Connection': 'keep-alive',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ topic }),
            signal: abortController.signal,
          }

          // For Node.js, we can try to set keepalive
          if (typeof process !== 'undefined') {
            // @ts-ignore - Node.js specific fetch options
            fetchOptions.keepalive = true
          }

          const response = await fetch(`${API_URL}/api/generate`, fetchOptions).finally(() => {
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

