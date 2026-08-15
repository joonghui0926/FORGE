export const ORDER_STATES = [
  'DRAFT', 'PAID', 'PLANNING', 'ACQUIRING', 'PRE_QC',
  'PROCESSING', 'CONTACTING', 'RETARGETING', 'VALIDATING',
  'RECOLLECTING', 'AMPLIFYING', 'BATCH_QC', 'PACKAGING',
  'READY', 'CANCELLED', 'FAILED',
] as const

export type OrderState = typeof ORDER_STATES[number]

export interface StatusEntry {
  label: string
  detail?: string
}

export const STATUS_LABELS: Record<OrderState, StatusEntry> = {
  DRAFT:       { label: 'Awaiting payment' },
  PAID:        { label: 'Planning your collection' },
  PLANNING:    { label: 'Planning your collection' },
  ACQUIRING:   { label: 'Collecting demonstrations' },
  PRE_QC:      { label: 'Processing', detail: 'Pre-quality check' },
  PROCESSING:  { label: 'Processing', detail: 'Data processing' },
  CONTACTING:  { label: 'Processing', detail: 'Contacting participants' },
  RETARGETING: { label: 'Processing', detail: 'Robot retargeting' },
  VALIDATING:  { label: 'Processing', detail: 'Physics validation' },
  RECOLLECTING:{ label: 'Processing', detail: 'Recollecting demonstrations' },
  AMPLIFYING:  { label: 'Processing', detail: 'Dataset amplification' },
  BATCH_QC:    { label: 'Processing', detail: 'Batch quality check' },
  PACKAGING:   { label: 'Processing', detail: 'Packaging dataset' },
  READY:       { label: 'Ready for review' },
  CANCELLED:   { label: 'Cancelled' },
  FAILED:      { label: 'Needs attention' },
}

export interface Order {
  order_id: string
  state: OrderState
  stripe_payment_link: string | null
  skill_name?: string
  created_at?: string
  volume_validated_episodes?: number
  contract?: Record<string, unknown>
}

export interface CreateOrderPayload {
  skill: {
    name: string
    initial_state: string
    success_predicate: string
    failure_predicates: string[]
    phases: string[]
  }
  embodiment: {
    robot_id: string
    model_uri: string
    model_sha256: string
    hand_type: 'dexterous' | 'parallel_gripper' | 'suction'
    joint_limits_uri: string
  }
  volume_validated_episodes: number
  coverage: {
    object_ids: string[]
    viewpoint_bins: string[]
    grasp_variation: 'required' | 'preferred' | 'not_required'
  }
  quality: {
    source_replay_pass_required: boolean
    max_penetration_m: number
    min_contact_phase_f1: number
    min_delivery_acceptance_rate: number
  }
  rights_profile: 'customer_exclusive_derivatives' | 'forge_retained' | 'open'
}

export interface CreateOrderResponse {
  order_id: string
  state: OrderState
  stripe_payment_link: string | null
}
