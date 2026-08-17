import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'FORGE',
  description: 'Multi-person demonstrations in. Auditable robotics training datasets out.',
  icons: {
    icon: '/brand/forge-favicon.png',
    shortcut: '/brand/forge-favicon.png',
    apple: '/brand/forge-favicon.png',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-forge-canvas text-forge-ink font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
