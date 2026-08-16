'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import { signOut } from 'next-auth/react'
import {
  CircleHelp,
  ClipboardList,
  Database,
  LogOut,
  Menu,
  PackageCheck,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'

const NAV_GROUPS = [
  {
    label: 'Workspace',
    items: [
      { href: '/orders', label: 'Orders', icon: ClipboardList, view: undefined },
      { href: '/orders/new', label: 'New order', icon: Plus, view: undefined },
    ],
  },
  {
    label: 'Delivery',
    items: [
      { href: '/orders?view=ready', label: 'Robot-ready data', icon: Database, view: 'ready' },
      { href: '/orders?view=quality', label: 'Quality pipeline', icon: ShieldCheck, view: 'quality' },
      { href: '/orders?view=packages', label: 'Packages', icon: PackageCheck, view: 'packages' },
    ],
  },
] as const

function ForgeMark() {
  return (
    <Image
      src="/brand/forge-logo.png"
      alt=""
      width={40}
      height={40}
      className="size-10 shrink-0 object-contain"
    />
  )
}

export function AppSidebar() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    setCollapsed(window.localStorage.getItem('forge-sidebar-collapsed') === 'true')
  }, [])

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      const next = !value
      window.localStorage.setItem('forge-sidebar-collapsed', String(next))
      return next
    })
  }

  const selectedView = searchParams.get('view')
  const isCompact = collapsed && !mobileOpen

  const sidebar = (
    <aside
      className={`flex h-full flex-col bg-forge-surface transition-[width] duration-200 ease-out ${
        isCompact ? 'w-[84px]' : 'w-[264px]'
      }`}
    >
      <div className={`flex h-20 items-center ${isCompact ? 'justify-center px-3' : 'justify-between px-5'}`}>
        <Link
          href="/orders"
          className="flex min-w-0 items-center gap-3 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-forge-focus"
          aria-label="FORGE orders"
        >
          <ForgeMark />
          {!isCompact && <span className="text-xl font-extrabold tracking-[-0.04em] text-forge-ink">FORGE</span>}
        </Link>
        {!isCompact && (
          <button
            type="button"
            onClick={toggleCollapsed}
            className="hidden size-10 place-items-center rounded-xl text-forge-ink-muted transition-colors hover:bg-forge-surface-soft hover:text-forge-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus lg:grid"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={21} strokeWidth={1.9} />
          </button>
        )}
      </div>

      {isCompact && (
        <button
          type="button"
          onClick={toggleCollapsed}
          className="mx-auto mb-3 hidden size-10 place-items-center rounded-xl text-forge-ink-muted transition-colors hover:bg-forge-surface-soft hover:text-forge-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus lg:grid"
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen size={21} strokeWidth={1.9} />
        </button>
      )}

      <nav className={`flex-1 overflow-y-auto pb-5 ${isCompact ? 'px-3' : 'px-4'}`} aria-label="Main navigation">
        {NAV_GROUPS.map((group, groupIndex) => (
          <section key={group.label} className={groupIndex === 0 ? '' : 'mt-7'}>
            {!isCompact && (
              <p className="mb-2 px-3 text-[14px] font-medium text-forge-ink-subtle">{group.label}</p>
            )}
            <ul className="space-y-1" role="list">
              {group.items.map(({ href, label, icon: Icon, view }) => {
                const active = view
                  ? pathname === '/orders' && selectedView === view
                  : href === '/orders'
                    ? pathname === '/orders' && !selectedView
                    : pathname.startsWith(href)
                return (
                  <li key={`${group.label}-${label}`}>
                    <Link
                      href={href}
                      onClick={() => setMobileOpen(false)}
                      title={isCompact ? label : undefined}
                      aria-current={active ? 'page' : undefined}
                      className={`flex min-h-11 items-center rounded-xl text-[15px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus ${
                        isCompact ? 'justify-center px-2' : 'gap-3 px-3'
                      } ${
                        active
                          ? 'bg-forge-surface-cyan text-forge-primary-active'
                          : 'text-forge-ink-muted hover:bg-forge-surface-soft hover:text-forge-ink'
                      }`}
                    >
                      <Icon size={21} strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
                      {!isCompact && <span>{label}</span>}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </nav>

      <div className={`pb-5 ${isCompact ? 'px-3' : 'px-4'}`}>
        <a
          href="mailto:support@forgephysical.ai"
          title={isCompact ? 'Support' : undefined}
          className={`flex min-h-11 items-center rounded-xl text-[15px] font-medium text-forge-ink-muted transition-colors hover:bg-forge-surface-soft hover:text-forge-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus ${
            isCompact ? 'justify-center px-2' : 'gap-3 px-3'
          }`}
        >
          <CircleHelp size={21} strokeWidth={1.8} aria-hidden="true" />
          {!isCompact && <span>Support</span>}
        </a>
        <button
          type="button"
          onClick={() => signOut({ callbackUrl: '/' })}
          title={isCompact ? 'Sign out' : undefined}
          className={`mt-1 flex min-h-11 w-full items-center rounded-xl text-[15px] font-medium text-forge-ink-muted transition-colors hover:bg-forge-surface-soft hover:text-forge-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus ${
            isCompact ? 'justify-center px-2' : 'gap-3 px-3'
          }`}
        >
          <LogOut size={21} strokeWidth={1.8} aria-hidden="true" />
          {!isCompact && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  )

  return (
    <>
      <div className="fixed inset-x-0 top-0 z-30 flex h-16 items-center justify-between bg-forge-surface px-4 shadow-[0_1px_0_rgba(21,33,38,0.08)] lg:hidden">
        <Link href="/orders" className="flex items-center gap-3" aria-label="FORGE orders">
          <ForgeMark />
          <span className="text-lg font-extrabold tracking-[-0.04em] text-forge-ink">FORGE</span>
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="grid size-11 place-items-center rounded-xl text-forge-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus"
          aria-label="Open navigation"
          aria-expanded={mobileOpen}
        >
          <Menu size={24} />
        </button>
      </div>

      <div className="hidden shrink-0 border-r border-black/[0.07] lg:block">{sidebar}</div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-forge-ink/25 backdrop-blur-[2px]"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          />
          <div className="absolute inset-y-0 left-0 shadow-2xl">
            {sidebar}
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-5 grid size-10 place-items-center rounded-xl text-forge-ink-muted"
              aria-label="Close navigation"
            >
              <X size={22} />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
