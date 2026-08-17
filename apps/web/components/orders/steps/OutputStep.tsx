'use client'

import { OrderFormData } from '@/lib/types'
import { Button } from '@/components/ui/Button'

type Output = OrderFormData['output']

export function OutputStep({ data, onChange, onNext, onBack }: {
  data: Output
  onChange: (value: Output) => void
  onNext: () => void
  onBack: () => void
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-control border border-forge-primary bg-forge-surface-cyan p-4">
        <p className="text-sm font-semibold text-forge-ink">Training-ready human data</p>
        <p className="mt-1 text-sm leading-6 text-forge-ink-muted">
          Rights-cleared source video, reconstruction artifacts, annotations, QC evidence, lineage,
          and a reproducible augmentation recipe. This is data delivery; no robot hardware is involved.
        </p>
      </div>
      <label className="flex items-start gap-3 rounded-control border border-forge-primary bg-forge-surface p-4">
        <input type="radio" checked readOnly className="mt-1 accent-forge-primary" />
        <span>
          <span className="block text-sm font-semibold text-forge-ink">FORGE canonical bundle</span>
          <span className="mt-1 block text-sm leading-6 text-forge-ink-muted">
            Immutable raw media plus manifests and checksums. LeRobot v3, RLDS, and robomimic are
            emitted only for jobs that contain compatible, accepted action/state signals.
          </span>
        </span>
      </label>
      <label className="flex items-start gap-3">
        <input type="checkbox" className="mt-1 accent-forge-primary"
          checked={data.augmentation === 'training_recipe'}
          onChange={(event) => onChange({ ...data, augmentation: event.target.checked ? 'training_recipe' : 'none' })} />
        <span>
          <span className="block text-sm font-medium text-forge-ink">Include training-time augmentation recipe</span>
          <span className="block text-sm text-forge-ink-muted">Seeds, transforms, safe ranges, and source lineage; raw clips remain unchanged.</span>
        </span>
      </label>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext}>Next</Button>
      </div>
    </div>
  )
}
