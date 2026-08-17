import { Order } from '@/lib/types'
import { RequestState, SectionTitle, WorkspaceEmpty } from './WorkspaceEmpty'

export function AcquisitionTab({ order }: { order: Order }) {
  const acquisition = order.workspace?.acquisition
  if (!acquisition) {
    return <WorkspaceEmpty title="Acquisition data is unavailable">Refresh after the order workspace has loaded.</WorkspaceEmpty>
  }

  const submitted = acquisition.batches.reduce((sum, batch) => sum + batch.submitted, 0)
  const accepted = acquisition.batches.reduce((sum, batch) => sum + batch.accepted, 0)
  const target = acquisition.batches.reduce((max, batch) => Math.max(max, batch.target_source_clips ?? 0), 0)
  const participantTarget = acquisition.batches.reduce((max, batch) => Math.max(max, batch.target_participant_count ?? 0), 0)
  const coverage = acquisition.coverage ?? {
    unique_participants: 0,
    unique_environments: 0,
    take_counts: { success: 0, failure: 0, recovery: 0 },
  }

  return (
    <div className="flex flex-col gap-10">
      <section className="rounded-surface bg-forge-surface-cyan px-5 py-5 sm:px-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-forge-primary-active">Terac acquisition</p>
        <p className="mt-2 max-w-3xl text-[15px] leading-6 text-forge-primary-ink">
          Terac turns the approved collection plan into staffed, rights-cleared capture campaigns. Band plans coverage before each campaign and requests recollection when evidence is insufficient.
        </p>
        <dl className="mt-5 grid grid-cols-2 gap-5 sm:grid-cols-4">
          <div><dt className="text-sm text-forge-ink-muted">Source target</dt><dd className="mt-1 text-2xl font-semibold tabular-nums text-forge-ink">{target}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Submitted</dt><dd className="mt-1 text-2xl font-semibold tabular-nums text-forge-ink">{submitted}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Accepted</dt><dd className="mt-1 text-2xl font-semibold tabular-nums text-forge-ink">{accepted}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Participants</dt><dd className="mt-1 text-2xl font-semibold tabular-nums text-forge-ink">{coverage.unique_participants}/{participantTarget}</dd></div>
        </dl>
      </section>

      <section>
        <SectionTitle>Campaign batches</SectionTitle>
        {acquisition.batches.length === 0 ? (
          <WorkspaceEmpty title="No Terac campaign yet">The first campaign appears here after payment and Band collection planning complete.</WorkspaceEmpty>
        ) : (
          <ol className="grid gap-5 md:grid-cols-2">
            {acquisition.batches.map((batch) => (
              <li key={batch.batch_id} className="border-l-4 border-forge-primary pl-4">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-semibold text-forge-ink">Batch {batch.sequence}</p>
                  <span className="text-sm text-forge-ink-muted">{batch.accepted}/{batch.submitted} accepted</span>
                </div>
                <p className="mt-1 break-all font-mono text-sm text-forge-ink-muted">
                  {batch.terac_campaign_id ?? 'Campaign provisioning'}
                </p>
                <p className="mt-1 text-sm text-forge-ink-subtle">Created {new Date(batch.created_at).toLocaleString('en-US')}</p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section>
        <SectionTitle>Provider handoffs</SectionTitle>
        {acquisition.provider_requests.length === 0 ? (
          <p className="text-[15px] text-forge-ink-muted">No collection-provider requests have been issued.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {acquisition.provider_requests.map((request) => (
              <div key={request.correlation_id} className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium capitalize text-forge-ink">{request.provider} · {request.purpose.replaceAll('_', ' ')}</p>
                  <p className="mt-1 text-sm text-forge-ink-muted">{new Date(request.created_at).toLocaleString('en-US')}</p>
                </div>
                <RequestState state={request.state} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Recent captures</SectionTitle>
        {acquisition.captures.length === 0 ? (
          <p className="text-[15px] text-forge-ink-muted">Captures appear after Terac workers submit their recordings.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead><tr className="text-forge-ink-muted"><th className="pb-3 font-medium">Capture</th><th className="pb-3 font-medium">Participant</th><th className="pb-3 font-medium">Take</th><th className="pb-3 font-medium">Environment</th><th className="pb-3 font-medium">Viewpoint</th><th className="pb-3 font-medium">State</th><th className="pb-3 font-medium">Submitted</th></tr></thead>
              <tbody>
                {acquisition.captures.map((capture) => (
                  <tr key={capture.capture_id} className="border-t border-forge-border">
                    <td className="py-3 pr-4 font-mono text-forge-ink">{capture.capture_id}</td>
                    <td className="py-3 pr-4 font-mono text-forge-ink-muted">{capture.participant_id}</td>
                    <td className="py-3 pr-4 text-forge-ink">{capture.take_kind} #{(capture.take_index ?? 0) + 1}</td>
                    <td className="py-3 pr-4 text-forge-ink-muted">{capture.environment_id}</td>
                    <td className="py-3 pr-4 text-forge-ink-muted">{capture.viewpoint_bin}</td>
                    <td className="py-3 pr-4 text-forge-ink-muted">{capture.state.replaceAll('_', ' ')}</td>
                    <td className="py-3 text-forge-ink-muted">{new Date(capture.submitted_at).toLocaleString('en-US')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
