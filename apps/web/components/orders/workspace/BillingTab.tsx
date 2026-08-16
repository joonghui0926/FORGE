import { Order } from '@/lib/types'
import { SectionTitle, WorkspaceEmpty } from './WorkspaceEmpty'

export function BillingTab({ order }: { order: Order }) {
  const billing = order.workspace?.billing
  const rights = typeof order.contract?.rights_profile === 'string' ? order.contract.rights_profile : null
  const paid = billing?.payment_status === 'paid'
  if (!billing) return <WorkspaceEmpty title="Billing data is unavailable">Refresh after the order workspace has loaded.</WorkspaceEmpty>

  return (
    <div className="flex flex-col gap-10">
      <section className={`rounded-surface px-5 py-5 sm:px-6 ${paid ? 'bg-forge-success-soft' : 'bg-forge-warning-soft'}`}>
        <p className={`text-sm font-semibold uppercase tracking-wide ${paid ? 'text-forge-success' : 'text-forge-warning'}`}>{paid ? 'Payment received' : 'Awaiting payment'}</p>
        <p className="mt-2 max-w-2xl text-[15px] leading-6 text-forge-ink-muted">{paid ? 'The collection and compiler workflow may proceed. Provider costs and GPU execution remain tied to this order audit trail.' : 'Acquisition starts only after Stripe confirms payment.'}</p>
      </section>
      <section>
        <SectionTitle>Order terms</SectionTitle>
        <dl className="grid gap-x-12 gap-y-6 sm:grid-cols-2">
          <div><dt className="text-sm text-forge-ink-muted">Payment reference</dt><dd className="mt-1 font-mono text-sm text-forge-ink">{billing.payment_reference ?? 'Not issued'}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Validated episode target</dt><dd className="mt-1 text-base font-medium text-forge-ink">{order.volume_validated_episodes ?? '—'}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Rights profile</dt><dd className="mt-1 text-base font-medium text-forge-ink">{rights?.replaceAll('_', ' ') ?? 'Not specified'}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Order ID</dt><dd className="mt-1 break-all font-mono text-sm text-forge-ink">{order.order_id}</dd></div>
        </dl>
      </section>
    </div>
  )
}
