import Link from 'next/link'
import { apiServer, ApiError } from '@/lib/api'
import { Order } from '@/lib/types'
import { OrderRow } from '@/components/orders/OrderRow'
import { Button } from '@/components/ui/Button'

export default async function OrdersPage() {
  let orders: Order[] = []
  let fetchError: string | null = null

  try {
    orders = await apiServer.get<Order[]>('/orders')
  } catch (err) {
    fetchError = err instanceof ApiError
      ? 'We could not connect to the server. Check your connection.'
      : 'Something went wrong. Please try again.'
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-forge-ink">Your Orders</h1>
          <p className="text-forge-ink-muted mt-1 text-sm">
            Track and manage your dataset orders.
          </p>
        </div>
        {!fetchError && orders.length > 0 && (
          <Link href="/orders/new">
            <Button variant="primary">New order</Button>
          </Link>
        )}
      </div>

      {fetchError ? (
        <div className="py-16 text-center">
          <p className="text-forge-ink-muted mb-5">{fetchError}</p>
          <a href="/orders">
            <Button variant="secondary">Try again</Button>
          </a>
        </div>
      ) : orders.length === 0 ? (
        <div className="py-20 text-center">
          <h2 className="text-xl font-semibold text-forge-ink mb-2">No orders yet</h2>
          <p className="text-forge-ink-muted mb-8 text-sm max-w-sm mx-auto">
            Place your first order to start collecting robot demonstration data.
          </p>
          <Link href="/orders/new">
            <Button variant="primary">Place your first order</Button>
          </Link>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-forge-border text-left">
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Skill name</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Status</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Episodes ordered</th>
              <th className="pb-3 text-xs font-medium text-forge-ink-muted uppercase tracking-wide">Created</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <OrderRow key={order.order_id} order={order} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
