import { ReactNode } from 'react'
import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { AppSidebar } from '@/components/layout/AppSidebar'
import { OrdersCanvas } from '@/components/layout/OrdersCanvas'

export default async function OrdersLayout({ children }: { children: ReactNode }) {
  const session = await auth()
  if (!session) redirect('/auth/signin')

  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <OrdersCanvas>{children}</OrdersCanvas>
    </div>
  )
}
