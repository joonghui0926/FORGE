const STEPS = [
  'Dataset Planning',
  'Human Acquisition',
  'Physical Data Compilation',
  'Robot Retargeting',
  'Physics Validation',
  'Dataset Amplification',
  'Delivery',
]

export function ProcessSteps() {
  return (
    <section className="px-6 py-20">
      <h2 className="text-2xl font-semibold text-forge-ink mb-12">How it works</h2>
      <ol className="flex flex-col gap-6" role="list">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-baseline gap-5">
            <span className="text-sm font-mono text-forge-ink-muted w-4 shrink-0 select-none">
              {i + 1}
            </span>
            <span className="text-lg text-forge-ink">{label}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
