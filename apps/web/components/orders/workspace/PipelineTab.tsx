import { Order } from '@/lib/types'


const PIPELINE = [
  'validate_contract',
  'request_band_collection_plan',
  'create_terac_campaign',
  'fast_pre_qc',
  'request_pioneer_pre_qc',
  'submit_runpod_gpu_job',
  'deterministic_validation',
  'request_pioneer_final_verdict',
  'request_band_quality_decision',
  'package_dataset',
]

const LABELS: Record<string, string> = {
  validate_contract: 'Contract validated',
  request_band_collection_plan: 'Band collection council',
  create_terac_campaign: 'Terac campaign',
  fast_pre_qc: 'Deterministic pre-QC',
  request_pioneer_pre_qc: 'Pioneer source verdict',
  submit_runpod_gpu_job: 'RunPod physical compiler',
  deterministic_validation: 'Physics and contract validation',
  request_pioneer_final_verdict: 'Pioneer final verdict',
  request_band_quality_decision: 'Band quality council',
  package_dataset: 'Robot-ready package',
}

export function PipelineTab({ order }: { order: Order }) {
  const events = order.pipeline ?? []
  const completed = new Map(events.map((event) => [event.step, event]))
  const current = events.at(-1)?.step

  return (
    <ol className="max-w-2xl" aria-label="FORGE production pipeline">
      {PIPELINE.map((step, index) => {
        const event = completed.get(step)
        const active = step === current
        return (
          <li key={step} className="grid grid-cols-[28px_1fr] gap-3 pb-6 last:pb-0">
            <div className="flex flex-col items-center" aria-hidden="true">
              <span className={`mt-0.5 h-3 w-3 rounded-full ${event ? 'bg-forge-primary' : active ? 'bg-forge-warning' : 'bg-forge-border-strong'}`} />
              {index < PIPELINE.length - 1 && <span className="mt-2 w-px grow bg-forge-border" />}
            </div>
            <div>
              <p className="text-base font-medium text-forge-ink">{LABELS[step]}</p>
              <p className="mt-1 text-sm text-forge-ink-muted">
                {event
                  ? `${event.state ?? 'complete'} · ${new Date(event.created_at).toLocaleString('en-US')}`
                  : active ? 'Running now' : 'Waiting for prior gates'}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
