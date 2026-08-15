import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'FORGE',
  description: 'Human demonstrations in. Validated robot-ready datasets out.',
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
