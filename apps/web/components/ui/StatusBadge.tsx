import { OrderState, STATUS_LABELS } from '@/lib/types'

const LABEL_ICON: Record<string, string> = {
  'Awaiting payment':          '○',
  'Planning your collection':  '◎',
  'Collecting demonstrations': '●',
  'Processing':                '⟳',
  'Ready for review':          '✓',
  'Cancelled':                 '✕',
  'Needs attention':           '!',
}

const LABEL_COLOR: Record<string, string> = {
  'Awaiting payment':          'text-forge-warning bg-forge-warning-soft',
  'Planning your collection':  'text-forge-info bg-forge-info-soft',
  'Collecting demonstrations': 'text-forge-info bg-forge-info-soft',
  'Processing':                'text-forge-info bg-forge-info-soft',
  'Ready for review':          'text-forge-success bg-forge-success-soft',
  'Cancelled':                 'text-forge-ink-muted bg-forge-surface-soft',
  'Needs attention':           'text-forge-danger bg-forge-danger-soft',
}

interface StatusBadgeProps {
  state: OrderState
  className?: string
}

export function StatusBadge({ state, className = '' }: StatusBadgeProps) {
  const { label, detail } = STATUS_LABELS[state]
  const icon  = LABEL_ICON[label]  ?? '·'
  const color = LABEL_COLOR[label] ?? 'text-forge-ink-muted bg-forge-surface-soft'

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-sm font-medium ${color} ${className}`}>
      <span aria-hidden="true">{icon}</span>
      {label}
      {detail && <span className="opacity-60 text-xs">· {detail}</span>}
    </span>
  )
}
