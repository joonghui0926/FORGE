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
    <section className="mx-auto max-w-[1440px] px-6 py-24 lg:px-12 xl:px-20">
      <p className="text-[15px] font-semibold uppercase tracking-[0.14em] text-forge-primary-active">How it works</p>
      <h2 className="mt-4 max-w-[18ch] text-4xl font-semibold leading-tight tracking-[-0.035em] text-forge-ink sm:text-5xl">
        One accountable path from brief to embodied skill.
      </h2>
      <ol className="mt-16 grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-4" role="list">
        {STEPS.map((label, i) => (
          <li key={label} className="group min-h-24">
            <span className="font-mono text-sm text-forge-primary-active">{String(i + 1).padStart(2, '0')}</span>
            <span className="mt-3 block text-lg font-medium leading-snug text-forge-ink">{label}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
