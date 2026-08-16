import type { Metadata } from 'next'
import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, Check, CreditCard, Database, ShieldCheck } from 'lucide-react'

export const metadata: Metadata = {
  title: '$350 Dataset Pilot | FORGE',
  description: 'Order a bounded FORGE robot-ready dataset pilot with secure Stripe checkout.',
}

const INCLUDED = [
  'One narrowly defined robot skill',
  'One target embodiment',
  '1-10 physics-validated episodes',
  'Trajectory, contact, quality, and lineage artifacts',
  'One robot-ready dataset export',
]

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[linear-gradient(145deg,#EEF8F7_0%,#F8F5EB_52%,#F8F5EB_100%)]">
      <header className="mx-auto flex w-full max-w-[1280px] items-center justify-between px-6 py-5 lg:px-12">
        <Link href="/" className="flex items-center gap-3" aria-label="FORGE home">
          <Image src="/brand/forge-favicon.png" alt="" width={56} height={56} priority className="size-14 object-contain" />
          <span className="text-[22px] font-extrabold tracking-[-0.045em] text-forge-ink">FORGE</span>
        </Link>
        <nav className="flex items-center gap-6 text-[15px] font-medium" aria-label="Public navigation">
          <Link href="/" className="text-forge-ink-muted transition-colors hover:text-forge-ink">Home</Link>
          <Link href="/auth/signin" className="text-forge-ink-muted transition-colors hover:text-forge-ink">Sign in</Link>
        </nav>
      </header>

      <main className="mx-auto grid w-full max-w-[1280px] gap-16 px-6 pb-24 pt-16 lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,0.7fr)] lg:px-12 lg:pb-32 lg:pt-24">
        <section className="max-w-2xl">
          <p className="text-[15px] font-semibold uppercase tracking-[0.16em] text-forge-primary-active">FORGE starter pilot</p>
          <h1 className="mt-5 text-[clamp(3.25rem,6vw,6rem)] font-bold leading-[0.94] tracking-[-0.065em] text-forge-ink">
            Robot-ready data for $350.
          </h1>
          <p className="mt-7 max-w-[56ch] text-lg leading-8 text-forge-ink-muted">
            Define the motion your robot needs. FORGE plans acquisition, compiles physical trajectories, validates quality, and delivers the dataset—not robot hardware.
          </p>

          <Link
            href="/auth/signin?callbackUrl=/orders/new"
            className="mt-10 inline-flex min-h-14 items-center justify-center gap-2 rounded-control bg-forge-primary px-7 text-base font-semibold text-forge-primary-ink transition-colors hover:bg-forge-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus"
          >
            Start the $350 pilot
            <ArrowRight size={20} aria-hidden="true" />
          </Link>
          <p className="mt-4 text-[15px] leading-6 text-forge-ink-muted">
            Configure the task first, then pay securely with Stripe. No recurring subscription.
          </p>
        </section>

        <section className="self-center" aria-labelledby="pilot-includes">
          <div className="flex items-end justify-between gap-6">
            <div>
              <p className="text-[15px] font-medium text-forge-ink-muted">One-time payment</p>
              <h2 id="pilot-includes" className="mt-1 text-3xl font-semibold tracking-[-0.04em] text-forge-ink">Starter dataset</h2>
            </div>
            <p className="text-5xl font-bold tracking-[-0.06em] text-forge-ink">$350</p>
          </div>

          <ul className="mt-10 space-y-5" role="list">
            {INCLUDED.map((item) => (
              <li key={item} className="flex gap-3 text-base leading-7 text-forge-ink">
                <Check className="mt-1 size-5 shrink-0 text-forge-primary-active" strokeWidth={2.4} aria-hidden="true" />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div className="mt-12 grid grid-cols-3 gap-5 border-t border-forge-border/80 pt-8 text-center">
            <div>
              <CreditCard className="mx-auto size-6 text-forge-primary-active" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-forge-ink">Stripe checkout</p>
            </div>
            <div>
              <ShieldCheck className="mx-auto size-6 text-forge-primary-active" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-forge-ink">Quality gated</p>
            </div>
            <div>
              <Database className="mx-auto size-6 text-forge-primary-active" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-forge-ink">Data delivery</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
