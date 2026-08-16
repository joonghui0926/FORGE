import { ReactNode } from 'react'

export function WorkspaceEmpty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="max-w-2xl py-10">
      <p className="text-base font-semibold text-forge-ink">{title}</p>
      <p className="mt-2 text-[15px] leading-6 text-forge-ink-muted">{children}</p>
    </div>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-forge-ink-muted">
      {children}
    </h3>
  )
}

export function RequestState({ state }: { state: string }) {
  const normalized = state.toUpperCase()
  const tone = normalized === 'SUCCEEDED'
    ? 'bg-forge-success-soft text-forge-success'
    : normalized === 'FAILED'
      ? 'bg-forge-danger-soft text-forge-danger'
      : 'bg-forge-info-soft text-forge-info'
  return <span className={`rounded-pill px-2.5 py-1 text-sm font-medium ${tone}`}>{state}</span>
}
