import { Order } from '@/lib/types'
import { SectionTitle } from './WorkspaceEmpty'

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
  const workflow = order.workspace?.processing.workflow
  const jobs = order.workspace?.processing.jobs ?? []

  return (
    <div className="flex flex-col gap-10">
      {workflow && (
        <section className="rounded-surface bg-[#EEF3F8] px-5 py-5 sm:px-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-forge-info">Render durable workflow</p>
          <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-lg font-semibold text-forge-ink">{workflow.current_step.replaceAll('_', ' ')}</p>
            <p className="text-sm text-forge-ink-muted">{workflow.status} · updated {new Date(workflow.updated_at).toLocaleString('en-US')}</p>
          </div>
          {workflow.last_error_code && <p className="mt-3 text-sm text-forge-danger">{workflow.last_error_code}: {workflow.last_error_message}</p>}
        </section>
      )}

      <section>
        <SectionTitle>Production pipeline</SectionTitle>
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
      </section>

      <section>
        <SectionTitle>RunPod compiler jobs</SectionTitle>
        {jobs.length === 0 ? (
          <p className="text-[15px] text-forge-ink-muted">GPU jobs appear after source pre-QC passes.</p>
        ) : (
          <div className="flex flex-col gap-5">
            {jobs.map((job) => (
              <div key={job.job_id} className="grid gap-2 border-l-4 border-forge-border-strong pl-4 sm:grid-cols-[1fr_auto]">
                <div>
                  <p className="font-medium text-forge-ink">{job.stage.replaceAll('_', ' ')} · {job.status}</p>
                  <p className="mt-1 text-sm text-forge-ink-muted">{job.pipeline_version} · attempt {job.attempt}{job.gpu_seconds != null ? ` · ${job.gpu_seconds.toFixed(1)} GPU seconds` : ''}</p>
                </div>
                <p className="font-mono text-sm text-forge-ink-subtle">{job.job_id}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
