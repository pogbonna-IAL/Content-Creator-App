'use client'

import { useMemo } from 'react'

interface SocialMediaPanelProps {
  output: string
  isLoading: boolean
  error: string | null
  status: string
  progress: number
}

interface ParsedSocialMedia {
  linkedin_post?: string
  twitter_post?: string
  facebook_post?: string
  instagram_post?: string
  hashtags?: string[]
  cta?: string
}

export default function SocialMediaPanel({ output, isLoading, error, status, progress }: SocialMediaPanelProps) {
  const showProgress = isLoading && progress > 0 && progress < 100;
  
  // Try to parse JSON from output (for structured social media content)
  const parsedContent = useMemo<ParsedSocialMedia | null>(() => {
    if (!output) return null
    
    // Try to extract JSON from markdown-formatted output
    try {
      // Look for JSON object in the output
      const jsonMatch = output.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0])
      }
      // Try parsing entire output as JSON
      return JSON.parse(output)
    } catch (e) {
      // Not JSON, return null to use plain text display
      return null
    }
  }, [output])

  return (
    <div className="glass-effect neon-border rounded-2xl p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gradient mb-2">Social Media Content</h2>
        <p className="text-gray-200 text-sm">
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
                <p className="text-xs text-gray-300 mt-2 text-right">Live Preview ({output.length} chars)</p>
              </div>
            )}
            {!output && (
              <p className="text-xs text-gray-300 text-center max-w-xs">
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
            <p className="text-xs text-gray-300 text-center mt-2">
              Check the browser console for more details
            </p>
          </div>
        ) : output ? (
          <div className="prose prose-invert max-w-none">
            {parsedContent ? (
              // Display structured content with separate sections for each platform
              <div className="space-y-4">
                {parsedContent.linkedin_post && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                      </svg>
                      <h3 className="text-lg font-semibold text-blue-400">LinkedIn</h3>
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                      {parsedContent.linkedin_post}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">{parsedContent.linkedin_post.length} characters</p>
                  </div>
                )}
                
                {parsedContent.twitter_post && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-sky-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                      </svg>
                      <h3 className="text-lg font-semibold text-sky-400">Twitter/X</h3>
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                      {parsedContent.twitter_post}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">{parsedContent.twitter_post.length} / 280 characters</p>
                  </div>
                )}
                
                {parsedContent.facebook_post && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                      </svg>
                      <h3 className="text-lg font-semibold text-blue-500">Facebook</h3>
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                      {parsedContent.facebook_post}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">{parsedContent.facebook_post.length} characters</p>
                  </div>
                )}
                
                {parsedContent.instagram_post && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-pink-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                      </svg>
                      <h3 className="text-lg font-semibold text-pink-500">Instagram</h3>
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                      {parsedContent.instagram_post}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">{parsedContent.instagram_post.length} / 2200 characters</p>
                  </div>
                )}
                
                {parsedContent.hashtags && parsedContent.hashtags.length > 0 && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <h3 className="text-lg font-semibold mb-2 text-gray-300">Hashtags</h3>
                    <div className="flex flex-wrap gap-2">
                      {parsedContent.hashtags.map((tag, idx) => (
                        <span key={idx} className="px-3 py-1 bg-neon-purple/20 border border-neon-purple/50 rounded-full text-sm text-neon-purple">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {parsedContent.cta && (
                  <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
                    <h3 className="text-lg font-semibold mb-2 text-gray-300">Call-to-Action</h3>
                    <p className="text-sm text-gray-300 leading-relaxed">{parsedContent.cta}</p>
                  </div>
                )}
            </div>
            ) : (
              // Fallback to plain text display (for markdown or non-JSON output)
              <div className="bg-dark-card rounded-lg p-6 border border-dark-border mb-4">
                <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
                  {output}
                </div>
                <p className="text-xs text-gray-300 mt-2 text-right">Total Length: {output.length} chars</p>
              </div>
            )}
            
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
            <p className="text-gray-300">No social media content generated yet</p>
            <p className="text-xs text-gray-200">Enter a topic and click generate to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

