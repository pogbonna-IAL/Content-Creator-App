import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Live demo | Content Creation Crew',
  description:
    'See how multi-agent AI turns one topic into blog, social, audio, and video-ready content—with real-time progress.',
}

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return children
}
