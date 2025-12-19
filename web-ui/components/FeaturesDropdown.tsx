'use client'

import { useState, useRef, useEffect } from 'react'

interface FeaturesDropdownProps {
  onFeatureSelect: (feature: string) => void
  selectedFeature: string
}

export default function FeaturesDropdown({ onFeatureSelect, selectedFeature }: FeaturesDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const features = [
    { id: 'blog', label: 'Blog Content', icon: '📝' },
    { id: 'social', label: 'Social Media Content', icon: '📱' },
    { id: 'audio', label: 'Audio', icon: '🎵' },
    { id: 'video', label: 'Video Content', icon: '🎬' },
  ]

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const selectedFeatureLabel = features.find(f => f.id === selectedFeature)?.label || 'Features'

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-gray-300 hover:text-neon-cyan transition-colors flex items-center space-x-1 bg-transparent border-none cursor-pointer"
      >
        <span>{selectedFeatureLabel}</span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 glass-effect neon-border rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="py-2">
            {features.map((feature) => (
              <button
                key={feature.id}
                onClick={() => {
                  onFeatureSelect(feature.id)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-4 py-3 flex items-center space-x-3 transition-colors ${
                  selectedFeature === feature.id
                    ? 'bg-neon-purple/20 text-neon-cyan border-l-2 border-neon-cyan'
                    : 'text-gray-300 hover:bg-dark-card hover:text-neon-cyan'
                }`}
              >
                <span className="text-xl">{feature.icon}</span>
                <span className="text-sm font-medium">{feature.label}</span>
                {selectedFeature === feature.id && (
                  <span className="ml-auto text-neon-cyan">✓</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

