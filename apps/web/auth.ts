import NextAuth from 'next-auth'
import PostgresAdapter from '@auth/pg-adapter'
import Google from 'next-auth/providers/google'
import Resend from 'next-auth/providers/resend'
import { SignJWT } from 'jose'
import authConfig from '@/auth.config'
import { authPool } from '@/lib/auth-db'

const jwtSecret = new TextEncoder().encode(process.env.AUTH_SECRET!)

async function tenantIdFor(subject: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(subject.toLowerCase()))
  const bytes = Array.from(new Uint8Array(digest).slice(0, 12))
  const token = bytes.map((value) => value.toString(16).padStart(2, '0')).join('')
  return `ten_${token}`
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  adapter: PostgresAdapter(authPool),
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    Resend({
      apiKey: process.env.AUTH_RESEND_KEY!,
      from: process.env.AUTH_EMAIL_FROM ?? 'FORGE <onboarding@resend.dev>',
    }),
  ],
  callbacks: {
    async signIn({ user }) {
      return !!user.email
    },
    async jwt({ token, user }) {
      const now = Math.floor(Date.now() / 1000)
      const isFirstSignIn = !!(user?.email && !token.forgeToken)
      const needsRefresh  = !!(token.forgeTokenExp as number | undefined &&
        (token.forgeTokenExp as number) - now < 300)
      if (isFirstSignIn || needsRefresh) {
        const sub      = user?.email ?? (token.sub as string)
        const tenantId = (token.tenantId as string | undefined) ?? await tenantIdFor(sub)
        const forgeToken = await new SignJWT({ sub, tenant_id: tenantId })
          .setProtectedHeader({ alg: 'HS256' })
          .setExpirationTime('1h')
          .sign(jwtSecret)
        token.forgeToken    = forgeToken
        token.tenantId      = tenantId
        token.forgeTokenExp = now + 3600
      }
      return token
    },
    async session({ session, token }) {
      session.forgeToken = token.forgeToken as string
      session.tenantId   = token.tenantId   as string
      return session
    },
  },
})
