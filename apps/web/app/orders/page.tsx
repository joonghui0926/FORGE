import Link from 'next/link'
import { ApiError } from '@/lib/api'
import { apiServer } from '@/lib/api-server'
import { Order } from '@/lib/types'
import { OrderRow } from '@/components/orders/OrderRow'
import { Button } from '@/components/ui/Button'

const VIEW_CONFIG = {
  ready: {
    title: 'Ready datasets',
    description: 'Validated datasets ready for review and delivery.',
    states: ['READY'],
  },
  quality: {
    title: 'Quality pipeline',
    description: 'Orders currently being collected, compiled, or quality-checked.',
    states: ['PAID', 'PLANNING', 'ACQUIRING', 'PRE_QC', 'PROCESSING', 'CONTACTING', 'RETARGETING', 'VALIDATING', 'RECOLLECTING', 'AMPLIFYING', 'BATCH_QC', 'REVIEW', 'BLOCKED', 'FAILED'],
  },
  packages: {
    title: 'Delivery packages',
    description: 'Immutable, validated packages prepared for customer delivery.',
    states: ['PACKAGING', 'READY'],
  },
} as const

type OrderView = keyof typeof VIEW_CONFIG

export default async function OrdersPage({ searchParams }: { searchParams?: { view?: string } }) {
  let orders: Order[] = []
  let fetchError: string | null = null
  const requestedView = searchParams?.view
  const view = requestedView && requestedView in VIEW_CONFIG ? requestedView as OrderView : null

  try {
    orders = await apiServer.get<Order[]>('/orders')
    if (view) {
      const states = VIEW_CONFIG[view].states as readonly string[]
      orders = orders.filter((order) => states.includes(order.state))
    }
  } catch (err) {
    fetchError = err instanceof ApiError
      ? 'We could not connect to the server. Check your connection.'
      : 'Something went wrong. Please try again.'
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-forge-ink">{view ? VIEW_CONFIG[view].title : 'Your Orders'}</h1>
          <p className="text-forge-ink-muted mt-1 text-[15px]">
            {view ? VIEW_CONFIG[view].description : 'Track and manage your dataset orders.'}
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
          <h2 className="text-xl font-semibold text-forge-ink mb-2">{view ? 'Nothing in this view yet' : 'No orders yet'}</h2>
          <p className="text-forge-ink-muted mb-8 text-sm max-w-sm mx-auto">
            {view ? 'Orders will appear here automatically as the production workflow advances.' : 'Place your first order to start collecting robot demonstration data.'}
          </p>
          <Link href="/orders/new">
            <Button variant="primary">Place your first order</Button>
          </Link>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-forge-border text-left">
              <th className="pb-3 text-sm font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Skill name</th>
              <th className="pb-3 text-sm font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Status</th>
              <th className="pb-3 text-sm font-medium text-forge-ink-muted uppercase tracking-wide pr-6">Episodes ordered</th>
              <th className="pb-3 text-sm font-medium text-forge-ink-muted uppercase tracking-wide">Created</th>
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
