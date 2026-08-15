import { auth } from '@/auth'
import { redirect } from 'next/navigation'

export async function requireSession() {
  const session = await auth()
  if (!session?.forgeToken) {
    redirect('/auth/signin')
  }
  return session
}
