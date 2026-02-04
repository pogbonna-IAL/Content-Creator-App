'use client'

import { useState } from 'react'

interface VideoPlayerProps {
  videoUrl: string
  title?: string
  metadata?: {
    duration_sec?: number
    resolution?: [number, number] | number[]
    fps?: number
    file_size?: number
  }
  onDownload?: () => void
}

export default function VideoPlayer({ videoUrl, title, metadata, onDownload }: VideoPlayerProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleDownload = () => {
    if (onDownload) {
      onDownload()
    } else {
      // Default download behavior
      const a = document.createElement('a')
      a.href = videoUrl
      a.download = title ? `${title}.mp4` : 'video.mp4'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  return (
    <div className="video-player-container space-y-4">
      {title && (
        <h3 className="text-lg font-semibold text-neon-cyan">{title}</h3>
      )}
      
      <div className="relative bg-black rounded-lg overflow-hidden border border-dark-border">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 z-10">
            <div className="w-12 h-12 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
          </div>
        )}
        
        {hasError ? (
          <div className="aspect-video flex items-center justify-center bg-gray-900 text-red-400">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>Failed to load video</p>
              <button
                onClick={() => {
                  setHasError(false)
                  setIsLoading(true)
                }}
                className="mt-2 px-4 py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg text-neon-purple hover:bg-neon-purple/30 transition-colors text-sm"
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <video
            controls
            src={videoUrl}
            className="w-full aspect-video"
            onLoadedData={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false)
              setHasError(true)
            }}
            preload="metadata"
          >
            Your browser does not support the video tag.
          </video>
        )}
      </div>

      {metadata && (
        <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {metadata.duration_sec !== undefined && (
              <div>
                <span className="text-gray-400">Duration:</span>
                <span className="ml-2 text-gray-200">{formatDuration(metadata.duration_sec)}</span>
              </div>
            )}
            {metadata.resolution && (
              <div>
                <span className="text-gray-400">Resolution:</span>
                <span className="ml-2 text-gray-200">
                  {Array.isArray(metadata.resolution) 
                    ? `${metadata.resolution[0]}x${metadata.resolution[1]}`
                    : metadata.resolution}
                </span>
              </div>
            )}
            {metadata.fps !== undefined && (
              <div>
                <span className="text-gray-400">FPS:</span>
                <span className="ml-2 text-gray-200">{metadata.fps}</span>
              </div>
            )}
            {metadata.file_size !== undefined && (
              <div>
                <span className="text-gray-400">Size:</span>
                <span className="ml-2 text-gray-200">{formatFileSize(metadata.file_size)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleDownload}
          className="px-4 py-2 bg-neon-cyan/20 border border-neon-cyan/50 rounded-lg 
                   text-neon-cyan hover:bg-neon-cyan/30 transition-colors text-sm
                   flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download Video
        </button>
      </div>
    </div>
  )
}
