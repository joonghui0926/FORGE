'use client'

import { OrderFormData } from '@/lib/types'
import { Button } from '@/components/ui/Button'

type RightsProfile = OrderFormData['rights_profile']

const OPTIONS: { value: RightsProfile; label: string; desc: string }[] = [
  {
    value: 'customer_exclusive_derivatives',
    label: 'Exclusive with derivatives',
    desc: 'You own the dataset and any derivatives. FORGE retains no rights.',
  },
  {
    value: 'forge_retained',
    label: 'FORGE retained',
    desc: 'FORGE may use anonymized data for research and model improvement.',
  },
  {
    value: 'open',
    label: 'Open',
    desc: 'Dataset published under CC-BY. Lower pricing applies.',
  },
]

interface RightsStepProps {
  data: RightsProfile
  onChange: (v: RightsProfile) => void
  onNext: () => void
  onBack: () => void
}

export function RightsStep({ data, onChange, onNext, onBack }: RightsStepProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        {OPTIONS.map(({ value, label, desc }) => (
          <label
            key={value}
            className={[
              'flex items-start gap-3 p-4 rounded-control border cursor-pointer transition-colors',
              data === value ? 'border-forge-primary bg-forge-surface-cyan' : 'border-forge-border hover:bg-forge-surface-soft',
            ].join(' ')}
          >
            <input
              type="radio" name="rights-profile" value={value}
              checked={data === value} onChange={() => onChange(value)}
              className="mt-0.5 accent-forge-primary"
            />
            <div>
              <p className="text-sm font-semibold text-forge-ink">{label}</p>
              <p className="text-sm text-forge-ink-muted mt-0.5">{desc}</p>
            </div>
          </label>
        ))}
      </div>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext}>Next</Button>
      </div>
    </div>
  )
}
