import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NewOrderStepper } from '@/components/orders/NewOrderStepper'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }))

describe('NewOrderStepper', () => {
  it('renders step 1 (Skill) initially', () => {
    render(<NewOrderStepper token="tok_test" />)
    expect(screen.getByText('What should the robot do?')).toBeInTheDocument()
    expect(screen.getByText(/step 1 of 6/i)).toBeInTheDocument()
  })

  it('does not advance from step 1 when task name is empty', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText('What should the robot do?')).toBeInTheDocument()
  })

  it('advances to step 2 after filling required step 1 fields', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.type(screen.getByLabelText(/task name/i), 'Pick apple')
    await userEvent.type(screen.getByLabelText(/initial state/i), 'Apple on table')
    await userEvent.type(screen.getByLabelText(/success/i), 'Apple in bin')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByText('Which robot and hand?')).toBeInTheDocument()
    expect(screen.getByText(/step 2 of 6/i)).toBeInTheDocument()
  })

  it('goes back and preserves data', async () => {
    render(<NewOrderStepper token="tok_test" />)
    await userEvent.type(screen.getByLabelText(/task name/i), 'Pick apple')
    await userEvent.type(screen.getByLabelText(/initial state/i), 'Apple on table')
    await userEvent.type(screen.getByLabelText(/success/i), 'Apple in bin')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await userEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(screen.getByDisplayValue('Pick apple')).toBeInTheDocument()
  })
})
