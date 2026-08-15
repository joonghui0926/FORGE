// apiServer methods import auth() at call time — they only work in Next.js server context.
// apiFetch works everywhere (pass token from /api/token route in client components).

import type { Session } from 'next-auth'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: 'no-store',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

export const apiServer = {
  async get<T>(path: string): Promise<T> {
    const { auth } = await import('@/auth')
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return request<T>(path, session.forgeToken)
  },
  async post<T>(path: string, body: unknown): Promise<T> {
    const { auth } = await import('@/auth')
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return request<T>(path, session.forgeToken, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },
}

export async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return request<T>(path, token, init)
}
