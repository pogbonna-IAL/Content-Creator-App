import { NextRequest } from 'next/server'
import { API_URL, getApiUrl } from '@/lib/env'

// Increase timeout for this API route (30 minutes)
export const maxDuration = 1800 // 30 minutes in seconds
export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic, content_types } = body

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

    console.log('Next.js API route received topic:', topic, 'content_types:', content_types)

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
    // Forward content_types if provided, otherwise backend will use plan defaults
    const requestBody: { topic: string; content_types?: string[]; idempotency_key?: string } = { topic }
    if (content_types && Array.isArray(content_types) && content_types.length > 0) {
      requestBody.content_types = content_types
    }
    
    // Add a unique idempotency key to prevent conflicts with cancelled jobs
    // Backend auto-generates from topic+content_types, but we add timestamp to make it unique
    // This ensures cancelled jobs don't block new generations
    requestBody.idempotency_key = `${topic}_${content_types?.join(',') || 'blog'}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    
    console.log('Forwarding to backend:', { topic, content_types: requestBody.content_types, hasIdempotencyKey: !!requestBody.idempotency_key })
    
    let createJobResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify(requestBody),
    })

    // Handle 409 conflict (job already exists with same idempotency key)
    if (createJobResponse.status === 409) {
      try {
        const errorText = await createJobResponse.text()
        let errorData: any = {}
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { message: errorText }
        }
        
        console.warn('Job conflict detected:', errorData)
        
        // If the existing job is cancelled, retry with a new unique idempotency key
        if (errorData.details?.status === 'cancelled' || errorData.status === 'cancelled') {
          console.log('Existing job is cancelled, retrying with new idempotency key...')
          // Generate a new unique idempotency key with random component
          requestBody.idempotency_key = `${topic}_${content_types?.join(',') || 'blog'}_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
          
          createJobResponse = await fetch(backendUrl, {
            method: 'POST',
            headers: authHeaders,
            body: JSON.stringify(requestBody),
          })
          
          // If retry succeeds, continue normally
          if (createJobResponse.ok) {
            console.log('Retry with new idempotency key succeeded')
            // Continue to process the response below
          } else if (createJobResponse.status === 409) {
            // Still getting conflict, return helpful error
            const retryErrorText = await createJobResponse.text()
            return new Response(
              JSON.stringify({ 
                error: 'Job conflict', 
                detail: 'Unable to create job due to idempotency conflict. Please try again in a moment.',
                hint: 'A job with similar parameters may be processing. Wait a few seconds and try again.'
              }),
              { status: 409, headers: { 'Content-Type': 'application/json' } }
            )
          } else {
            // Other error on retry
            const retryErrorText = await createJobResponse.text()
            console.error('Retry failed:', createJobResponse.status, retryErrorText)
            return new Response(
              JSON.stringify({ 
                error: 'Failed to create generation job', 
                detail: retryErrorText,
                hint: 'Please try again in a moment'
              }),
              { status: createJobResponse.status, headers: { 'Content-Type': 'application/json' } }
            )
          }
        } else {
          // If job exists and is not cancelled, return helpful error
          return new Response(
            JSON.stringify({ 
              error: 'Job already exists', 
              detail: errorData.message || 'A job with the same parameters is already in progress',
              hint: 'Please wait for the current job to complete or cancel it first',
              existing_job_id: errorData.details?.job_id || errorData.job_id
            }),
            { status: 409, headers: { 'Content-Type': 'application/json' } }
          )
        }
      } catch (parseError) {
        console.error('Error parsing 409 response:', parseError)
        const errorText = await createJobResponse.text()
        return new Response(
          JSON.stringify({ 
            error: 'Job conflict', 
            detail: errorText,
            hint: 'A job with the same parameters may already exist. Please try again with a slightly different topic or wait a moment.'
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } }
        )
      }
    }

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
        // Track controller state to prevent double-close errors
        // Define these OUTSIDE the try block so they're available in catch
        let controllerClosed = false
        
        const safeEnqueue = (data: Uint8Array) => {
          if (!controllerClosed) {
            try {
              streamController.enqueue(data)
            } catch (e) {
              // Controller might be closed by client disconnect
              if (e instanceof TypeError && (e.message.includes('closed') || e.message.includes('Invalid state'))) {
                controllerClosed = true
                console.log('Stream controller closed by client')
              } else {
                throw e
              }
            }
          }
        }
        
        const safeClose = () => {
          if (!controllerClosed) {
            try {
              streamController.close()
              controllerClosed = true
            } catch (e) {
              // Already closed - ignore
              controllerClosed = true
              console.log('Stream controller already closed:', e instanceof Error ? e.message : String(e))
            }
          }
        }

        try {
          // Create AbortController with extended timeout (30 minutes)
          const abortController = new AbortController()
          const timeoutId = setTimeout(() => {
            abortController.abort()
          }, 30 * 60 * 1000) // 30 minutes timeout

          // Configure fetch with extended timeout for streaming
          // Node.js fetch uses undici which has a default body timeout
          // We need to ensure the connection stays active
          const streamHeaders: Record<string, string> = {
            'Connection': 'keep-alive',
            'Authorization': `Bearer ${token}`,
          }
          
          // Forward cookies to backend (in case backend also checks cookies)
          if (cookieHeader) {
            streamHeaders['Cookie'] = cookieHeader
          }
          
          // Inject job_id as first event so frontend can capture it
          const jobIdEvent = `data: ${JSON.stringify({
            type: 'job_started',
            job_id: jobId,
            message: 'Job started'
          })}\n\n`
          safeEnqueue(encoder.encode(jobIdEvent))
          
          console.log('Stream request headers:', {
            'Authorization': `Bearer ${token.substring(0, 20)}...`,
            'Cookie': cookieHeader ? 'present' : 'missing',
          })
          
          const fetchOptions: RequestInit & { 
            // Node.js undici-specific options
            bodyTimeout?: number
            headersTimeout?: number
            keepalive?: boolean
          } = {
            method: 'GET',
            headers: streamHeaders,
            signal: abortController.signal,
          }

          // For Node.js, configure undici-specific timeout options
          // These are needed to prevent body timeout errors during long streaming
          if (typeof process !== 'undefined') {
            // @ts-ignore - Node.js undici-specific fetch options
            // Set body timeout to 30 minutes (1800000ms) to match our maxDuration
            // Note: These options may need to be set via undici directly in some cases
            fetchOptions.bodyTimeout = 30 * 60 * 1000 // 30 minutes (1800000ms)
            fetchOptions.headersTimeout = 30 * 60 * 1000 // 30 minutes
            fetchOptions.keepalive = true
            // Also try setting via dispatcher if available
            // This is critical for preventing UND_ERR_BODY_TIMEOUT errors
            // Note: undici is available as a dependency, but may not be accessible in all build contexts
            try {
              // Try require first (works in CommonJS/Node.js contexts)
              // @ts-ignore - undici types
              const undici = require('undici')
              const { Agent, setGlobalDispatcher, getGlobalDispatcher } = undici
              
              // Create a custom agent with extended timeouts for streaming
              const customAgent = new Agent({
                bodyTimeout: 30 * 60 * 1000, // 30 minutes - critical for long streams
                headersTimeout: 30 * 60 * 1000, // 30 minutes
                connectTimeout: 60000, // 1 minute connection timeout
              })
              
              // Set as dispatcher for this fetch call
              // @ts-ignore
              fetchOptions.dispatcher = customAgent
              
              // Also set global dispatcher temporarily (will be used by fetch)
              const originalDispatcher = getGlobalDispatcher()
              setGlobalDispatcher(customAgent)
              
              // Store restore function for cleanup
              // @ts-ignore
              fetchOptions._restoreDispatcher = () => {
                if (originalDispatcher) {
                  setGlobalDispatcher(originalDispatcher)
                }
              }
            } catch (e) {
              // undici not available or already configured, continue with fetchOptions only
              // This is not critical - fetchOptions.bodyTimeout should be sufficient
              // Node.js 18+ fetch already uses undici internally, so these options should work
              // The error is expected in some build contexts and can be safely ignored
              if (process.env.NODE_ENV === 'development') {
                console.debug('Could not configure undici dispatcher, using fetchOptions only:', e instanceof Error ? e.message : String(e))
              }
            }
          }

          let response: Response
          try {
            console.log('Fetching stream from:', getApiUrl(`v1/content/jobs/${jobId}/stream`))
            response = await fetch(getApiUrl(`v1/content/jobs/${jobId}/stream`), fetchOptions)
          } catch (fetchError: any) {
            // Handle fetch errors (network errors, connection refused, socket closed, etc.)
            clearTimeout(timeoutId)
            // Restore original dispatcher if we changed it
            // @ts-ignore
            if (fetchOptions._restoreDispatcher) {
              // @ts-ignore
              fetchOptions._restoreDispatcher()
            }
            
            console.error('Fetch error (before response):', {
              name: fetchError?.name,
              message: fetchError?.message,
              cause: fetchError?.cause,
              code: fetchError?.code,
              stack: fetchError?.stack
            })
            
            // Check if it's a socket/connection error
            const errorMsg = fetchError?.message || 'Unknown fetch error'
            const errorCause = fetchError?.cause
            const errorCode = errorCause && typeof errorCause === 'object' && 'code' in errorCause ? errorCause.code : fetchError?.code
            
            const isConnectionError = errorMsg.includes('terminated') ||
              errorMsg.includes('SocketError') ||
              errorMsg.includes('other side closed') ||
              errorCode === 'UND_ERR_SOCKET' ||
              fetchError?.name === 'TypeError' ||
              errorMsg.includes('fetch failed')
            
            if (isConnectionError) {
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ 
                  type: 'error', 
                  message: 'Failed to connect to backend server. The connection was closed before streaming could start.',
                  error_code: 'CONNECTION_FAILED',
                  error_type: 'SocketError',
                  hint: 'This usually means: 1) Backend server is not running or crashed, 2) Network connectivity issue, 3) Backend rejected the connection. Check Railway backend service logs and ensure the backend is healthy and accessible.'
                })}\n\n`)
              )
            } else {
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ 
                  type: 'error', 
                  message: `Connection error: ${errorMsg}`,
                  error_code: 'FETCH_ERROR',
                  error_type: fetchError?.name || 'UnknownError',
                  hint: 'Check network connectivity and ensure backend server is accessible.'
                })}\n\n`)
              )
            }
            safeClose()
            return
          } finally {
            // Only clear timeout if fetch succeeded (if it failed, we already cleared it)
            if (response) {
              clearTimeout(timeoutId)
            }
            // Restore original dispatcher if we changed it
            // @ts-ignore
            if (fetchOptions._restoreDispatcher) {
              // @ts-ignore
              fetchOptions._restoreDispatcher()
            }
          }

          // Log stream response details
          console.log('Stream response received:', {
            ok: response.ok,
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries()),
            hasBody: !!response.body
          })

          if (!response.ok) {
            const errorText = await response.text()
            console.error('Stream response not OK:', errorText)
            safeEnqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'error', message: errorText })}\n\n`)
            )
            safeClose()
            return
          }

          const reader = response.body?.getReader()
          const decoder = new TextDecoder()

          if (!reader) {
            console.error('No reader available - response body is null')
            safeEnqueue(
              encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'No response body' })}\n\n`)
            )
            safeClose()
            return
          }

          console.log('Stream reader obtained, starting to read chunks...')
          
          // Read stream with timeout handling and keep-alive
          const readStream = async () => {
            let keepAliveInterval: NodeJS.Timeout | null = null
            try {
              let lastActivity = Date.now()
              // Send keep-alive more frequently (every 5 seconds) to prevent undici body timeout
              // This ensures the connection stays active even during long pauses in content generation
              // Backend also sends keep-alive every 5 seconds, so this is a backup
              keepAliveInterval = setInterval(() => {
                // Only send keep-alive if controller is still open
                if (!controllerClosed) {
                  try {
                    safeEnqueue(encoder.encode(': keep-alive\n\n'))
                    lastActivity = Date.now()
                  } catch (e) {
                    // Controller closed, clear interval
                    if (keepAliveInterval) {
                      clearInterval(keepAliveInterval)
                      keepAliveInterval = null
                    }
                  }
                } else {
                  // Controller closed, clear interval
                  if (keepAliveInterval) {
                    clearInterval(keepAliveInterval)
                    keepAliveInterval = null
                  }
                }
              }, 5000) // Every 5 seconds - very frequent to prevent timeout

              try {
                let chunkCount = 0
                while (true) {
                  const { done, value } = await reader.read()
                  
                  if (done) {
                    console.log('Stream ended (done=true), total chunks received:', chunkCount)
                    if (keepAliveInterval) {
                      clearInterval(keepAliveInterval)
                      keepAliveInterval = null
                    }
                    safeClose()
                    break
                  }

                  chunkCount++
                  // Log ALL chunks for first 10, then every 10th chunk to catch initial events
                  if (chunkCount <= 10 || chunkCount % 10 === 0) {
                    console.log(`Stream chunk #${chunkCount} read:`, {
                      done: false,
                      valueLength: value?.length,
                      preview: value ? decoder.decode(value.slice(0, Math.min(200, value.length)), { stream: true }) : 'null'
                    })
                  }

                  // Update last activity time
                  lastActivity = Date.now()

                  // Forward the SSE data to the client
                  const chunk = decoder.decode(value, { stream: true })
                  // Log ALL chunks for first 10, then every 10th chunk
                  if (chunkCount <= 10 || chunkCount % 10 === 0) {
                    console.log(`Decoded chunk #${chunkCount} (full content):`, chunk)
                    // Also check if this chunk contains data events
                    if (chunk.includes('data: ')) {
                      console.log(`✓ Chunk #${chunkCount} contains data event!`)
                    }
                    if (chunk.includes('event: ')) {
                      console.log(`✓ Chunk #${chunkCount} contains event type!`)
                    }
                  }
                  safeEnqueue(encoder.encode(chunk))
                }
              } finally {
                // Ensure interval is cleared
                if (keepAliveInterval) {
                  clearInterval(keepAliveInterval)
                  keepAliveInterval = null
                }
              }
            } catch (readError) {
              // Ensure interval is cleared on error
              if (keepAliveInterval) {
                clearInterval(keepAliveInterval)
                keepAliveInterval = null
              }
              
              if (readError instanceof Error && readError.name === 'AbortError') {
                safeEnqueue(
                  encoder.encode(`data: ${JSON.stringify({ 
                    type: 'error', 
                    message: 'Request timeout - content generation took too long (30 minutes)' 
                  })}\n\n`)
                )
                safeClose()
              } else {
                throw readError
              }
            }
          }
          
          await readStream()
        } catch (error) {
          console.error('Streaming error:', error)
          const errorMessage = error instanceof Error ? error.message : 'Unknown error'
          const errorCause = error instanceof Error && error.cause ? error.cause : null
          console.error('Error name:', error instanceof Error ? error.name : 'Unknown')
          console.error('Error details:', errorMessage)
          console.error('Error cause:', errorCause)
          console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace')
          
          // Log additional details for socket errors
          if (errorCause && typeof errorCause === 'object' && 'code' in errorCause && errorCause.code === 'UND_ERR_SOCKET') {
            console.error('Socket error details:', {
              code: errorCause.code,
              socket: errorCause.socket,
              message: errorCause.message
            })
          }
          
          // Check error types
          const errorCode = errorCause && typeof errorCause === 'object' && 'code' in errorCause ? errorCause.code : null
          const isTimeoutError = errorMessage.includes('UND_ERR_BODY_TIMEOUT') || 
              errorMessage.includes('Body Timeout') ||
              errorMessage.includes('body timeout') ||
              errorMessage.includes('BodyTimeoutError') ||
              errorMessage.includes('timeout') ||
              errorCode === 'UND_ERR_BODY_TIMEOUT'
          
          const isSocketError = errorMessage.includes('terminated') ||
              errorMessage.includes('SocketError') ||
              errorMessage.includes('other side closed') ||
              errorCode === 'UND_ERR_SOCKET' ||
              (errorCause && typeof errorCause === 'object' && 
               'code' in errorCause && 
               errorCause.code === 'UND_ERR_SOCKET')
          
          // Use safe enqueue/close functions (they're in scope from the start function)
          try {
            if (isTimeoutError) {
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ 
                  type: 'error', 
                  message: 'Stream timeout - content generation is taking longer than expected. The connection timed out while waiting for data. Please try again with a shorter topic or check the FastAPI server logs.',
                  error_code: 'STREAM_TIMEOUT',
                  hint: 'This usually happens when content generation takes more than 5 minutes without sending data. Try breaking your topic into smaller parts.'
                })}\n\n`)
              )
            } else if (isSocketError) {
              // Socket closed - backend likely closed the connection
              // This often happens when OPENAI_API_KEY is missing or LLM initialization fails
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ 
                  type: 'error', 
                  message: 'Connection closed by server. The backend closed the connection, which usually indicates an error during content generation.',
                  error_code: 'STREAM_CLOSED',
                  hint: 'Common causes: Missing OPENAI_API_KEY in backend environment, LLM initialization failure, or backend crash. Check Railway backend service variables and ensure OPENAI_API_KEY is set (not in frontend .env).'
                })}\n\n`)
              )
            } else {
              safeEnqueue(
                encoder.encode(`data: ${JSON.stringify({ 
                  type: 'error', 
                  message: errorMessage,
                  error_code: 'STREAM_ERROR',
                  error_details: errorCode ? { code: errorCode } : undefined
                })}\n\n`)
              )
            }
            safeClose()
          } catch (finalError) {
            // If safe functions fail, controller is likely already closed
            console.log('Failed to send error message to client (controller may be closed):', finalError instanceof Error ? finalError.message : String(finalError))
          }
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

