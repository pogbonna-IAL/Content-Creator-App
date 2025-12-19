'use client'

import { useState } from 'react'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState<string>('getting-started')

  const sections = [
    { id: 'getting-started', title: 'Getting Started' },
    { id: 'account', title: 'Creating Your Account' },
    { id: 'generating', title: 'Generating Content' },
    { id: 'content-types', title: 'Content Types' },
    { id: 'managing', title: 'Managing Your Content' },
    { id: 'tips', title: 'Tips for Best Results' },
    { id: 'troubleshooting', title: 'Troubleshooting' },
  ]

  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-5xl">
        <div className="glass-effect neon-border rounded-2xl p-8">
          <h1 className="text-4xl font-bold text-gradient mb-4">User Guide</h1>
          <p className="text-gray-400 mb-8">
            Complete step-by-step guide to using Content Creator
          </p>

          {/* Table of Contents */}
          <div className="mb-8 p-6 bg-dark-card rounded-lg border border-dark-border">
            <h2 className="text-xl font-semibold text-gray-300 mb-4">Table of Contents</h2>
            <ul className="space-y-2">
              {sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    onClick={(e) => {
                      e.preventDefault()
                      setActiveSection(section.id)
                      document.getElementById(section.id)?.scrollIntoView({ behavior: 'smooth' })
                    }}
                    className="text-neon-cyan hover:text-neon-purple transition-colors"
                  >
                    {section.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Getting Started */}
          <section id="getting-started" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Getting Started</h2>
            <div className="prose prose-invert max-w-none">
              <h3 className="text-xl font-semibold text-gray-300 mb-3">Prerequisites</h3>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-6">
                <li>A modern web browser (Chrome, Firefox, Safari, or Edge)</li>
                <li>An active internet connection</li>
                <li>JavaScript enabled in your browser</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Accessing the Application</h3>
              <ol className="list-decimal list-inside text-gray-400 space-y-2">
                <li>Open your web browser</li>
                <li>Navigate to the Content Creator application URL</li>
                <li>You'll be redirected to the authentication page if you're not logged in</li>
              </ol>
            </div>
          </section>

          {/* Creating Your Account */}
          <section id="account" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Creating Your Account</h2>
            <div className="prose prose-invert max-w-none">
              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 1: Sign Up</h3>
              <ol className="list-decimal list-inside text-gray-400 space-y-2 mb-6">
                <li>On the authentication page, you'll see a <strong className="text-white">Sign Up</strong> form</li>
                <li>Enter your email address</li>
                <li>Create a password (must be at least 8 characters)</li>
                <li>Optionally, enter your full name</li>
                <li>Click the <strong className="text-white">Sign Up</strong> button</li>
              </ol>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 2: Verify Your Account</h3>
              <p className="text-gray-400 mb-6">
                After successful signup, you'll be automatically logged in. Your account is created and ready to use immediately.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Alternative: Log In</h3>
              <p className="text-gray-400 mb-3">If you already have an account:</p>
              <ol className="list-decimal list-inside text-gray-400 space-y-2 mb-6">
                <li>Click on the <strong className="text-white">Log In</strong> tab</li>
                <li>Enter your email address</li>
                <li>Enter your password</li>
                <li>Click the <strong className="text-white">Log In</strong> button</li>
              </ol>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">OAuth Login (Optional)</h3>
              <p className="text-gray-400">
                You can also sign in using Google, Facebook, or GitHub by clicking the respective buttons on the login page.
              </p>
            </div>
          </section>

          {/* Generating Content */}
          <section id="generating" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Generating Content</h2>
            <div className="prose prose-invert max-w-none">
              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 1: Enter Your Topic</h3>
              <ol className="list-decimal list-inside text-gray-400 space-y-2 mb-6">
                <li>Once logged in, you'll see the main dashboard</li>
                <li>In the <strong className="text-white">Input Panel</strong> on the left side, enter your topic</li>
                <li>Enter a clear, specific topic for your content</li>
              </ol>

              <div className="bg-dark-card p-4 rounded-lg mb-6 border border-dark-border">
                <p className="text-sm font-semibold text-gray-300 mb-2">Good examples:</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 mb-3">
                  <li>"The benefits of renewable energy for small businesses"</li>
                  <li>"Latest trends in artificial intelligence for 2024"</li>
                  <li>"How to start a successful e-commerce business"</li>
                </ul>
                <p className="text-sm font-semibold text-gray-300 mb-2">Avoid vague topics:</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
                  <li>"Technology" (too broad)</li>
                  <li>"Stuff" (not specific)</li>
                </ul>
              </div>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 2: Select Content Type</h3>
              <p className="text-gray-400 mb-6">
                Use the <strong className="text-white">Features</strong> dropdown in the navigation bar to select what type of content you want to generate: Blog Post, Social Media, Audio, or Video.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 3: Generate Content</h3>
              <ol className="list-decimal list-inside text-gray-400 space-y-2 mb-6">
                <li>After entering your topic, click the <strong className="text-white">Generate Content</strong> button</li>
                <li>You'll see a loading indicator and status messages showing progress</li>
                <li>Content will stream in real-time as it's generated</li>
                <li>A progress bar shows the completion percentage</li>
              </ol>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">Step 4: Review Your Content</h3>
              <p className="text-gray-400">
                Once generation is complete, your content will appear in the <strong className="text-white">Output Panel</strong> on the right. The content is automatically displayed and you can scroll through the full content.
              </p>
            </div>
          </section>

          {/* Content Types */}
          <section id="content-types" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Content Types</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-xl font-semibold text-neon-cyan mb-3">Blog Posts</h3>
                <p className="text-gray-400 mb-3"><strong className="text-white">Best for:</strong> Long-form articles, blog posts</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
                  <li>Comprehensive research and analysis</li>
                  <li>Well-structured with introduction, body, conclusion</li>
                  <li>Detailed insights and key points</li>
                  <li>Professional writing style</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-xl font-semibold text-neon-purple mb-3">Social Media Content</h3>
                <p className="text-gray-400 mb-3"><strong className="text-white">Best for:</strong> Social media posts, tweets, LinkedIn posts</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
                  <li>Optimized for social platforms</li>
                  <li>Engaging and shareable format</li>
                  <li>Concise and impactful messaging</li>
                  <li>Platform-appropriate formatting</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-xl font-semibold text-neon-cyan mb-3">Audio Content</h3>
                <p className="text-gray-400 mb-3"><strong className="text-white">Best for:</strong> Podcast scripts, audio narrations</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
                  <li>Conversational tone</li>
                  <li>Natural speech patterns</li>
                  <li>Clear structure for audio delivery</li>
                  <li>Engaging storytelling elements</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-xl font-semibold text-neon-purple mb-3">Video Content</h3>
                <p className="text-gray-400 mb-3"><strong className="text-white">Best for:</strong> Video scripts, YouTube content</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1">
                  <li>Visual descriptions and scene setups</li>
                  <li>Engaging hooks and transitions</li>
                  <li>Structured for video production</li>
                  <li>Action-oriented language</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Tips */}
          <section id="tips" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Tips for Best Results</h2>
            <div className="space-y-4">
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">1. Be Specific with Topics</h3>
                <p className="text-gray-400 text-sm mb-2">✅ <strong>Good:</strong> "5 ways to improve productivity using AI tools in 2024"</p>
                <p className="text-gray-400 text-sm">❌ <strong>Bad:</strong> "Productivity"</p>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">2. Provide Context</h3>
                <p className="text-gray-400 text-sm">Include relevant details like target audience, purpose, key points, and desired tone.</p>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">3. Be Patient</h3>
                <p className="text-gray-400 text-sm">Content generation can take several minutes. The AI agents are researching and creating comprehensive content. Don't refresh the page during generation.</p>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">4. Review and Edit</h3>
                <p className="text-gray-400 text-sm">Always review generated content, edit as needed for your specific use case, and add your personal touch and brand voice.</p>
              </div>
            </div>
          </section>

          {/* Troubleshooting */}
          <section id="troubleshooting" className="mb-12">
            <h2 className="text-3xl font-bold text-gradient mb-4">Troubleshooting</h2>
            <div className="space-y-4">
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-red-400 mb-2">"Authentication failed" Error</h3>
                <p className="text-gray-400 text-sm mb-2"><strong>Solutions:</strong></p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                  <li>Log out and log back in</li>
                  <li>Clear your browser cookies and cache</li>
                  <li>Ensure your session hasn't expired</li>
                  <li>Try using a different browser</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-red-400 mb-2">"Connection terminated" Error</h3>
                <p className="text-gray-400 text-sm mb-2"><strong>Solutions:</strong></p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                  <li>Check your internet connection</li>
                  <li>Ensure the backend server is running</li>
                  <li>Try generating again with a simpler topic</li>
                  <li>Check server logs for detailed error messages</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-red-400 mb-2">Content Not Generating</h3>
                <p className="text-gray-400 text-sm mb-2"><strong>Solutions:</strong></p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                  <li>Ensure you've entered a topic</li>
                  <li>Check that you're logged in</li>
                  <li>Refresh the page and try again</li>
                  <li>Check browser console for error messages</li>
                </ul>
              </div>

              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <h3 className="text-lg font-semibold text-yellow-400 mb-2">Slow Generation</h3>
                <p className="text-gray-400 text-sm mb-2"><strong>Note:</strong> This is normal - comprehensive content can take 5-15 minutes.</p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                  <li>Check the status messages for progress updates</li>
                  <li>Ensure Ollama is running (for local installations)</li>
                  <li>Try with a simpler, more focused topic</li>
                </ul>
              </div>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}

