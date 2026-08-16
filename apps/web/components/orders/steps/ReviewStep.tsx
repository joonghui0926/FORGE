'use client'

import { OrderFormData } from '@/lib/types'
import { Button } from '@/components/ui/Button'

interface ReviewStepProps {
  data: OrderFormData
  onBack: () => void
  onSubmit: () => Promise<void>
  submitting: boolean
  error: string | null
}

const RIGHTS_LABELS: Record<string, string> = {
  customer_exclusive_derivatives: 'Exclusive with derivatives',
  forge_retained: 'FORGE retained',
  open: 'Open (CC-BY)',
}

export function ReviewStep({ data, onBack, onSubmit, submitting, error }: ReviewStepProps) {
  return (
    <div className="flex flex-col gap-6">
      <dl className="flex flex-col gap-4 text-sm">
        <div>
          <dt className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Task</dt>
          <dd className="text-forge-ink font-medium">{data.skill.name}</dd>
          <dd className="text-forge-ink-muted mt-0.5">{data.skill.motion_family.replace(/_/g, ' ')}</dd>
          <dd className="text-forge-ink-muted mt-0.5">{data.skill.initial_state} &rarr; {data.skill.success_predicate}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Robot</dt>
          <dd className="text-forge-ink">{data.embodiment.robot_id} &middot; {data.embodiment.hand_type.replace(/_/g, ' ')}</dd>
          <dd className="text-forge-ink-muted font-mono text-sm mt-0.5 break-all">{data.embodiment.model_uri}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Coverage</dt>
          <dd className="text-forge-ink">
            {data.coverage.object_ids.length > 0 ? data.coverage.object_ids.join(', ') : '—'}
          </dd>
          {data.coverage.viewpoint_bins.length > 0 && (
            <dd className="text-forge-ink-muted mt-0.5">Viewpoints: {data.coverage.viewpoint_bins.join(', ')}</dd>
          )}
        </div>
        <div>
          <dt className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Volume</dt>
          <dd className="text-forge-ink">{data.volume_validated_episodes} validated episodes</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-forge-ink-muted uppercase tracking-wide mb-1">Rights</dt>
          <dd className="text-forge-ink">{RIGHTS_LABELS[data.rights_profile] ?? data.rights_profile}</dd>
        </div>
      </dl>

      <div className="flex items-end justify-between gap-6 border-t border-forge-border/70 pt-5">
        <div>
          <p className="text-sm font-medium text-forge-ink-muted">One-time dataset pilot</p>
          <p className="mt-1 text-sm leading-6 text-forge-ink-muted">
            Robot-ready data delivery. Robot hardware is not included.
          </p>
        </div>
        <p className="shrink-0 text-3xl font-semibold tracking-[-0.04em] text-forge-ink">$350</p>
      </div>

      {error && (
        <p className="text-sm text-forge-danger bg-forge-danger-soft rounded-control px-4 py-3">
          {error}
        </p>
      )}

      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack} disabled={submitting}>Back</Button>
        <Button variant="primary" onClick={onSubmit} loading={submitting}>
          Continue to secure payment
        </Button>
      </div>
    </div>
  )
}
