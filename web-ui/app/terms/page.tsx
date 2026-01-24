'use client'

import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-dark-bg">
      <Navbar selectedFeature="blog" onFeatureSelect={() => {}} />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        <div className="glass-effect neon-border rounded-2xl p-8">
          <h1 className="text-4xl font-bold text-gradient mb-4">Terms of Service</h1>
          <p className="text-gray-200 mb-2">Last Updated: December 18, 2024</p>
          <p className="text-gray-200 mb-8">
            Please read these Terms of Service carefully before using Content Creator by Patrick Ogbonna.
          </p>

          <div className="prose prose-invert max-w-none space-y-8">
            {/* Agreement to Terms */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">1. Agreement to Terms</h2>
              <p className="text-gray-200 mb-4">
                By accessing or using Content Creator ("Service", "we", "our", or "us"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of these terms, you may not access the Service.
              </p>
              <p className="text-gray-200">
                These Terms apply to all users of the Service, including without limitation users who are browsers, vendors, customers, merchants, and contributors of content.
              </p>
            </section>

            {/* Subscription Tiers */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">2. Subscription Tiers and Features</h2>
              <p className="text-gray-200 mb-6">
                Content Creator offers multiple subscription tiers with different features and usage limits. Your access to features depends on your selected subscription tier.
              </p>

              {/* Free Tier */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-neon-cyan mb-4">2.1 Free Tier</h3>
                <p className="text-gray-200 mb-4"><strong className="text-white">Price:</strong> $0/month</p>
                <p className="text-gray-200 mb-4"><strong className="text-white">Features:</strong></p>
                <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                  <li>Up to 5 content generations per month</li>
                  <li>Access to Blog Post content type</li>
                  <li>Basic content generation features</li>
                  <li>Standard content quality</li>
                  <li>Community support</li>
                  <li>Standard processing speed</li>
                </ul>
                <p className="text-gray-200 text-sm">
                  <strong className="text-white">Limitations:</strong> Content generations reset monthly. Unused generations do not roll over.
                </p>
              </div>

              {/* Basic Tier */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-neon-purple mb-4">2.2 Basic Tier</h3>
                <p className="text-gray-200 mb-4"><strong className="text-white">Price:</strong> $9.99/month or $99/year (save 17%)</p>
                <p className="text-gray-200 mb-4"><strong className="text-white">Features:</strong></p>
                <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                  <li>Up to 50 content generations per month</li>
                  <li>Access to Blog Post and Social Media content types</li>
                  <li>Enhanced content quality</li>
                  <li>Faster processing speed</li>
                  <li>Email support</li>
                  <li>Content export options</li>
                  <li>Basic analytics and insights</li>
                </ul>
                <p className="text-gray-200 text-sm">
                  <strong className="text-white">Best for:</strong> Individual content creators and small businesses.
                </p>
              </div>

              {/* Pro Tier */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-neon-cyan mb-4">2.3 Pro Tier</h3>
                <p className="text-gray-200 mb-4"><strong className="text-white">Price:</strong> $29.99/month or $299/year (save 17%)</p>
                <p className="text-gray-200 mb-4"><strong className="text-white">Features:</strong></p>
                <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                  <li>Unlimited content generations</li>
                  <li>Access to all content types (Blog, Social Media, Audio, Video)</li>
                  <li>Premium content quality with advanced AI models</li>
                  <li>Priority processing (faster generation times)</li>
                  <li>Priority email and chat support</li>
                  <li>Advanced content export formats</li>
                  <li>Advanced analytics and performance insights</li>
                  <li>Content templates and presets</li>
                  <li>API access (limited requests)</li>
                  <li>White-label options</li>
                </ul>
                <p className="text-gray-200 text-sm">
                  <strong className="text-white">Best for:</strong> Professional content creators, marketing agencies, and growing businesses.
                </p>
              </div>

              {/* Enterprise Tier */}
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border mb-6">
                <h3 className="text-xl font-semibold text-neon-purple mb-4">2.4 Enterprise Tier</h3>
                <p className="text-gray-200 mb-4"><strong className="text-white">Price:</strong> Custom pricing (contact sales)</p>
                <p className="text-gray-200 mb-4"><strong className="text-white">Features:</strong></p>
                <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                  <li>Unlimited content generations</li>
                  <li>All Pro tier features</li>
                  <li>Dedicated account manager</li>
                  <li>24/7 priority support</li>
                  <li>Custom AI model training</li>
                  <li>Unlimited API access</li>
                  <li>Custom integrations</li>
                  <li>SLA guarantees</li>
                  <li>On-premise deployment options</li>
                  <li>Custom branding and white-labeling</li>
                  <li>Team collaboration features</li>
                  <li>Advanced security and compliance features</li>
                  <li>Custom contract terms</li>
                </ul>
                <p className="text-gray-200 text-sm">
                  <strong className="text-white">Best for:</strong> Large organizations, enterprises, and agencies requiring custom solutions.
                </p>
              </div>

              <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 rounded-lg mb-6">
                <p className="text-yellow-400 text-sm">
                  <strong>Note:</strong> Feature availability and limits may vary. We reserve the right to modify subscription tiers, features, and pricing with 30 days' notice to existing subscribers.
                </p>
              </div>
            </section>

            {/* Account Registration */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">3. Account Registration</h2>
              <p className="text-gray-200 mb-4">
                To access certain features of the Service, you must register for an account. When you register, you agree to:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Provide accurate, current, and complete information</li>
                <li>Maintain and update your information to keep it accurate</li>
                <li>Maintain the security of your password and account</li>
                <li>Accept responsibility for all activities under your account</li>
                <li>Notify us immediately of any unauthorized use</li>
                <li>Be at least 13 years old (or the age of majority in your jurisdiction)</li>
              </ul>
              <p className="text-gray-200">
                You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.
              </p>
            </section>

            {/* Payment Terms */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">4. Payment Terms</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.1 Subscription Fees</h3>
              <p className="text-gray-200 mb-4">
                Subscription fees are billed in advance on a monthly or annual basis, depending on your selected billing cycle. All fees are non-refundable except as required by law or as stated in these Terms.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.2 Payment Methods</h3>
              <p className="text-gray-200 mb-4">
                We accept major credit cards, debit cards, and other payment methods as displayed during checkout. By providing payment information, you authorize us to charge your payment method for all fees associated with your subscription.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.3 Price Changes</h3>
              <p className="text-gray-200 mb-4">
                We reserve the right to modify subscription prices at any time. Price changes will not affect your current billing cycle but will apply to subsequent renewal periods. We will provide at least 30 days' notice of any price increases.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.4 Failed Payments</h3>
              <p className="text-gray-200 mb-4">
                If payment fails, we may suspend or terminate your subscription. You remain responsible for any uncollected amounts. We may retry failed payments using the payment method on file.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">4.5 Taxes</h3>
              <p className="text-gray-200">
                You are responsible for all applicable taxes, duties, and fees. Prices displayed are exclusive of taxes unless otherwise stated.
              </p>
            </section>

            {/* Billing and Renewal */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">5. Billing and Renewal</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.1 Automatic Renewal</h3>
              <p className="text-gray-200 mb-4">
                Subscriptions automatically renew at the end of each billing period unless cancelled before the renewal date. By subscribing, you authorize us to charge your payment method automatically for renewal fees.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.2 Billing Cycle</h3>
              <p className="text-gray-200 mb-4">
                Monthly subscriptions renew every 30 days. Annual subscriptions renew every 365 days. Renewal occurs on the same day of the month as your initial subscription date.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">5.3 Upgrades and Downgrades</h3>
              <p className="text-gray-200 mb-4">
                You may upgrade your subscription at any time. Upgrades take effect immediately, and you will be charged a prorated amount for the remainder of your billing cycle. Downgrades take effect at the start of your next billing cycle.
              </p>
            </section>

            {/* Cancellation and Refunds */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">6. Cancellation and Refunds</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">6.1 Cancellation</h3>
              <p className="text-gray-200 mb-4">
                You may cancel your subscription at any time through your account settings or by contacting support. Cancellation takes effect at the end of your current billing period. You will continue to have access to paid features until the end of your billing period.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">6.2 Refund Policy</h3>
              <p className="text-gray-200 mb-4">
                <strong className="text-white">Free Tier:</strong> No refunds applicable (free service).<br />
                <strong className="text-white">Paid Tiers:</strong> We offer a 14-day money-back guarantee for new subscriptions. Refund requests must be made within 14 days of initial subscription. After 14 days, all fees are non-refundable except as required by law.
              </p>
              <p className="text-gray-200 mb-4">
                Refunds are processed to the original payment method within 5-10 business days. Partial refunds may be provided for annual subscriptions cancelled mid-term, calculated on a prorated basis.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">6.3 Effect of Cancellation</h3>
              <p className="text-gray-200">
                Upon cancellation, your account will be downgraded to the Free tier at the end of your billing period. You will lose access to paid features but may continue using the Service under the Free tier terms.
              </p>
            </section>

            {/* Usage Limits and Fair Use */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">7. Usage Limits and Fair Use</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">7.1 Subscription Limits</h3>
              <p className="text-gray-200 mb-4">
                Each subscription tier has specific usage limits (e.g., number of content generations per month). Exceeding these limits may result in:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Automatic upgrade prompts</li>
                <li>Temporary suspension of service</li>
                <li>Additional charges for overage</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">7.2 Fair Use Policy</h3>
              <p className="text-gray-200 mb-4">
                You agree to use the Service in a reasonable manner and not to:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Abuse or exploit the Service</li>
                <li>Attempt to circumvent usage limits</li>
                <li>Use automated systems to generate excessive content</li>
                <li>Resell or redistribute content generation capacity</li>
                <li>Use the Service for illegal or harmful purposes</li>
              </ul>
              <p className="text-gray-200">
                We reserve the right to suspend or terminate accounts that violate fair use policies.
              </p>
            </section>

            {/* Service Availability */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">8. Service Availability</h2>
              <p className="text-gray-200 mb-4">
                We strive to maintain high availability but do not guarantee uninterrupted or error-free service. The Service may be temporarily unavailable due to:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Maintenance and updates</li>
                <li>Technical issues or failures</li>
                <li>Third-party service outages</li>
                <li>Force majeure events</li>
              </ul>
              <p className="text-gray-200">
                We are not liable for any loss or damage resulting from Service unavailability. Enterprise tier subscribers may have SLA guarantees as specified in their custom agreements.
              </p>
            </section>

            {/* Intellectual Property */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">9. Intellectual Property</h2>
              
              <h3 className="text-xl font-semibold text-gray-300 mb-3">9.1 Service Ownership</h3>
              <p className="text-gray-200 mb-4">
                The Service, including its original content, features, and functionality, is owned by Content Creator by Patrick Ogbonna and is protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">9.2 Generated Content</h3>
              <p className="text-gray-200 mb-4">
                You retain ownership of content you generate using the Service. You grant us a limited license to use, store, and process your content solely for the purpose of providing the Service.
              </p>

              <h3 className="text-xl font-semibold text-gray-300 mb-3">9.3 User Content</h3>
              <p className="text-gray-200">
                You retain ownership of any content you submit to the Service. By submitting content, you grant us a worldwide, non-exclusive, royalty-free license to use, reproduce, and distribute your content as necessary to provide the Service.
              </p>
            </section>

            {/* Prohibited Uses */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">10. Prohibited Uses</h2>
              <p className="text-gray-200 mb-4">
                You agree not to use the Service:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>For any unlawful purpose or to solicit unlawful acts</li>
                <li>To violate any international, federal, provincial, or state regulations, rules, or laws</li>
                <li>To infringe upon or violate our intellectual property rights or the rights of others</li>
                <li>To harass, abuse, insult, harm, defame, slander, disparage, intimidate, or discriminate</li>
                <li>To submit false or misleading information</li>
                <li>To upload or transmit viruses or any other malicious code</li>
                <li>To collect or track personal information of others</li>
                <li>To spam, phish, pharm, pretext, spider, crawl, or scrape</li>
                <li>For any obscene or immoral purpose</li>
                <li>To interfere with or circumvent security features of the Service</li>
              </ul>
            </section>

            {/* Termination */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">11. Termination</h2>
              <p className="text-gray-200 mb-4">
                We may terminate or suspend your account and access to the Service immediately, without prior notice, for any reason, including:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Breach of these Terms</li>
                <li>Fraudulent, abusive, or illegal activity</li>
                <li>Non-payment of fees</li>
                <li>Violation of fair use policies</li>
                <li>Request by law enforcement or government agencies</li>
              </ul>
              <p className="text-gray-200">
                Upon termination, your right to use the Service will cease immediately. We may delete your account and data, though we may retain certain information as required by law or for legitimate business purposes.
              </p>
            </section>

            {/* Disclaimer of Warranties */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">12. Disclaimer of Warranties</h2>
              <p className="text-gray-200 mb-4">
                THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>IMPLIED WARRANTIES OF MERCHANTABILITY</li>
                <li>FITNESS FOR A PARTICULAR PURPOSE</li>
                <li>NON-INFRINGEMENT</li>
                <li>ACCURACY OR RELIABILITY OF GENERATED CONTENT</li>
              </ul>
              <p className="text-gray-200">
                We do not warrant that the Service will be uninterrupted, secure, or error-free, or that defects will be corrected.
              </p>
            </section>

            {/* Limitation of Liability */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">13. Limitation of Liability</h2>
              <p className="text-gray-200 mb-4">
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL CONTENT CREATOR BY PATRICK OGBONNA, ITS AFFILIATES, AGENTS, DIRECTORS, EMPLOYEES, SUPPLIERS, OR LICENSORS BE LIABLE FOR:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>ANY INDIRECT, PUNITIVE, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR EXEMPLARY DAMAGES</li>
                <li>ANY LOSS OF PROFITS, REVENUES, CUSTOMERS, BUSINESS, OR DATA</li>
                <li>ANY DAMAGES ARISING FROM YOUR USE OF OR INABILITY TO USE THE SERVICE</li>
              </ul>
              <p className="text-gray-200 mb-4">
                Our total liability for any claims arising from or related to the Service shall not exceed the amount you paid us in the 12 months preceding the claim, or $100, whichever is greater.
              </p>
              <p className="text-gray-200">
                Some jurisdictions do not allow the exclusion of certain warranties or limitation of liability, so some of the above limitations may not apply to you.
              </p>
            </section>

            {/* Indemnification */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">14. Indemnification</h2>
              <p className="text-gray-200">
                You agree to defend, indemnify, and hold harmless Content Creator by Patrick Ogbonna and its affiliates from any claims, damages, obligations, losses, liabilities, costs, or debt arising from your use of the Service, violation of these Terms, or infringement of any rights of another party.
              </p>
            </section>

            {/* Changes to Terms */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">15. Changes to Terms</h2>
              <p className="text-gray-200 mb-4">
                We reserve the right to modify these Terms at any time. We will notify you of material changes by:
              </p>
              <ul className="list-disc list-inside text-gray-200 space-y-2 mb-4 ml-4">
                <li>Posting the updated Terms on this page</li>
                <li>Updating the "Last Updated" date</li>
                <li>Sending email notifications (for significant changes)</li>
                <li>Displaying notices within the Service</li>
              </ul>
              <p className="text-gray-200">
                Your continued use of the Service after changes become effective constitutes acceptance of the new Terms. If you do not agree to the changes, you must stop using the Service and cancel your subscription.
              </p>
            </section>

            {/* Governing Law */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">16. Governing Law</h2>
              <p className="text-gray-200">
                These Terms shall be governed by and construed in accordance with applicable laws, without regard to conflict of law provisions. Any disputes arising from these Terms or the Service shall be resolved in the appropriate courts.
              </p>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">17. Contact Information</h2>
              <p className="text-gray-200 mb-4">
                If you have any questions about these Terms, please contact us:
              </p>
              <div className="bg-dark-card p-6 rounded-lg border border-dark-border">
                <p className="text-gray-300 mb-2"><strong>Content Creator by Patrick Ogbonna</strong></p>
                <p className="text-gray-200 text-sm mb-2">
                  You can reach us through:
                </p>
                <ul className="list-disc list-inside text-gray-200 text-sm space-y-1 ml-4">
                  <li>The Contact form in the application</li>
                  <li>Email support (for paid tier subscribers)</li>
                  <li>GitHub Issues (for technical questions)</li>
                </ul>
              </div>
            </section>

            {/* Severability */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">18. Severability</h2>
              <p className="text-gray-200">
                If any provision of these Terms is found to be unenforceable or invalid, that provision shall be limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.
              </p>
            </section>

            {/* Entire Agreement */}
            <section>
              <h2 className="text-2xl font-bold text-gradient mb-4">19. Entire Agreement</h2>
              <p className="text-gray-200">
                These Terms, together with our Privacy Policy, constitute the entire agreement between you and Content Creator by Patrick Ogbonna regarding the Service and supersede all prior agreements and understandings.
              </p>
            </section>
          </div>

          <div className="mt-8 pt-8 border-t border-dark-border">
            <p className="text-sm text-gray-300 text-center">
              By using Content Creator, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}

