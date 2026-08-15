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
  const callbackUrl = searchParams.callbackUrl ?? '/orders'
  const errorMsg = searchParams.error ? (ERROR_TEXT[searchParams.error] ?? ERROR_TEXT.Default) : null

  async function handleProvider(provider: 'google' | 'github') {
    setLoading(provider)
    await signIn(provider, { callbackUrl })
  }

  return (
    <div className="min-h-screen bg-forge-surface flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-forge-ink mb-1">Sign in to FORGE</h1>
        <p className="text-forge-ink-muted mb-8 text-sm">Order and track your robot datasets.</p>

        {errorMsg && (
          <p className="mb-6 text-sm text-forge-danger bg-forge-danger-soft rounded-control px-4 py-3">
            {errorMsg}
          </p>
        )}

        <div className="flex flex-col gap-3">
          <Button variant="secondary" onClick={() => handleProvider('google')}
                  loading={loading === 'google'} className="w-full justify-center">
            Continue with Google
          </Button>
          <Button variant="secondary" onClick={() => handleProvider('github')}
                  loading={loading === 'github'} className="w-full justify-center">
            Continue with GitHub
          </Button>
        </div>
      </div>
    </div>
  )
}
