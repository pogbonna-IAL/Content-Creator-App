'use client'

import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        <div className="glass-effect neon-border rounded-2xl p-8">
          <h1 className="text-4xl font-bold text-gradient mb-4">Privacy Policy</h1>
          <p className="text-gray-200 mb-2">Last Updated: December 18, 2024</p>
          <p className="text-gray-200 mb-8">
            Content Creator by Patrick Ogbonna is an open source project. This privacy policy explains how we handle your data.
          </p>

          <div className="prose prose-invert max-w-none space-y-8">
            {/* Introduction */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">1. Introduction</h2>
              <p className="text-gray-200 mb-4">
                Content Creator ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our open source application.
              </p>
              <p className="text-gray-200">
                As an open source project, we believe in transparency and user privacy. We collect minimal data necessary to provide our services.
              </p>
            </section>

            {/* Information We Collect */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">2. Information We Collect</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">2.1 Account Information</h3>
              <p className="text-gray-200 mb-4">
                When you create an account, we collect:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Email address (required for account creation)</li>
                <li>Password (stored securely using industry-standard hashing)</li>
                <li>Full name (optional, if provided)</li>
                <li>Authentication provider information (if using OAuth)</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">2.2 Usage Information</h3>
              <p className="text-gray-200 mb-4">
                We may collect information about how you use our service:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Topics you generate content for</li>
                <li>Content types you select</li>
                <li>Timestamps of your activities</li>
                <li>Error logs and debugging information</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">2.3 Technical Information</h3>
              <p className="text-gray-200 mb-4">
                Automatically collected technical information:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>IP address (for security and debugging purposes)</li>
                <li>Browser type and version</li>
                <li>Device information</li>
                <li>Cookies and similar tracking technologies</li>
              </ul>
            </section>

            {/* How We Use Information */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">3. How We Use Your Information</h2>
              <p className="text-gray-200 mb-4">
                We use the collected information for the following purposes:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Service Provision:</strong> To provide, maintain, and improve our content generation services</li>
                <li><strong className="text-white">Authentication:</strong> To authenticate your identity and manage your account</li>
                <li><strong className="text-white">Communication:</strong> To respond to your inquiries and provide customer support</li>
                <li><strong className="text-white">Security:</strong> To detect, prevent, and address technical issues and security threats</li>
                <li><strong className="text-white">Analytics:</strong> To understand usage patterns and improve our services (anonymized where possible)</li>
                <li><strong className="text-white">Legal Compliance:</strong> To comply with applicable laws and regulations</li>
              </ul>
            </section>

            {/* Data Storage and Security */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">4. Data Storage and Security</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.1 Data Storage</h3>
              <p className="text-gray-200 mb-4">
                Your data is stored securely using industry-standard practices:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Passwords are hashed using bcrypt before storage</li>
                <li>Database connections are encrypted</li>
                <li>Data is stored in secure databases with access controls</li>
                <li>Regular backups are performed to prevent data loss</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.2 Security Measures</h3>
              <p className="text-gray-200 mb-4">
                We implement various security measures to protect your information:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Encryption of data in transit (HTTPS/TLS)</li>
                <li>Secure authentication tokens (JWT)</li>
                <li>Regular security audits and updates</li>
                <li>Access controls and authentication requirements</li>
              </ul>

              <p className="text-gray-200 mb-4">
                However, no method of transmission over the Internet or electronic storage is 100% secure. While we strive to use commercially acceptable means to protect your data, we cannot guarantee absolute security.
              </p>
            </section>

            {/* Data Sharing */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">5. Data Sharing and Disclosure</h2>
              <p className="text-gray-200 mb-4">
                As an open source project, we are committed to transparency. We do not sell your personal information. We may share your information only in the following circumstances:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">With Your Consent:</strong> We may share information when you explicitly consent</li>
                <li><strong className="text-white">Service Providers:</strong> We may share data with trusted third-party service providers who assist in operating our service (e.g., hosting providers)</li>
                <li><strong className="text-white">Legal Requirements:</strong> We may disclose information if required by law or in response to valid legal requests</li>
                <li><strong className="text-white">Open Source:</strong> As an open source project, our code is publicly available, but user data remains private</li>
                <li><strong className="text-white">Business Transfers:</strong> In the event of a merger, acquisition, or sale, your information may be transferred</li>
              </ul>
            </section>

            {/* Your Rights */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">6. Your Rights and Choices</h2>
              <p className="text-gray-200 mb-4">
                You have the following rights regarding your personal information:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">Access:</strong> You can request access to your personal data</li>
                <li><strong className="text-white">Correction:</strong> You can update or correct your account information at any time</li>
                <li><strong className="text-white">Deletion:</strong> You can request deletion of your account and associated data</li>
                <li><strong className="text-white">Data Portability:</strong> You can request a copy of your data in a portable format</li>
                <li><strong className="text-white">Opt-Out:</strong> You can opt-out of certain data collection practices</li>
                <li><strong className="text-white">Account Deletion:</strong> You can delete your account through your account settings</li>
              </ul>
              <p className="text-gray-200">
                To exercise these rights, please contact us using the contact information provided below.
              </p>
            </section>

            {/* Cookies */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">7. Cookies and Tracking Technologies</h2>
              <p className="text-gray-200 mb-4">
                We use cookies and similar tracking technologies to:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Maintain your login session</li>
                <li>Remember your preferences</li>
                <li>Analyze usage patterns</li>
                <li>Improve our services</li>
              </ul>
              <p className="text-gray-200 mb-4">
                You can control cookies through your browser settings. However, disabling cookies may limit your ability to use certain features of our service.
              </p>
            </section>

            {/* Third-Party Services */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">8. Third-Party Services</h2>
              <p className="text-gray-200 mb-4">
                Our service may integrate with third-party services:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li><strong className="text-white">OAuth Providers:</strong> Google, Facebook, GitHub (for authentication)</li>
                <li><strong className="text-white">AI Services:</strong> Ollama and other AI providers (for content generation)</li>
                <li><strong className="text-white">Hosting Services:</strong> Cloud hosting providers</li>
              </ul>
              <p className="text-gray-200">
                These third-party services have their own privacy policies. We encourage you to review their privacy policies to understand how they handle your information.
              </p>
            </section>

            {/* Data Retention */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">9. Data Retention</h2>
              <p className="text-gray-200 mb-4">
                We retain your personal information for as long as necessary to:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Provide our services to you</li>
                <li>Comply with legal obligations</li>
                <li>Resolve disputes and enforce agreements</li>
                <li>Maintain security and prevent fraud</li>
              </ul>
              <p className="text-gray-200">
                When you delete your account, we will delete or anonymize your personal information, except where we are required to retain it for legal purposes.
              </p>
            </section>

            {/* Children's Privacy */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">10. Children's Privacy</h2>
              <p className="text-gray-200">
                Our service is not intended for children under the age of 13. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately, and we will take steps to delete such information.
              </p>
            </section>

            {/* International Users */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">11. International Data Transfers</h2>
              <p className="text-gray-200">
                Your information may be transferred to and processed in countries other than your country of residence. These countries may have data protection laws that differ from those in your country. By using our service, you consent to the transfer of your information to these countries.
              </p>
            </section>

            {/* Changes to Privacy Policy */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">12. Changes to This Privacy Policy</h2>
              <p className="text-gray-200 mb-4">
                We may update this Privacy Policy from time to time. We will notify you of any changes by:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Posting the new Privacy Policy on this page</li>
                <li>Updating the "Last Updated" date</li>
                <li>Sending you an email notification (for significant changes)</li>
              </ul>
              <p className="text-gray-200">
                You are advised to review this Privacy Policy periodically for any changes. Changes are effective when posted on this page.
              </p>
            </section>

            {/* Open Source Disclaimer */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">13. Open Source Disclaimer</h2>
              <p className="text-gray-200 mb-4">
                Content Creator is an open source project. This means:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Our source code is publicly available for review</li>
                <li>You can review how we handle your data by examining our code</li>
                <li>You can contribute to improving our privacy practices</li>
                <li>We welcome community feedback and contributions</li>
              </ul>
              <p className="text-gray-200">
                However, your personal data remains private and is not included in the open source codebase.
              </p>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">14. Contact Us</h2>
              <p className="text-gray-200 mb-4">
                If you have any questions about this Privacy Policy or our data practices, please contact us:
              </p>
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <p className="text-gray-300 mb-2"><strong>Content Creator by Patrick Ogbonna</strong></p>
                <p className="text-gray-200 text-sm mb-2">
                  You can reach us through:
                </p>
                <ul className="list-disc list-inside text-gray-200 text-sm space-y-1 ml-4">
                  <li>The Contact form in the application</li>
                  <li>GitHub Issues (for technical questions)</li>
                  <li>Email (if provided in the application)</li>
                </ul>
              </div>
            </section>

            {/* Governing Law */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">15. Governing Law</h2>
              <p className="text-gray-200">
                This Privacy Policy is governed by and construed in accordance with applicable data protection laws. If you are located in the European Economic Area (EEA), you have additional rights under the General Data Protection Regulation (GDPR).
              </p>
            </section>
          </div>

          <div className="mt-8 pt-8 border-t border-dark-border">
            <p className="text-sm text-gray-300 text-center">
              This Privacy Policy is effective as of December 18, 2024 and applies to all users of Content Creator.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}

