'use client'

import { useState } from 'react'
import { Order } from '@/lib/types'
import { OverviewTab } from './OverviewTab'
import { PlaceholderTab } from './PlaceholderTab'
import { PipelineTab } from './PipelineTab'

const TABS = [
  { id: 'overview',    label: 'Overview' },
  { id: 'acquisition', label: 'Acquisition' },
  { id: 'processing',  label: 'Pipeline' },
  { id: 'quality',     label: 'Quality' },
  { id: 'episodes',    label: 'Episodes' },
  { id: 'dataset',     label: 'Dataset' },
  { id: 'activity',    label: 'Activity' },
  { id: 'billing',     label: 'Billing' },
] as const

type TabId = typeof TABS[number]['id']

const PLACEHOLDER_DESCRIPTIONS: Partial<Record<TabId, string>> = {
  acquisition: 'Details about human operator assignments, session schedule, and collection progress.',
  processing:  'Retargeting jobs, physics simulation runs, and intermediate QC results.',
  quality:     'Penetration metrics, F1 scores, acceptance rates, and QC decision history.',
  episodes:    'Individual episode recordings with replay validation status.',
  dataset:     'Final packaged dataset, file manifest, and download links.',
  activity:    'Full audit trail — every state transition and decision for this order.',
  billing:     'Invoice, payment status, and rights license summary.',
}

interface WorkspaceTabsProps {
  order: Order
}

export function WorkspaceTabs({ order }: WorkspaceTabsProps) {
  const [active, setActive] = useState<TabId>('overview')

  return (
    <div>
      <div className="flex gap-0 border-b border-forge-border" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={active === id}
            aria-controls={`tabpanel-${id}`}
            onClick={() => setActive(id)}
            className={[
              'px-4 py-3 text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-forge-focus focus-visible:ring-inset',
              active === id
                ? 'text-forge-primary border-b-2 border-forge-primary -mb-px'
                : 'text-forge-ink-muted hover:text-forge-ink',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="pt-8" id={`tabpanel-${active}`} role="tabpanel">
        {active === 'overview' ? (
          <OverviewTab order={order} />
        ) : active === 'processing' ? (
          <PipelineTab order={order} />
        ) : (
          <PlaceholderTab
            name={TABS.find((t) => t.id === active)!.label}
            description={PLACEHOLDER_DESCRIPTIONS[active] ?? 'Details for this section will appear here.'}
          />
        )}
      </div>
    </div>
  )
}
