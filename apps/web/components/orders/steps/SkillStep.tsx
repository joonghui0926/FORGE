'use client'

import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type SkillData = OrderFormData['skill']

interface SkillStepProps {
  data: SkillData
  onChange: (data: SkillData) => void
  onNext: () => void
}

export function SkillStep({ data, onChange, onNext }: SkillStepProps) {
  function set<K extends keyof SkillData>(key: K, value: SkillData[K]) {
    onChange({ ...data, [key]: value })
  }

  function handleNext() {
    if (!data.name.trim() || !data.initial_state.trim() || !data.success_predicate.trim()) return
    onNext()
  }

  const canProceed = data.name.trim() && data.initial_state.trim() && data.success_predicate.trim()

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="task-name" label="Task name" required
        value={data.name} onChange={(e) => set('name', e.target.value)}
        placeholder="e.g. Pick and place apple"
      />
      <div className="flex flex-col gap-1">
        <label htmlFor="motion-family" className="text-sm font-medium text-forge-ink">
          Motion family
        </label>
        <select
          id="motion-family"
          value={data.motion_family}
          onChange={(event) => set('motion_family', event.target.value as SkillData['motion_family'])}
          className="min-h-[48px] px-4 text-base rounded-control border border-forge-border bg-forge-surface text-forge-ink focus:outline-none focus:ring-2 focus:ring-forge-focus"
        >
          <option value="whole_body">Whole-body motion</option>
          <option value="manipulation">Manipulation</option>
          <option value="bimanual">Bimanual manipulation</option>
          <option value="tool_use">Tool use</option>
          <option value="locomotion">Locomotion</option>
          <option value="mobile_manipulation">Mobile manipulation</option>
          <option value="navigation">Navigation</option>
          <option value="articulated_machine">Articulated machine</option>
          <option value="aerial">Aerial robot</option>
          <option value="multi_robot">Multi-robot coordination</option>
        </select>
        <p className="text-sm text-forge-ink-muted">
          FORGE selects the matching capture protocol, retargeter, and physics profile.
        </p>
      </div>
      <Field
        id="initial-state" label="Initial state" required
        value={data.initial_state} onChange={(e) => set('initial_state', e.target.value)}
        placeholder="e.g. Apple resting on table surface"
      />
      <Field
        id="success-predicate" label="Success condition" required
        value={data.success_predicate} onChange={(e) => set('success_predicate', e.target.value)}
        placeholder="e.g. Apple grasped and held above table by 10 cm"
      />
      <Field
        id="failure-predicates" label="Failure conditions"
        help="Comma-separated. e.g. apple dropped, apple crushed"
        value={data.failure_predicates.join(', ')}
        onChange={(e) => set('failure_predicates', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
      />
      <Field
        id="phases" label="Task phases"
        help="Comma-separated. e.g. approach, grasp, lift"
        value={data.phases.join(', ')}
        onChange={(e) => set('phases', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
      />
      <div className="flex justify-end pt-2">
        <Button variant="primary" onClick={handleNext} disabled={!canProceed}>
          Next
        </Button>
      </div>
    </div>
  )
}
