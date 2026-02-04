'use client'

import { useState, useEffect, useRef } from 'react'
import { getApiUrl } from '@/lib/env'
import ProgressiveAudioPlayer from './ProgressiveAudioPlayer'

interface AudioPanelProps {
  output: string
  isLoading: boolean
  error: string | null
  status: string
  progress: number
  jobId: number | null
}

export default function AudioPanel({ output, isLoading, error, status, progress, jobId }: AudioPanelProps) {
  const showProgress = isLoading && progress > 0 && progress < 100;
  
  // Voiceover/TTS state
  const [isGeneratingVoiceover, setIsGeneratingVoiceover] = useState(false)
  const [voiceoverError, setVoiceoverError] = useState<string | null>(null)
  const [voiceoverStatus, setVoiceoverStatus] = useState<string>('')
  const [voiceoverProgress, setVoiceoverProgress] = useState<number>(0)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [audioMetadata, setAudioMetadata] = useState<any>(null)
  const [voiceoverJobId, setVoiceoverJobId] = useState<number | null>(null)
  
  // Track voiceover stream resources for cancellation
  const [voiceoverReaderRef, setVoiceoverReaderRef] = useState<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const [voiceoverAbortControllerRef, setVoiceoverAbortControllerRef] = useState<AbortController | null>(null)
  
  // FIX 3: Track timeout for fallback completion
  const artifactReadyTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const progressTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Function to generate voiceover
  const handleGenerateVoiceover = async () => {
    if (!jobId && !output) {
      setVoiceoverError('No audio script available. Please generate audio content first.')
      return
    }

    setIsGeneratingVoiceover(true)
    setVoiceoverError(null)
    setVoiceoverStatus('Starting voiceover generation...')
    setVoiceoverProgress(5) // Start at 5% to show progress bar immediately
    setAudioUrl(null)

    try {
      // Get auth token from localStorage (same as generate flow)
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      console.log('AudioPanel - Token from localStorage:', token ? `Found (length: ${token.length})` : 'Not found')
      
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
        console.log('AudioPanel - Authorization header set')
      } else {
        console.error('AudioPanel - No token found in localStorage!')
        setVoiceoverError('Authentication token not found. Please log in again.')
        setIsGeneratingVoiceover(false)
        return
      }

      const requestBody = {
        job_id: jobId || undefined,
        narration_text: jobId ? undefined : output, // Use narration_text if no job_id
        voice_id: 'default',
        speed: 1.0,
        format: 'wav'
      }
      
      console.log('AudioPanel - Calling /api/voiceover:', {
        hasJobId: !!jobId,
        jobId: jobId,
        hasNarrationText: !!requestBody.narration_text,
        narrationTextLength: requestBody.narration_text?.length || 0,
        voiceId: requestBody.voice_id
      })

      // Call voiceover API
      const response = await fetch('/api/voiceover', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(requestBody),
      })
      
      console.log('AudioPanel - Voiceover API response:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorData: any = {}
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Unknown error' }
        }
        
        // Log full error details for debugging
        const errorDetails = {
          status: response.status,
          statusText: response.statusText,
          error: errorData.error,
          detail: errorData.detail,
          hint: errorData.hint,
          fullResponse: errorText,
          errorData: errorData
        }
        console.error('AudioPanel - Voiceover API error (full details):', JSON.stringify(errorDetails, null, 2))
        console.error('AudioPanel - Voiceover API error (object):', errorDetails)
        
        // Build detailed error message
        let errorMessage = errorData.error || errorData.detail || `Failed to start voiceover generation (${response.status})`
        if (errorData.detail && errorData.detail !== errorMessage && typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        }
        if (errorData.hint) {
          errorMessage += `\n\nHint: ${errorData.hint}`
        }
        
        // If we have a detail object (FastAPI error format), extract the message
        if (errorData.detail && typeof errorData.detail === 'object') {
          if (errorData.detail.message) {
            errorMessage = errorData.detail.message
          } else if (errorData.detail.detail) {
            errorMessage = errorData.detail.detail
          }
        }
        
        throw new Error(errorMessage)
      }

      const result = await response.json()
      const newVoiceoverJobId = result.job_id

      if (!newVoiceoverJobId) {
        throw new Error('No job ID returned from voiceover API')
      }

      // Store job ID for cancellation
      setVoiceoverJobId(newVoiceoverJobId)

      // Stream TTS progress via SSE
      await streamVoiceoverProgress(newVoiceoverJobId)

    } catch (err) {
      console.error('Voiceover generation error:', err)
      setVoiceoverError(err instanceof Error ? err.message : 'Failed to generate voiceover')
      setIsGeneratingVoiceover(false)
      setVoiceoverStatus('')
    }
  }

  // Stream voiceover progress via SSE
  const streamVoiceoverProgress = async (voiceoverJobId: number) => {
    // Clean up any existing stream before starting new one
    if (voiceoverReaderRef) {
      try {
        await voiceoverReaderRef.cancel().catch(() => {})
        voiceoverReaderRef.releaseLock()
      } catch (e) {
        console.log('Error cleaning up previous voiceover reader:', e)
      }
      setVoiceoverReaderRef(null)
    }
    
    if (voiceoverAbortControllerRef) {
      voiceoverAbortControllerRef.abort()
      setVoiceoverAbortControllerRef(null)
    }

    // Create new abort controller for this stream
    const abortController = new AbortController()
    setVoiceoverAbortControllerRef(abortController)

    try {
      // Use Next.js API proxy route instead of direct backend connection
      // This avoids CORS issues and provides better error handling
      const streamUrl = `/api/jobs/${voiceoverJobId}/stream`

      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      const headers: HeadersInit = {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      console.log('AudioPanel - Starting SSE stream for voiceover job:', voiceoverJobId, 'URL:', streamUrl)

      let response: Response
      try {
        // Add connection timeout (10 seconds) to detect connection issues early
        const connectionTimeoutId = setTimeout(() => {
          if (!response) {
            console.error('AudioPanel - Connection timeout after 10s, aborting fetch')
            abortController.abort()
          }
        }, 10000)

        response = await fetch(streamUrl, {
          method: 'GET',
          headers,
          credentials: 'include',
          signal: abortController.signal,
        })
        
        clearTimeout(connectionTimeoutId)
      } catch (fetchError: any) {
        // Handle network errors (CORS, connection refused, timeout, etc.)
        console.error('AudioPanel - Fetch error (network/CORS/timeout):', fetchError)
        const errorMessage = fetchError.message || 'Network error'
        const isNetworkError = errorMessage.includes('network') || 
                              errorMessage.includes('Failed to fetch') ||
                              errorMessage.includes('CORS') ||
                              errorMessage.includes('timeout') ||
                              errorMessage.includes('aborted') ||
                              fetchError.name === 'TypeError' ||
                              fetchError.name === 'AbortError'
        
        if (isNetworkError) {
          const detailedError = errorMessage.includes('timeout') || errorMessage.includes('aborted')
            ? `Connection timeout or aborted. The voiceover service may be slow to respond. Please try again.`
            : `Network error connecting to voiceover stream. ` +
              `Please check: 1) Backend is running and accessible, ` +
              `2) Network connectivity, ` +
              `3) Try refreshing the page. ` +
              `URL: ${streamUrl}. ` +
              `Original error: ${errorMessage}`
          throw new Error(detailedError)
        }
        throw fetchError
      }

      console.log('AudioPanel - SSE stream response:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('AudioPanel - SSE stream failed:', response.status, errorText)
        let errorMessage = `Failed to stream voiceover progress: ${response.status} ${response.statusText}`
        try {
          const errorData = JSON.parse(errorText)
          if (errorData.error || errorData.detail) {
            errorMessage += ` - ${errorData.error || errorData.detail}`
          }
        } catch {
          if (errorText) {
            errorMessage += ` - ${errorText.substring(0, 200)}`
          }
        }
        throw new Error(errorMessage)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body reader available')
      }

      // Store reader reference for cancellation
      setVoiceoverReaderRef(reader)

      const decoder = new TextDecoder()
      let buffer = ''
      let eventCount = 0

      console.log('AudioPanel - Starting to read SSE stream...')

      // FIX 3: Set timeout fallback to advance progress if no events received within 3 seconds
      // Increased timeout to account for proxy route connection time
      // This prevents progress from being stuck at 5% if events are delayed
      if (progressTimeoutRef.current) {
        clearTimeout(progressTimeoutRef.current)
      }
      progressTimeoutRef.current = setTimeout(() => {
        if (voiceoverProgress === 5 && isGeneratingVoiceover) {
          console.warn('AudioPanel - No progress events received within 3s, advancing to 10%')
          setVoiceoverStatus('Connecting to voiceover service...')
          setVoiceoverProgress(10)
        }
        progressTimeoutRef.current = null
      }, 3000) // Increased from 2s to 3s to account for proxy connection time

      while (true) {
        // Check if we should stop (abort signal)
        if (abortController.signal.aborted) {
          console.log('AudioPanel - Stream aborted, stopping read loop')
          break
        }

        const { done, value } = await reader.read()
        
        // Handle abort errors gracefully
        if (done && abortController.signal.aborted) {
          console.log('AudioPanel - Stream ended due to abort')
          break
        }
        
        if (done) {
          console.log('AudioPanel - SSE stream ended, total events received:', eventCount)
          // If stream ended without completion, check if we should wait or error
          if (isGeneratingVoiceover && voiceoverProgress < 100) {
            console.warn('AudioPanel - Stream ended but voiceover not complete, progress:', voiceoverProgress)
            // Don't error immediately - might be a keep-alive timeout
          }
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk

        // Process complete SSE messages (SSE format: "event: <type>\ndata: {...}\n\n")
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || '' // Keep incomplete message in buffer

        for (const part of parts) {
          if (!part.trim()) continue
          
          // Skip keep-alive messages
          if (part.trim() === ': keep-alive' || part.trim().startsWith(': ')) {
            continue
          }

          // Parse SSE message (can have multiple lines: event, id, data)
          const lines = part.split('\n')
          let eventType: string | null = null
          let eventData: string | null = null

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6).trim()
            }
          }

          if (eventData) {
            try {
              const data = JSON.parse(eventData)
              eventCount++
              console.log(`AudioPanel - SSE event #${eventCount}:`, {
                event_type: eventType || 'default',
                data_type: data.type,
                full_data: data
              })

              // FIX 3: Clear progress timeout when events are received
              if (progressTimeoutRef.current) {
                clearTimeout(progressTimeoutRef.current)
                progressTimeoutRef.current = null
              }

              // FIX 3: Clear progress timeout when events are received
              if (progressTimeoutRef.current) {
                clearTimeout(progressTimeoutRef.current)
                progressTimeoutRef.current = null
              }

              // Handle events by both data.type and eventType (SSE event line)
              if (data.type === 'tts_started' || eventType === 'tts_started') {
                setVoiceoverStatus('TTS generation started...')
                setVoiceoverProgress(10)
              } else if (data.type === 'tts_progress' || eventType === 'tts_progress') {
                setVoiceoverStatus(data.message || 'Generating voiceover...')
                // FIX: Only update progress if new progress is higher than current (prevent backward jumps)
                const newProgress = data.progress || 20
                setVoiceoverProgress(prevProgress => Math.max(prevProgress, newProgress))
              } else if (data.type === 'artifact_ready' && data.artifact_type === 'voiceover_audio') {
                setVoiceoverStatus('Voiceover ready!')
                setVoiceoverProgress(90)
                // Check both metadata.storage_url and url fields
                const audioUrl = data.metadata?.storage_url || data.metadata?.url || data.url
                if (audioUrl) {
                  console.log('AudioPanel - Setting audio URL:', audioUrl)
                  setAudioUrl(audioUrl)
                  setAudioMetadata(data.metadata || {})
                  
                  // FIX 3: Set timeout fallback to complete progress if tts_completed doesn't arrive
                  // Clear any existing timeout
                  if (artifactReadyTimeoutRef.current) {
                    clearTimeout(artifactReadyTimeoutRef.current)
                  }
                  // Set new timeout (2 seconds)
                  artifactReadyTimeoutRef.current = setTimeout(() => {
                    // Only complete if still at 90% and still generating
                    if (voiceoverProgress === 90 && isGeneratingVoiceover) {
                      console.warn('AudioPanel - tts_completed event not received within 2s, completing progress automatically')
                      setVoiceoverStatus('Voiceover generation complete!')
                      setVoiceoverProgress(100)
                      setIsGeneratingVoiceover(false)
                    }
                    artifactReadyTimeoutRef.current = null
                  }, 2000)
                } else {
                  console.warn('AudioPanel - artifact_ready event missing audio URL:', data)
                }
              } else if (data.type === 'tts_completed') {
                // FIX 3: Clear timeout since tts_completed arrived
                if (artifactReadyTimeoutRef.current) {
                  clearTimeout(artifactReadyTimeoutRef.current)
                  artifactReadyTimeoutRef.current = null
                }
                
                setVoiceoverStatus('Voiceover generation complete!')
                setVoiceoverProgress(100)
                setIsGeneratingVoiceover(false)
                const audioUrl = data.storage_url || data.url || data.metadata?.storage_url
                if (audioUrl) {
                  console.log('AudioPanel - Setting audio URL from tts_completed:', audioUrl)
                  setAudioUrl(audioUrl)
                }
              } else if (data.type === 'tts_failed') {
                throw new Error(data.message || 'TTS generation failed')
              } else if (data.type === 'error') {
                throw new Error(data.message || data.detail || 'Voiceover generation error')
              } else {
                // Log unhandled event types for debugging
                console.log('AudioPanel - Unhandled SSE event type:', data.type, data)
              }
            } catch (e) {
              console.error('AudioPanel - Error parsing SSE data:', e, 'Raw data:', eventData)
            }
          }
        }
      }
      
      // FIX 3: Clean up progress timeout when stream ends
      if (progressTimeoutRef.current) {
        clearTimeout(progressTimeoutRef.current)
        progressTimeoutRef.current = null
      }
    } catch (err) {
      // Handle abort errors gracefully (user cancelled)
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('AudioPanel - Voiceover stream aborted by user')
        setVoiceoverStatus('Voiceover generation cancelled')
        // Don't set error, just stop generating
        setIsGeneratingVoiceover(false)
        // Preserve progress and status for potential restart
      } else {
        console.error('AudioPanel - Streaming error:', err)
        const errorMessage = err instanceof Error 
          ? err.message 
          : typeof err === 'string' 
            ? err 
            : 'Failed to stream voiceover progress'
        
        // Provide more helpful error messages
        let displayError = errorMessage
        if (errorMessage.includes('Network error') || errorMessage.includes('Failed to fetch')) {
          displayError = `Cannot connect to voiceover service. Please check your connection and ensure the backend is running. ${errorMessage}`
        }
        
        setVoiceoverError(displayError)
        setIsGeneratingVoiceover(false)
        setVoiceoverStatus('')
        setVoiceoverProgress(0)
      }
    } finally {
      // FIX 3: Clean up timeout on stream end
      if (artifactReadyTimeoutRef.current) {
        clearTimeout(artifactReadyTimeoutRef.current)
        artifactReadyTimeoutRef.current = null
      }
      
      // Clean up references
      setVoiceoverReaderRef(null)
      setVoiceoverAbortControllerRef(null)
    }
  }

  // Stop voiceover generation
  const handleStopVoiceover = async () => {
    console.log('AudioPanel - Stop voiceover button clicked')
    
    try {
      // Abort the fetch request if active
      if (voiceoverAbortControllerRef) {
        console.log('AudioPanel - Aborting voiceover fetch request...')
        voiceoverAbortControllerRef.abort()
      }

      // Cancel and release the stream reader if active
      if (voiceoverReaderRef) {
        try {
          console.log('AudioPanel - Cancelling voiceover stream reader...')
          await voiceoverReaderRef.cancel().catch(() => {})
        } catch (e) {
          console.log('AudioPanel - Reader already closed or cancelled:', e)
        }
        
        try {
          console.log('AudioPanel - Releasing voiceover reader lock...')
          voiceoverReaderRef.releaseLock()
        } catch (e) {
          console.log('AudioPanel - Reader lock already released:', e)
        }
        setVoiceoverReaderRef(null)
      }

      // Call cancel endpoint on backend if we have a job ID
      if (voiceoverJobId) {
        try {
          const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
          const cancelUrl = `${apiUrl}/v1/content/jobs/${voiceoverJobId}/cancel`
          
          const headers: HeadersInit = {}
          if (token) {
            headers['Authorization'] = `Bearer ${token}`
          }

          console.log('AudioPanel - Calling cancel endpoint for job:', voiceoverJobId)
          
          // Don't wait for this - just fire and forget
          fetch(cancelUrl, {
            method: 'POST',
            headers,
            credentials: 'include',
          }).catch((cancelError) => {
            console.warn('AudioPanel - Cancel endpoint call failed (non-critical):', cancelError)
          })
        } catch (cancelError) {
          console.warn('AudioPanel - Error calling cancel endpoint (non-critical):', cancelError)
        }
      }

      // Update UI state - preserve progress and status
      setIsGeneratingVoiceover(false)
      setVoiceoverStatus('Voiceover generation cancelled')
      // Don't reset progress or error - preserve state for potential restart
      
      // Clean up references
      setVoiceoverAbortControllerRef(null)
      
      console.log('AudioPanel - Voiceover stopped successfully')
    } catch (err) {
      console.error('AudioPanel - Error stopping voiceover:', err)
      // Still update UI even if cleanup fails
      setIsGeneratingVoiceover(false)
      setVoiceoverStatus('Voiceover generation stopped')
      setVoiceoverAbortControllerRef(null)
      setVoiceoverReaderRef(null)
    }
  }

  // Cleanup audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrl && audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [audioUrl])

  // Cleanup voiceover stream on unmount only
  // Use refs to track current values without triggering cleanup on every change
  const voiceoverReaderRefForCleanup = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const voiceoverAbortControllerRefForCleanup = useRef<AbortController | null>(null)
  
  // Update refs when state changes (for cleanup access)
  useEffect(() => {
    voiceoverReaderRefForCleanup.current = voiceoverReaderRef
  }, [voiceoverReaderRef])
  
  useEffect(() => {
    voiceoverAbortControllerRefForCleanup.current = voiceoverAbortControllerRef
  }, [voiceoverAbortControllerRef])
  
  // Only run cleanup on unmount
  useEffect(() => {
    return () => {
      // Clean up voiceover stream resources when component unmounts
      if (voiceoverReaderRefForCleanup.current) {
        voiceoverReaderRefForCleanup.current.cancel().catch(() => {})
        try {
          voiceoverReaderRefForCleanup.current.releaseLock()
        } catch (e) {
          // Ignore errors during cleanup
        }
      }
      if (voiceoverAbortControllerRefForCleanup.current) {
        voiceoverAbortControllerRefForCleanup.current.abort()
      }
    }
  }, []) // Empty dependency array - only runs on unmount

  return (
    <div className="glass-effect neon-border rounded-2xl p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gradient mb-2">Audio Output</h2>
        <p className="text-gray-200 text-sm">
          AI-generated audio content will appear here
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-neon-purple rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
            </div>
            <p className="text-neon-cyan animate-pulse">{status || 'Generating audio content...'}</p>
            {showProgress && (
              <div className="w-full max-w-xs bg-gray-700 rounded-full h-2.5 mt-2">
                <div className="bg-neon-purple h-2.5 rounded-full" style={{ width: `${progress}%` }}></div>
              </div>
            )}
            {output && (
              <div className="mt-4 bg-dark-card rounded-lg p-4 border border-dark-border max-h-48 overflow-y-auto w-full max-w-md">
                <p className="text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap break-words">
                  {output}
                </p>
                <p className="text-xs text-gray-300 mt-2 text-right">Live Preview ({output.length} chars)</p>
              </div>
            )}
            {!output && (
              <p className="text-xs text-gray-300 text-center max-w-xs">
                Our AI crew is creating audio content
              </p>
            )}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4 p-4">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-red-400 font-medium">Error</p>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 max-w-md">
              <p className="text-sm text-red-300 text-center break-words">{error}</p>
            </div>
            <p className="text-xs text-gray-300 text-center mt-2">
              Check the browser console for more details
            </p>
          </div>
        ) : output ? (
          <div className="prose prose-invert max-w-none">
            <div className="bg-dark-card rounded-lg p-6 border border-dark-border mb-4">
              <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                {output}
              </div>
              <p className="text-xs text-gray-300 mt-2 text-right">Total Length: {output.length} chars</p>
            </div>
            
            {/* Voiceover Section */}
            {(isGeneratingVoiceover || audioUrl || voiceoverError) && (
              <div className="bg-dark-card rounded-lg p-4 border border-dark-border mb-4">
                <h3 className="text-lg font-semibold text-gradient mb-3">Voiceover (TTS)</h3>
                
                {isGeneratingVoiceover && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
                      <p className="text-neon-cyan flex-1">{voiceoverStatus || 'Generating voiceover...'}</p>
                      <button
                        onClick={handleStopVoiceover}
                        className="px-3 py-1.5 bg-red-500/20 border border-red-500/50 rounded-lg 
                                   text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium
                                   flex items-center gap-2"
                        title="Stop voiceover generation"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Stop
                      </button>
                    </div>
                    {/* Progress bar with percentage */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-300">Progress</span>
                        <span className="text-neon-cyan font-semibold">{voiceoverProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-neon-cyan to-neon-purple h-3 rounded-full transition-all duration-300 ease-out flex items-center justify-end pr-2"
                          style={{ width: `${Math.max(voiceoverProgress, 5)}%` }}
                        >
                          {voiceoverProgress >= 15 && (
                            <span className="text-xs text-white font-medium">{voiceoverProgress}%</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {voiceoverError && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-3">
                    <p className="text-sm text-red-300">{voiceoverError}</p>
                  </div>
                )}
                
                {audioUrl && !isGeneratingVoiceover && (
                  <div className="space-y-3">
                    {/* Progressive audio player with buffering support */}
                    <ProgressiveAudioPlayer 
                      audioUrl={audioUrl}
                      onError={(error) => {
                        console.error('ProgressiveAudioPlayer error:', error)
                        setVoiceoverError(error)
                      }}
                      className="w-full"
                    />
                    {audioMetadata && (
                      <div className="text-xs text-gray-400 space-y-1">
                        {audioMetadata.duration_sec && (
                          <p>Duration: {audioMetadata.duration_sec.toFixed(1)}s</p>
                        )}
                        {audioMetadata.voice_id && (
                          <p>Voice: {audioMetadata.voice_id}</p>
                        )}
                      </div>
                    )}
                    <a
                      href={audioUrl}
                      download="voiceover.wav"
                      className="inline-block px-4 py-2 bg-neon-cyan/20 border border-neon-cyan/50 rounded-lg 
                                 text-neon-cyan hover:bg-neon-cyan/30 transition-colors text-sm"
                    >
                      Download Audio
                    </a>
                  </div>
                )}
              </div>
            )}
            
            <div className="mt-4 flex flex-wrap gap-4">
              <button
                onClick={async (event) => {
                  try {
                    await navigator.clipboard.writeText(output)
                    const btn = event.target as HTMLButtonElement
                    const originalText = btn.textContent
                    btn.textContent = 'Copied!'
                    setTimeout(() => {
                      btn.textContent = originalText
                    }, 2000)
                  } catch (err) {
                    console.error('Failed to copy:', err)
                  }
                }}
                className="px-4 py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg 
                           text-neon-purple hover:bg-neon-purple/30 transition-colors text-sm"
              >
                Copy to Clipboard
              </button>
              <button
                onClick={() => {
                  const blob = new Blob([output], { type: 'text/plain' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'audio_output.txt'
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="px-4 py-2 bg-neon-cyan/20 border border-neon-cyan/50 rounded-lg 
                           text-neon-cyan hover:bg-neon-cyan/30 transition-colors text-sm"
              >
                Download Script
              </button>
              {(jobId || output) && !isGeneratingVoiceover && (
                <button
                  onClick={handleGenerateVoiceover}
                  disabled={isGeneratingVoiceover}
                  className="px-4 py-2 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg 
                             text-white hover:opacity-90 transition-opacity text-sm font-semibold
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {audioUrl ? '🔄 Regenerate Voiceover' : '🎙️ Generate Voiceover'}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 
                          flex items-center justify-center border border-neon-cyan/30">
              <svg className="w-12 h-12 text-neon-cyan/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                      d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <p className="text-gray-300">No audio content generated yet</p>
            <p className="text-xs text-gray-200">Enter a topic and click generate to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

