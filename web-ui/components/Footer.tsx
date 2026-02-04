'use client'

export default function Footer() {
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }

  return (
    <footer className="glass-effect border-t border-dark-border mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
          <div>
            <h3 className="text-lg font-bold text-gradient mb-4">Content Creator</h3>
            <p className="text-sm text-gray-200">
              AI-powered content generation using MAS technology. Create comprehensive, 
              engaging content with the power of multiple AI agents working together.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Quick Links</h4>
            <ul className="space-y-2 text-sm text-gray-200">
              <li>
                <button
                  onClick={scrollToTop}
                  className="hover:text-neon-cyan transition-colors text-left flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  Home
                </button>
              </li>
              <li>
                <a 
                  href="/docs" 
                  className="hover:text-neon-cyan transition-colors"
                >
                  User Guide
                </a>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Connect</h4>
            <ul className="space-y-2 text-sm text-gray-200">
              <li>
                <a 
                  href="https://github.com/joaomdmoura/crewai" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-neon-cyan transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a 
                  href="https://discord.com/invite/X4JWnZnxPb" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-neon-cyan transition-colors"
                >
                  Discord
                </a>
              </li>
              <li>
                <a 
                  href="/documentation" 
                  className="hover:text-neon-cyan transition-colors"
                >
                  Documentation
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-dark-border pt-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-300">
              © {new Date().getFullYear()} Content Creator by Patrick Ogbonna. All rights reserved.
            </p>
            <div className="flex space-x-6">
              <a href="/privacy" className="text-gray-300 hover:text-neon-cyan transition-colors text-sm">Privacy</a>
              <a href="/terms" className="text-gray-300 hover:text-neon-cyan transition-colors text-sm">Terms</a>
              <a href="/cookies" className="text-gray-300 hover:text-neon-cyan transition-colors text-sm">Cookies</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

