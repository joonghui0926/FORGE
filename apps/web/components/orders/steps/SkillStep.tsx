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
