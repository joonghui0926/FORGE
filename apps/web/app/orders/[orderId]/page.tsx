import { notFound } from 'next/navigation'
import { apiServer, ApiError } from '@/lib/api'
import { Order } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { WorkspaceTabs } from '@/components/orders/workspace/WorkspaceTabs'
import { Button } from '@/components/ui/Button'

interface PageProps {
  params: { orderId: string }
}

export default async function OrderDetailPage({ params }: PageProps) {
  let order: Order

  try {
    order = await apiServer.get<Order>(`/orders/${params.orderId}`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound()
    throw err
  }

  const isReady = order.state === 'READY'

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-forge-ink mb-1">
            {order.skill_name ?? 'Order'}
          </h1>
          <StatusBadge state={order.state} />
        </div>
        <Button variant="secondary" disabled={!isReady} className="text-sm">
          Download dataset
        </Button>
      </div>
      <WorkspaceTabs order={order} />
    </div>
  )
}
