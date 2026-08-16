import 'server-only'

import type { Session } from 'next-auth'
import { auth } from '@/auth'
import { ApiError, apiFetch } from '@/lib/api'

export const apiServer = {
  async get<T>(path: string): Promise<T> {
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return apiFetch<T>(path, session.forgeToken)
  },
  async post<T>(path: string, body: unknown): Promise<T> {
    const session = await auth() as Session & { forgeToken?: string }
    if (!session?.forgeToken) throw new ApiError(401, 'Not authenticated')
    return apiFetch<T>(path, session.forgeToken, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },
}

