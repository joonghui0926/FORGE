'use client'

import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type CoverageData = OrderFormData['coverage']

const VIEWPOINT_BINS = ['top', 'front', 'side-left', 'side-right', 'angled'] as const
const GRASP_OPTIONS: { value: CoverageData['grasp_variation']; label: string; desc: string }[] = [
  { value: 'required',     label: 'Required',     desc: 'Operators must demonstrate multiple grasp styles' },
  { value: 'preferred',    label: 'Preferred',    desc: 'Operators encouraged to vary grasp — default' },
  { value: 'not_required', label: 'Not required', desc: 'Single consistent grasp style acceptable' },
]

interface CoverageStepProps {
  data: CoverageData
  onChange: (data: CoverageData) => void
  onNext: () => void
  onBack: () => void
}

export function CoverageStep({ data, onChange, onNext, onBack }: CoverageStepProps) {
  function set<K extends keyof CoverageData>(key: K, value: CoverageData[K]) {
    onChange({ ...data, [key]: value })
  }

  function toggleViewpoint(bin: string) {
    const bins = data.viewpoint_bins.includes(bin)
      ? data.viewpoint_bins.filter((b) => b !== bin)
      : [...data.viewpoint_bins, bin]
    set('viewpoint_bins', bins)
  }

  const canProceed = data.object_ids.length > 0

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="object-ids" label="Object IDs" required
        help="Comma-separated object identifiers. e.g. apple, green-cup, blue-block"
        value={data.object_ids.join(', ')}
        onChange={(e) => set('object_ids', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
        placeholder="apple, green-cup"
      />
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium text-forge-ink">Viewpoint bins</span>
        <div className="flex flex-wrap gap-3">
          {VIEWPOINT_BINS.map((bin) => (
            <label key={bin} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox" value={bin}
                checked={data.viewpoint_bins.includes(bin)}
                onChange={() => toggleViewpoint(bin)}
                className="accent-forge-primary"
              />
              <span className="text-sm text-forge-ink capitalize">{bin.replace('-', ' ')}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium text-forge-ink">Grasp variation</span>
        <div className="flex flex-col gap-2">
          {GRASP_OPTIONS.map(({ value, label, desc }) => (
            <label key={value} className="flex items-start gap-3 cursor-pointer">
              <input
                type="radio" name="grasp-variation" value={value}
                checked={data.grasp_variation === value}
                onChange={() => set('grasp_variation', value)}
                className="mt-0.5 accent-forge-primary"
              />
              <div>
                <p className="text-sm font-medium text-forge-ink">{label}</p>
                <p className="text-sm text-forge-ink-muted">{desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext} disabled={!canProceed}>Next</Button>
      </div>
    </div>
  )
}
