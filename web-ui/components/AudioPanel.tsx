'use client'

import { useState, useEffect } from 'react'

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

  // Function to generate voiceover
  const handleGenerateVoiceover = async () => {
    if (!jobId && !output) {
      setVoiceoverError('No audio script available. Please generate audio content first.')
      return
    }

    setIsGeneratingVoiceover(true)
    setVoiceoverError(null)
    setVoiceoverStatus('Starting voiceover generation...')
    setVoiceoverProgress(0)
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

      console.log('AudioPanel - Calling /api/voiceover with job_id:', jobId, 'narration_text length:', jobId ? 0 : output.length)

      // Call voiceover API
      const response = await fetch('/api/voiceover', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          job_id: jobId || undefined,
          narration_text: jobId ? undefined : output, // Use narration_text if no job_id
          voice_id: 'default',
          speed: 1.0,
          format: 'wav'
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorData: any = {}
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Unknown error' }
        }
        
        console.error('AudioPanel - Voiceover API error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData.error,
          detail: errorData.detail
        })
        
        throw new Error(errorData.error || errorData.detail || `Failed to start voiceover generation (${response.status})`)
      }

      const result = await response.json()
      const voiceoverJobId = result.job_id

      if (!voiceoverJobId) {
        throw new Error('No job ID returned from voiceover API')
      }

      // Stream TTS progress via SSE
      await streamVoiceoverProgress(voiceoverJobId)

    } catch (err) {
      console.error('Voiceover generation error:', err)
      setVoiceoverError(err instanceof Error ? err.message : 'Failed to generate voiceover')
      setIsGeneratingVoiceover(false)
      setVoiceoverStatus('')
    }
  }

  // Stream voiceover progress via SSE
  const streamVoiceoverProgress = async (voiceoverJobId: number) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const streamUrl = `${apiUrl}/v1/content/jobs/${voiceoverJobId}/stream`

      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      const headers: HeadersInit = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch(streamUrl, {
        method: 'GET',
        headers,
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error(`Failed to stream voiceover progress: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body reader available')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim()
              if (!jsonStr) continue

              const data = JSON.parse(jsonStr)
              console.log('Voiceover SSE event:', data.type, data)

              if (data.type === 'tts_started') {
                setVoiceoverStatus('TTS generation started...')
                setVoiceoverProgress(10)
              } else if (data.type === 'tts_progress') {
                setVoiceoverStatus(data.message || 'Generating voiceover...')
                setVoiceoverProgress(data.progress || 50)
              } else if (data.type === 'artifact_ready' && data.artifact_type === 'voiceover_audio') {
                setVoiceoverStatus('Voiceover ready!')
                setVoiceoverProgress(90)
                if (data.metadata?.storage_url) {
                  setAudioUrl(data.metadata.storage_url)
                  setAudioMetadata(data.metadata)
                }
              } else if (data.type === 'tts_completed') {
                setVoiceoverStatus('Voiceover generation complete!')
                setVoiceoverProgress(100)
                setIsGeneratingVoiceover(false)
                if (data.storage_url) {
                  setAudioUrl(data.storage_url)
                }
              } else if (data.type === 'tts_failed') {
                throw new Error(data.message || 'TTS generation failed')
              } else if (data.type === 'error') {
                throw new Error(data.message || data.detail || 'Voiceover generation error')
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (err) {
      console.error('Streaming error:', err)
      setVoiceoverError(err instanceof Error ? err.message : 'Failed to stream voiceover progress')
      setIsGeneratingVoiceover(false)
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
                      <p className="text-neon-cyan">{voiceoverStatus || 'Generating voiceover...'}</p>
                    </div>
                    {voiceoverProgress > 0 && (
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-neon-purple h-2 rounded-full transition-all duration-300" 
                          style={{ width: `${voiceoverProgress}%` }}
                        ></div>
                      </div>
                    )}
                  </div>
                )}
                
                {voiceoverError && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-3">
                    <p className="text-sm text-red-300">{voiceoverError}</p>
                  </div>
                )}
                
                {audioUrl && !isGeneratingVoiceover && (
                  <div className="space-y-3">
                    <audio 
                      controls 
                      className="w-full"
                      src={audioUrl}
                    >
                      Your browser does not support the audio element.
                    </audio>
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
              {(jobId || output) && !isGeneratingVoiceover && !audioUrl && (
                <button
                  onClick={handleGenerateVoiceover}
                  disabled={isGeneratingVoiceover}
                  className="px-4 py-2 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg 
                             text-white hover:opacity-90 transition-opacity text-sm font-semibold
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  🎙️ Generate Voiceover
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

