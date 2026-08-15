import { InputHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label: string
  help?: string
  error?: string
}

export function Field({ id, label, help, error, className = '', required, ...rest }: FieldProps) {
  const errorId = `${id}-error`
  const helpId  = `${id}-help`
  const describedBy = [error ? errorId : null, help ? helpId : null].filter(Boolean).join(' ')

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-forge-ink">
        {label}
        {!required && (
          <span className="ml-1.5 text-sm font-normal text-forge-ink-muted">Optional</span>
        )}
      </label>
      <input
        id={id}
        required={required}
        aria-describedby={describedBy || undefined}
        aria-invalid={error ? true : undefined}
        className={[
          'min-h-[48px] px-4 text-base rounded-control border',
          error ? 'border-forge-danger' : 'border-forge-border',
          'bg-forge-surface text-forge-ink',
          'focus:outline-none focus:ring-2 focus:ring-forge-focus',
          className,
        ].join(' ')}
        {...rest}
      />
      {help  && <p id={helpId}  className="text-sm text-forge-ink-muted">{help}</p>}
      {error && <p id={errorId} className="text-sm text-forge-danger">{error}</p>}
    </div>
  )
}
