import { describe, expect, it } from 'vitest'
import authConfig from '@/auth.config'

describe('Edge auth configuration', () => {
  it('stays provider-free so middleware never requires the server adapter', () => {
    expect(authConfig.providers).toEqual([])
    expect(authConfig.session?.strategy).toBe('jwt')
    expect(authConfig.trustHost).toBe(true)
  })
})
