'use client'

import { signIn } from 'next-auth/react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'

interface PageProps {
  searchParams: { callbackUrl?: string; error?: string }
}

const ERROR_TEXT: Record<string, string> = {
  OAuthSignin:    'Could not start OAuth sign-in. Please try again.',
  OAuthCallback:  'OAuth sign-in failed. Please try again.',
  OAuthCreateAccount: 'Could not create your account. Please contact support.',
  Verification:   'Your sign-in link expired. Please request a new one.',
  Default:        'Sign-in failed. Please try again.',
}

export default function SignInPage({ searchParams }: PageProps) {
  const [loading, setLoading] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [emailSent, setEmailSent] = useState(false)
  const callbackUrl = searchParams.callbackUrl ?? '/orders'
  const errorMsg = searchParams.error ? (ERROR_TEXT[searchParams.error] ?? ERROR_TEXT.Default) : null

  async function handleGoogle() {
    const provider = 'google'
    setLoading(provider)
    await signIn(provider, { callbackUrl })
  }

  async function handleEmail(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading('resend')
    const result = await signIn('resend', { email, callbackUrl, redirect: false })
    setLoading(null)
    if (!result?.error) setEmailSent(true)
  }

  return (
    <div className="min-h-screen bg-[#F1F7F5] flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-forge-ink mb-1">Sign in to FORGE</h1>
        <p className="text-forge-ink-muted mb-8 text-sm">Order and track your robot datasets.</p>

        {errorMsg && (
          <p className="mb-6 text-sm text-forge-danger bg-forge-danger-soft rounded-control px-4 py-3">
            {errorMsg}
          </p>
        )}

        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={handleGoogle}
                  loading={loading === 'google'} className="w-full justify-center">
            Continue with Google
          </Button>

          <div className="flex items-center gap-3 py-2 text-sm text-forge-ink-subtle" aria-hidden="true">
            <span className="h-px flex-1 bg-forge-border" />
            or
            <span className="h-px flex-1 bg-forge-border" />
          </div>

          {emailSent ? (
            <p className="rounded-control bg-forge-primary-soft px-4 py-3 text-sm text-forge-ink">
              Check your email for a secure sign-in link.
            </p>
          ) : (
            <form className="flex flex-col gap-3" onSubmit={handleEmail}>
              <label className="text-sm font-medium text-forge-ink" htmlFor="email">
                Work email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                className="min-h-11 rounded-control border border-forge-border bg-white px-3 text-base text-forge-ink outline-none transition focus:border-forge-primary focus:ring-2 focus:ring-forge-focus"
              />
              <Button type="submit" loading={loading === 'resend'} className="w-full justify-center">
                Email me a sign-in link
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
