'use client'

import { ReactNode } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

function canvasTone(pathname: string, view: string | null) {
  if (pathname.startsWith('/orders/new')) return 'bg-[#F2F6EF]'
  if (pathname !== '/orders') return 'bg-[#F1F7F6]'
  if (view === 'ready') return 'bg-[#EEF7F6]'
  if (view === 'quality') return 'bg-[#F7F2E8]'
  if (view === 'packages') return 'bg-[#F2F3F8]'
  return 'bg-forge-canvas'
}

export function OrdersCanvas({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const view = useSearchParams().get('view')

  return (
    <main className={`min-w-0 flex-1 overflow-y-auto pt-16 transition-colors duration-300 lg:pt-0 ${canvasTone(pathname, view)}`}>
      <div className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
        {children}
      </div>
    </main>
  )
}
