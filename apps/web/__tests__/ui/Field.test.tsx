import { render, screen } from '@testing-library/react'
import { Field } from '@/components/ui/Field'
import { describe, it, expect } from 'vitest'

describe('Field', () => {
  it('associates label with input via htmlFor', () => {
    render(<Field id="email" label="Email" type="email" required />)
    expect(screen.getByLabelText('Email')).toHaveAttribute('id', 'email')
  })

  it('shows Optional marker when not required', () => {
    render(<Field id="notes" label="Notes" />)
    expect(screen.getByText(/optional/i)).toBeInTheDocument()
  })

  it('shows error text and sets aria-invalid + aria-describedby', () => {
    render(<Field id="name" label="Name" error="Name is required" required />)
    const input = screen.getByRole('textbox')
    expect(screen.getByText('Name is required')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('name-error'))
  })

  it('shows help text associated via aria-describedby', () => {
    render(<Field id="uri" label="Model URI" help="Use r2:// format" required />)
    const input = screen.getByRole('textbox')
    expect(screen.getByText('Use r2:// format')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('uri-help'))
  })
})
