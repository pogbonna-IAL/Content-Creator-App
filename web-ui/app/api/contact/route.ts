import { NextRequest, NextResponse } from 'next/server'

// Email configuration - update these with your SMTP settings
// For production, use environment variables
const SMTP_CONFIG = {
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: parseInt(process.env.SMTP_PORT || '587'),
  secure: false, // true for 465, false for other ports
  auth: {
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASS || '',
  },
}

const RECIPIENT_EMAIL = 'contact@patrickogbonna.com'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, email, phone, message } = body

    // Validate required fields
    if (!name || !email || !message) {
      return NextResponse.json(
        { error: 'Name, email, and message are required' },
        { status: 400 }
      )
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      )
    }

    // Try to send email using nodemailer
    try {
      // Dynamic import to avoid issues if nodemailer is not installed
      const nodemailer = await import('nodemailer')
      
      // Create transporter
      const transporter = nodemailer.createTransport({
        host: SMTP_CONFIG.host,
        port: SMTP_CONFIG.port,
        secure: SMTP_CONFIG.secure,
        auth: SMTP_CONFIG.auth.user ? SMTP_CONFIG.auth : undefined,
      })

      // Email content
      const mailOptions = {
        from: `"${name}" <${SMTP_CONFIG.auth.user || email}>`,
        to: RECIPIENT_EMAIL,
        replyTo: email,
        subject: `Contact Form Submission from ${name}`,
        html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #00d4ff;">New Contact Form Submission</h2>
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin-top: 20px;">
              <p><strong style="color: #a855f7;">Name:</strong> ${name}</p>
              <p><strong style="color: #a855f7;">Email:</strong> <a href="mailto:${email}" style="color: #00d4ff;">${email}</a></p>
              ${phone ? `<p><strong style="color: #a855f7;">Phone:</strong> ${phone}</p>` : ''}
              <div style="margin-top: 20px;">
                <strong style="color: #a855f7;">Message:</strong>
                <p style="color: #e5e7eb; white-space: pre-wrap; margin-top: 10px;">${message}</p>
              </div>
            </div>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">
              This email was sent from the Content Creator contact form.
            </p>
          </div>
        `,
        text: `
New Contact Form Submission

Name: ${name}
Email: ${email}
${phone ? `Phone: ${phone}` : ''}

Message:
${message}
        `.trim(),
      }

      // Send email
      await transporter.sendMail(mailOptions)

      return NextResponse.json(
        { message: 'Message sent successfully' },
        { status: 200 }
      )
    } catch (emailError) {
      console.error('Email sending error:', emailError)
      
      // Fallback: Log the contact form data (for development/debugging)
      // In production, you might want to save to a database or use a service like SendGrid
      console.log('Contact form submission:', {
        name,
        email,
        phone,
        message,
        timestamp: new Date().toISOString(),
      })

      // Return error if SMTP is configured but failed
      if (SMTP_CONFIG.auth.user) {
        return NextResponse.json(
          { error: 'Failed to send email. Please try again later or contact us directly.' },
          { status: 500 }
        )
      }

      // If SMTP is not configured, return success but log a warning
      console.warn('SMTP not configured. Email not sent. Please configure SMTP settings.')
      return NextResponse.json(
        { 
          message: 'Message received (SMTP not configured - check server logs)',
          warning: 'Email functionality requires SMTP configuration'
        },
        { status: 200 }
      )
    }
  } catch (error) {
    console.error('Contact form error:', error)
    return NextResponse.json(
      { error: 'An error occurred while processing your request' },
      { status: 500 }
    )
  }
}

