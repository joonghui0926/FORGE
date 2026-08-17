import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

export function Hero() {
  return (
    <section className="relative mx-auto grid min-h-[680px] max-w-[1440px] items-center overflow-hidden px-6 pb-16 pt-12 lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)] lg:px-12 lg:pb-20 lg:pt-8 xl:px-20">
      <div className="relative z-10 max-w-[760px] py-16">
        <p className="mb-6 text-[15px] font-semibold uppercase tracking-[0.16em] text-forge-primary-active">
          Physical AI dataset compiler
        </p>
        <h1 className="max-w-[13ch] text-[clamp(3.25rem,6.1vw,6.6rem)] font-bold leading-[0.96] tracking-[-0.065em] text-forge-ink">
          Teach any robot from real motion.
        </h1>
        <p className="mt-7 max-w-[58ch] text-lg leading-8 text-forge-ink-muted sm:text-xl">
          Tell us the skill. FORGE plans multi-person collection, verifies rights and coverage,
          compiles supported physical representations, and delivers an auditable dataset your team can train on.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-5">
          <Link href="/pricing">
            <Button variant="primary" className="px-8 text-base">
              Start the $350 pilot
            </Button>
          </Link>
          <span className="text-[15px] font-medium text-forge-ink-muted">
            3 participants × 6 clips · Quality-gated at every stage
          </span>
        </div>
      </div>

      <div className="relative hidden h-[640px] items-end justify-center lg:flex" aria-hidden="true">
        <div className="absolute inset-x-[2%] bottom-[8%] top-[11%] rounded-[50%] bg-[radial-gradient(circle_at_50%_48%,rgba(0,171,194,0.22),rgba(0,171,194,0.06)_48%,transparent_72%)] blur-sm" />
        <div className="absolute right-[7%] top-[18%] size-3 rounded-full bg-forge-primary/65 motion-safe:animate-[forge-trail_2.8s_ease-in-out_infinite]" />
        <div className="absolute right-[18%] top-[29%] size-2 rounded-full bg-forge-primary/40 motion-safe:animate-[forge-trail_2.8s_0.35s_ease-in-out_infinite]" />
        <div className="absolute right-[4%] top-[41%] size-1.5 rounded-full bg-forge-primary/30 motion-safe:animate-[forge-trail_2.8s_0.7s_ease-in-out_infinite]" />
        <Image
          src="/brand/forge-humanoid-runner.png"
          alt=""
          width={1024}
          height={1536}
          priority
          className="relative z-10 h-[610px] w-auto object-contain drop-shadow-[0_28px_32px_rgba(8,47,53,0.18)] motion-safe:animate-[forge-robot-float_4.6s_ease-in-out_infinite]"
        />
      </div>
    </section>
  )
}
