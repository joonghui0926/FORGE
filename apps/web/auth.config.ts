import type { NextAuthConfig } from 'next-auth'

export default {
  // Render terminates TLS at its proxy and forwards the public Host header.
  // Cloudflare will do the same once the custom domain is attached.
  trustHost: true,
  // Keep the Edge-compatible configuration provider-free. The full server
  // config adds OAuth/email providers together with the Postgres adapter.
  providers: [],
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
} satisfies NextAuthConfig
