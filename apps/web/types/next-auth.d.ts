import { DefaultSession } from 'next-auth'

declare module 'next-auth' {
  interface Session extends DefaultSession {
    forgeToken: string
    tenantId: string
  }
}

declare module '@auth/core/jwt' {
  interface JWT {
    forgeToken?: string
    tenantId?: string
    forgeTokenExp?: number
  }
}
