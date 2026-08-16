import NextAuth from 'next-auth'
import { NextResponse } from 'next/server'
import authConfig from '@/auth.config'

const { auth } = NextAuth(authConfig)

export default auth((req) => {
  if (!req.auth) {
    const url = new URL('/auth/signin', req.url)
    url.searchParams.set('callbackUrl', req.nextUrl.pathname)
    return NextResponse.redirect(url)
  }
})

export const config = {
  matcher: ['/orders/:path*', '/api/token'],
}
