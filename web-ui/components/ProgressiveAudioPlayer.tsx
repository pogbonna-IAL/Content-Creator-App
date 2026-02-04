'use client'

import { useEffect, useRef, useState } from 'react'

interface ProgressiveAudioPlayerProps {
  audioUrl: string | null
  onError?: (error: string) => void
  className?: string
}

/**
 * ProgressiveAudioPlayer - Plays audio with progressive buffering
 * 
 * Uses HTML5 audio element with preload="auto" for automatic buffering.
 * The browser will automatically start playing when enough data is buffered.
 * 
 * Features:
 * - Starts playing as soon as enough data is buffered (browser handles this automatically)
 * - Shows buffering progress
 * - Works with all browsers
 * - Compatible with streaming audio files
 */
export default function ProgressiveAudioPlayer({ 
  audioUrl, 
  onError,
  className = "w-full"
}: ProgressiveAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isBuffering, setIsBuffering] = useState(false)
  const [bufferedPercent, setBufferedPercent] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState<number | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
        audioRef.current.load()
      }
    }
  }, [])

  // Handle audio URL changes
  useEffect(() => {
    if (!audioUrl) {
      // Reset state when URL is cleared
      setIsBuffering(false)
      setBufferedPercent(0)
      setIsPlaying(false)
      setDuration(null)
      setCurrentTime(0)
      setError(null)
      return
    }

    // Reset error state
    setError(null)
    setIsBuffering(true)
    setBufferedPercent(0)

    setupAudio(audioUrl)
  }, [audioUrl])

  // Setup audio element with progressive buffering
  const setupAudio = (url: string) => {
    if (!audioRef.current) return

    try {
      const audio = audioRef.current
      audio.src = url
      audio.preload = 'auto' // Enable automatic buffering
      
      // Set up event listeners
      audio.addEventListener('loadedmetadata', () => {
        setDuration(audio.duration)
        updateBufferedPercent()
      })
      
      audio.addEventListener('timeupdate', () => {
        setCurrentTime(audio.currentTime)
        updateBufferedPercent()
      })
      
      audio.addEventListener('progress', () => {
        updateBufferedPercent()
        // If we have enough buffered data, stop showing buffering indicator
        if (audio.buffered.length > 0) {
          const bufferedEnd = audio.buffered.end(audio.buffered.length - 1)
          if (bufferedEnd > audio.currentTime + 1) {
            setIsBuffering(false)
          }
        }
      })
      
      audio.addEventListener('canplay', () => {
        // Browser has enough data to start playing
        setIsBuffering(false)
        // Auto-play when enough data is buffered (browser will handle this)
        // Note: Autoplay may be blocked by browser policy, which is fine
        audio.play().catch((err) => {
          // Autoplay blocked - user will need to click play button
          console.log('Autoplay prevented (this is normal):', err)
        })
      })
      
      audio.addEventListener('waiting', () => {
        // Waiting for more data to buffer
        setIsBuffering(true)
      })
      
      audio.addEventListener('canplaythrough', () => {
        // Enough data buffered to play through without stopping
        setIsBuffering(false)
        setBufferedPercent(100)
      })
      
      audio.addEventListener('play', () => setIsPlaying(true))
      audio.addEventListener('pause', () => setIsPlaying(false))
      audio.addEventListener('ended', () => setIsPlaying(false))
      
      audio.addEventListener('error', (e) => {
        let errorMsg = 'Audio playback error: '
        if (audio.error) {
          switch (audio.error.code) {
            case MediaError.MEDIA_ERR_ABORTED:
              errorMsg += 'Playback aborted'
              break
            case MediaError.MEDIA_ERR_NETWORK:
              errorMsg += 'Network error loading audio'
              break
            case MediaError.MEDIA_ERR_DECODE:
              errorMsg += 'Format error - audio file cannot be decoded. The file may be corrupted or in an unsupported format.'
              break
            case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
              errorMsg += 'Format not supported - browser cannot play this audio format. Try downloading the file instead.'
              break
            default:
              errorMsg += audio.error.message || 'Unknown error'
          }
        } else {
          errorMsg += 'Unknown error'
        }
        console.error('Audio error:', errorMsg, audio.error, {
          code: audio.error?.code,
          url: url,
          errorType: audio.error ? 'MediaError' : 'Unknown'
        })
        setError(errorMsg)
        setIsBuffering(false)
        onError?.(errorMsg)
      })

      // Load audio (triggers buffering)
      audio.load()
      
    } catch (err) {
      console.error('Error setting up audio:', err)
      const errorMsg = `Failed to setup audio: ${err instanceof Error ? err.message : 'Unknown error'}`
      setError(errorMsg)
      setIsBuffering(false)
      onError?.(errorMsg)
    }
  }

  // Update buffered percent
  const updateBufferedPercent = () => {
    if (!audioRef.current || !duration) return
    
    const buffered = audioRef.current.buffered
    if (buffered.length > 0) {
      const bufferedEnd = buffered.end(buffered.length - 1)
      const percent = duration > 0 ? (bufferedEnd / duration) * 100 : 0
      setBufferedPercent(Math.min(100, percent))
    }
  }

  // Format time
  const formatTime = (seconds: number | null): string => {
    if (seconds === null || isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (!audioUrl) {
    return null
  }

  return (
    <div className={className}>
      {/* Audio element with controls */}
      <audio
        ref={audioRef}
        controls
        className="w-full"
        preload="auto"
      >
        Your browser does not support the audio element.
      </audio>
      
      {/* Buffering indicator */}
      {isBuffering && (
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
          <div className="w-3 h-3 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin" />
          <span>Buffering... {Math.round(bufferedPercent)}%</span>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="mt-2 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded p-2">
          {error}
        </div>
      )}
    </div>
  )
}
