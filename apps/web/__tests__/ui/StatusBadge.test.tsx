import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ORDER_STATES, STATUS_LABELS } from '@/lib/types'
import { describe, it, expect } from 'vitest'

describe('StatusBadge', () => {
  it('renders visible text for every OrderState — never color-only', () => {
    for (const state of ORDER_STATES) {
      const { unmount } = render(<StatusBadge state={state} />)
      expect(screen.getByText(STATUS_LABELS[state].label)).toBeInTheDocument()
      unmount()
    }
  })

  it('renders a non-empty icon aria-hidden element alongside the label', () => {
    render(<StatusBadge state="READY" />)
    const icon = document.querySelector('[aria-hidden="true"]')
    expect(icon?.textContent?.trim().length).toBeGreaterThan(0)
  })
})
