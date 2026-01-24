'use client'

import { useState } from 'react'

interface InputPanelProps {
  onGenerate: (topic: string) => void
  isLoading: boolean
}

export default function InputPanel({ onGenerate, isLoading }: InputPanelProps) {
  const [topic, setTopic] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (topic.trim() && !isLoading) {
      onGenerate(topic.trim())
    }
  }

  return (
    <div className="glass-effect neon-border rounded-2xl p-4 sm:p-6 h-full">
      <div className="mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-gradient mb-2">Create Content</h2>
        <p className="text-gray-200 text-xs sm:text-sm">
          Enter a topic and let our AI crew create comprehensive content for you
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
        <div>
          <label htmlFor="topic" className="block text-sm font-medium text-gray-300 mb-2">
            Topic
          </label>
          <textarea
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., The benefits of renewable energy, Latest trends in AI, etc."
            className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg 
                     text-white placeholder-gray-500 focus:outline-none focus:border-neon-cyan 
                     focus:ring-2 focus:ring-neon-cyan/20 transition-all resize-none
                     text-base sm:text-sm touch-manipulation"
            rows={4}
            disabled={isLoading}
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !topic.trim()}
          className="w-full neon-button px-6 py-3 sm:py-3 rounded-lg font-semibold
                   bg-gradient-to-r from-neon-cyan/20 to-neon-purple/20
                   text-neon-cyan disabled:opacity-50 disabled:cursor-not-allowed
                   flex items-center justify-center space-x-2
                   touch-manipulation min-h-[44px] active:scale-95 transition-transform"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Generating...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Generate Content</span>
            </>
          )}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-dark-border">
        <p className="text-xs text-gray-300">
          💡 Tip: Be specific about your topic for better results
        </p>
      </div>
    </div>
  )
}

