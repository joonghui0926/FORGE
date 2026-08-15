import Link from 'next/link'
import { Button } from '@/components/ui/Button'

export function Hero() {
  return (
    <section className="px-6 pt-24 pb-20 max-w-3xl">
      <h1 className="text-5xl font-bold text-forge-ink leading-tight tracking-tight">
        Human demonstrations in.
        <br />
        Validated robot-ready datasets out.
      </h1>
      <p className="mt-6 text-xl text-forge-ink-muted max-w-[56ch]">
        Physics-validated robot datasets from human demos.
      </p>
      <div className="mt-10">
        <Link href="/auth/signin?callbackUrl=/orders/new">
          <Button variant="primary" className="text-base px-8">
            Define your robot task
          </Button>
        </Link>
      </div>
    </section>
  )
}
