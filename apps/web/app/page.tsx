import Image from 'next/image'
import Link from 'next/link'
import { Hero } from '@/components/landing/Hero'
import { ProcessSteps } from '@/components/landing/ProcessSteps'

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[linear-gradient(135deg,#F8F5EB_0%,#F8F5EB_58%,#EDF7F6_100%)]">
      <header className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-6 py-5 lg:px-12 xl:px-20">
        <Link href="/" className="flex items-center gap-3" aria-label="FORGE home">
          <Image src="/brand/forge-logo.png" alt="" width={44} height={44} priority className="size-11 object-contain" />
          <span className="text-xl font-extrabold tracking-[-0.045em] text-forge-ink">FORGE</span>
        </Link>
        <Link href="/auth/signin" className="text-[15px] font-medium text-forge-ink-muted transition-colors hover:text-forge-ink">
          Sign in
        </Link>
      </header>
      <main className="flex-1">
        <Hero />
        <ProcessSteps />
      </main>
      <footer className="mx-auto w-full max-w-[1440px] px-6 py-8 lg:px-12 xl:px-20">
        <div className="flex gap-6 text-[15px] text-forge-ink-muted">
          <Link href="/auth/signin" className="hover:text-forge-ink transition-colors">Sign in</Link>
          <a href="mailto:hello@forge.app" className="hover:text-forge-ink transition-colors">Contact</a>
        </div>
      </footer>
    </div>
  )
}
