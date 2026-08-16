import { Order } from '@/lib/types'
import { RequestState, SectionTitle, WorkspaceEmpty } from './WorkspaceEmpty'

function metric(value: unknown) {
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3)
  if (typeof value === 'boolean') return value ? 'Pass' : 'Fail'
  return String(value)
}

export function QualityTab({ order }: { order: Order }) {
  const quality = order.workspace?.quality
  if (!quality) return <WorkspaceEmpty title="Quality data is unavailable">Refresh after the order workspace has loaded.</WorkspaceEmpty>

  const passed = quality.runs.filter((run) => run.passed).length
  const acceptance = quality.runs.length ? Math.round((passed / quality.runs.length) * 100) : 0

  return (
    <div className="flex flex-col gap-10">
      <section className="grid gap-5 rounded-surface bg-[#F7F2E8] px-5 py-5 sm:grid-cols-[1fr_auto] sm:px-6">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-forge-warning">Evidence-backed quality</p>
          <p className="mt-2 max-w-2xl text-[15px] leading-6 text-forge-ink-muted">Deterministic physics gates remain authoritative. Pioneer predicts usability from pseudonymous metrics; Band converts evidence into accept, recollect, review, or block decisions.</p>
        </div>
        <div className="sm:text-right"><p className="text-sm text-forge-ink-muted">QC pass rate</p><p className="mt-1 text-3xl font-semibold tabular-nums text-forge-ink">{quality.runs.length ? `${acceptance}%` : '—'}</p></div>
      </section>

      <section>
        <SectionTitle>QC runs</SectionTitle>
        {quality.runs.length === 0 ? (
          <WorkspaceEmpty title="No QC evidence yet">Results appear after deterministic pre-QC, replay validation, or batch QC completes.</WorkspaceEmpty>
        ) : (
          <div className="flex flex-col gap-6">
            {quality.runs.map((run) => (
              <article key={run.qc_run_id} className="grid gap-4 border-l-4 border-forge-border-strong pl-4 sm:grid-cols-[180px_1fr]">
                <div>
                  <p className={`font-semibold ${run.passed ? 'text-forge-success' : 'text-forge-danger'}`}>{run.passed ? 'Passed' : 'Failed'} · {run.stage.replaceAll('_', ' ')}</p>
                  <p className="mt-1 text-sm text-forge-ink-muted">{run.subject_type} · {new Date(run.created_at).toLocaleString('en-US')}</p>
                  {run.simulation && <p className="mt-1 text-sm font-medium text-forge-warning">Simulation result</p>}
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  {Object.entries(run.metrics).map(([name, value]) => (
                    <p key={name} className="text-sm text-forge-ink-muted"><span className="text-forge-ink">{name.replaceAll('_', ' ')}</span> {metric(value)}</p>
                  ))}
                  {run.reason_codes.map((code) => <span key={code} className="rounded-pill bg-forge-danger-soft px-2.5 py-1 text-sm text-forge-danger">{code}</span>)}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Quality decisions</SectionTitle>
        {quality.decisions.length === 0 ? (
          <p className="text-[15px] text-forge-ink-muted">No final quality decision has been recorded.</p>
        ) : quality.decisions.map((decision) => (
          <div key={decision.decision_id} className="mb-5 flex flex-wrap justify-between gap-4 last:mb-0">
            <div><p className="font-medium text-forge-ink">{decision.decision_type.replaceAll('_', ' ')}</p><p className="mt-1 text-sm text-forge-ink-muted">Policy {decision.policy_version} · confidence {decision.confidence == null ? '—' : `${Math.round(decision.confidence * 100)}%`}</p></div>
            <div className="text-right"><p className="text-sm text-forge-ink-muted">{decision.requires_human_approval ? (decision.approved_by ? 'Human approved' : 'Human review required') : 'Policy approved'}</p><p className="mt-1 text-sm text-forge-ink-subtle">{new Date(decision.created_at).toLocaleString('en-US')}</p></div>
          </div>
        ))}
      </section>

      <section>
        <SectionTitle>Pioneer and Band verdicts</SectionTitle>
        {quality.provider_requests.length === 0 ? <p className="text-[15px] text-forge-ink-muted">Learned quality requests appear here once source features are available.</p> : (
          <div className="flex flex-col gap-4">{quality.provider_requests.map((request) => <div key={request.correlation_id} className="flex items-center justify-between gap-4"><div><p className="font-medium capitalize text-forge-ink">{request.provider} · {request.purpose.replaceAll('_', ' ')}</p><p className="mt-1 text-sm text-forge-ink-muted">{new Date(request.created_at).toLocaleString('en-US')}</p></div><RequestState state={request.state} /></div>)}</div>
        )}
      </section>
    </div>
  )
}
