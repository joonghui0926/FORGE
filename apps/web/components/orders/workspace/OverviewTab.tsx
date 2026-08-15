import { Order, STATUS_LABELS } from '@/lib/types'

interface OverviewTabProps {
  order: Order
}

export function OverviewTab({ order }: OverviewTabProps) {
  const { label, detail } = STATUS_LABELS[order.state]
  const statusText = detail ? `${label} · ${detail}` : label
  const coverage = order.contract?.coverage as { object_ids?: string[]; viewpoint_bins?: string[] } | undefined
  const billing  = order.contract?.rights_profile as string | undefined

  const nextAction: Record<string, string> = {
    DRAFT:       'Complete payment to begin planning your collection.',
    PAID:        'Our team is reviewing your order and planning acquisition.',
    PLANNING:    'Our team is planning your acquisition schedule.',
    ACQUIRING:   'Demonstrations are being collected by human operators.',
    READY:       'Your dataset is ready. Review and approve to trigger delivery.',
  }

  return (
    <div className="flex flex-col gap-10">
      <section>
        <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Status</h3>
        <p className="text-lg text-forge-ink">{statusText}</p>
        {nextAction[order.state] && (
          <p className="mt-2 text-sm text-forge-ink-muted">{nextAction[order.state]}</p>
        )}
        {order.created_at && (
          <p className="mt-1 text-xs text-forge-ink-subtle">
            Last updated: {new Date(order.created_at).toLocaleString('en-US')}
          </p>
        )}
      </section>

      {coverage?.object_ids && coverage.object_ids.length > 0 && (
        <section>
          <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Coverage</h3>
          <div className="flex flex-wrap gap-2">
            {coverage.object_ids.map((id) => (
              <span key={id} className="text-sm px-2.5 py-1 rounded-control border border-forge-border text-forge-ink-muted">
                {id}
              </span>
            ))}
          </div>
          {coverage.viewpoint_bins && coverage.viewpoint_bins.length > 0 && (
            <p className="mt-2 text-sm text-forge-ink-muted">
              Viewpoints: {coverage.viewpoint_bins.join(', ')}
            </p>
          )}
        </section>
      )}

      <section>
        <h3 className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-3">Billing</h3>
        <p className="text-sm text-forge-ink">
          {order.state === 'DRAFT'
            ? 'Awaiting payment to begin collection.'
            : 'Payment received. Billing details available in the Billing tab.'}
        </p>
        {billing && (
          <p className="mt-1 text-xs text-forge-ink-muted">
            Rights profile: {billing.replace(/_/g, ' ')}
          </p>
        )}
      </section>
    </div>
  )
}
