'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOut } from 'next-auth/react'
import { Button } from '@/components/ui/Button'

const NAV_ITEMS = [
  { href: '/orders',   label: 'Orders' },
  { href: '/datasets', label: 'Datasets' },
  { href: '/account',  label: 'Account' },
] as const

interface NavBarProps {
  authenticated?: boolean
}

export function NavBar({ authenticated }: NavBarProps) {
  const pathname = usePathname()

  return (
    <nav className="flex items-center justify-between px-6 py-4 border-b border-forge-border bg-forge-surface">
      <div className="flex items-center gap-8">
        <Link href={authenticated ? '/orders' : '/'} className="text-lg font-bold text-forge-ink tracking-tight">
          FORGE
        </Link>
        {authenticated && (
          <ul className="flex items-center gap-6" role="list">
            {NAV_ITEMS.map(({ href, label }) => {
              const active = pathname.startsWith(href)
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={`text-sm transition-colors ${
                      active
                        ? 'text-forge-primary font-semibold'
                        : 'text-forge-ink-muted hover:text-forge-ink'
                    }`}
                    aria-current={active ? 'page' : undefined}
                  >
                    {label}
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <div>
        {authenticated ? (
          <Button variant="tertiary" onClick={() => signOut({ callbackUrl: '/' })}
                  className="text-sm min-h-[44px]">
            Sign out
          </Button>
        ) : (
          <Link href="/auth/signin">
            <Button variant="secondary" className="text-sm min-h-[44px]">Sign in</Button>
          </Link>
        )}
      </div>
    </nav>
  )
}
