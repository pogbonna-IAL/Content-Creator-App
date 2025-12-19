'use client'

interface SocialMediaPanelProps {
  output: string
  isLoading: boolean
  error: string | null
  status: string
  progress: number
}

export default function SocialMediaPanel({ output, isLoading, error, status, progress }: SocialMediaPanelProps) {
  const showProgress = isLoading && progress > 0 && progress < 100;

  return (
    <div className="glass-effect neon-border rounded-2xl p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gradient mb-2">Social Media Content</h2>
        <p className="text-gray-400 text-sm">
          AI-generated social media posts will appear here
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-neon-purple rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
            </div>
            <p className="text-neon-cyan animate-pulse">{status || 'Creating social media content...'}</p>
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
                <p className="text-xs text-gray-500 mt-2 text-right">Live Preview ({output.length} chars)</p>
              </div>
            )}
            {!output && (
              <p className="text-xs text-gray-500 text-center max-w-xs">
                Our AI crew is creating engaging social media content
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
        ) : output ? (
          <div className="prose prose-invert max-w-none">
            <div className="bg-dark-card rounded-lg p-6 border border-dark-border mb-4">
              <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                {output}
              </div>
              <p className="text-xs text-gray-500 mt-2 text-right">Total Length: {output.length} chars</p>
            </div>
            <div className="mt-4 flex flex-wrap gap-4">
              <button
                onClick={async (event) => {
                  try {
                    await navigator.clipboard.writeText(output)
                    // Show feedback
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
                  const blob = new Blob([output], { type: 'text/markdown' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'social_media_content.md'
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="px-4 py-2 bg-neon-cyan/20 border border-neon-cyan/50 rounded-lg 
                           text-neon-cyan hover:bg-neon-cyan/30 transition-colors text-sm"
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
                      d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
            </div>
            <p className="text-gray-500">No social media content generated yet</p>
            <p className="text-xs text-gray-600">Enter a topic and click generate to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

