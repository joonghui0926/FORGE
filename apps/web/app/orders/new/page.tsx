import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { NewOrderStepper } from '@/components/orders/NewOrderStepper'

export default async function NewOrderPage() {
  const session = await auth()
  if (!session?.forgeToken) redirect('/auth/signin')

  return (
    <div>
      <h1 className="text-2xl font-bold text-forge-ink mb-2">New order</h1>
      <p className="text-forge-ink-muted text-sm mb-10">
        Configure your dataset. No data is saved until you place the order.
      </p>
      <NewOrderStepper token={session.forgeToken} />
    </div>
  )
}
