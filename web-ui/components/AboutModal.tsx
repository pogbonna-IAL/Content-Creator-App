'use client'

interface AboutModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div 
        className="glass-effect neon-border rounded-2xl p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-6">
          <h2 className="text-3xl font-bold text-gradient">About Content Creator</h2>
          <button
            onClick={onClose}
            className="text-gray-200 hover:text-neon-cyan transition-colors text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="space-y-6 text-gray-300">
          <div>
            <p className="text-lg leading-relaxed">
              Content Creator is an AI-powered application that helps you create high-quality content 
              across multiple formats effortlessly. Simply enter a topic, and our intelligent AI crew 
              will generate blog posts, social media content, audio scripts, and video scripts—all 
              tailored to their respective platforms.
            </p>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-neon-cyan mb-3">How It Works</h3>
            <p className="leading-relaxed">
              Our application uses a team of specialized AI agents that work together to create comprehensive 
              content across multiple formats. First, a researcher analyzes your topic and gathers key insights. 
              Then, a writer transforms this research into an engaging blog post. An editor polishes the content 
              to ensure it's publication-ready. Finally, our specialized content creators branch out to generate 
              multiple content formats: social media posts, audio scripts, and video scripts - all optimized for 
              their respective platforms.
            </p>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-neon-cyan mb-3">What You Get</h3>
            <ul className="space-y-2 list-disc list-inside leading-relaxed">
              <li><strong className="text-neon-purple">Complete Blog Post:</strong> A well-researched, 
              well-written, and professionally edited article ready for publication</li>
              <li><strong className="text-neon-purple">Social Media Content:</strong> Engaging posts 
              optimized for platforms like LinkedIn, Twitter, Facebook, and Instagram, complete with 
              hashtags and calls-to-action</li>
              <li><strong className="text-neon-purple">Audio Script:</strong> Professional audio scripts 
              optimized for podcasts, audiobooks, and voice narration with natural pacing, transitions, 
              and engaging hooks</li>
              <li><strong className="text-neon-purple">Video Script:</strong> Compelling video scripts 
              for YouTube and video platforms with visual cues, scene descriptions, and on-screen text 
              suggestions</li>
              <li><strong className="text-neon-purple">Download Options:</strong> Save your content 
              as markdown files or copy to clipboard for easy sharing</li>
            </ul>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-neon-cyan mb-3">Perfect For</h3>
            <p className="leading-relaxed">
              Whether you're a content creator, marketer, blogger, or business owner, Content Creator 
              helps you produce professional-quality content quickly and efficiently. No writing experience 
              required—just enter your topic and let our AI crew handle the rest.
            </p>
          </div>

          <div className="pt-4 border-t border-dark-border">
            <p className="text-sm text-gray-200 italic">
              Powered by CrewAI and advanced language models. Built to make content creation accessible 
              to everyone.
            </p>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-neon-purple/20 border border-neon-purple/50 rounded-lg 
                     text-neon-purple hover:bg-neon-purple/30 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

