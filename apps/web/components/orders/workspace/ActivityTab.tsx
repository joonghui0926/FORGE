import { Order } from '@/lib/types'
import { WorkspaceEmpty } from './WorkspaceEmpty'

export function ActivityTab({ order }: { order: Order }) {
  const events = [...(order.pipeline ?? [])].reverse()
  if (events.length === 0) return <WorkspaceEmpty title="No activity recorded">Every state transition, provider handoff, and decision will be appended here.</WorkspaceEmpty>
  return (
    <ol className="max-w-3xl">
      {events.map((event, index) => (
        <li key={`${event.step}-${event.created_at}-${index}`} className="grid grid-cols-[14px_1fr] gap-4 pb-7 last:pb-0">
          <span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-forge-primary" aria-hidden="true" />
          <div className="flex flex-wrap justify-between gap-x-5 gap-y-1">
            <div><p className="font-medium text-forge-ink">{event.step.replaceAll('_', ' ')}</p><p className="mt-1 text-sm text-forge-ink-muted">Actor: {event.actor}{event.state ? ` · state ${event.state}` : ''}</p></div>
            <time className="text-sm text-forge-ink-subtle">{new Date(event.created_at).toLocaleString('en-US')}</time>
          </div>
        </li>
      ))}
    </ol>
  )
}
