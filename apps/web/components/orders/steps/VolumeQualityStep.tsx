'use client'

import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type QualityData = OrderFormData['quality']

interface VolumeQualityStepProps {
  volume: number
  quality: QualityData
  onChangeVolume: (v: number) => void
  onChangeQuality: (q: QualityData) => void
  onNext: () => void
  onBack: () => void
}

export function VolumeQualityStep({ volume, quality, onChangeVolume, onChangeQuality, onNext, onBack }: VolumeQualityStepProps) {
  function setQ<K extends keyof QualityData>(key: K, value: QualityData[K]) {
    onChangeQuality({ ...quality, [key]: value })
  }

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="episode-count" label="Validated episode count" type="number" required
        help="Number of physics-validated episodes to deliver"
        value={volume}
        onChange={(e) => onChangeVolume(Math.max(1, parseInt(e.target.value, 10) || 1))}
        min={1} step={1}
      />
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={quality.source_replay_pass_required}
          onChange={(e) => setQ('source_replay_pass_required', e.target.checked)}
          className="accent-forge-primary w-4 h-4"
        />
        <div>
          <p className="text-sm font-medium text-forge-ink">Require source replay pass</p>
          <p className="text-sm text-forge-ink-muted">
            Each episode must pass source replay before retargeting. Recommended.
          </p>
        </div>
      </label>
      <Field
        id="max-penetration" label="Max penetration (m)" type="number" required
        help="Maximum allowed mesh interpenetration depth per frame"
        value={quality.max_penetration_m}
        onChange={(e) => setQ('max_penetration_m', parseFloat(e.target.value) || 0.002)}
        step={0.001} min={0}
      />
      <Field
        id="min-f1" label="Minimum contact-phase F1" type="number" required
        help="Minimum F1 score for contact phase detection (0-1)"
        value={quality.min_contact_phase_f1}
        onChange={(e) => setQ('min_contact_phase_f1', parseFloat(e.target.value) || 0.8)}
        step={0.05} min={0} max={1}
      />
      <Field
        id="min-acceptance" label="Minimum delivery acceptance rate" type="number" required
        help="Minimum fraction of retargeted episodes that must pass final QC (0-1)"
        value={quality.min_delivery_acceptance_rate}
        onChange={(e) => setQ('min_delivery_acceptance_rate', parseFloat(e.target.value) || 0.9)}
        step={0.05} min={0} max={1}
      />
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext}>Next</Button>
      </div>
    </div>
  )
}
