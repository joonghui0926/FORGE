'use client'

import { OrderFormData } from '@/lib/types'
import { Field } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'

type EmbodimentData = OrderFormData['embodiment']

interface RobotStepProps {
  data: EmbodimentData
  onChange: (data: EmbodimentData) => void
  onNext: () => void
  onBack: () => void
}

const HAND_TYPES: { value: EmbodimentData['hand_type']; label: string }[] = [
  { value: 'parallel_gripper', label: 'Parallel gripper' },
  { value: 'dexterous',        label: 'Dexterous hand' },
  { value: 'suction',          label: 'Suction cup' },
]

export function RobotStep({ data, onChange, onNext, onBack }: RobotStepProps) {
  function set<K extends keyof EmbodimentData>(key: K, value: EmbodimentData[K]) {
    onChange({ ...data, [key]: value })
  }

  const canProceed = data.robot_id.trim() && data.model_uri.trim() && data.model_sha256.trim() && data.joint_limits_uri.trim()

  return (
    <div className="flex flex-col gap-5">
      <Field
        id="robot-id" label="Robot ID" required
        value={data.robot_id} onChange={(e) => set('robot_id', e.target.value)}
        placeholder="e.g. franka-panda-001"
      />
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-forge-ink">
          Hand type <span className="text-forge-danger ml-0.5">*</span>
        </label>
        <div className="flex gap-4">
          {HAND_TYPES.map(({ value, label }) => (
            <label key={value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio" name="hand-type" value={value}
                checked={data.hand_type === value}
                onChange={() => set('hand_type', value)}
                className="accent-forge-primary"
              />
              <span className="text-sm text-forge-ink">{label}</span>
            </label>
          ))}
        </div>
      </div>
      <Field
        id="model-uri" label="URDF / MJCF URI" required
        help="Use r2://bucket/path format. Contact us if you need help uploading your model."
        value={data.model_uri} onChange={(e) => set('model_uri', e.target.value)}
        placeholder="r2://forge-dev/robots/franka.urdf"
      />
      <Field
        id="model-sha256" label="Model SHA-256" required
        help="SHA-256 hash of the URDF/MJCF file for integrity verification"
        value={data.model_sha256} onChange={(e) => set('model_sha256', e.target.value)}
        placeholder="abc123..."
      />
      <Field
        id="joint-limits-uri" label="Joint limits URI" required
        help="Immutable r2:// URI to the target robot's joint-limit configuration."
        value={data.joint_limits_uri} onChange={(e) => set('joint_limits_uri', e.target.value)}
        placeholder="r2://forge-dev/robots/franka-limits.yaml"
      />
      <div className="flex justify-between pt-2">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button variant="primary" onClick={onNext} disabled={!canProceed}>Next</Button>
      </div>
    </div>
  )
}
