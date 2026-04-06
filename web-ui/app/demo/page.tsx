'use client'

import { useState } from 'react'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export const dynamic = 'force-dynamic'

export default function DemoLandingPage() {
  const [selectedFeature, setSelectedFeature] = useState('blog')

  return (
    <main className="min-h-screen flex flex-col">
      <Navbar selectedFeature={selectedFeature} onFeatureSelect={setSelectedFeature} />
      <div className="flex-1">
        <section className="container mx-auto px-4 py-16 md:py-20 max-w-3xl">
          <p className="text-sm font-medium text-neon-cyan uppercase tracking-wide mb-3">
            Portfolio & evaluation
          </p>
          <h1 className="text-3xl md:text-4xl font-bold mb-4 text-balance">
            Try the live product
          </h1>
          <p className="text-lg text-white/80 mb-8 leading-relaxed">
            This route is the public entry for recruiters, clients, and collaborators who want to
            verify the platform firsthand—streaming generation, multi-format outputs, and the same
            product surface users see in production.
          </p>

          <div className="rounded-xl border border-dark-border bg-white/5 p-6 md:p-8 mb-10">
            <h2 className="text-lg font-semibold mb-3">What you will see</h2>
            <ul className="list-disc list-inside space-y-2 text-white/85 text-sm md:text-base">
              <li>Real-time progress as AI agents collaborate on your topic</li>
              <li>Blog, social, audio-oriented, and video-oriented outputs in one flow</li>
              <li>The same authentication and API behavior as the deployed app</li>
            </ul>
            <p className="mt-4 text-sm text-white/65">
              Create a free account if prompted—no payment is required to explore core generation.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 sm:items-center">
            <Link
              href="/"
              className="inline-flex justify-center items-center rounded-lg px-6 py-3 font-semibold bg-gradient-to-r from-neon-cyan to-neon-purple text-dark-bg hover:opacity-90 transition-opacity"
            >
              Open the application
            </Link>
            <Link
              href="/auth"
              className="inline-flex justify-center items-center rounded-lg px-6 py-3 font-semibold border border-dark-border text-white hover:bg-white/5 transition-colors"
            >
              Sign in or create an account
            </Link>
          </div>
          <p className="mt-8 text-sm text-white/55">
            Deployed URL: use your production base (for example your Railway or custom domain), then{' '}
            <code className="text-neon-cyan/90">/demo</code> for this page or <code className="text-neon-cyan/90">/</code>{' '}
            to go straight to the app.
          </p>
        </section>
      </div>
      <Footer />
    </main>
  )
}
