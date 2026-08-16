import { Order } from '@/lib/types'
import { SectionTitle, WorkspaceEmpty } from './WorkspaceEmpty'

export function EpisodesTab({ order }: { order: Order }) {
  const episodes = order.workspace?.episodes
  if (!episodes) return <WorkspaceEmpty title="Episode data is unavailable">Refresh after the order workspace has loaded.</WorkspaceEmpty>
  const sourceCount = episodes.filter((episode) => episode.kind === 'source').length
  const generatedCount = episodes.length - sourceCount
  const passedCount = episodes.filter((episode) => episode.batch_qc_passed).length

  return (
    <div className="flex flex-col gap-10">
      <dl className="grid grid-cols-3 gap-5 rounded-surface bg-[#EEF3F8] px-5 py-5 sm:px-6">
        <div><dt className="text-sm text-forge-ink-muted">Source</dt><dd className="mt-1 text-2xl font-semibold text-forge-ink">{sourceCount}</dd></div>
        <div><dt className="text-sm text-forge-ink-muted">Generated</dt><dd className="mt-1 text-2xl font-semibold text-forge-ink">{generatedCount}</dd></div>
        <div><dt className="text-sm text-forge-ink-muted">QC passed</dt><dd className="mt-1 text-2xl font-semibold text-forge-ink">{passedCount}</dd></div>
      </dl>
      <section>
        <SectionTitle>Lineage-safe episodes</SectionTitle>
        {episodes.length === 0 ? (
          <WorkspaceEmpty title="No compiled episodes yet">Source and amplified episodes appear here after reconstruction, retargeting, and validation.</WorkspaceEmpty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead><tr className="text-forge-ink-muted"><th className="pb-3 font-medium">Episode</th><th className="pb-3 font-medium">Kind</th><th className="pb-3 font-medium">Lineage</th><th className="pb-3 font-medium">Batch QC</th><th className="pb-3 font-medium">Delivery</th></tr></thead>
              <tbody>{episodes.map((episode) => <tr key={episode.episode_id} className="border-t border-forge-border"><td className="py-3 pr-4 font-mono text-forge-ink">{episode.episode_id}</td><td className="py-3 pr-4 capitalize text-forge-ink">{episode.kind}</td><td className="py-3 pr-4 font-mono text-forge-ink-muted">{episode.lineage_group_id}</td><td className="py-3 pr-4 text-forge-ink-muted">{episode.batch_qc_passed == null ? 'Pending' : episode.batch_qc_passed ? 'Passed' : 'Failed'}</td><td className="py-3 text-forge-ink-muted">{episode.delivered ? 'Included' : 'Not included'}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
