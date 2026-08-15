import Link from 'next/link'
import { Button } from '@/components/ui/Button'

const ERROR_MESSAGES: Record<string, string> = {
  Configuration: 'There is a problem with the server configuration. Please contact support.',
  AccessDenied:  'You do not have permission to sign in with this account.',
  Verification:  'The sign-in link has expired or already been used. Please try again.',
  Default:       'Something went wrong during sign-in. Please try again.',
}

export default function AuthErrorPage({
  searchParams,
}: {
  searchParams: { error?: string }
}) {
  const message = ERROR_MESSAGES[searchParams.error ?? 'Default'] ?? ERROR_MESSAGES.Default

  return (
    <div className="min-h-screen bg-forge-surface flex items-center justify-center p-6">
      <div className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold text-forge-ink mb-3">Sign-in failed</h1>
        <p className="text-forge-ink-muted mb-8 text-sm">{message}</p>
        <Link href="/auth/signin">
          <Button variant="primary">Try again</Button>
        </Link>
      </div>
    </div>
  )
}
