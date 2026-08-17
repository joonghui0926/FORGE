import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { WorkspaceTabs } from '@/components/orders/workspace/WorkspaceTabs'
import { Order } from '@/lib/types'

const order: Order = {
  order_id: 'ord_workspace_test',
  state: 'PLANNING',
  stripe_payment_link: null,
  skill_name: 'Whole-body tote loading',
  volume_validated_episodes: 20,
  contract: { rights_profile: 'customer_exclusive_derivatives' },
  pipeline: [],
  workspace: {
    acquisition: { batches: [], captures: [], provider_requests: [] },
    processing: { workflow: null, jobs: [] },
    quality: { runs: [], decisions: [], provider_requests: [] },
    episodes: [],
    delivery: null,
    billing: { payment_status: 'paid', payment_reference: '...12345678' },
  },
}

describe('WorkspaceTabs', () => {
  it('opens every production workspace without placeholder content', async () => {
    const user = userEvent.setup()
    render(<WorkspaceTabs order={order} />)

    await user.click(screen.getByRole('tab', { name: 'Acquisition' }))
    expect(screen.getByText('Terac acquisition')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Pipeline' }))
    expect(screen.getByText('Production pipeline')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Quality' }))
    expect(screen.getByText('Evidence-backed quality')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Episodes' }))
    expect(screen.getByText('Lineage-safe episodes')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Dataset' }))
    expect(screen.getByText('The dataset package is still compiling')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Activity' }))
    expect(screen.getByText('No activity recorded')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Billing' }))
    expect(screen.getByText('Payment received')).toBeInTheDocument()
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })
})
