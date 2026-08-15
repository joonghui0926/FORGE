interface PlaceholderTabProps {
  name: string
  description: string
}

export function PlaceholderTab({ name, description }: PlaceholderTabProps) {
  return (
    <div className="py-16">
      <h3 className="text-lg font-semibold text-forge-ink mb-2">{name} — coming soon</h3>
      <p className="text-forge-ink-muted text-sm max-w-prose">{description}</p>
    </div>
  )
}
