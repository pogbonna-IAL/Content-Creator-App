'use client'

import { useState, useEffect, useRef } from 'react'
import { getApiUrl } from '@/lib/env'
import VideoPlayer from './VideoPlayer'

interface VideoPanelProps {
  output: string
  isLoading: boolean
  error: string | null
  status: string
  progress: number
  jobId: number | null
}

interface VideoRenderOptions {
  resolution: [number, number]
  fps: number
  background_type: 'solid' | 'placeholder' | 'upload'
  background_color: string
  include_narration: boolean
  renderer: 'baseline' | 'comfyui'
}

export default function VideoPanel({ output, isLoading, error, status, progress, jobId }: VideoPanelProps) {
  const showProgress = isLoading && progress > 0 && progress < 100;

  // Video rendering state
  const [isRenderingVideo, setIsRenderingVideo] = useState(false)
  const [videoRenderError, setVideoRenderError] = useState<string | null>(null)
  const [videoRenderStatus, setVideoRenderStatus] = useState<string>('')
  const [videoRenderProgress, setVideoRenderProgress] = useState<number>(0)
  const [renderedVideoUrl, setRenderedVideoUrl] = useState<string | null>(null)
  const [videoMetadata, setVideoMetadata] = useState<any>(null)
  const [showRenderOptions, setShowRenderOptions] = useState(false)
  
  // Default rendering options (optimized for quality and speed)
  const defaultRenderOptions: VideoRenderOptions = {
    resolution: [1920, 1080], // Full HD - best quality
    fps: 30, // Standard video FPS
    background_type: 'solid', // Solid color background
    background_color: '#1a1a1a', // Dark gray (better than pure black)
    include_narration: true, // Include audio if available
    renderer: 'baseline' // CPU-based renderer
  }
  
  const [renderOptions, setRenderOptions] = useState<VideoRenderOptions>(defaultRenderOptions)
  
  // Reset to defaults function
  const resetToDefaults = () => {
    setRenderOptions(defaultRenderOptions)
  }
  const [currentScene, setCurrentScene] = useState<{ index: number; title: string } | null>(null)
  const [totalScenes, setTotalScenes] = useState<number>(0)
  
  // Track video render stream resources for cancellation
  const [videoRenderReaderRef, setVideoRenderReaderRef] = useState<ReadableStreamDefaultReader<Uint8Array> | null>(null)
  const [videoRenderAbortControllerRef, setVideoRenderAbortControllerRef] = useState<AbortController | null>(null)

  // Check if video script exists (output is not empty)
  const hasVideoScript = output && output.trim().length > 0

  // Function to start video rendering
  const handleRenderVideo = async () => {
    if (!jobId) {
      setVideoRenderError('No job ID available. Please generate video content first.')
      return
    }

    setIsRenderingVideo(true)
    setVideoRenderError(null)
    setVideoRenderStatus('Starting video rendering...')
    setVideoRenderProgress(5)
    setRenderedVideoUrl(null)
    setVideoMetadata(null)
    setCurrentScene(null)
    setTotalScenes(0)

    try {
      // Get auth token from localStorage
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      } else {
        setVideoRenderError('Authentication token not found. Please log in again.')
        setIsRenderingVideo(false)
        return
      }

      const requestBody = {
        job_id: jobId,
        resolution: renderOptions.resolution,
        fps: renderOptions.fps,
        background_type: renderOptions.background_type,
        background_color: renderOptions.background_color,
        include_narration: renderOptions.include_narration,
        renderer: renderOptions.renderer
      }
      
      console.log('VideoPanel - Calling /api/video/render:', requestBody)

      // Call video render API
      const response = await fetch('/api/video/render', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(requestBody),
      })
      
      console.log('VideoPanel - Video render API response:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorData: any = {}
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Unknown error' }
        }
        throw new Error(errorData.detail || errorData.error || 'Failed to start video rendering')
      }

      const result = await response.json()
      console.log('VideoPanel - Video render started:', result)
      
      const renderJobId = result.job_id || jobId
      
      // Stream video render progress via SSE
      await streamVideoRenderProgress(renderJobId)

    } catch (err) {
      console.error('Video rendering error:', err)
      setVideoRenderError(err instanceof Error ? err.message : 'Failed to render video')
      setIsRenderingVideo(false)
      setVideoRenderStatus('')
    }
  }

  // Stream video render progress via SSE
  const streamVideoRenderProgress = async (renderJobId: number) => {
    // Clean up any existing stream
    if (videoRenderReaderRef) {
      try {
        await videoRenderReaderRef.cancel().catch(() => {})
        videoRenderReaderRef.releaseLock()
      } catch (e) {
        console.log('Error cleaning up previous video render reader:', e)
      }
      setVideoRenderReaderRef(null)
    }
    
    if (videoRenderAbortControllerRef) {
      videoRenderAbortControllerRef.abort()
      setVideoRenderAbortControllerRef(null)
    }

    // Create new abort controller
    const abortController = new AbortController()
    setVideoRenderAbortControllerRef(abortController)

    try {
      const streamUrl = getApiUrl(`v1/content/jobs/${renderJobId}/stream`)

      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      const headers: HeadersInit = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      console.log('VideoPanel - Starting SSE stream for video render job:', renderJobId)

      const response = await fetch(streamUrl, {
        method: 'GET',
        headers,
        credentials: 'include',
        signal: abortController.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to stream video render progress: ${response.status} ${response.statusText} - ${errorText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body reader available')
      }

      setVideoRenderReaderRef(reader)

      const decoder = new TextDecoder()
      let buffer = ''
      let eventCount = 0

      while (true) {
        if (abortController.signal.aborted) {
          console.log('VideoPanel - Stream aborted, stopping read loop')
          break
        }

        const { done, value } = await reader.read()
        
        if (done && abortController.signal.aborted) {
          console.log('VideoPanel - Stream ended due to abort')
          break
        }
        
        if (done) {
          console.log('VideoPanel - SSE stream ended, total events received:', eventCount)
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk

        // Process complete SSE messages
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          if (!part.trim()) continue
          
          // Skip keep-alive messages
          if (part.trim() === ': keep-alive' || part.trim().startsWith(': ')) {
            continue
          }

          // Parse SSE message
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
              console.log(`VideoPanel - SSE event #${eventCount}:`, {
                event_type: eventType || 'default',
                data_type: data.type,
                full_data: data
              })

              // Handle video rendering events
              if (data.type === 'video_render_started' || eventType === 'video_render_started') {
                setVideoRenderStatus('Video rendering started...')
                setVideoRenderProgress(10)
                if (data.scenes_count) {
                  setTotalScenes(data.scenes_count)
                }
              } else if (data.type === 'scene_started' || eventType === 'scene_started') {
                const sceneIndex = data.scene_index ?? data.sceneIndex ?? 0
                const sceneTitle = data.scene_title ?? data.sceneTitle ?? `Scene ${sceneIndex + 1}`
                setCurrentScene({ index: sceneIndex, title: sceneTitle })
                setVideoRenderStatus(`Rendering scene ${sceneIndex + 1}${totalScenes > 0 ? ` of ${totalScenes}` : ''}: ${sceneTitle}`)
                // Progress: 10% start + (scene_index / total_scenes) * 70% (up to 80%)
                if (totalScenes > 0) {
                  setVideoRenderProgress(10 + Math.floor((sceneIndex / totalScenes) * 70))
                } else {
                  setVideoRenderProgress(20)
                }
              } else if (data.type === 'scene_completed' || eventType === 'scene_completed') {
                const sceneIndex = data.scene_index ?? data.sceneIndex ?? 0
                setVideoRenderStatus(`Scene ${sceneIndex + 1} completed`)
                // Progress: 10% start + ((scene_index + 1) / total_scenes) * 70% (up to 80%)
                if (totalScenes > 0) {
                  setVideoRenderProgress(10 + Math.floor(((sceneIndex + 1) / totalScenes) * 70))
                } else {
                  setVideoRenderProgress(30)
                }
              } else if (data.type === 'artifact_ready' && data.artifact_type === 'final_video') {
                setVideoRenderStatus('Video ready!')
                setVideoRenderProgress(90)
                const videoUrl = data.metadata?.storage_url || data.metadata?.url || data.url
                if (videoUrl) {
                  console.log('VideoPanel - Setting video URL:', videoUrl)
                  setRenderedVideoUrl(videoUrl)
                  setVideoMetadata({
                    ...data.metadata,
                    duration_sec: data.metadata?.duration_sec,
                    resolution: data.metadata?.resolution || renderOptions.resolution,
                    fps: data.metadata?.fps || renderOptions.fps
                  })
                }
              } else if (data.type === 'video_render_completed' || eventType === 'video_render_completed') {
                setVideoRenderStatus('Video rendering complete!')
                setVideoRenderProgress(100)
                setIsRenderingVideo(false)
                const videoUrl = data.storage_url || data.url || data.metadata?.storage_url
                if (videoUrl) {
                  setRenderedVideoUrl(videoUrl)
                  setVideoMetadata({
                    ...data.metadata,
                    duration_sec: data.duration_sec || data.metadata?.duration_sec,
                    resolution: data.resolution || data.metadata?.resolution || renderOptions.resolution,
                    fps: data.metadata?.fps || renderOptions.fps
                  })
                }
              } else if (data.type === 'video_render_failed' || eventType === 'video_render_failed') {
                setVideoRenderError(data.message || 'Video rendering failed')
                setIsRenderingVideo(false)
                setVideoRenderStatus('')
              }
            } catch (parseError) {
              console.error('VideoPanel - Error parsing SSE data:', parseError, eventData)
            }
          }
        }
      }
    } catch (err) {
      console.error('VideoPanel - SSE stream error:', err)
      setVideoRenderError(err instanceof Error ? err.message : 'Failed to stream video render progress')
      setIsRenderingVideo(false)
    } finally {
      // Clean up
      if (videoRenderReaderRef) {
        try {
          await videoRenderReaderRef.cancel().catch(() => {})
          videoRenderReaderRef.releaseLock()
        } catch (e) {
          console.log('Error cleaning up video render reader:', e)
        }
        setVideoRenderReaderRef(null)
      }
      setVideoRenderAbortControllerRef(null)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoRenderReaderRef) {
        videoRenderReaderRef.cancel().catch(() => {})
        videoRenderReaderRef.releaseLock()
      }
      if (videoRenderAbortControllerRef) {
        videoRenderAbortControllerRef.abort()
      }
    }
  }, [videoRenderReaderRef, videoRenderAbortControllerRef])

  return (
    <div className="glass-effect neon-border rounded-2xl p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gradient mb-2">Video Content Output</h2>
        <p className="text-gray-200 text-sm">
          AI-generated video content will appear here
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        {/* Video Script Display */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-neon-purple rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
            </div>
            <p className="text-neon-cyan animate-pulse">{status || 'Generating video content...'}</p>
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
                Our AI crew is creating video content
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
          <div className="space-y-4">
            {/* Video Script Display */}
            <div className="bg-dark-card rounded-lg p-6 border border-dark-border">
              <h3 className="text-lg font-semibold text-neon-cyan mb-3">Video Script</h3>
              <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words max-h-64 overflow-y-auto">
                {output}
              </div>
              <p className="text-xs text-gray-300 mt-2 text-right">Total Length: {output.length} chars</p>
            </div>

            {/* Render Video Button */}
            {hasVideoScript && !isRenderingVideo && !renderedVideoUrl && (
              <div className="space-y-3">
                <button
                  onClick={() => setShowRenderOptions(!showRenderOptions)}
                  className="w-full px-4 py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg 
                           text-neon-purple hover:bg-neon-purple/30 transition-colors text-sm
                           flex items-center justify-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  {showRenderOptions ? 'Hide' : 'Show'} Render Options
                </button>

                {showRenderOptions && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border space-y-4">
                    {/* Reset to Defaults Button */}
                    <div className="flex items-center justify-between pb-2 border-b border-dark-border">
                      <p className="text-xs text-gray-400">Recommended defaults are pre-selected</p>
                      <button
                        onClick={resetToDefaults}
                        className="px-3 py-1 text-xs bg-gray-700/50 border border-dark-border rounded-lg 
                                 text-gray-300 hover:bg-gray-700 transition-colors"
                      >
                        Reset to Defaults
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-gray-300 mb-1">
                          Resolution
                          <span className="ml-2 text-xs text-gray-500">(Default: 1920x1080)</span>
                        </label>
                        <select
                          value={`${renderOptions.resolution[0]}x${renderOptions.resolution[1]}`}
                          onChange={(e) => {
                            const [w, h] = e.target.value.split('x').map(Number)
                            setRenderOptions({ ...renderOptions, resolution: [w, h] })
                          }}
                          className="w-full px-3 py-2 bg-gray-800 border border-dark-border rounded-lg text-gray-200 text-sm"
                        >
                          <option value="1920x1080">1920x1080 (Full HD) - Recommended</option>
                          <option value="1280x720">1280x720 (HD) - Faster</option>
                          <option value="854x480">854x480 (SD) - Fastest</option>
                          <option value="640x360">640x360 (Low) - Quick Preview</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-gray-300 mb-1">
                          FPS
                          <span className="ml-2 text-xs text-gray-500">(Default: 30)</span>
                        </label>
                        <select
                          value={renderOptions.fps}
                          onChange={(e) => setRenderOptions({ ...renderOptions, fps: Number(e.target.value) })}
                          className="w-full px-3 py-2 bg-gray-800 border border-dark-border rounded-lg text-gray-200 text-sm"
                        >
                          <option value="24">24 fps - Cinematic</option>
                          <option value="30">30 fps - Standard (Recommended)</option>
                          <option value="60">60 fps - Smooth (Slower)</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-300 mb-1">
                        Background Type
                        <span className="ml-2 text-xs text-gray-500">(Default: Solid)</span>
                      </label>
                      <select
                        value={renderOptions.background_type}
                        onChange={(e) => setRenderOptions({ ...renderOptions, background_type: e.target.value as any })}
                        className="w-full px-3 py-2 bg-gray-800 border border-dark-border rounded-lg text-gray-200 text-sm"
                      >
                        <option value="solid">Solid Color - Recommended</option>
                        <option value="placeholder">Placeholder Gradient</option>
                      </select>
                    </div>
                    {renderOptions.background_type === 'solid' && (
                      <div>
                        <label className="block text-sm text-gray-300 mb-1">
                          Background Color
                          <span className="ml-2 text-xs text-gray-500">(Default: Dark Gray)</span>
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            type="color"
                            value={renderOptions.background_color}
                            onChange={(e) => setRenderOptions({ ...renderOptions, background_color: e.target.value })}
                            className="w-16 h-10 bg-gray-800 border border-dark-border rounded-lg cursor-pointer"
                          />
                          <input
                            type="text"
                            value={renderOptions.background_color}
                            onChange={(e) => setRenderOptions({ ...renderOptions, background_color: e.target.value })}
                            placeholder="#1a1a1a"
                            className="flex-1 px-3 py-2 bg-gray-800 border border-dark-border rounded-lg text-gray-200 text-sm font-mono"
                          />
                          <button
                            onClick={() => setRenderOptions({ ...renderOptions, background_color: defaultRenderOptions.background_color })}
                            className="px-3 py-2 text-xs bg-gray-700/50 border border-dark-border rounded-lg 
                                     text-gray-300 hover:bg-gray-700 transition-colors"
                            title="Reset to default color"
                          >
                            Reset
                          </button>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {[
                            { name: 'Dark Gray', color: '#1a1a1a' },
                            { name: 'Black', color: '#000000' },
                            { name: 'Dark Blue', color: '#0a1929' },
                            { name: 'Dark Purple', color: '#1a0a2e' },
                            { name: 'White', color: '#ffffff' }
                          ].map((preset) => (
                            <button
                              key={preset.color}
                              onClick={() => setRenderOptions({ ...renderOptions, background_color: preset.color })}
                              className="px-2 py-1 text-xs bg-gray-700/30 border border-dark-border rounded 
                                       text-gray-300 hover:bg-gray-700/50 transition-colors"
                              title={preset.name}
                            >
                              {preset.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center gap-2 pt-2 border-t border-dark-border">
                      <input
                        type="checkbox"
                        id="include_narration"
                        checked={renderOptions.include_narration}
                        onChange={(e) => setRenderOptions({ ...renderOptions, include_narration: e.target.checked })}
                        className="w-4 h-4 text-neon-purple bg-gray-800 border-dark-border rounded"
                      />
                      <label htmlFor="include_narration" className="text-sm text-gray-300">
                        Include narration audio (if available)
                        <span className="ml-2 text-xs text-gray-500">(Default: Enabled)</span>
                      </label>
                    </div>
                    
                    {/* Quick Presets */}
                    <div className="pt-2 border-t border-dark-border">
                      <p className="text-xs text-gray-400 mb-2">Quick Presets:</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => setRenderOptions({
                            ...defaultRenderOptions,
                            resolution: [1920, 1080],
                            fps: 30
                          })}
                          className="px-3 py-1 text-xs bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg 
                                   text-neon-cyan hover:bg-neon-cyan/20 transition-colors"
                        >
                          High Quality (1080p, 30fps)
                        </button>
                        <button
                          onClick={() => setRenderOptions({
                            ...defaultRenderOptions,
                            resolution: [1280, 720],
                            fps: 30
                          })}
                          className="px-3 py-1 text-xs bg-neon-purple/10 border border-neon-purple/30 rounded-lg 
                                   text-neon-purple hover:bg-neon-purple/20 transition-colors"
                        >
                          Balanced (720p, 30fps)
                        </button>
                        <button
                          onClick={() => setRenderOptions({
                            ...defaultRenderOptions,
                            resolution: [854, 480],
                            fps: 24
                          })}
                          className="px-3 py-1 text-xs bg-gray-700/50 border border-dark-border rounded-lg 
                                   text-gray-300 hover:bg-gray-700 transition-colors"
                        >
                          Fast Preview (480p, 24fps)
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleRenderVideo}
                  disabled={!jobId}
                  className="w-full px-6 py-3 bg-gradient-to-r from-neon-cyan/20 to-neon-purple/20 
                           border border-neon-cyan/50 rounded-lg text-neon-cyan hover:bg-neon-cyan/30 
                           transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Render Video
                </button>
              </div>
            )}

            {/* Video Rendering Progress */}
            {isRenderingVideo && (
              <div className="bg-dark-card rounded-lg p-6 border border-dark-border space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-neon-cyan">Rendering Video</h3>
                  <span className="text-sm text-gray-400">{videoRenderProgress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-neon-cyan to-neon-purple h-3 rounded-full transition-all duration-300"
                    style={{ width: `${videoRenderProgress}%` }}
                  ></div>
                </div>
                {videoRenderStatus && (
                  <p className="text-sm text-gray-300">{videoRenderStatus}</p>
                )}
                {currentScene && (
                  <div className="text-xs text-gray-400">
                    Current: {currentScene.title}
                  </div>
                )}
              </div>
            )}

            {/* Rendered Video Display */}
            {renderedVideoUrl && (
              <div className="bg-dark-card rounded-lg p-6 border border-dark-border">
                <h3 className="text-lg font-semibold text-neon-cyan mb-4">Rendered Video</h3>
                <VideoPlayer
                  videoUrl={renderedVideoUrl}
                  title="Generated Video"
                  metadata={videoMetadata}
                />
              </div>
            )}

            {/* Video Rendering Error */}
            {videoRenderError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <p className="text-sm text-red-300">{videoRenderError}</p>
                <button
                  onClick={() => {
                    setVideoRenderError(null)
                    if (hasVideoScript) {
                      handleRenderVideo()
                    }
                  }}
                  className="mt-2 px-4 py-2 bg-red-600/20 border border-red-600/50 rounded-lg 
                           text-red-400 hover:bg-red-600/30 transition-colors text-sm"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Copy/Download Script Buttons */}
            <div className="flex flex-wrap gap-4">
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
                Copy Script
              </button>
              <button
                onClick={() => {
                  const blob = new Blob([output], { type: 'text/plain' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'video_script.txt'
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
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 
                          flex items-center justify-center border border-neon-cyan/30">
              <svg className="w-12 h-12 text-neon-cyan/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                      d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-gray-300">No video content generated yet</p>
            <p className="text-xs text-gray-200">Enter a topic and click generate to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}
