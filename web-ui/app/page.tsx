'use client'

import { useState, useEffect } from 'react'
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

  // Track reader and job ID for cancellation - MUST be declared before any conditional returns
  const [readerRef, setReaderRef] = useState<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const [abortControllerRef, setAbortControllerRef] = useState<AbortController | null>(null)

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
    if (!currentJobId) {
      console.warn('No job ID available to cancel')
      return
    }

    try {
      // Cancel the stream reader if active
      if (readerRef) {
        try {
          await readerRef.cancel()
        } catch (e) {
          console.log('Reader already closed or cancelled')
        }
      }

      // Abort the fetch request if active
      if (abortControllerRef) {
        abortControllerRef.abort()
      }

      // Call cancel endpoint
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
        setStatus('Job cancelled')
        setIsGenerating(false)
        console.log('Job cancelled successfully')
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Failed to cancel job' }))
        console.error('Failed to cancel job:', errorData)
        setError(errorData.error || errorData.detail || 'Failed to cancel job')
      }
    } catch (err) {
      console.error('Error cancelling job:', err)
      setError(err instanceof Error ? err.message : 'Failed to cancel job')
    }
  }

  const handleGenerate = async (topic: string) => {
    setIsGenerating(true)
    setError(null)
    setOutput('')
    setSocialMediaOutput('')
    setAudioOutput('')
    setVideoOutput('')
    setStatus('')
    setProgress(0)
    setCurrentJobId(null) // Reset job ID for new generation

    // Create abort controller for this request
    const abortController = new AbortController()
    setAbortControllerRef(abortController)

    // Track if we should stop reading and the reader instance
    let shouldStop = false
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null

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
        
        // Handle other errors
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new Error(errorData.error || errorData.detail || 'Failed to generate content')
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

      while (true) {
        // Check if we should stop before reading next chunk
        if (shouldStop) {
          console.log('Stopping stream reading due to error')
          break
        }
        
        const { done, value } = await reader.read()
        
        if (done) {
          console.log('Stream completed, final buffer:', buffer)
          // Process any remaining buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.slice(6).trim()
                  if (!jsonStr) continue
                  const data = JSON.parse(jsonStr)
                  console.log('Final data:', data)
                  if (data.type === 'complete' && data.content) {
                    accumulatedContent = data.content
                    setOutput(accumulatedContent)
                    setProgress(100)
                    setStatus('Content generation complete!')
                    setIsGenerating(false) // Stop spinner when complete event is in final buffer
                  } else if (data.type === 'complete') {
                    // Complete event without content field - still stop spinner
                    setIsGenerating(false)
                    setProgress(100)
                    setStatus('Content generation complete!')
                  } else if (data.type === 'error') {
                    // Handle error in final buffer
                    const errorMsg = data.message || data.detail || 'Unknown error occurred'
                    let displayError = `Content generation failed: ${errorMsg}`
                    if (data.error_type) {
                      displayError += `\n\nError Type: ${data.error_type}`
                    }
                    if (data.hint) {
                      displayError += `\n\nHint: ${data.hint}`
                    }
                    setError(displayError)
                    setIsGenerating(false)
                    setStatus('Generation failed')
                    setProgress(0)
                  }
                } catch (e) {
                  console.error('Error parsing final buffer:', e)
                }
              }
            }
          }
          
          // If stream ended but we have no content and no error, show a message
          if (!accumulatedContent && !error) {
            console.warn('Stream ended but no content or error received')
            setError('Stream ended unexpectedly. No content was generated. This may indicate a timeout or server error. Please try again.')
            setIsGenerating(false)
            setStatus('Generation incomplete')
          } else if (accumulatedContent && !error) {
            // Stream ended with content - ensure spinner is stopped and status is set
            setIsGenerating(false)
            setProgress(100)
            if (!status || status === '' || status.includes('Streaming')) {
              setStatus('Content generation complete!')
            }
            console.log('✓ Stream ended with content, spinner stopped')
          }
          
          break
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true })
        // Log first 10 chunks fully, then periodically
        const chunkNum = (buffer.match(/\n\n/g) || []).length + 1
        if (chunkNum <= 10 || chunkNum % 10 === 0) {
          console.log(`Frontend received chunk #${chunkNum}:`, chunk)
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
                } else if (data.type === 'content') {
                  // Append chunk to accumulated content based on content type
                  if (data.chunk) {
                    const contentType = data.content_type || 'blog' // Default to blog if not specified
                    
                    // Route to appropriate content accumulator based on content type
                    if (contentType === 'audio') {
                      // For audio content, accumulate separately and update audio output
                      accumulatedAudioContent += data.chunk
                      setAudioOutput(accumulatedAudioContent)
                      setProgress(data.progress || 0)
                      setStatus(`Streaming audio content... ${data.progress || 0}%`)
                      console.log(`Received audio chunk, total length: ${accumulatedAudioContent.length}, progress: ${data.progress}%`)
                    } else {
                      // Default to blog content
                      accumulatedContent += data.chunk
                      setOutput(accumulatedContent)
                      setProgress(data.progress || 0)
                      setStatus(`Streaming content... ${data.progress || 0}%`)
                      console.log(`Received chunk, total length: ${accumulatedContent.length}, progress: ${data.progress}%`)
                    }
                  }
                } else if (data.type === 'complete') {
                  // Final content received - ALWAYS use this as it contains the complete content
                  const finalContent = data.content
                  const socialMediaContent = data.social_media_content || ''
                  // Use audio_content from completion message, or fallback to accumulated audio content
                  const audioContent = data.audio_content || accumulatedAudioContent || ''
                  const videoContent = data.video_content || ''
                  
                  // Capture job_id if present in completion event
                  if (data.job_id) {
                    setCurrentJobId(data.job_id)
                    console.log(`✓ Job ID from completion: ${data.job_id}`)
                  }
                  
                  // CRITICAL: Stop the spinner immediately when complete event is received
                  setIsGenerating(false)
                  
                  if (finalContent && finalContent.trim().length > 0) {
                    // Use the complete content from the completion message
                    accumulatedContent = finalContent
                    setOutput(accumulatedContent)
                    setProgress(100)
                    setStatus('Content generation complete!')
                    console.log('✓ Stream complete - using full content from completion message')
                    console.log('Final content length:', accumulatedContent.length)
                    console.log('Final content preview:', accumulatedContent.substring(0, 200))
                    
                    // Set social media content if available
                    if (socialMediaContent && socialMediaContent.trim().length > 0) {
                      setSocialMediaOutput(socialMediaContent)
                      console.log('✓ Social media content received, length:', socialMediaContent.length)
                    }
                    
                    // Set audio content if available (from completion message or accumulated)
                    if (audioContent && audioContent.trim().length > 0) {
                      setAudioOutput(audioContent)
                      console.log('✓ Audio content received, length:', audioContent.length)
                    }
                    
                    // Set video content if available
                    if (videoContent && videoContent.trim().length > 0) {
                      setVideoOutput(videoContent)
                      console.log('✓ Video content received, length:', videoContent.length)
                    }
                  } else if (accumulatedContent && accumulatedContent.trim().length > 0) {
                    // Fallback to accumulated content if completion message doesn't have content
                    console.warn('Completion message missing content, using accumulated content')
                    setOutput(accumulatedContent)
                    setProgress(100)
                    setStatus('Content generation complete!')
                    
                    // Set social media content if available
                    if (socialMediaContent && socialMediaContent.trim().length > 0) {
                      setSocialMediaOutput(socialMediaContent)
                    }
                    
                    // Set audio content if available (from completion message or accumulated)
                    if (audioContent && audioContent.trim().length > 0) {
                      setAudioOutput(audioContent)
                    }
                    
                    // Set video content if available
                    if (videoContent && videoContent.trim().length > 0) {
                      setVideoOutput(videoContent)
                    }
                  } else if (accumulatedAudioContent && accumulatedAudioContent.trim().length > 0) {
                    // If only audio content was streamed (no blog content)
                    console.log('Only audio content was generated')
                    setAudioOutput(accumulatedAudioContent)
                    setProgress(100)
                    setStatus('Audio content generation complete!')
                  } else {
                    console.error('No content in completion message and no accumulated content')
                    // Even if no content, stop the spinner
                    setStatus('Content generation completed but no content was received')
                  }
                  
                  // Mark that we should stop reading the stream since we're complete
                  shouldStop = true
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
                  const errorMsg = data.message || data.detail || 'Unknown error occurred'
                  const errorType = data.error_type || data.error_code || 'unknown'
                  
                  console.error('❌ Server error received - stopping immediately:', {
                    message: errorMsg,
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
                    displayError += `\n\nHint: ${data.hint}`
                  }
                  
                  setError(displayError)
                  
                  // Mark that we should stop and cancel reader
                  shouldStop = true
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
              // Log non-data lines for debugging
              console.log('Non-data line:', line)
            }
          }
        }
      }

      // Ensure reader is released
      if (reader) {
        try {
          reader.releaseLock()
        } catch (releaseError) {
          console.warn('Error releasing reader:', releaseError)
        }
      }

      // Ensure final content is set - prioritize completion message content
      console.log('Stream reading completed', shouldStop ? '(stopped due to error)' : '(normal completion)')
      console.log('Final accumulatedContent length:', accumulatedContent.length)
      
      if (accumulatedContent && accumulatedContent.trim().length > 0) {
        // Final check - ensure we have the complete content
        setOutput(accumulatedContent)
        setProgress(100)
        setStatus('Content generation complete!')
        console.log('✓ Final output set, length:', accumulatedContent.length)
        console.log('Final content preview:', accumulatedContent.substring(0, 300))
        
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
                }
              }
            }
          } catch (e) {
            console.warn('Could not parse additional content from final buffer:', e)
          }
        }
      } else {
        console.warn('⚠ No content accumulated after stream completion')
        console.warn('Buffer at end:', buffer.substring(0, 500))
        if (!error) {
          setError('No content received from stream. The content may have been generated but not properly streamed. Check browser console and server logs for details.')
        }
      }
    } catch (err) {
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
      
      setError(errorMessage)
      setOutput('') // Clear output on error
    } finally {
      setIsGenerating(false)
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

