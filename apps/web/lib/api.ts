// apiFetch works everywhere (pass token from /api/token route in client components).

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

export async function apiFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return request<T>(path, token, init)
}
