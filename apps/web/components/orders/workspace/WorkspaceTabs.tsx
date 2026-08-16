'use client'

import { useState } from 'react'
import { Order } from '@/lib/types'
import { AcquisitionTab } from './AcquisitionTab'
import { ActivityTab } from './ActivityTab'
import { BillingTab } from './BillingTab'
import { DatasetTab } from './DatasetTab'
import { EpisodesTab } from './EpisodesTab'
import { OverviewTab } from './OverviewTab'
import { PipelineTab } from './PipelineTab'
import { QualityTab } from './QualityTab'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'acquisition', label: 'Acquisition' },
  { id: 'processing', label: 'Pipeline' },
  { id: 'quality', label: 'Quality' },
  { id: 'episodes', label: 'Episodes' },
  { id: 'dataset', label: 'Dataset' },
  { id: 'activity', label: 'Activity' },
  { id: 'billing', label: 'Billing' },
] as const

type TabId = typeof TABS[number]['id']

export function WorkspaceTabs({ order }: { order: Order }) {
  const [active, setActive] = useState<TabId>('overview')

  return (
    <div>
      <div className="flex gap-0 overflow-x-auto border-b border-forge-border" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={active === id}
            aria-controls={`tabpanel-${id}`}
            onClick={() => setActive(id)}
            className={[
              'shrink-0 px-4 py-3 text-sm font-medium transition-colors',
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
        {active === 'overview' && <OverviewTab order={order} />}
        {active === 'acquisition' && <AcquisitionTab order={order} />}
        {active === 'processing' && <PipelineTab order={order} />}
        {active === 'quality' && <QualityTab order={order} />}
        {active === 'episodes' && <EpisodesTab order={order} />}
        {active === 'dataset' && <DatasetTab order={order} />}
        {active === 'activity' && <ActivityTab order={order} />}
        {active === 'billing' && <BillingTab order={order} />}
      </div>
    </div>
  )
}
