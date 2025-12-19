'use client'

import { useState, useEffect } from 'react'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function CookiesPage() {
  const [lastUpdated, setLastUpdated] = useState<string>('')

  useEffect(() => {
    // Format date consistently on client side to avoid hydration mismatch
    const date = new Date()
    const formattedDate = date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
    setLastUpdated(formattedDate)
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        <div className="glass-effect neon-border rounded-2xl p-8">
          <h1 className="text-4xl font-bold text-gradient mb-4">Cookie Policy</h1>
          <p className="text-gray-400 mb-2">Last Updated: {lastUpdated || 'Loading...'}</p>
          <p className="text-gray-400 mb-8">
            This Cookie Policy explains how Content Creator by Patrick Ogbonna ("we", "our", or "us") uses cookies and similar tracking technologies in compliance with the General Data Protection Regulation (GDPR) and other applicable privacy laws.
          </p>

          <div className="prose prose-invert max-w-none space-y-8">
            {/* Introduction */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">1. What Are Cookies?</h2>
              <p className="text-gray-400 mb-4">
                Cookies are small text files that are placed on your device (computer, tablet, or mobile) when you visit a website. They are widely used to make websites work more efficiently and provide information to website owners.
              </p>
              <p className="text-gray-400">
                Cookies allow a website to recognize your device and store some information about your preferences or past actions. This helps us provide you with a better experience when you browse our website and allows us to improve our services.
              </p>
            </section>

            {/* GDPR Compliance */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">2. GDPR Compliance and Your Consent</h2>
              <p className="text-gray-400 mb-4">
                Under the GDPR, we are required to obtain your consent before placing non-essential cookies on your device. We comply with GDPR requirements by:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li>Providing clear information about the cookies we use</li>
                <li>Obtaining your explicit consent for non-essential cookies</li>
                <li>Allowing you to withdraw consent at any time</li>
                <li>Providing easy-to-use cookie management tools</li>
                <li>Respecting your privacy preferences</li>
              </ul>
              <div className="bg-blue-500/10 border border-blue-500/30 p-4 rounded-lg mb-4">
                <p className="text-blue-400 text-sm">
                  <strong>Your Rights:</strong> You have the right to accept or reject non-essential cookies. You can change your cookie preferences at any time through your browser settings or our cookie consent manager.
                </p>
              </div>
            </section>

            {/* Types of Cookies */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">3. Types of Cookies We Use</h2>
              <p className="text-gray-400 mb-6">
                We use different types of cookies for various purposes. Cookies are categorized as follows:
              </p>

              {/* Essential Cookies */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-green-400 mb-4">3.1 Essential Cookies (Strictly Necessary)</h3>
                <p className="text-gray-400 mb-4">
                  These cookies are essential for the website to function properly and cannot be switched off. They are usually set in response to actions you take, such as logging in or filling in forms.
                </p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Legal Basis:</strong> Legitimate interest (Article 6(1)(f) GDPR) - necessary for the performance of a contract</p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Consent Required:</strong> No (these cookies are necessary for the service to function)</p>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-gray-400 mt-4">
                    <thead>
                      <tr className="border-b border-dark-border">
                        <th className="text-left py-2 px-4 text-gray-300">Cookie Name</th>
                        <th className="text-left py-2 px-4 text-gray-300">Purpose</th>
                        <th className="text-left py-2 px-4 text-gray-300">Duration</th>
                        <th className="text-left py-2 px-4 text-gray-300">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">auth_token</td>
                        <td className="py-2 px-4">Stores authentication token to maintain your login session</td>
                        <td className="py-2 px-4">7 days</td>
                        <td className="py-2 px-4">HTTP Only</td>
                      </tr>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">auth_user</td>
                        <td className="py-2 px-4">Stores user information for session management</td>
                        <td className="py-2 px-4">7 days</td>
                        <td className="py-2 px-4">HTTP Only</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-mono text-xs">session_id</td>
                        <td className="py-2 px-4">Maintains session state and security</td>
                        <td className="py-2 px-4">Session</td>
                        <td className="py-2 px-4">HTTP Only, Secure</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Functional Cookies */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-blue-400 mb-4">3.2 Functional Cookies</h3>
                <p className="text-gray-400 mb-4">
                  These cookies enable enhanced functionality and personalization. They remember choices you make (such as your language preference) and provide enhanced, more personalized features.
                </p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Legal Basis:</strong> Consent (Article 6(1)(a) GDPR)</p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Consent Required:</strong> Yes</p>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-gray-400 mt-4">
                    <thead>
                      <tr className="border-b border-dark-border">
                        <th className="text-left py-2 px-4 text-gray-300">Cookie Name</th>
                        <th className="text-left py-2 px-4 text-gray-300">Purpose</th>
                        <th className="text-left py-2 px-4 text-gray-300">Duration</th>
                        <th className="text-left py-2 px-4 text-gray-300">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">user_preferences</td>
                        <td className="py-2 px-4">Stores your UI preferences (theme, layout, etc.)</td>
                        <td className="py-2 px-4">1 year</td>
                        <td className="py-2 px-4">First-party</td>
                      </tr>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">language</td>
                        <td className="py-2 px-4">Remembers your language preference</td>
                        <td className="py-2 px-4">1 year</td>
                        <td className="py-2 px-4">First-party</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-mono text-xs">remember_me</td>
                        <td className="py-2 px-4">Remembers your "Remember Me" preference for login</td>
                        <td className="py-2 px-4">1 year</td>
                        <td className="py-2 px-4">First-party</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Analytics Cookies */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-purple-400 mb-4">3.3 Analytics Cookies</h3>
                <p className="text-gray-400 mb-4">
                  These cookies help us understand how visitors interact with our website by collecting and reporting information anonymously. This helps us improve the way our website works.
                </p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Legal Basis:</strong> Consent (Article 6(1)(a) GDPR)</p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Consent Required:</strong> Yes</p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Data Processing:</strong> Analytics data is anonymized and aggregated</p>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-gray-400 mt-4">
                    <thead>
                      <tr className="border-b border-dark-border">
                        <th className="text-left py-2 px-4 text-gray-300">Cookie Name</th>
                        <th className="text-left py-2 px-4 text-gray-300">Purpose</th>
                        <th className="text-left py-2 px-4 text-gray-300">Duration</th>
                        <th className="text-left py-2 px-4 text-gray-300">Provider</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">_ga</td>
                        <td className="py-2 px-4">Google Analytics - distinguishes unique users</td>
                        <td className="py-2 px-4">2 years</td>
                        <td className="py-2 px-4">Google (Third-party)</td>
                      </tr>
                      <tr className="border-b border-dark-border/50">
                        <td className="py-2 px-4 font-mono text-xs">_gid</td>
                        <td className="py-2 px-4">Google Analytics - distinguishes unique users</td>
                        <td className="py-2 px-4">24 hours</td>
                        <td className="py-2 px-4">Google (Third-party)</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-4 font-mono text-xs">_gat</td>
                        <td className="py-2 px-4">Google Analytics - throttles request rate</td>
                        <td className="py-2 px-4">1 minute</td>
                        <td className="py-2 px-4">Google (Third-party)</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="text-gray-400 text-sm mt-4">
                  <strong className="text-white">Note:</strong> We use Google Analytics with IP anonymization enabled. Your IP address is anonymized before being sent to Google.
                </p>
              </div>

              {/* Marketing Cookies */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-yellow-400 mb-4">3.4 Marketing/Advertising Cookies</h3>
                <p className="text-gray-400 mb-4">
                  These cookies are used to deliver advertisements and track campaign performance. They may be set by our advertising partners to build a profile of your interests.
                </p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Legal Basis:</strong> Consent (Article 6(1)(a) GDPR)</p>
                <p className="text-gray-400 mb-4"><strong className="text-white">Consent Required:</strong> Yes</p>
                <p className="text-gray-400 mb-4">
                  <strong className="text-white">Current Status:</strong> We do not currently use marketing/advertising cookies. This section is included for future reference and compliance.
                </p>
              </div>
            </section>

            {/* Third-Party Cookies */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">4. Third-Party Cookies</h2>
              <p className="text-gray-400 mb-4">
                In addition to our own cookies, we may also use various third-party cookies to report usage statistics and deliver advertisements. These third parties may set their own cookies:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Google Analytics:</strong> For website analytics (with IP anonymization)</li>
                <li><strong className="text-white">OAuth Providers:</strong> Google, Facebook, GitHub (for authentication only)</li>
                <li><strong className="text-white">Payment Processors:</strong> Stripe, PayPal (for subscription payments)</li>
              </ul>
              <p className="text-gray-400 mb-4">
                These third parties have their own privacy policies and cookie policies. We encourage you to review their policies:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">Google Privacy Policy</a></li>
                <li><a href="https://stripe.com/privacy" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">Stripe Privacy Policy</a></li>
              </ul>
            </section>

            {/* Managing Cookies */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">5. How to Manage Cookies</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.1 Cookie Consent Manager</h3>
              <p className="text-gray-400 mb-4">
                You can manage your cookie preferences at any time through our cookie consent manager, which appears when you first visit our website or can be accessed through your account settings.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.2 Browser Settings</h3>
              <p className="text-gray-400 mb-4">
                Most web browsers allow you to control cookies through their settings. You can set your browser to refuse cookies or delete certain cookies. However, blocking or deleting cookies may impact your user experience.
              </p>
              <p className="text-gray-400 mb-4"><strong className="text-white">Browser-specific instructions:</strong></p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Chrome:</strong> Settings → Privacy and Security → Cookies and other site data</li>
                <li><strong className="text-white">Firefox:</strong> Options → Privacy & Security → Cookies and Site Data</li>
                <li><strong className="text-white">Safari:</strong> Preferences → Privacy → Cookies and website data</li>
                <li><strong className="text-white">Edge:</strong> Settings → Privacy, search, and services → Cookies and site permissions</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.3 Opt-Out Tools</h3>
              <p className="text-gray-400 mb-4">
                You can opt-out of certain third-party cookies:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">Google Analytics Opt-Out</a></li>
                <li><a href="https://www.youronlinechoices.com/" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">Your Online Choices (EU)</a></li>
                <li><a href="https://optout.networkadvertising.org/" target="_blank" rel="noopener noreferrer" className="text-neon-cyan hover:underline">Network Advertising Initiative</a></li>
              </ul>

              <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 rounded-lg mb-4">
                <p className="text-yellow-400 text-sm">
                  <strong>Important:</strong> Blocking essential cookies may prevent you from accessing certain features of our website, including logging in and using core functionality.
                </p>
              </div>
            </section>

            {/* GDPR Rights */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">6. Your GDPR Rights Regarding Cookies</h2>
              <p className="text-gray-400 mb-4">
                Under the GDPR, you have the following rights regarding cookies and your personal data:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Right to Information:</strong> You have the right to be informed about the cookies we use (this policy)</li>
                <li><strong className="text-white">Right to Consent:</strong> You have the right to give or withdraw consent for non-essential cookies</li>
                <li><strong className="text-white">Right to Access:</strong> You can request information about what cookies are stored on your device</li>
                <li><strong className="text-white">Right to Object:</strong> You can object to the use of cookies for certain purposes</li>
                <li><strong className="text-white">Right to Erasure:</strong> You can delete cookies stored on your device at any time</li>
                <li><strong className="text-white">Right to Data Portability:</strong> You can request a copy of your cookie data</li>
              </ul>
              <p className="text-gray-400">
                To exercise these rights, please contact us using the information provided in the Contact section below.
              </p>
            </section>

            {/* Cookie Duration */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">7. Cookie Duration</h2>
              <p className="text-gray-400 mb-4">
                Cookies can be either "persistent" or "session" cookies:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Session Cookies:</strong> Temporary cookies that expire when you close your browser</li>
                <li><strong className="text-white">Persistent Cookies:</strong> Remain on your device for a set period or until you delete them</li>
              </ul>
              <p className="text-gray-400">
                The duration of each cookie is specified in the cookie tables above. We regularly review and update cookie expiration periods to ensure they are appropriate for their purpose.
              </p>
            </section>

            {/* Updates to Cookie Policy */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">8. Updates to This Cookie Policy</h2>
              <p className="text-gray-400 mb-4">
                We may update this Cookie Policy from time to time to reflect changes in our practices or for other operational, legal, or regulatory reasons. We will notify you of any material changes by:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li>Posting the updated Cookie Policy on this page</li>
                <li>Updating the "Last Updated" date</li>
                <li>Displaying a notice on our website</li>
                <li>Sending email notifications (for significant changes)</li>
              </ul>
              <p className="text-gray-400">
                We encourage you to review this Cookie Policy periodically to stay informed about our use of cookies.
              </p>
            </section>

            {/* Data Retention */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">9. Data Retention</h2>
              <p className="text-gray-400 mb-4">
                Cookie data is retained according to the duration specified for each cookie type:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li>Essential cookies: Retained for the duration necessary to provide the service</li>
                <li>Functional cookies: Retained for up to 1 year or until you delete them</li>
                <li>Analytics cookies: Retained according to the third-party provider's retention policy (typically 2 years)</li>
                <li>Marketing cookies: Retained according to the third-party provider's retention policy</li>
              </ul>
              <p className="text-gray-400">
                You can delete cookies at any time through your browser settings, which will immediately remove them from your device.
              </p>
            </section>

            {/* Security */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">10. Cookie Security</h2>
              <p className="text-gray-400 mb-4">
                We take the security of cookies seriously and implement various security measures:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li>HTTP Only cookies to prevent JavaScript access</li>
                <li>Secure flag for HTTPS-only transmission</li>
                <li>SameSite attribute to prevent cross-site request forgery</li>
                <li>Encryption of sensitive cookie data</li>
                <li>Regular security audits</li>
              </ul>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">11. Contact Us</h2>
              <p className="text-gray-400 mb-4">
                If you have any questions about this Cookie Policy or wish to exercise your GDPR rights regarding cookies, please contact us:
              </p>
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <p className="text-gray-300 mb-2"><strong>Content Creator by Patrick Ogbonna</strong></p>
                <p className="text-gray-400 text-sm mb-2">
                  You can reach us through:
                </p>
                <ul className="list-disc list-inside text-gray-400 text-sm space-y-1 ml-4">
                  <li>The Contact form in the application</li>
                  <li>Email support (for paid tier subscribers)</li>
                  <li>GitHub Issues (for technical questions)</li>
                </ul>
                <p className="text-gray-400 text-sm mt-4">
                  <strong>Data Protection Officer:</strong> For GDPR-related inquiries, please use the contact form and specify "GDPR Cookie Inquiry" in your message.
                </p>
              </div>
            </section>

            {/* Additional Information */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">12. Additional Information</h2>
              <p className="text-gray-400 mb-4">
                For more information about how we handle your personal data, please refer to our:
              </p>
              <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4 ml-4">
                <li><a href="/privacy" className="text-neon-cyan hover:underline">Privacy Policy</a></li>
                <li><a href="/terms" className="text-neon-cyan hover:underline">Terms of Service</a></li>
              </ul>
              <p className="text-gray-400">
                This Cookie Policy should be read in conjunction with our Privacy Policy, which provides more detailed information about our data processing practices.
              </p>
            </section>
          </div>

          <div className="mt-8 pt-8 border-t border-dark-border">
            <div className="bg-blue-500/10 border border-blue-500/30 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-blue-400 mb-3">Quick Cookie Preferences</h3>
              <p className="text-gray-400 text-sm mb-4">
                You can manage your cookie preferences at any time. Essential cookies cannot be disabled as they are necessary for the website to function.
              </p>
              <div className="flex flex-wrap gap-3">
                <button className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan rounded-lg hover:bg-neon-cyan/30 transition-colors text-sm">
                  Manage Cookie Preferences
                </button>
                <a href="/privacy" className="px-4 py-2 bg-dark-card text-gray-300 rounded-lg hover:bg-dark-border transition-colors text-sm border border-dark-border">
                  View Privacy Policy
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}

