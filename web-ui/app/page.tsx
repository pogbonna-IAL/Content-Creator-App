'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import Navbar from '@/components/Navbar'
import InputPanel from '@/components/InputPanel'
import OutputPanel from '@/components/OutputPanel'
import SocialMediaPanel from '@/components/SocialMediaPanel'
import AudioPanel from '@/components/AudioPanel'
import VideoPanel from '@/components/VideoPanel'
import Footer from '@/components/Footer'

export default function Home() {
  // ALL hooks must be called at the top, before any conditional returns
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  
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

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth')
    }
  }, [user, authLoading, router])

  // Conditional returns AFTER all hooks
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
      </div>
    )
  }

  if (!user) {
    return null
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

    try {
      console.log('Sending streaming request for topic:', topic)
      
      // Call the streaming API endpoint
      // Token is automatically included via cookies
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
        body: JSON.stringify({ topic }),
      })

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
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedContent = ''

      console.log('Starting to read stream...')

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          console.log('Stream completed, final buffer:', buffer)
          // Process any remaining buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  console.log('Final data:', data)
                  if (data.type === 'complete' && data.content) {
                    accumulatedContent = data.content
                    setOutput(accumulatedContent)
                    setProgress(100)
                    setStatus('Content generation complete!')
                  }
                } catch (e) {
                  console.error('Error parsing final buffer:', e)
                }
              }
            }
          }
          break
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true })
        console.log('Received chunk:', chunk.substring(0, 100))
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
                
                if (data.type === 'status') {
                  // Update status message
                  setStatus(data.message)
                  console.log('Status:', data.message)
                } else if (data.type === 'content') {
                  // Append chunk to accumulated content
                  if (data.chunk) {
                    accumulatedContent += data.chunk
                    // Update UI in real-time
                    setOutput(accumulatedContent)
                    setProgress(data.progress || 0)
                    setStatus(`Streaming content... ${data.progress || 0}%`)
                    console.log(`Received chunk, total length: ${accumulatedContent.length}, progress: ${data.progress}%`)
                  }
                } else if (data.type === 'complete') {
                  // Final content received - ALWAYS use this as it contains the complete content
                  const finalContent = data.content
                  const socialMediaContent = data.social_media_content || ''
                  const audioContent = data.audio_content || ''
                  const videoContent = data.video_content || ''
                  
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
                    
                    // Set audio content if available
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
                    
                    // Set audio content if available
                    if (audioContent && audioContent.trim().length > 0) {
                      setAudioOutput(audioContent)
                    }
                    
                    // Set video content if available
                    if (videoContent && videoContent.trim().length > 0) {
                      setVideoOutput(videoContent)
                    }
                  } else {
                    console.error('No content in completion message and no accumulated content')
                  }
                } else if (data.type === 'error') {
                  // Handle error messages from the server gracefully
                  const errorMsg = data.message || 'Unknown error'
                  console.error('Server error:', errorMsg)
                  
                  // Don't throw - set error state and stop processing
                  // If we have accumulated content, show it; otherwise show error
                  if (!accumulatedContent || accumulatedContent.trim().length < 10) {
                    setError(errorMsg)
                  } else {
                    // We have content, so just log the error but don't fail
                    console.warn('Error received but content was already generated:', errorMsg)
                  }
                  setIsGenerating(false)
                  return // Exit the stream reading loop
                }
              } catch (parseError) {
                // Only log parse errors if they're not "terminated" errors
                // "terminated" is a normal error message from the server
                if (parseError instanceof Error) {
                  if (parseError.message === 'terminated') {
                    // This is likely a connection termination - handle gracefully
                    console.warn('Stream terminated - connection closed')
                    if (!accumulatedContent || accumulatedContent.trim().length < 10) {
                      setError('Connection terminated. Please try again.')
                    }
                    setIsGenerating(false)
                    return
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

      // Ensure final content is set - prioritize completion message content
      console.log('Stream reading completed')
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
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      console.error('Generation error:', err)
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
      <div className="flex-1 container mx-auto px-4 py-4 sm:py-6 md:py-8 max-w-7xl">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 md:gap-8 mb-4 sm:mb-6 md:mb-8">
          <div className="order-1 lg:order-none">
            <InputPanel onGenerate={handleGenerate} isLoading={isGenerating} />
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

