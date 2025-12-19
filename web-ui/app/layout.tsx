import type { Metadata } from 'next'
import './globals.css'
import DevToolsSuppress from '@/components/DevToolsSuppress'
import { AuthProvider } from '@/contexts/AuthContext'

export const metadata: Metadata = {
  title: 'Content Creator',
  description: 'AI-powered content creation with CrewAI',
  icons: {
    icon: '/favicon.svg',
    apple: '/icon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-dark-bg text-white antialiased">
        <DevToolsSuppress />
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}

