import { ReactNode } from 'react'
import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { NavBar } from '@/components/layout/NavBar'

export default async function OrdersLayout({ children }: { children: ReactNode }) {
  const session = await auth()
  if (!session) redirect('/auth/signin')

  return (
    <div className="min-h-screen bg-forge-canvas">
      <NavBar authenticated />
      <main className="max-w-5xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}
