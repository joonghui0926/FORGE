export const ORDER_STATES = [
  'DRAFT', 'PAID', 'PLANNING', 'ACQUIRING', 'PRE_QC',
  'PROCESSING', 'CONTACTING', 'RETARGETING', 'VALIDATING',
  'RECOLLECTING', 'AMPLIFYING', 'BATCH_QC', 'PACKAGING',
  'READY', 'REVIEW', 'BLOCKED', 'CANCELLED', 'FAILED',
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
  REVIEW:      { label: 'Needs review', detail: 'Operator decision required' },
  BLOCKED:     { label: 'Blocked', detail: 'Closed with evidence' },
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
  pipeline?: PipelineEvent[]
  workspace?: OrderWorkspace
}

export interface PipelineEvent {
  step: string
  actor: string
  state?: string
  evidence?: Record<string, unknown>
  created_at: string
}

export interface ProviderRequestSummary {
  provider: 'terac' | 'band' | 'pioneer' | string
  purpose: string
  state: string
  external_id: string | null
  correlation_id: string
  created_at: string
  completed_at: string | null
}

export interface AcquisitionBatch {
  batch_id: string
  sequence: number
  terac_campaign_id: string | null
  created_at: string
  submitted: number
  accepted: number
}

export interface CaptureSummary {
  capture_id: string
  state: string
  object_id: string
  viewpoint_bin: string
  submitted_at: string
}

export interface WorkflowSummary {
  status: string
  current_step: string
  render_root_run_id: string | null
  last_error_code: string | null
  last_error_message: string | null
  updated_at: string
}

export interface GPUJobSummary {
  job_id: string
  stage: string
  attempt: number
  status: string
  pipeline_version: string
  provider_job_id: string | null
  gpu_seconds: number | null
  metrics: Record<string, unknown>
  error_code: string | null
  created_at: string
  completed_at: string | null
}

export interface QCRunSummary {
  qc_run_id: string
  subject_type: string
  stage: string
  passed: boolean
  reason_codes: string[]
  metrics: Record<string, unknown>
  thresholds: Record<string, unknown>
  simulation: boolean
  created_at: string
}

export interface DecisionSummary {
  decision_id: string
  decision_type: string
  reason_codes: string[]
  confidence: number | null
  policy_version: string
  requires_human_approval: boolean
  approved_by: string | null
  created_at: string
}

export interface EpisodeSummary {
  episode_id: string
  kind: 'source' | 'generated'
  source_id: string | null
  lineage_group_id: string
  batch_qc_passed: boolean | null
  delivered: boolean
  created_at: string
}

export interface DeliverySummary {
  delivery_id: string
  dataset_version: string
  rights_profile: string
  schema_version: string | null
  episode_count: number | null
  artifact_count: number
  created_at: string
}

export interface OrderWorkspace {
  acquisition: {
    batches: AcquisitionBatch[]
    captures: CaptureSummary[]
    provider_requests: ProviderRequestSummary[]
  }
  processing: {
    workflow: WorkflowSummary | null
    jobs: GPUJobSummary[]
  }
  quality: {
    runs: QCRunSummary[]
    decisions: DecisionSummary[]
    provider_requests: ProviderRequestSummary[]
  }
  episodes: EpisodeSummary[]
  delivery: DeliverySummary | null
  billing: {
    payment_status: 'paid' | 'awaiting_payment'
    payment_reference: string | null
  }
}

export interface DeliveryResponse {
  delivery_id: string
  order_id: string
  dataset_version: string
  download_url: string
  manifest_url: string
  expires_in_seconds: number
}

export interface CreateOrderPayload {
  skill: {
    name: string
    motion_family: MotionFamily
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

export interface OrderFormData {
  skill: {
    name: string
    motion_family: MotionFamily
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
  coverage: {
    object_ids: string[]
    viewpoint_bins: string[]
    grasp_variation: 'required' | 'preferred' | 'not_required'
  }
  volume_validated_episodes: number
  quality: {
    source_replay_pass_required: boolean
    max_penetration_m: number
    min_contact_phase_f1: number
    min_delivery_acceptance_rate: number
  }
  rights_profile: 'customer_exclusive_derivatives' | 'forge_retained' | 'open'
}

export const INITIAL_ORDER_FORM_DATA: OrderFormData = {
  skill: { name: '', motion_family: 'whole_body', initial_state: '', success_predicate: '', failure_predicates: [], phases: [] },
  embodiment: { robot_id: '', model_uri: '', model_sha256: '', hand_type: 'parallel_gripper', joint_limits_uri: '' },
  coverage: { object_ids: [], viewpoint_bins: [], grasp_variation: 'preferred' },
  volume_validated_episodes: 10,
  quality: {
    source_replay_pass_required: true,
    max_penetration_m: 0.002,
    min_contact_phase_f1: 0.8,
    min_delivery_acceptance_rate: 0.9,
  },
  rights_profile: 'customer_exclusive_derivatives',
}

export type MotionFamily =
  | 'manipulation' | 'bimanual' | 'tool_use' | 'locomotion' | 'whole_body'
  | 'mobile_manipulation' | 'navigation' | 'articulated_machine' | 'aerial' | 'multi_robot'
