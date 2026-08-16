import { ReactNode } from 'react'
import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { AppSidebar } from '@/components/layout/AppSidebar'

export default async function OrdersLayout({ children }: { children: ReactNode }) {
  const session = await auth()
  if (!session) redirect('/auth/signin')

  return (
    <div className="flex h-screen overflow-hidden bg-forge-canvas">
      <AppSidebar />
      <main className="min-w-0 flex-1 overflow-y-auto pt-16 lg:pt-0">
        <div className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          {children}
        </div>
      </main>
    </div>
  )
}
