import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiError, apiFetch } from '@/lib/api'

describe('ApiError', () => {
  it('has status, message, and name properties', () => {
    const err = new ApiError(404, 'Not found')
    expect(err.status).toBe(404)
    expect(err.message).toBe('Not found')
    expect(err.name).toBe('ApiError')
  })

  it('is instanceof Error', () => {
    expect(new ApiError(500, 'fail')).toBeInstanceOf(Error)
  })
})

describe('apiFetch', () => {
  beforeEach(() => { vi.stubGlobal('fetch', vi.fn()) })
  afterEach(() => { vi.unstubAllGlobals() })

  it('attaches Authorization Bearer header', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }))
    await apiFetch('/orders', 'tok_abc')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/orders'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer tok_abc' }),
      }),
    )
  })

  it('throws ApiError with detail from JSON body on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
    )
    await expect(apiFetch('/missing', 'tok')).rejects.toMatchObject({
      status: 404,
      message: 'Not found',
    })
  })

  it('throws ApiError with fallback when body is not JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('Bad Gateway', { status: 502 }))
    await expect(apiFetch('/fail', 'tok')).rejects.toMatchObject({
      status: 502,
      message: 'Request failed',
    })
  })

  it('returns parsed JSON on success', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify([{ order_id: 'ord_1' }]), { status: 200 }),
    )
    const result = await apiFetch<{ order_id: string }[]>('/orders', 'tok')
    expect(result[0].order_id).toBe('ord_1')
  })
})
