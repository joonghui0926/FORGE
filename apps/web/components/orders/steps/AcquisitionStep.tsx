'use client'

import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type Acquisition = OrderFormData['acquisition']

export function AcquisitionStep({ data, onChange, onNext, onBack }: {
  data: Acquisition
  onChange: (value: Acquisition) => void
  onNext: () => void
  onBack: () => void
}) {
  const mixTotal = data.take_mix.success + data.take_mix.failure + data.take_mix.recovery
  const valid = mixTotal === data.clips_per_participant

  function set<K extends keyof Acquisition>(key: K, value: Acquisition[K]) {
    onChange({ ...data, [key]: value })
  }

  function setMix(key: keyof Acquisition['take_mix'], value: number) {
    onChange({ ...data, take_mix: { ...data.take_mix, [key]: Math.max(0, value) } })
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-control bg-forge-surface-cyan px-4 py-3 text-sm leading-6 text-forge-primary-ink">
        One Terac assignment is one participant session. Multiple clips per person reduce cost;
        multiple people and environments protect diversity.
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="participant-count" label="Unique participants" type="number" required min={2} max={50}
          value={data.participant_count}
          onChange={(event) => set('participant_count', Math.max(2, Number(event.target.value) || 2))} />
        <Field id="clips-per-participant" label="Clips per participant" type="number" required min={2} max={30}
          help={`${data.participant_count * data.clips_per_participant} source clips planned`}
          value={data.clips_per_participant}
          onChange={(event) => set('clips_per_participant', Math.max(2, Number(event.target.value) || 2))} />
        <Field id="environment-count" label="Unique environments" type="number" required min={1} max={data.participant_count}
          value={data.minimum_unique_environments}
          onChange={(event) => set('minimum_unique_environments', Math.min(data.participant_count, Math.max(1, Number(event.target.value) || 1)))} />
      </div>
      <fieldset className="flex flex-col gap-3">
        <legend className="text-sm font-medium text-forge-ink">Per-participant take mix</legend>
        <div className="grid grid-cols-3 gap-3">
          {(['success', 'failure', 'recovery'] as const).map((kind) => (
            <Field key={kind} id={`${kind}-takes`} label={kind[0].toUpperCase() + kind.slice(1)} type="number" required min={kind === 'success' ? 1 : 0}
              value={data.take_mix[kind]}
              onChange={(event) => setMix(kind, Number(event.target.value) || 0)} />
          ))}
        </div>
        <p className={`text-sm ${valid ? 'text-forge-ink-muted' : 'text-forge-danger'}`}>
          Take mix totals {mixTotal}; it must equal {data.clips_per_participant} clips per participant.
        </p>
      </fieldset>
      <label className="flex flex-col gap-1 text-sm font-medium text-forge-ink">
        Participant expertise
        <select value={data.expertise} onChange={(event) => set('expertise', event.target.value as Acquisition['expertise'])}
          className="min-h-12 rounded-control border border-forge-border bg-forge-surface px-4 text-base">
          <option value="general_contributor">General contributor</option>
          <option value="experienced_practitioner">Experienced practitioner</option>
          <option value="verified_domain_expert">Verified domain expert</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-forge-ink">
        Capture mode
        <select value={data.capture_mode} onChange={(event) => set('capture_mode', event.target.value as Acquisition['capture_mode'])}
          className="min-h-12 rounded-control border border-forge-border bg-forge-surface px-4 text-base">
          <option value="mixed_views">Mixed egocentric and third-person</option>
          <option value="egocentric">Egocentric</option>
          <option value="third_person">Third-person</option>
          <option value="synchronized_multiview">Synchronized multiview</option>
        </select>
      </label>
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext} disabled={!valid}>Next</Button>
      </div>
    </div>
  )
}
