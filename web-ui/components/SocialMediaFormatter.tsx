'use client'

import React from 'react'

interface SocialMediaFormatterProps {
  platform: 'linkedin' | 'twitter' | 'facebook' | 'instagram'
  content: string
  hashtags?: string[]
  cta?: string
}

/**
 * Platform-specific formatter for social media content
 * Applies formatting based on audience usage preferences for each platform
 */
export default function SocialMediaFormatter({ platform, content, hashtags, cta }: SocialMediaFormatterProps) {
  const formatContent = (text: string, platform: string): React.ReactElement => {
    // Clean and split content into paragraphs/lines
    const cleanedText = text.trim()
    const lines = cleanedText.split('\n').filter(line => line.trim())
    
    switch (platform) {
      case 'linkedin':
        // LinkedIn: Professional, clean formatting, paragraph breaks, emphasis on key points
        // B2B audience prefers structured, informative content
        return (
          <div className="linkedin-content">
            {lines.map((line, idx) => {
              const trimmedLine = line.trim()
              // Detect bullet points or numbered lists
              if (trimmedLine.match(/^[-•*]\s/) || trimmedLine.match(/^\d+\.\s/)) {
                const bulletText = trimmedLine.replace(/^[-•*]\s/, '').replace(/^\d+\.\s/, '')
                return (
                  <div key={idx} className="flex items-start mb-2 text-gray-200">
                    <span className="text-blue-400 mr-2 mt-1">•</span>
                    <span className="flex-1">{bulletText}</span>
                  </div>
                )
              }
              // Detect bold text (**text**)
              const processedLine = trimmedLine
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
                .replace(/\*(.*?)\*/g, '<em class="text-gray-100 italic">$1</em>')
              return (
                <p key={idx} className="mb-3 text-gray-200 leading-relaxed break-words" dangerouslySetInnerHTML={{ __html: processedLine }} />
              )
            })}
          </div>
        )
      
      case 'twitter':
        // Twitter/X: Short, punchy, line breaks for readability, character count awareness
        // Audience prefers concise, engaging content with clear breaks
        return (
          <div className="twitter-content">
            {lines.map((line, idx) => {
              const trimmedLine = line.trim()
              // Preserve line breaks for readability
              return (
                <p key={idx} className="mb-1.5 text-gray-200 leading-snug break-words">
                  {trimmedLine}
                </p>
              )
            })}
            {content.length > 250 && (
              <div className={`mt-3 pt-2 border-t ${content.length > 260 ? 'border-red-500/30' : 'border-yellow-500/30'}`}>
                <div className={`text-xs font-medium ${content.length > 260 ? 'text-red-400' : 'text-yellow-400'}`}>
                  ⚠️ {content.length > 260 ? 'Exceeds' : 'Approaching'} character limit ({content.length}/280)
                </div>
              </div>
            )}
          </div>
        )
      
      case 'facebook':
        // Facebook: Conversational, emoji-friendly, paragraph breaks, community tone
        // Audience prefers friendly, engaging content with visual elements
        return (
          <div className="facebook-content">
            {lines.map((line, idx) => {
              const trimmedLine = line.trim()
              // Preserve emojis and make them slightly larger for visual appeal
              const processedLine = trimmedLine
                .replace(/([\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}])/gu, '<span class="text-lg inline-block mx-0.5">$1</span>')
              return (
                <p key={idx} className="mb-2.5 text-gray-200 leading-relaxed break-words" dangerouslySetInnerHTML={{ __html: processedLine }} />
              )
            })}
          </div>
        )
      
      case 'instagram':
        // Instagram: Visual-first, hashtag integration, emoji-rich, creative spacing
        // Audience prefers visually appealing content with hashtags and emojis
        return (
          <div className="instagram-content">
            {lines.map((line, idx) => {
              const trimmedLine = line.trim()
              // Process hashtags and emojis for visual appeal
              let processedLine = trimmedLine
                // Make hashtags stand out (pink color, medium weight)
                .replace(/#(\w+)/g, '<span class="text-pink-400 font-medium hover:text-pink-300 transition-colors">#$1</span>')
                // Make emojis larger
                .replace(/([\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}])/gu, '<span class="text-lg inline-block mx-0.5">$1</span>')
              return (
                <p key={idx} className="mb-3 text-gray-200 leading-relaxed break-words" dangerouslySetInnerHTML={{ __html: processedLine }} />
              )
            })}
            {hashtags && hashtags.length > 0 && (
              <div className="mt-4 pt-4 border-t border-pink-500/30">
                <div className="text-xs text-gray-400 mb-2 font-medium">Suggested Hashtags:</div>
                <div className="flex flex-wrap gap-2">
                  {hashtags.map((tag, idx) => (
                    <span key={idx} className="px-2 py-1 bg-pink-500/20 border border-pink-500/50 rounded-full text-pink-400 font-medium text-sm hover:bg-pink-500/30 transition-colors cursor-pointer">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      
      default:
        return <p className="text-gray-200 whitespace-pre-wrap break-words">{content}</p>
    }
  }

  return (
    <div className="social-media-formatted-content">
      {formatContent(content, platform)}
      {cta && platform !== 'instagram' && (
        <div className={`mt-4 pt-3 border-t border-gray-700 ${platform === 'linkedin' ? 'cta-professional' : 'cta-casual'}`}>
          <p className={`font-semibold ${platform === 'linkedin' ? 'text-blue-400' : platform === 'twitter' ? 'text-sky-400' : 'text-blue-500'}`}>
            {cta}
          </p>
        </div>
      )}
    </div>
  )
}
