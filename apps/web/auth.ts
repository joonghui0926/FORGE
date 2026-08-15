import NextAuth from 'next-auth'
import Google from 'next-auth/providers/google'
import GitHub from 'next-auth/providers/github'
import { SignJWT } from 'jose'

const jwtSecret = new TextEncoder().encode(process.env.AUTH_SECRET!)

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
    }),
  ],
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  callbacks: {
    async signIn({ user }) {
      return !!user.email
    },
    async jwt({ token, user }) {
      const now = Math.floor(Date.now() / 1000)
      const needsMint = (user?.email && !token.forgeToken) ||
        (token.forgeTokenExp as number | undefined && (token.forgeTokenExp as number) - now < 300)
      if (user?.email && needsMint) {
        // Stub: email as tenant_id. Replace with DB lookup when tenant table is set up.
        const tenantId = user.email
        const forgeToken = await new SignJWT({ sub: user.email, tenant_id: tenantId })
          .setProtectedHeader({ alg: 'HS256' })
          .setExpirationTime('1h')
          .sign(jwtSecret)
        token.forgeToken = forgeToken
        token.tenantId   = tenantId
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
