import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import PricingPage from '@/app/pricing/page'

describe('PricingPage', () => {
  it('makes the $350 checkout path obvious and describes a data-only offer', () => {
    render(<PricingPage />)

    expect(screen.getByRole('heading', { name: /multi-person training data for \$350/i })).toBeInTheDocument()
    expect(screen.getByText(/delivers data—not robot hardware/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /start the \$350 pilot/i })).toHaveAttribute(
      'href',
      '/auth/signin?callbackUrl=/orders/new',
    )
  })
})
