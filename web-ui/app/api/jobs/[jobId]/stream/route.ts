import { NextRequest } from 'next/server'
import { getApiUrl } from '@/lib/env'

export const dynamic = 'force-dynamic'
// Increase timeout for SSE streams (10 minutes)
export const maxDuration = 600

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ jobId: string }> }
) {
  // Safely await params promise (Next.js 15+ requirement)
  let jobId: string | undefined
  try {
    const params = await context.params
    jobId = params?.jobId
  } catch (paramsError) {
    console.error('[SSE Proxy] Error reading params:', paramsError)
    return new Response(
      JSON.stringify({ error: 'Invalid request parameters', detail: 'Failed to read route parameters' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    )
  }

  if (!jobId || jobId === 'undefined' || jobId === 'null') {
    return new Response(
      JSON.stringify({ error: 'Invalid job ID', detail: `Job ID is required. Received: ${jobId || 'undefined'}` }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    )
  }

  const backendStreamUrl = getApiUrl(`v1/content/jobs/${jobId}/stream`)

  console.log(`[SSE Proxy] Proxying SSE stream for job ${jobId} to ${backendStreamUrl}`)

  // Get auth token from cookies or Authorization header
  const cookieHeader = request.headers.get('cookie') || ''
  const authHeader = request.headers.get('authorization') || request.headers.get('Authorization')
  
  let token: string | null = null
  
  if (authHeader && authHeader.startsWith('Bearer ')) {
    token = authHeader.substring(7).trim()
  } else if (cookieHeader) {
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

  if (!token) {
    console.error(`[SSE Proxy] No auth token found for job ${jobId}`)
    return new Response(
      JSON.stringify({ error: 'Authentication required' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }

  try {
    // Create a ReadableStream to proxy the SSE stream
    const stream = new ReadableStream({
      async start(controller) {
        let backendResponse: Response | null = null
        let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
        
        try {
          console.log(`[SSE Proxy] Starting fetch to backend for job ${jobId}`)
          
          // Fetch from backend with timeout
          const abortController = new AbortController()
          const timeoutId = setTimeout(() => {
            console.error(`[SSE Proxy] Backend fetch timeout for job ${jobId}`)
            abortController.abort()
          }, 300000) // 5 minute timeout

          backendResponse = await fetch(backendStreamUrl, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'text/event-stream',
              'Cache-Control': 'no-cache',
            },
            credentials: 'include',
            signal: abortController.signal,
          })

          clearTimeout(timeoutId)

          if (!backendResponse.ok) {
            const errorText = await backendResponse.text()
            console.error(`[SSE Proxy] Backend responded with ${backendResponse.status} for job ${jobId}: ${errorText}`)
            controller.enqueue(new TextEncoder().encode(`event: error\ndata: ${JSON.stringify({ error: errorText, status: backendResponse.status })}\n\n`))
            controller.close()
            return
          }

          console.log(`[SSE Proxy] Backend connection established for job ${jobId}, status: ${backendResponse.status}`)

          if (!backendResponse.body) {
            console.error(`[SSE Proxy] No response body from backend for job ${jobId}`)
            controller.enqueue(new TextEncoder().encode(`event: error\ndata: ${JSON.stringify({ error: 'No response body from backend' })}\n\n`))
            controller.close()
            return
          }

          reader = backendResponse.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''

          console.log(`[SSE Proxy] Starting to read SSE stream for job ${jobId}`)
          
          let chunkCount = 0
          let lastEventTime = Date.now()

          while (true) {
            try {
              const { done, value } = await reader.read()
              
              if (done) {
                console.log(`[SSE Proxy] Backend stream ended for job ${jobId} after ${chunkCount} chunks`)
                // Send any remaining buffer before closing
                if (buffer.trim()) {
                  controller.enqueue(new TextEncoder().encode(buffer + '\n\n'))
                }
                controller.close()
                break
              }

              chunkCount++
              lastEventTime = Date.now()

              // Decode and forward chunks immediately
              const chunk = decoder.decode(value, { stream: true })
              buffer += chunk

              // Process complete SSE messages
              const parts = buffer.split('\n\n')
              buffer = parts.pop() || ''

              for (const part of parts) {
                if (part.trim()) {
                  // Forward the SSE message immediately
                  try {
                    controller.enqueue(new TextEncoder().encode(part + '\n\n'))
                    // Log first few events for debugging
                    if (chunkCount <= 5) {
                      console.log(`[SSE Proxy] Forwarded chunk #${chunkCount} for job ${jobId}, length: ${part.length}`)
                    }
                  } catch (enqueueError: any) {
                    // Controller might be closed (client disconnected)
                    if (enqueueError.message?.includes('closed') || enqueueError.message?.includes('Invalid state')) {
                      console.log(`[SSE Proxy] Controller closed, stopping stream for job ${jobId}`)
                      return
                    }
                    throw enqueueError
                  }
                }
              }
              
              // Check for timeout (no data for 5 minutes)
              if (Date.now() - lastEventTime > 300000) {
                console.error(`[SSE Proxy] Stream timeout for job ${jobId} - no data for 5 minutes`)
                controller.enqueue(new TextEncoder().encode(`event: error\ndata: ${JSON.stringify({ error: 'Stream timeout', message: 'No data received for 5 minutes' })}\n\n`))
                controller.close()
                break
              }
            } catch (readError: any) {
              console.error(`[SSE Proxy] Error reading chunk for job ${jobId}:`, readError)
              if (readError.name === 'AbortError') {
                console.log(`[SSE Proxy] Stream aborted for job ${jobId}`)
                controller.close()
                break
              }
              throw readError
            }
          }
        } catch (error: any) {
          console.error(`[SSE Proxy] Error proxying stream for job ${jobId}:`, error)
          
          if (error.name === 'AbortError') {
            controller.enqueue(new TextEncoder().encode(`event: error\ndata: ${JSON.stringify({ error: 'Stream timeout', message: 'Connection to backend timed out' })}\n\n`))
          } else {
            controller.enqueue(new TextEncoder().encode(`event: error\ndata: ${JSON.stringify({ error: error.message || 'Stream error', message: error.message })}\n\n`))
          }
          controller.close()
        } finally {
          if (reader) {
            try {
              await reader.cancel()
              reader.releaseLock()
            } catch (e) {
              // Ignore cleanup errors
            }
          }
        }
      },
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    })
  } catch (error: any) {
    console.error(`[SSE Proxy] Failed to create stream proxy for job ${jobId}:`, error)
    return new Response(
      JSON.stringify({ error: 'Failed to proxy stream', detail: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}
