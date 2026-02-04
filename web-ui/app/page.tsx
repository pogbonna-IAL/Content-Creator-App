'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Navbar from '@/components/Navbar'
import EmailVerificationBanner from '@/components/EmailVerificationBanner'
import InputPanel from '@/components/InputPanel'
import OutputPanel from '@/components/OutputPanel'
import SocialMediaPanel from '@/components/SocialMediaPanel'
import AudioPanel from '@/components/AudioPanel'
import VideoPanel from '@/components/VideoPanel'
import Footer from '@/components/Footer'

// Force dynamic rendering (no static generation) to prevent React Context errors
export const dynamic = 'force-dynamic'

export default function Home() {
  // ALL hooks must be called at the top, before any conditional returns
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [isMounted, setIsMounted] = useState(false)
  
  // State hooks - must be called unconditionally
  const [selectedFeature, setSelectedFeature] = useState<string>('blog')
  const [output, setOutput] = useState<string>('')
  const [socialMediaOutput, setSocialMediaOutput] = useState<string>('')
  const [audioOutput, setAudioOutput] = useState<string>('')
  const [videoOutput, setVideoOutput] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [currentJobId, setCurrentJobId] = useState<number | null>(null) // Track current job ID for voiceover generation
  // OPTIMIZATION #12: Quality metrics state for blog content
  const [qualityMetrics, setQualityMetrics] = useState<{word_count?: number, char_count?: number, reading_time_minutes?: number, estimated_reading_time?: string} | undefined>(undefined)

  // Track reader and job ID for cancellation - MUST be declared before any conditional returns
  const [readerRef, setReaderRef] = useState<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const [abortControllerRef, setAbortControllerRef] = useState<AbortController | null>(null)
  
  // Track output state for final validation (to check if content was set)
  const outputRef = useRef(output)
  const audioOutputRef = useRef(audioOutput)
  
  // Update refs when state changes
  useEffect(() => {
    outputRef.current = output
  }, [output])
  
  useEffect(() => {
    audioOutputRef.current = audioOutput
  }, [audioOutput])

  // Prevent hydration mismatch by only rendering conditionally after mount
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // REMOVED: Redirect to /auth - now show marketing page instead

  // Conditional returns AFTER all hooks
  // Show loading spinner while auth is being verified or before mount (prevents hydration mismatch)
  if (!isMounted || authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
      </div>
    )
  }

  // Show marketing page if user is not authenticated (only after loading is complete)
  // This ensures we don't show marketing page while auth is still being verified
  if (!user && !authLoading) {
    return (
      <main className="min-h-screen flex flex-col">
        <Navbar selectedFeature={selectedFeature} onFeatureSelect={setSelectedFeature} />
        <div className="flex-1">
          {/* Hero Section */}
          <section className="container mx-auto px-4 py-16 md:py-24 text-center">
            <div className="max-w-4xl mx-auto">
              <h1 className="text-5xl md:text-6xl font-bold text-gradient mb-6">
                AI-Powered Content Creation
              </h1>
              <p className="text-xl md:text-2xl text-gray-300 mb-8">
                Create professional blog posts, social media content, audio, and videos with the power of AI
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={() => router.push('/auth')}
                  className="px-8 py-3 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-cyan/50 transition-all"
                >
                  Get Started
                </button>
                <button
                  onClick={() => router.push('/auth')}
                  className="px-8 py-3 border-2 border-neon-cyan rounded-lg font-semibold hover:bg-neon-cyan/10 transition-all"
                >
                  Sign In
                </button>
              </div>
            </div>
          </section>

          {/* Features Section */}
          <section className="container mx-auto px-4 py-16">
            <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 text-gradient">
              Everything You Need to Create Amazing Content
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-effect neon-border rounded-lg p-6">
                <div className="text-4xl mb-4">📝</div>
                <h3 className="text-xl font-bold mb-2">Blog Posts</h3>
                <p className="text-gray-200">Generate comprehensive blog articles on any topic</p>
              </div>
              <div className="glass-effect neon-border rounded-lg p-6">
                <div className="text-4xl mb-4">📱</div>
                <h3 className="text-xl font-bold mb-2">Social Media</h3>
                <p className="text-gray-200">Create engaging posts for all social platforms</p>
              </div>
              <div className="glass-effect neon-border rounded-lg p-6">
                <div className="text-4xl mb-4">🎙️</div>
                <h3 className="text-xl font-bold mb-2">Audio Content</h3>
                <p className="text-gray-200">Generate voiceovers and audio content</p>
              </div>
              <div className="glass-effect neon-border rounded-lg p-6">
                <div className="text-4xl mb-4">🎬</div>
                <h3 className="text-xl font-bold mb-2">Video Content</h3>
                <p className="text-gray-200">Create video scripts and content</p>
              </div>
            </div>
          </section>

          {/* CTA Section */}
          <section className="container mx-auto px-4 py-16">
            <div className="glass-effect neon-border rounded-2xl p-12 text-center max-w-3xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold mb-4 text-gradient">
                Ready to Start Creating?
              </h2>
              <p className="text-xl text-gray-300 mb-8">
                Join thousands of creators using AI to streamline their content workflow
              </p>
              <button
                onClick={() => router.push('/auth')}
                className="px-10 py-4 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg font-semibold text-lg hover:shadow-lg hover:shadow-neon-cyan/50 transition-all"
              >
                Create Your Account
              </button>
            </div>
          </section>
        </div>
        <Footer />
      </main>
    )
  }

  const handleStop = async () => {
    console.log('Stop button clicked - cleaning up...')
    
    try {
      // First, abort the fetch request if active (this will stop the stream)
      if (abortControllerRef) {
        console.log('Aborting fetch request...')
        abortControllerRef.abort()
      }

      // Cancel and release the stream reader if active
      if (readerRef) {
        try {
          console.log('Cancelling stream reader...')
          await readerRef.cancel()
        } catch (e) {
          console.log('Reader already closed or cancelled:', e)
        }
        
        try {
          console.log('Releasing reader lock...')
          readerRef.releaseLock()
        } catch (e) {
          console.log('Reader lock already released:', e)
        }
      }

      // Call cancel endpoint if we have a job ID
      if (currentJobId) {
        try {
          const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
          const headers: HeadersInit = {
            'Content-Type': 'application/json',
          }
          if (token) {
            headers['Authorization'] = `Bearer ${token}`
          }

          const response = await fetch(`/api/jobs/${currentJobId}/cancel`, {
            method: 'POST',
            headers,
            credentials: 'include',
          })

          if (response.ok) {
            console.log('Job cancelled successfully on server')
          } else {
            const errorData = await response.json().catch(() => ({ error: 'Failed to cancel job' }))
            console.warn('Failed to cancel job on server:', errorData)
            // Don't set error here - we've already stopped the stream locally
          }
        } catch (err) {
          console.warn('Error calling cancel endpoint:', err)
          // Don't set error here - we've already stopped the stream locally
        }
      }

      // Clean up all state and references
      setStatus('Generation cancelled')
      setIsGenerating(false)
      setProgress(0)
      setReaderRef(null)
      setAbortControllerRef(null)
      setCurrentJobId(null)
      
      console.log('Stop cleanup complete - ready for new generation')
    } catch (err) {
      console.error('Error during stop cleanup:', err)
      // Even if there's an error, reset state so user can try again
      setIsGenerating(false)
      setStatus('Generation stopped')
      setProgress(0)
      setReaderRef(null)
      setAbortControllerRef(null)
      setCurrentJobId(null)
    }
  }

  const handleGenerate = async (topic: string) => {
    // Clean up any existing stream/reader before starting new generation
    if (readerRef) {
      try {
        await readerRef.cancel().catch(() => {})
        readerRef.releaseLock() // releaseLock() returns void, not a Promise
      } catch (e) {
        console.log('Error cleaning up previous reader:', e)
      }
      setReaderRef(null)
    }
    
    if (abortControllerRef) {
      abortControllerRef.abort()
      setAbortControllerRef(null)
    }

    // Reset all state for new generation
    setIsGenerating(true)
    setError(null)
    setOutput('')
    setSocialMediaOutput('')
    setAudioOutput('')
    setVideoOutput('')
    setStatus('')
    setProgress(0)
    setCurrentJobId(null)

    // Create abort controller for this request
    const abortController = new AbortController()
    setAbortControllerRef(abortController)

    // Track if we should stop reading and the reader instance
    let shouldStop = false
    let stopReason: string | null = null // Track why we're stopping
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
    
    // Track if component is still mounted to prevent state updates after unmount
    let isMounted = true

    try {
      console.log('Sending streaming request for topic:', topic)
      
      // Call the streaming API endpoint
      // Include Authorization header for cross-subdomain auth
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      // Map selectedFeature to content_types array
      // selectedFeature can be: 'blog', 'social', 'audio', 'video'
      const contentTypes = selectedFeature === 'blog' ? ['blog'] :
                          selectedFeature === 'social' ? ['social'] :
                          selectedFeature === 'audio' ? ['audio'] :
                          selectedFeature === 'video' ? ['video'] :
                          ['blog'] // Default to blog if unknown
      
      console.log('Sending request with content_types:', contentTypes, 'selectedFeature:', selectedFeature)
      
      let response: Response
      try {
        response = await fetch('/api/generate', {
          method: 'POST',
          headers,
          credentials: 'include', // Include cookies as fallback
          body: JSON.stringify({ topic, content_types: contentTypes }),
          signal: abortController.signal,
        })
      } catch (fetchError) {
        // Handle abort errors gracefully (user cancelled)
        if (fetchError instanceof Error && fetchError.name === 'AbortError') {
          console.log('Request aborted by user')
          setIsGenerating(false)
          setStatus('Generation cancelled')
          setProgress(0)
          setReaderRef(null)
          setAbortControllerRef(null)
          return // Exit gracefully without throwing error
        }
        
        // Handle network-level errors (connection refused, DNS failure, etc.)
        console.error('Fetch network error:', fetchError)
        if (fetchError instanceof TypeError) {
          // TypeError usually means network error (connection refused, CORS, etc.)
          const networkErrorMsg = fetchError.message.includes('network') 
            ? fetchError.message 
            : `Network error: ${fetchError.message}`
          throw new Error(`Cannot connect to server: ${networkErrorMsg}. Please ensure the API server is running and try again.`)
        }
        throw fetchError
      }

      if (!response.ok) {
        // Handle authentication errors specifically
        if (response.status === 401) {
          const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }))
          const errorMessage = errorData.detail || errorData.error || 'Authentication failed. Please log in again.'
          console.error('Authentication error:', errorMessage)
          // Redirect to auth page - the AuthContext will handle logout
          router.push('/auth')
          throw new Error(errorMessage)
        }
        
        // Handle other errors - try to parse detailed error message
        let errorData: any = { error: 'Unknown error' }
        try {
          const errorText = await response.text()
          try {
            errorData = JSON.parse(errorText)
          } catch {
            // If not JSON, use the text as the error detail
            errorData = { error: 'Failed to generate content', detail: errorText }
          }
        } catch (e) {
          console.error('Error parsing error response:', e)
          errorData = { error: 'Failed to generate content', detail: `HTTP ${response.status}: ${response.statusText}` }
        }
        
        // Build comprehensive error message
        let errorMessage = errorData.error || 'Failed to generate content'
        if (errorData.detail && errorData.detail !== errorMessage) {
          errorMessage = `${errorMessage}: ${errorData.detail}`
        }
        if (errorData.hint) {
          errorMessage = `${errorMessage}\n\nHint: ${errorData.hint}`
        }
        
        console.error('Generation request failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData.error,
          detail: errorData.detail,
          hint: errorData.hint
        })
        
        throw new Error(errorMessage)
      }

      if (!response.body) {
        throw new Error('No response body received')
      }

      // Set up streaming reader
      reader = response.body.getReader()
      setReaderRef(reader) // Store reader reference for cancellation
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedContent = ''
      let accumulatedAudioContent = '' // Track audio content separately during streaming

      console.log('Starting to read stream...')
      
      let chunkCount = 0
      let receivedCompleteEvent = false

      while (true) {
        // Check if we should stop before reading next chunk
        if (shouldStop) {
          console.log(`Stopping stream reading: ${stopReason || 'unknown reason'}`)
          break
        }
        
        const { done, value } = await reader.read()
        chunkCount++
        
        if (chunkCount % 10 === 0 || done) {
          console.log(`Stream chunk #${chunkCount} read: { done: ${done}, valueLength: ${value?.length || 0}, preview: ${value ? decoder.decode(value.slice(0, 50), { stream: true }).replace(/\n/g, '\\n') : 'null'} }`)
        }
        
        if (done) {
          console.log(`Stream ended (done=true), total chunks received: ${chunkCount}`)
          console.log('Final buffer length:', buffer.length)
          console.log('Received complete event:', receivedCompleteEvent)
          console.log('Accumulated content length:', accumulatedContent.length)
          console.log('Accumulated audio content length:', accumulatedAudioContent.length)
          
          // Process any remaining buffer - try multiple times to catch late-arriving data
          let bufferProcessed = false
          const maxBufferProcessAttempts = 3
          
          for (let attempt = 0; attempt < maxBufferProcessAttempts; attempt++) {
            if (buffer.trim()) {
              const lines = buffer.split('\n')
              for (const line of lines) {
                // Skip keep-alive and empty lines
                if (!line.trim() || line.trim() === ': keep-alive' || (line.startsWith(':') && line.trim() !== ':')) {
                  continue
                }
                
                if (line.startsWith('data: ')) {
                  try {
                    const jsonStr = line.slice(6).trim()
                    if (!jsonStr) continue
                    const data = JSON.parse(jsonStr)
                    console.log(`Final buffer data (attempt ${attempt + 1}):`, data.type, data)
                    
                    if (data.type === 'complete') {
                      receivedCompleteEvent = true
                      bufferProcessed = true
                      if (data.content) {
                        accumulatedContent = data.content
                        setOutput(accumulatedContent)
                      }
                      if (data.audio_content) {
                        accumulatedAudioContent = data.audio_content
                        setAudioOutput(accumulatedAudioContent)
                      }
                      if (data.social_media_content) {
                        setSocialMediaOutput(data.social_media_content)
                      }
                      if (data.video_content) {
                        setVideoOutput(data.video_content)
                      }
                      setProgress(100)
                      setStatus('Content generation complete!')
                      setIsGenerating(false)
                    } else if (data.type === 'error') {
                      // Handle error in final buffer
                      bufferProcessed = true
                      // Safely extract error message - handle both string and object cases
                      let errorMsg: string = 'Unknown error occurred'
                      if (data.message) {
                        errorMsg = typeof data.message === 'string' ? data.message : JSON.stringify(data.message)
                      } else if (data.detail) {
                        errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
                      } else if (data.error) {
                        errorMsg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error)
                      }
                      
                      let displayError = `Content generation failed: ${errorMsg}`
                      if (data.error_type) {
                        displayError += `\n\nError Type: ${data.error_type}`
                      }
                      if (data.hint) {
                        const hintText = typeof data.hint === 'string' ? data.hint : JSON.stringify(data.hint)
                        displayError += `\n\nHint: ${hintText}`
                      }
                      setError(displayError)
                      setIsGenerating(false)
                      setStatus('Generation failed')
                      setProgress(0)
                    } else if (data.type === 'content' && data.chunk) {
                      // Process content chunks in final buffer
                      bufferProcessed = true
                      // Enhanced content type detection with audio-specific checks
                      let contentType = data.artifact_type || 
                                      (data.content_field === 'audio_content' ? 'audio' :
                                       data.content_field === 'social_media_content' ? 'social' :
                                       data.content_field === 'video_content' ? 'video' :
                                       data.content_type) || 'blog'
                      
                      // Additional check: detect audio content by structure (intro_hook, main_sections)
                      if (contentType === 'blog' && data.chunk) {
                        const chunkStr = String(data.chunk).toLowerCase()
                        if ((chunkStr.includes('intro_hook') || chunkStr.includes('main_sections') || 
                             chunkStr.includes('pacing_notes')) && 
                            (chunkStr.includes('audio') || chunkStr.includes('podcast') || chunkStr.includes('narration'))) {
                          contentType = 'audio'
                        }
                      }
                      
                      if (contentType === 'audio') {
                        accumulatedAudioContent += data.chunk
                        setAudioOutput(accumulatedAudioContent)
                      } else if (contentType === 'social') {
                        setSocialMediaOutput(data.chunk)
                      } else if (contentType === 'video') {
                        setVideoOutput(data.chunk)
                      } else {
                        accumulatedContent += data.chunk
                        setOutput(accumulatedContent)
                      }
                    }
                  } catch (e) {
                    console.error('Error parsing final buffer:', e, 'Line:', line.substring(0, 100))
                  }
                }
              }
            }
            
            // If we processed something, break early
            if (bufferProcessed) {
              break
            }
            
            // Wait a bit before next attempt (only if not last attempt)
            if (attempt < maxBufferProcessAttempts - 1) {
              await new Promise(resolve => setTimeout(resolve, 100)) // 100ms delay
              // Re-read buffer in case more data arrived
              buffer = buffer // Keep existing buffer, but allow for potential new data
            }
          }
          
          // Final check: Wait a bit more for any late-arriving complete events
          // This handles race conditions where the stream closes before the complete event is fully sent
          if (!receivedCompleteEvent && !accumulatedContent && !accumulatedAudioContent && !error) {
            console.log('Waiting for potential late-arriving content events...')
            // Give it a short delay to catch any final events
            await new Promise(resolve => setTimeout(resolve, 500))
            
            // Re-check state after delay
            // Note: We can't re-read the stream, but state might have been updated by React
            // Check if content was set during the delay (via state updates)
            const finalCheck = await new Promise<boolean>((resolve) => {
              setTimeout(() => {
                // Check current state values
                // Since we can't access state directly here, we'll rely on the error check below
                resolve(false)
              }, 100)
            })
          }
          
          // Final validation: Check if we have any content
          // Use refs to get latest state values, as state updates might be pending
          const currentOutput = outputRef.current
          const currentAudioOutput = audioOutputRef.current
          const hasAnyContent = accumulatedContent.trim().length > 0 || 
                               accumulatedAudioContent.trim().length > 0 ||
                               currentOutput.trim().length > 0 ||
                               currentAudioOutput.trim().length > 0
          
          // If stream ended but we have no content and no error, show a message
          if (!receivedCompleteEvent && !hasAnyContent && !error) {
            console.warn('Stream ended but no complete event and no content received')
            console.warn('Buffer preview:', buffer.substring(0, 500))
            console.warn('State check - output:', output.length, 'audioOutput:', audioOutput.length)
            setError('No content received from stream. The content may have been generated but not properly streamed. Check browser console and server logs for details.')
            setIsGenerating(false)
            setStatus('Generation incomplete')
          } else if (receivedCompleteEvent || hasAnyContent) {
            // Stream ended with complete event or content - ensure spinner is stopped and status is set
            setIsGenerating(false)
            setProgress(100)
            if (!status || status === '' || status.includes('Streaming')) {
              setStatus('Content generation complete!')
            }
            console.log('✓ Stream ended successfully, spinner stopped')
          }
          
          break
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true })
        
        // Skip keep-alive messages (they're just heartbeat, not actual data)
        if (chunk.trim() === ': keep-alive' || chunk.trim().startsWith(': ')) {
          // This is a keep-alive heartbeat, ignore it and continue reading
          continue
        }
        
        // Log first 10 chunks fully, then periodically
        const chunkNum = (buffer.match(/\n\n/g) || []).length + 1
        if (chunkNum <= 10 || chunkNum % 10 === 0) {
          console.log(`Frontend received chunk #${chunkNum}:`, chunk.substring(0, 100))
          if (chunk.includes('data: ')) {
            console.log(`✓ Frontend chunk #${chunkNum} contains data event!`)
          }
          if (chunk.includes('event: ')) {
            console.log(`✓ Frontend chunk #${chunkNum} contains event type!`)
          }
        }
        buffer += chunk
        
        // Process complete SSE messages (SSE format: "data: {...}\n\n")
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || '' // Keep incomplete message in buffer

        for (const part of parts) {
          if (!part.trim()) continue
          
          // Handle multiple data lines in one part
          const lines = part.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const jsonStr = line.slice(6).trim()
                if (!jsonStr) continue
                
                const data = JSON.parse(jsonStr)
                console.log('Parsed SSE data:', data.type, data)
                
                if (data.type === 'status' || data.type === 'status_update') {
                  // Update status message
                  const statusMessage = data.content_type_display 
                    ? `Generating ${data.content_type_display}...`
                    : data.message || 'Processing...'
                  setStatus(statusMessage)
                  console.log('Status:', statusMessage, 'Content Type:', data.content_type_display || data.content_type)
                  
                  // If content type is specified, log it for user visibility
                  if (data.content_type_display) {
                    console.log(`✓ Content type notification: ${data.content_type_display}`)
                  }
                } else if (data.type === 'job_started') {
                  // Handle job_started event with content type notification
                  if (data.job_id) {
                    setCurrentJobId(data.job_id)
                    console.log(`✓ Job ID captured: ${data.job_id}`)
                  }
                  if (data.content_type_display) {
                    setStatus(`Starting ${data.content_type_display} generation...`)
                    console.log(`✓ Job started - Content type: ${data.content_type_display}`)
                  } else if (data.message) {
                    setStatus(data.message)
                  }
                } else if (data.type === 'content_preview') {
                  // OPTIMIZATION #8: Handle content preview events for optimistic updates
                  // Display preview immediately after extraction (before validation)
                  if (data.preview) {
                    const previewContent = data.preview
                    const artifactType = data.artifact_type || 'blog'
                    
                    if (artifactType === 'blog') {
                      // Show preview immediately, will be replaced with full content later
                      setOutput(previewContent + '...')
                      setStatus(data.message || 'Content extracted, validating...')
                      setProgress(85) // Preview is at ~85% progress
                      console.log(`✓ Content preview received (${previewContent.length} chars), total expected: ${data.total_length || 'unknown'}`)
                    }
                  }
                } else if (data.type === 'artifact_ready') {
                  // OPTIMIZATION #12: Capture quality metrics from artifact_ready events
                  if (data.artifact_type === 'blog' && data.quality_metrics && isMounted) {
                    setQualityMetrics(data.quality_metrics)
                    console.log('✓ Quality metrics received:', data.quality_metrics)
                  }
                } else if (data.type === 'content') {
                  // Append chunk to accumulated content based on content type
                  if (data.chunk) {
                    // Check artifact_type first (from artifact_ready events), then content_field, then content_type
                    const contentType = data.artifact_type || 
                                      (data.content_field === 'audio_content' ? 'audio' :
                                       data.content_field === 'social_media_content' ? 'social' :
                                       data.content_field === 'video_content' ? 'video' :
                                       data.content_type) || 'blog' // Default to blog if not specified
                    
                    console.log(`Content event received:`, {
                      artifact_type: data.artifact_type,
                      content_field: data.content_field,
                      content_type: data.content_type,
                      resolved_content_type: contentType,
                      chunk_length: data.chunk?.length || 0
                    })
                    
                    // Route to appropriate content accumulator based on content type
                    if (contentType === 'audio') {
                      // For audio content, accumulate separately and update audio output
                      accumulatedAudioContent += data.chunk
                      setAudioOutput(accumulatedAudioContent)
                      setProgress(data.progress || 0)
                      setStatus(`Streaming audio content... ${data.progress || 0}%`)
                      console.log(`✓ Received audio chunk, total length: ${accumulatedAudioContent.length}, progress: ${data.progress}%`)
                    } else if (contentType === 'social') {
                      // For social media content
                      setSocialMediaOutput(data.chunk) // Social content is usually sent complete
                      setProgress(data.progress || 0)
                      setStatus(`Social media content received`)
                      console.log(`✓ Received social media content, length: ${data.chunk.length}`)
                    } else if (contentType === 'video') {
                      // For video content
                      setVideoOutput(data.chunk) // Video content is usually sent complete
                      setProgress(data.progress || 0)
                      setStatus(`Video content received`)
                      console.log(`✓ Received video content, length: ${data.chunk.length}`)
                    } else {
                      // Default to blog content
                      accumulatedContent += data.chunk
                      setOutput(accumulatedContent)
                      setProgress(data.progress || 0)
                      setStatus(`Streaming content... ${data.progress || 0}%`)
                      console.log(`✓ Received blog chunk, total length: ${accumulatedContent.length}, progress: ${data.progress}%`)
                    }
                  }
                } else if (data.type === 'complete') {
                  // Mark that we received the complete event
                  receivedCompleteEvent = true
                  console.log('✓ Complete event received:', {
                    hasContent: !!data.content,
                    contentLength: data.content?.length || 0,
                    hasAudio: !!data.audio_content,
                    audioLength: data.audio_content?.length || 0,
                    hasSocial: !!data.social_media_content,
                    hasVideo: !!data.video_content
                  })
                  
                  // Final content received - ALWAYS use this as it contains the complete content
                  const finalContent = data.content || ''
                  const socialMediaContent = data.social_media_content || ''
                  // Use audio_content from completion message, or fallback to accumulated audio content
                  const audioContent = data.audio_content || accumulatedAudioContent || ''
                  const videoContent = data.video_content || ''
                  
                  // Capture job_id if present in completion event
                  if (data.job_id && isMounted) {
                    setCurrentJobId(data.job_id)
                    console.log(`✓ Job ID from completion: ${data.job_id}`)
                  }
                  
                  // CRITICAL: Stop the spinner immediately when complete event is received
                  if (isMounted) {
                    setIsGenerating(false)
                    setProgress(100)
                  }
                  
                  // Determine what content types were generated
                  const hasBlogContent = (finalContent && finalContent.trim().length > 0) || 
                                       (accumulatedContent && accumulatedContent.trim().length > 0)
                  const hasSocialContent = socialMediaContent && socialMediaContent.trim().length > 0
                  const hasAudioContent = audioContent && audioContent.trim().length > 0
                  const hasVideoContent = videoContent && videoContent.trim().length > 0
                  
                  console.log('Complete event received:', {
                    hasBlogContent,
                    hasSocialContent,
                    hasAudioContent,
                    hasVideoContent,
                    audioContentLength: audioContent.length,
                    finalContentLength: finalContent.length,
                    accumulatedContentLength: accumulatedContent.length
                  })
                  
                  // Set blog content if available (only if component is still mounted)
                  if (isMounted) {
                    if (finalContent && finalContent.trim().length > 0) {
                      accumulatedContent = finalContent
                      setOutput(accumulatedContent)
                      console.log('✓ Blog content received, length:', accumulatedContent.length)
                    } else if (accumulatedContent && accumulatedContent.trim().length > 0) {
                      setOutput(accumulatedContent)
                      console.log('✓ Blog content from accumulated, length:', accumulatedContent.length)
                    }
                    
                    // Set social media content if available
                    if (hasSocialContent) {
                      setSocialMediaOutput(socialMediaContent)
                      console.log('✓ Social media content received, length:', socialMediaContent.length)
                    }
                    
                    // Set audio content if available (ALWAYS set if present, even without blog content)
                    if (hasAudioContent) {
                      setAudioOutput(audioContent)
                      console.log('✓ Audio content received, length:', audioContent.length)
                      // If only audio content (no blog), update status accordingly
                      if (!hasBlogContent && !hasSocialContent && !hasVideoContent) {
                        setStatus('Audio content generation complete!')
                      }
                    }
                    
                    // Set video content if available
                    if (hasVideoContent) {
                      setVideoOutput(videoContent)
                      console.log('✓ Video content received, length:', videoContent.length)
                      // If only video content (no blog), update status accordingly
                      if (!hasBlogContent && !hasSocialContent && !hasAudioContent) {
                        setStatus('Video content generation complete!')
                      }
                    }
                    
                    // Set appropriate status message based on what was generated
                    if (hasBlogContent || hasSocialContent || hasAudioContent || hasVideoContent) {
                      if (!status || status === '') {
                        setStatus('Content generation complete!')
                      }
                    } else {
                      console.warn('No content received in completion event')
                      setStatus('Content generation completed but no content was received')
                    }
                  }
                  
                  // Mark that we should stop reading the stream since we're complete
                  shouldStop = true
                  stopReason = 'complete event received'
                  try {
                    reader.cancel()
                  } catch (cancelError) {
                    console.warn('Error canceling reader after completion:', cancelError)
                  }
                  
                  break // Exit the stream reading loop since we're done
                } else if (data.type === 'cancelled') {
                  // Handle cancellation event from server
                  setIsGenerating(false)
                  setStatus('Job cancelled')
                  setProgress(0)
                  console.log('Job cancelled:', data.message)
                  // Stop reading stream
                  shouldStop = true
                  stopReason = 'job cancelled by server'
                  if (reader) {
                    try {
                      await reader.cancel()
                    } catch (e) {
                      // Reader may already be closed
                    }
                  }
                  break
                } else if (data.type === 'error') {
                  // Handle error messages from the server - STOP IMMEDIATELY
                  // Safely extract error message - handle both string and object cases
                  let errorMsg: string = 'Unknown error occurred'
                  if (data.message) {
                    errorMsg = typeof data.message === 'string' ? data.message : JSON.stringify(data.message)
                  } else if (data.detail) {
                    errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
                  } else if (data.error) {
                    errorMsg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error)
                  }
                  
                  const errorType = data.error_type || data.error_code || 'unknown'
                  
                  // Log error message as string first for better console visibility
                  console.error('❌ Server error received - stopping immediately:', errorMsg)
                  console.error('Error details:', {
                    type: errorType,
                    job_id: data.job_id,
                    status: data.status,
                    full_data: data
                  })
                  
                  // ALWAYS stop on error - don't continue processing
                  setIsGenerating(false)
                  setStatus('Generation failed')
                  setProgress(0)
                  
                  // Build comprehensive error message
                  let displayError = `Content generation failed: ${errorMsg}`
                  if (data.error_type) {
                    displayError += `\n\nError Type: ${data.error_type}`
                  }
                  if (data.hint) {
                    const hintText = typeof data.hint === 'string' ? data.hint : JSON.stringify(data.hint)
                    displayError += `\n\nHint: ${hintText}`
                  }
                  
                  setError(displayError)
                  
                  // Mark that we should stop and cancel reader
                  shouldStop = true
                  stopReason = `server error: ${errorType}`
                  try {
                    reader.cancel()
                  } catch (cancelError) {
                    console.warn('Error canceling reader:', cancelError)
                  }
                  
                  break // Exit the stream reading loop immediately
                } else if (data.type === 'job_started' && data.status === 'failed') {
                  // Job started but immediately failed - STOP IMMEDIATELY
                  console.error('❌ Job started but status is failed - stopping immediately:', data)
                  
                  setIsGenerating(false)
                  setStatus('Generation failed')
                  setProgress(0)
                  
                  // Show error - backend should send error event with details, but if not, show generic message
                  setError('Content generation failed immediately. The job could not start. Please check:\n\n' +
                    '1. Backend logs for detailed error messages\n' +
                    '2. That OPENAI_API_KEY is set in backend environment\n' +
                    '3. That the LLM service is accessible')
                  
                  // Mark that we should stop and cancel reader
                  shouldStop = true
                  try {
                    reader.cancel()
                  } catch (cancelError) {
                    console.warn('Error canceling reader:', cancelError)
                  }
                  
                  break // Exit the stream reading loop immediately
                } else if (data.type === 'status_update' && data.status === 'failed') {
                  // Status update showing failed - STOP IMMEDIATELY
                  console.error('❌ Status update shows failed - stopping immediately:', data)
                  
                  setIsGenerating(false)
                  setStatus('Generation failed')
                  setProgress(0)
                  
                  setError(`Content generation failed. Status: ${data.status}\n\n` +
                    (data.message ? `Error: ${data.message}` : 'Check backend logs for details.'))
                  
                  // Mark that we should stop and cancel reader
                  shouldStop = true
                  try {
                    reader.cancel()
                  } catch (cancelError) {
                    console.warn('Error canceling reader:', cancelError)
                  }
                  
                  break // Exit the stream reading loop immediately
                }
              } catch (parseError) {
                // Only log parse errors if they're not "terminated" errors
                // "terminated" is a normal error message from the server
                if (parseError instanceof Error) {
                  if (parseError.message === 'terminated') {
                    // This is likely a connection termination - handle gracefully
                    console.warn('Stream terminated - connection closed')
                    setIsGenerating(false)
                    if (!accumulatedContent || accumulatedContent.trim().length < 10) {
                      setError('Connection terminated. Please try again.')
                      setStatus('Connection closed')
                      setProgress(0)
                    }
                    shouldStop = true
                    stopReason = 'connection terminated'
                    try {
                      reader?.cancel()
                    } catch (cancelError) {
                      console.warn('Error canceling reader:', cancelError)
                    }
                    break
                  } else {
                    // Real parse error - log it but don't break the stream
                    console.error('Error parsing SSE data:', parseError)
                    console.error('Line that failed:', line)
                  }
                } else {
                  console.error('Error parsing SSE data:', parseError)
                  console.error('Line that failed:', line)
                }
                // Continue processing other messages - don't break on parse errors
              }
            } else if (line.trim() && !line.startsWith(':')) {
              // Log non-data lines for debugging (but skip keep-alive)
              if (line.trim() !== ': keep-alive') {
                console.log('Non-data line:', line)
              }
            } else if (line.trim() === ': keep-alive' || line.startsWith(': ')) {
              // Skip keep-alive heartbeat messages silently
              continue
            }
          }
        }
      }

      // Ensure reader is released and cleaned up
      if (reader) {
        try {
          reader.releaseLock()
        } catch (releaseError) {
          console.warn('Error releasing reader:', releaseError)
        }
      }
      
      // Clean up references
      setReaderRef(null)
      setAbortControllerRef(null)

      // Ensure final content is set - prioritize completion message content
      console.log('Stream reading completed', shouldStop ? `(${stopReason || 'stopped'})` : '(normal completion)')
      console.log('Final accumulatedContent length:', accumulatedContent.length)
      console.log('Final accumulatedAudioContent length:', accumulatedAudioContent.length)
      
      // Wait a bit for any late-arriving state updates (React state updates are async)
      // This handles race conditions where the stream closes before React state is fully updated
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // Check current state values using refs (which track the latest state)
      const currentOutput = outputRef.current
      const currentAudioOutput = audioOutputRef.current
      const hasBlogContent = (accumulatedContent && accumulatedContent.trim().length > 0) || 
                            (currentOutput && currentOutput.trim().length > 0)
      const hasAudioContent = (accumulatedAudioContent && accumulatedAudioContent.trim().length > 0) ||
                             (currentAudioOutput && currentAudioOutput.trim().length > 0)
      const hasAnyContent = hasBlogContent || hasAudioContent || 
                           (socialMediaOutput && socialMediaOutput.trim().length > 0) ||
                           (videoOutput && videoOutput.trim().length > 0)
      
      console.log('Final content check:', {
        hasBlogContent,
        hasAudioContent,
        hasAnyContent,
        accumulatedContentLength: accumulatedContent.length,
        currentOutputLength: currentOutput.length,
        accumulatedAudioLength: accumulatedAudioContent.length,
        currentAudioLength: currentAudioOutput.length
      })
      
      if (hasBlogContent) {
        // Final check - ensure we have the complete content
        if (accumulatedContent && accumulatedContent.trim().length > 0) {
          setOutput(accumulatedContent)
        }
        setProgress(100)
        setStatus('Content generation complete!')
        console.log('✓ Final output set, length:', accumulatedContent.length || currentOutput.length)
        console.log('Final content preview:', (accumulatedContent || currentOutput).substring(0, 300))
      }
      
      // Check if we have additional content in the final buffer
      if (buffer.trim()) {
        try {
          const lines = buffer.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'complete') {
                if (data.social_media_content) {
                  setSocialMediaOutput(data.social_media_content)
                  console.log('✓ Social media content found in final buffer')
                }
                if (data.audio_content) {
                  setAudioOutput(data.audio_content)
                  console.log('✓ Audio content found in final buffer')
                }
                if (data.video_content) {
                  setVideoOutput(data.video_content)
                  console.log('✓ Video content found in final buffer')
                }
                if (data.content && !hasBlogContent) {
                  setOutput(data.content)
                  console.log('✓ Blog content found in final buffer')
                }
              }
            }
          }
        } catch (e) {
          console.warn('Could not parse additional content from final buffer:', e)
        }
      }
      
      // Final validation: Only show error if we truly have no content
      if (!hasAnyContent && !error && !receivedCompleteEvent) {
        console.warn('⚠ No content accumulated after stream completion')
        console.warn('Buffer at end:', buffer.substring(0, 500))
        console.warn('State values:', {
          output: currentOutput.length,
          audioOutput: currentAudioOutput.length,
          socialMediaOutput: socialMediaOutput.length,
          videoOutput: videoOutput.length
        })
        setError('No content received from stream. The content may have been generated but not properly streamed. Check browser console and server logs for details.')
        setIsGenerating(false)
        setStatus('Generation incomplete')
      } else if (hasAnyContent || receivedCompleteEvent) {
        // Ensure spinner is stopped if we have content
        setIsGenerating(false)
        setProgress(100)
        if (!status || status === '' || status.includes('Streaming') || status.includes('incomplete')) {
          setStatus('Content generation complete!')
        }
        console.log('✓ Stream completed successfully with content')
      }
    } catch (err) {
      // Don't show error if it was aborted (user cancelled)
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Generation aborted by user')
        setIsGenerating(false)
        setStatus('Generation cancelled')
        setProgress(0)
        setReaderRef(null)
        setAbortControllerRef(null)
        return
      }
      
      console.error('Generation error:', err)
      
      // Provide more helpful error messages based on error type
      let errorMessage = 'An error occurred while generating content'
      
      if (err instanceof TypeError) {
        if (err.message.includes('network') || err.message.includes('fetch')) {
          errorMessage = 'Network error: Cannot connect to the server. Please check:\n' +
            '1. The API server is running\n' +
            '2. Your internet connection is active\n' +
            '3. Try refreshing the page and generating again'
        } else {
          errorMessage = `Connection error: ${err.message}`
        }
      } else if (err instanceof Error) {
        // Check for specific error messages
        if (err.message.includes('Failed to fetch')) {
          errorMessage = 'Cannot connect to the server. The API may be down or unreachable. Please try again later.'
        } else if (err.message.includes('timeout')) {
          errorMessage = 'Request timed out. The content generation is taking longer than expected. Please try again.'
        } else if (err.message.includes('Authentication')) {
          errorMessage = 'Authentication failed. Please log in again.'
          router.push('/auth')
        } else {
          errorMessage = err.message
        }
      } else {
        errorMessage = String(err)
      }
      
      if (isMounted) {
        setError(errorMessage)
        setOutput('') // Clear output on error
      }
    } finally {
      // Mark component as unmounted to prevent state updates
      isMounted = false
      // Always clean up references and reset generating state (only if still mounted)
      try {
        setIsGenerating(false)
        setReaderRef(null)
        setAbortControllerRef(null)
      } catch (e) {
        // Ignore errors if component has unmounted
        console.debug('Component unmounted during cleanup:', e)
      }
    }
  }

  const renderOutputPanel = () => {
    switch (selectedFeature) {
      case 'blog':
        return (
          <OutputPanel 
            output={output} 
            isLoading={isGenerating} 
            error={error} 
            status={status} 
            progress={progress}
            qualityMetrics={qualityMetrics}
          />
        )
      case 'social':
        return (
          <SocialMediaPanel 
            output={socialMediaOutput} 
            isLoading={isGenerating} 
            error={error} 
            status={status} 
            progress={progress} 
          />
        )
      case 'audio':
        return (
          <AudioPanel 
            output={audioOutput} 
            isLoading={isGenerating} 
            error={error} 
            status={status} 
            progress={progress}
            jobId={currentJobId}
          />
        )
      case 'video':
        return (
          <VideoPanel 
            output={videoOutput} 
            isLoading={isGenerating} 
            error={error} 
            status={status} 
            progress={progress}
            jobId={currentJobId}
          />
        )
      default:
        return (
          <OutputPanel 
            output={output} 
            isLoading={isGenerating} 
            error={error} 
            status={status} 
            progress={progress}
            qualityMetrics={qualityMetrics}
          />
        )
    }
  }

  return (
    <main className="min-h-screen flex flex-col">
      <Navbar selectedFeature={selectedFeature} onFeatureSelect={setSelectedFeature} />
      <EmailVerificationBanner />
      <div className="flex-1 container mx-auto px-4 py-4 sm:py-6 md:py-8 max-w-7xl">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 md:gap-8 mb-4 sm:mb-6 md:mb-8">
          <div className="order-1 lg:order-none">
            <InputPanel onGenerate={handleGenerate} onStop={handleStop} isLoading={isGenerating} />
          </div>
          <div className="order-2 lg:order-none">
            {renderOutputPanel()}
          </div>
        </div>
      </div>
      <Footer />
    </main>
  )
}

