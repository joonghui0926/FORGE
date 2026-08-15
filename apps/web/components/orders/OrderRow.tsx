import Link from 'next/link'
import { Order } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface OrderRowProps {
  order: Order
}

export function OrderRow({ order }: OrderRowProps) {
  const date = order.created_at
    ? new Date(order.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—'

  return (
    <tr className="border-b border-forge-border last:border-0 hover:bg-forge-surface-soft transition-colors">
      <td className="py-4 pr-6">
        <Link
          href={`/orders/${order.order_id}`}
          className="text-forge-ink font-medium hover:text-forge-primary transition-colors"
        >
          {order.skill_name ?? 'Untitled order'}
        </Link>
      </td>
      <td className="py-4 pr-6">
        <StatusBadge state={order.state} />
      </td>
      <td className="py-4 pr-6 text-forge-ink-muted tabular-nums">
        {order.volume_validated_episodes ?? '—'}
      </td>
      <td className="py-4 text-sm text-forge-ink-muted tabular-nums">{date}</td>
    </tr>
  )
}
