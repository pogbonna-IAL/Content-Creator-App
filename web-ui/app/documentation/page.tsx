'use client'

import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function DocumentationPage() {
  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-5xl">
        <div className="glass-effect neon-border rounded-2xl p-8">
          <h1 className="text-4xl font-bold text-gradient mb-4">Product Documentation</h1>
          <p className="text-gray-400 mb-8">
            Everything you need to know about Content Creator - your AI-powered content generation platform
          </p>

          <div className="prose prose-invert max-w-none space-y-12">
            {/* Overview */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">What is Content Creator?</h2>
              <p className="text-gray-400 mb-4">
                Content Creator is an innovative AI-powered platform that helps you create high-quality, comprehensive content for various purposes. Using advanced Multi-Agent System (MAS) technology, multiple AI agents work together collaboratively to research, write, and refine content that meets your specific needs.
              </p>
              <p className="text-gray-400 mb-4">
                Whether you need blog posts, social media content, audio scripts, or video outlines, Content Creator transforms a simple topic into polished, ready-to-use content in minutes.
              </p>
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mt-6">
                <h3 className="text-xl font-semibold text-neon-cyan mb-3">Key Highlights</h3>
                <ul className="list-disc list-inside text-gray-400 space-y-2">
                  <li>AI-powered content generation using multiple specialized agents</li>
                  <li>Support for multiple content types (blog, social media, audio, video)</li>
                  <li>Real-time content streaming as it's being created</li>
                  <li>User-friendly web interface</li>
                  <li>Secure authentication and data protection</li>
                </ul>
              </div>
            </section>

            {/* How It Works */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">How It Works</h2>
              <p className="text-gray-400 mb-6">
                Content Creator uses a sophisticated multi-agent system where different AI agents specialize in different aspects of content creation. Here's how the process works:
              </p>
              
              <div className="space-y-6">
                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon-cyan/20 flex items-center justify-center text-neon-cyan font-bold">
                      1
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-300 mb-2">You Provide a Topic</h3>
                      <p className="text-gray-400">
                        Simply enter a topic or subject you want content about. Be as specific as possible - the more details you provide, the better the results.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon-purple/20 flex items-center justify-center text-neon-purple font-bold">
                      2
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-300 mb-2">AI Agents Research</h3>
                      <p className="text-gray-400">
                        Specialized research agents analyze your topic, gather relevant information, identify key points, and understand the context needed for quality content.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon-cyan/20 flex items-center justify-center text-neon-cyan font-bold">
                      3
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-300 mb-2">Content Creation</h3>
                      <p className="text-gray-400">
                        Writing agents use the research to create comprehensive, well-structured content tailored to your selected content type (blog, social media, audio, or video).
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon-purple/20 flex items-center justify-center text-neon-purple font-bold">
                      4
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-300 mb-2">Review and Refine</h3>
                      <p className="text-gray-400">
                        Quality assurance agents review the content for accuracy, coherence, and completeness. The content is refined and polished before being delivered to you.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon-cyan/20 flex items-center justify-center text-neon-cyan font-bold">
                      5
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-300 mb-2">Receive Your Content</h3>
                      <p className="text-gray-400">
                        Your finished content is delivered in real-time as it's being created. You can copy, edit, and use it immediately for your projects.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Features */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Key Features</h2>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Multiple Content Types</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Generate different types of content from a single topic:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Blog Posts - Long-form articles</li>
                    <li>Social Media - Posts for platforms</li>
                    <li>Audio Scripts - Podcast and narration content</li>
                    <li>Video Scripts - YouTube and video content</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">Real-Time Generation</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Watch your content being created in real-time with:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Live streaming of content</li>
                    <li>Progress indicators</li>
                    <li>Status updates</li>
                    <li>Instant preview</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Multi-Agent Technology</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Advanced MAS technology ensures:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Specialized agents for each task</li>
                    <li>Collaborative content creation</li>
                    <li>Quality assurance</li>
                    <li>Comprehensive research</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">User-Friendly Interface</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Designed for ease of use:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Simple topic input</li>
                    <li>Clean, modern design</li>
                    <li>Easy content management</li>
                    <li>Mobile-responsive</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Secure & Private</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Your data is protected with:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Secure authentication</li>
                    <li>Encrypted data storage</li>
                    <li>GDPR compliance</li>
                    <li>Privacy-first approach</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">Flexible Subscription</h3>
                  <p className="text-gray-400 text-sm mb-3">
                    Choose the plan that fits:
                  </p>
                  <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                    <li>Free tier available</li>
                    <li>Multiple subscription options</li>
                    <li>Pay-as-you-go flexibility</li>
                    <li>Enterprise solutions</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Use Cases */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Who Can Use Content Creator?</h2>
              
              <div className="space-y-4">
                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Content Creators & Bloggers</h3>
                  <p className="text-gray-400">
                    Generate engaging blog posts, articles, and long-form content quickly. Perfect for bloggers, writers, and content creators who need to produce quality content consistently.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Social Media Managers</h3>
                  <p className="text-gray-400">
                    Create social media posts, captions, and content optimized for different platforms. Ideal for social media managers and marketing teams.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Podcasters & Audio Creators</h3>
                  <p className="text-gray-400">
                    Generate scripts and outlines for podcasts, narrations, and audio content. Perfect for podcasters, YouTubers, and audio content creators.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Video Content Creators</h3>
                  <p className="text-gray-400">
                    Create video scripts, outlines, and scene descriptions. Ideal for YouTubers, video producers, and content creators.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Marketing Agencies</h3>
                  <p className="text-gray-400">
                    Scale content creation for multiple clients. Generate various content types quickly and efficiently for marketing campaigns.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-gray-300 mb-3">Businesses & Entrepreneurs</h3>
                  <p className="text-gray-400">
                    Create content for websites, marketing materials, and communications. Perfect for businesses that need regular content but don't have dedicated content teams.
                  </p>
                </div>
              </div>
            </section>

            {/* Content Types Explained */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Content Types Explained</h2>
              
              <div className="space-y-6">
                <div className="bg-gradient-to-r from-neon-cyan/10 to-transparent p-6 rounded-lg border border-neon-cyan/30">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Blog Posts</h3>
                  <p className="text-gray-400 mb-3">
                    Comprehensive, long-form articles perfect for websites, blogs, and publications. These are well-researched, structured pieces with introductions, detailed body content, and conclusions.
                  </p>
                  <p className="text-gray-400 text-sm">
                    <strong className="text-white">Best for:</strong> Website content, blog articles, educational content, thought leadership pieces
                  </p>
                </div>

                <div className="bg-gradient-to-r from-neon-purple/10 to-transparent p-6 rounded-lg border border-neon-purple/30">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">Social Media Content</h3>
                  <p className="text-gray-400 mb-3">
                    Optimized posts designed for social media platforms. These are concise, engaging, and formatted for maximum impact on platforms like Twitter, LinkedIn, Facebook, and Instagram.
                  </p>
                  <p className="text-gray-400 text-sm">
                    <strong className="text-white">Best for:</strong> Social media posts, tweets, LinkedIn updates, Instagram captions
                  </p>
                </div>

                <div className="bg-gradient-to-r from-neon-cyan/10 to-transparent p-6 rounded-lg border border-neon-cyan/30">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Audio Content</h3>
                  <p className="text-gray-400 mb-3">
                    Scripts and content designed for audio delivery. These use conversational language, natural speech patterns, and are structured for easy narration or podcast delivery.
                  </p>
                  <p className="text-gray-400 text-sm">
                    <strong className="text-white">Best for:</strong> Podcast scripts, audio narrations, voice-over content, audio courses
                  </p>
                </div>

                <div className="bg-gradient-to-r from-neon-purple/10 to-transparent p-6 rounded-lg border border-neon-purple/30">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">Video Content</h3>
                  <p className="text-gray-400 mb-3">
                    Scripts and outlines designed for video production. These include scene descriptions, visual cues, engaging hooks, and action-oriented language perfect for video content.
                  </p>
                  <p className="text-gray-400 text-sm">
                    <strong className="text-white">Best for:</strong> YouTube videos, video scripts, video outlines, video courses
                  </p>
                </div>
              </div>
            </section>

            {/* Getting Started */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Getting Started</h2>
              <p className="text-gray-400 mb-6">
                Ready to start creating content? Here's what you need to know:
              </p>
              
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-lg font-semibold text-gray-300 mb-4">Quick Start Guide</h3>
                <ol className="list-decimal list-inside text-gray-400 space-y-3 ml-4">
                  <li><strong className="text-white">Create an Account:</strong> Sign up for free or choose a subscription plan</li>
                  <li><strong className="text-white">Enter Your Topic:</strong> Provide a clear, specific topic for your content</li>
                  <li><strong className="text-white">Select Content Type:</strong> Choose blog, social media, audio, or video</li>
                  <li><strong className="text-white">Generate Content:</strong> Click generate and watch your content being created</li>
                  <li><strong className="text-white">Review & Use:</strong> Review the content, make any edits, and use it for your projects</li>
                </ol>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/30 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-blue-400 mb-3">💡 Pro Tips</h3>
                <ul className="list-disc list-inside text-gray-400 space-y-2 ml-4">
                  <li>Be specific with your topics - include context and key points you want covered</li>
                  <li>Try different content types for the same topic to see what works best</li>
                  <li>Review and edit generated content to add your personal touch</li>
                  <li>Use the content as a starting point and customize it for your audience</li>
                </ul>
              </div>
            </section>

            {/* Technology */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Technology Behind Content Creator</h2>
              <p className="text-gray-400 mb-4">
                Content Creator is powered by advanced Multi-Agent System (MAS) technology. This innovative approach uses multiple specialized AI agents that work together collaboratively, each focusing on their area of expertise:
              </p>
              
              <div className="grid md:grid-cols-2 gap-4 mt-6">
                <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
                  <h4 className="font-semibold text-gray-300 mb-2">Research Agents</h4>
                  <p className="text-gray-400 text-sm">Specialize in gathering and analyzing information</p>
                </div>
                <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
                  <h4 className="font-semibold text-gray-300 mb-2">Writing Agents</h4>
                  <p className="text-gray-400 text-sm">Focus on creating well-structured, engaging content</p>
                </div>
                <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
                  <h4 className="font-semibold text-gray-300 mb-2">Quality Agents</h4>
                  <p className="text-gray-400 text-sm">Ensure accuracy, coherence, and completeness</p>
                </div>
                <div className="bg-dark-card p-4 rounded-lg border border-dark-border">
                  <h4 className="font-semibold text-gray-300 mb-2">Specialized Agents</h4>
                  <p className="text-gray-400 text-sm">Handle specific content types and formats</p>
                </div>
              </div>
            </section>

            {/* Support & Resources */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Support & Resources</h2>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-cyan mb-3">Need Help?</h3>
                  <ul className="space-y-2 text-gray-400 text-sm">
                    <li>📖 <a href="/docs" className="text-neon-cyan hover:underline">User Guide</a> - Step-by-step instructions</li>
                    <li>📧 Contact Support - Use the contact form</li>
                    <li>💬 FAQ - Check our frequently asked questions</li>
                  </ul>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-xl font-semibold text-neon-purple mb-3">Learn More</h3>
                  <ul className="space-y-2 text-gray-400 text-sm">
                    <li>🔒 <a href="/privacy" className="text-neon-purple hover:underline">Privacy Policy</a></li>
                    <li>📋 <a href="/terms" className="text-neon-purple hover:underline">Terms of Service</a></li>
                    <li>🍪 <a href="/cookies" className="text-neon-purple hover:underline">Cookie Policy</a></li>
                  </ul>
                </div>
              </div>
            </section>

            {/* FAQ */}
            <section>
              <h2 className="text-3xl font-bold text-gradient mb-4">Frequently Asked Questions</h2>
              
              <div className="space-y-4">
                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-lg font-semibold text-gray-300 mb-2">How long does content generation take?</h3>
                  <p className="text-gray-400 text-sm">
                    Typically 5-15 minutes depending on the complexity of the topic and the type of content requested. You can watch the progress in real-time.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-lg font-semibold text-gray-300 mb-2">Is the content original?</h3>
                  <p className="text-gray-400 text-sm">
                    Yes, all content is generated uniquely based on your topic. However, we recommend reviewing and editing the content to ensure it meets your specific needs and style.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-lg font-semibold text-gray-300 mb-2">Can I edit the generated content?</h3>
                  <p className="text-gray-400 text-sm">
                    Absolutely! The generated content is yours to use, edit, and customize as needed. We encourage you to add your personal touch and brand voice.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-lg font-semibold text-gray-300 mb-2">What topics work best?</h3>
                  <p className="text-gray-400 text-sm">
                    Specific, well-defined topics produce the best results. Include context, target audience, and key points you want covered for optimal content quality.
                  </p>
                </div>

                <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                  <h3 className="text-lg font-semibold text-gray-300 mb-2">Is my data secure?</h3>
                  <p className="text-gray-400 text-sm">
                    Yes, we take data security seriously. Your information is encrypted, stored securely, and we comply with GDPR and other privacy regulations. See our <a href="/privacy" className="text-neon-cyan hover:underline">Privacy Policy</a> for details.
                  </p>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}

