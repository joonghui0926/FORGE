import Link from 'next/link'
import { Hero } from '@/components/landing/Hero'
import { ProcessSteps } from '@/components/landing/ProcessSteps'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-forge-canvas flex flex-col">
      <header className="flex items-center justify-between px-6 py-4">
        <span className="text-lg font-bold text-forge-ink tracking-tight">FORGE</span>
        <Link href="/auth/signin" className="text-sm text-forge-ink-muted hover:text-forge-ink transition-colors">
          Sign in
        </Link>
      </header>
      <main className="flex-1">
        <Hero />
        <ProcessSteps />
      </main>
      <footer className="px-6 py-8 border-t border-forge-border">
        <div className="flex gap-6 text-sm text-forge-ink-muted">
          <Link href="/auth/signin" className="hover:text-forge-ink transition-colors">Sign in</Link>
          <a href="mailto:hello@forge.app" className="hover:text-forge-ink transition-colors">Contact</a>
        </div>
      </footer>
    </div>
  )
}
