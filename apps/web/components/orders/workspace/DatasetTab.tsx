import { Order } from '@/lib/types'
import { DatasetDownloadButton } from './DatasetDownloadButton'
import { SectionTitle, WorkspaceEmpty } from './WorkspaceEmpty'

export function DatasetTab({ order }: { order: Order }) {
  const delivery = order.workspace?.delivery
  if (!delivery) {
    return <WorkspaceEmpty title="The robot-ready package is still compiling">Once every deterministic and learned quality gate passes, FORGE writes an immutable manifest and enables a one-hour signed R2 download.</WorkspaceEmpty>
  }

  return (
    <div className="flex flex-col gap-10">
      <section className="rounded-surface bg-forge-success-soft px-5 py-5 sm:px-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-forge-success">Ready for delivery</p>
        <h3 className="mt-2 text-xl font-semibold text-forge-ink">Dataset {delivery.dataset_version}</h3>
        <p className="mt-2 max-w-2xl text-[15px] leading-6 text-forge-ink-muted">The download URL is generated only when requested and expires after one hour. The private R2 object keys never enter the customer workspace.</p>
        <div className="mt-5"><DatasetDownloadButton deliveryId={delivery.delivery_id} /></div>
      </section>
      <section>
        <SectionTitle>Package manifest</SectionTitle>
        <dl className="grid gap-x-10 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="text-sm text-forge-ink-muted">Schema</dt><dd className="mt-1 font-mono text-sm text-forge-ink">{delivery.schema_version ?? 'forge.delivery.v1'}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Episodes</dt><dd className="mt-1 text-base font-medium text-forge-ink">{delivery.episode_count ?? order.workspace?.episodes.length ?? '—'}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Artifacts</dt><dd className="mt-1 text-base font-medium text-forge-ink">{delivery.artifact_count}</dd></div>
          <div><dt className="text-sm text-forge-ink-muted">Rights</dt><dd className="mt-1 text-base font-medium text-forge-ink">{delivery.rights_profile.replaceAll('_', ' ')}</dd></div>
        </dl>
        <p className="mt-6 text-sm text-forge-ink-subtle">Packaged {new Date(delivery.created_at).toLocaleString('en-US')}</p>
      </section>
    </div>
  )
}
