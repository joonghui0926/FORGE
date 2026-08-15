import { describe, it, expect } from 'vitest'
import { ORDER_STATES, STATUS_LABELS } from '@/lib/types'

describe('STATUS_LABELS', () => {
  it('has an entry for every OrderState', () => {
    for (const state of ORDER_STATES) {
      expect(STATUS_LABELS[state], `missing entry for ${state}`).toBeDefined()
      expect(STATUS_LABELS[state].label.length).toBeGreaterThan(0)
    }
  })

  it('never exposes raw DB enum values as customer labels', () => {
    const rawValues = new Set(ORDER_STATES as readonly string[])
    for (const { label } of Object.values(STATUS_LABELS)) {
      expect(rawValues.has(label)).toBe(false)
    }
  })
})
