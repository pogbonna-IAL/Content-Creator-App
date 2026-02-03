'use client'

import { useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import AboutModal from './AboutModal'
import ContactModal from './ContactModal'
import FeaturesDropdown from './FeaturesDropdown'

interface NavbarProps {
  selectedFeature: string
  onFeatureSelect: (feature: string) => void
}

export default function Navbar({ selectedFeature, onFeatureSelect }: NavbarProps) {
  const [isAboutOpen, setIsAboutOpen] = useState(false)
  const [isContactOpen, setIsContactOpen] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const { user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  const handleLogoClick = () => {
    // If already on home page, scroll to top, otherwise navigate
    if (pathname === '/') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } else {
      router.push('/')
    }
  }

  return (
    <>
      <nav className="glass-effect border-b border-dark-border sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="relative flex items-center">
            {/* Logo and Title - Left Aligned */}
            <button
              onClick={handleLogoClick}
              className="flex items-center space-x-3 flex-shrink-0 hover:opacity-80 transition-opacity cursor-pointer"
              aria-label="Go to home page"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center glow-text">
                <span className="text-2xl font-bold">C</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gradient">Content Creator</h1>
                <p className="text-xs text-gray-200">AI-Powered Content Generation</p>
              </div>
            </button>
            
            {/* Nav Buttons - Starting from 40% width (only show if authenticated) */}
            {user && (
              <div className="hidden md:flex items-center space-x-6 absolute left-[40%]">
                <FeaturesDropdown selectedFeature={selectedFeature} onFeatureSelect={onFeatureSelect} />
                <button
                  onClick={() => setIsAboutOpen(true)}
                  className="text-gray-300 hover:text-neon-cyan transition-colors bg-transparent border-none cursor-pointer"
                >
                  About
                </button>
                <button
                  onClick={() => setIsContactOpen(true)}
                  className="text-gray-300 hover:text-neon-cyan transition-colors bg-transparent border-none cursor-pointer"
                >
                  Contact
                </button>
                {user.is_admin && (
                  <button
                    onClick={() => router.push('/admin')}
                    className="text-gray-300 hover:text-neon-cyan transition-colors bg-transparent border-none cursor-pointer font-semibold"
                  >
                    Admin
                  </button>
                )}
              </div>
            )}
            
            {/* Right side - Login/Signup buttons or User Profile */}
            <div className="hidden md:flex items-center ml-auto gap-4">
              {user ? (
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-dark-card border border-dark-border hover:border-neon-cyan transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center">
                      <span className="text-sm font-bold">
                        {user.full_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || 'U'}
                      </span>
                    </div>
                    <span className="text-sm text-gray-300">{user.full_name || user.email || 'User'}</span>
                  </button>
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-56 glass-effect neon-border rounded-lg p-2">
                      <div className="px-3 py-2 border-b border-dark-border">
                        <p className="text-sm font-medium text-white">{user.full_name || user.email || 'User'}</p>
                        {user.email && <p className="text-xs text-gray-200">{user.email}</p>}
                        {user.email_verified === false && (
                          <div className="mt-2 flex items-center gap-1">
                            <svg className="w-3 h-3 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            <span className="text-xs text-yellow-400">Email not verified</span>
                          </div>
                        )}
                        {user.email_verified === true && (
                          <div className="mt-2 flex items-center gap-1">
                            <svg className="w-3 h-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            <span className="text-xs text-green-400">Email verified</span>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      >
                        Sign Out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <button
                    onClick={() => router.push('/auth')}
                    className="px-4 py-2 text-gray-300 hover:text-neon-cyan transition-colors bg-transparent border-none cursor-pointer"
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => router.push('/auth')}
                    className="px-4 py-2 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-cyan/50 transition-all"
                  >
                    Get Started
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
      <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
      <ContactModal isOpen={isContactOpen} onClose={() => setIsContactOpen(false)} />
    </>
  )
}

