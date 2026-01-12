'use client'

import { useEffect } from 'react'

interface OutputPanelProps {
  output: string
  isLoading: boolean
  error: string | null
  status?: string
  progress?: number
}

export default function OutputPanel({ output, isLoading, error, status, progress }: OutputPanelProps) {
  // Debug logging
  useEffect(() => {
    if (output) {
      console.log('OutputPanel received output, length:', output.length)
      console.log('Output preview:', output.substring(0, 100))
    }
  }, [output])
  return (
    <div className="glass-effect neon-border rounded-2xl p-4 sm:p-6 h-full flex flex-col">
      <div className="mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-gradient mb-2">Generated Content</h2>
        <p className="text-gray-400 text-xs sm:text-sm">
          Your AI-generated content will appear here
        </p>
        {output && (
          <p className="text-xs text-neon-cyan mt-2">
            ✓ Content loaded ({output.length} characters)
          </p>
        )}
      </div>

      <div className="flex-1 overflow-auto touch-pan-y overscroll-contain">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4 py-4">
            <div className="relative">
              <div className="w-12 h-12 sm:w-16 sm:h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-12 h-12 sm:w-16 sm:h-16 border-4 border-transparent border-r-neon-purple rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
            </div>
            <p className="text-neon-cyan animate-pulse text-sm sm:text-base text-center px-4">{status || 'Creating your content...'}</p>
            {progress !== undefined && progress > 0 && (
              <div className="w-full max-w-xs px-4">
                <div className="w-full bg-dark-card rounded-full h-2 mb-2">
                  <div 
                    className="bg-gradient-to-r from-neon-cyan to-neon-purple h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-400 text-center">{progress}%</p>
              </div>
            )}
            {output && (
              <div className="w-full max-w-xs mt-4">
                <p className="text-xs text-gray-500 text-center mb-2">Preview:</p>
                <div className="bg-dark-card rounded-lg p-3 max-h-32 overflow-y-auto">
                  <p className="text-xs text-gray-300">{output.substring(0, 200)}...</p>
                </div>
              </div>
            )}
            {!output && (
              <p className="text-xs text-gray-500 text-center max-w-xs">
                Our AI crew is researching, writing, and editing your content
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
            <p className="text-xs text-gray-500 text-center mt-2">
              Check the browser console for more details
            </p>
          </div>
        ) : output && output.trim() ? (
          <div className="prose prose-invert max-w-none">
            <div className="bg-dark-card rounded-lg p-4 sm:p-6 border border-dark-border mb-4 max-h-[600px] overflow-y-auto touch-pan-y overscroll-contain">
              <div className="text-sm sm:text-base text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                {output}
              </div>
              {output.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  Content length: {output.length} characters
                </div>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-3 sm:gap-4">
              <button
                onClick={async (event) => {
                  try {
                    await navigator.clipboard.writeText(output)
                    // Show feedback
                    const btn = event?.target as HTMLButtonElement
                    const originalText = btn.textContent
                    btn.textContent = 'Copied!'
                    setTimeout(() => {
                      btn.textContent = originalText
                    }, 2000)
                  } catch (err) {
                    console.error('Failed to copy:', err)
                  }
                }}
                className="px-4 py-2.5 sm:py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg 
                         text-neon-purple hover:bg-neon-purple/30 active:scale-95 transition-all text-sm
                         touch-manipulation min-h-[44px] flex-1 sm:flex-none"
              >
                Copy to Clipboard
              </button>
              <button
                onClick={() => {
                  const blob = new Blob([output], { type: 'text/markdown' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'content_output.md'
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="px-4 py-2.5 sm:py-2 bg-neon-cyan/20 border border-neon-cyan/50 rounded-lg 
                         text-neon-cyan hover:bg-neon-cyan/30 active:scale-95 transition-all text-sm
                         touch-manipulation min-h-[44px] flex-1 sm:flex-none"
              >
                Download as MD
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 
                          flex items-center justify-center border border-neon-cyan/30">
              <svg className="w-12 h-12 text-neon-cyan/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-gray-500">No content generated yet</p>
            <p className="text-xs text-gray-600">Enter a topic and click generate to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

