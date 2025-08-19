import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes that don't require authentication
const publicRoutes = [
  '/login',
  '/_next',
  '/favicon.ico',
]

// Debug mode - set to true to enable logging
const DEBUG = process.env.NODE_ENV !== 'production'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Log request details in debug mode
  if (DEBUG) {
    console.log('[Middleware] Request:', {
      pathname,
      cookies: request.cookies.getAll().map(c => ({ name: c.name, hasValue: !!c.value })),
      headers: {
        host: request.headers.get('host'),
        referer: request.headers.get('referer'),
      }
    })
  }

  // Check if this is a public route
  const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route))
  if (isPublicRoute) {
    if (DEBUG) console.log('[Middleware] Public route, allowing access')
    return NextResponse.next()
  }

  // Check for access_token cookie
  const accessToken = request.cookies.get('access_token')
  
  if (DEBUG) {
    console.log('[Middleware] Access token check:', {
      exists: !!accessToken,
      name: accessToken?.name,
      hasValue: !!accessToken?.value,
    })
  }

  // If no token, redirect to login
  if (!accessToken || !accessToken.value) {
    if (DEBUG) console.log('[Middleware] No valid access token, redirecting to login')
    const loginUrl = new URL('/login', request.url)
    // Preserve the original URL as a redirect parameter
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Token exists, check if it's not expired (basic check)
  try {
    // Parse JWT to check expiry (basic validation without verification)
    const tokenParts = accessToken.value.split('.')
    if (tokenParts.length === 3) {
      const payload = JSON.parse(Buffer.from(tokenParts[1], 'base64').toString())
      const now = Math.floor(Date.now() / 1000)
      
      if (payload.exp && payload.exp < now) {
        if (DEBUG) console.log('[Middleware] Token expired, redirecting to login')
        const loginUrl = new URL('/login', request.url)
        loginUrl.searchParams.set('redirect', pathname)
        return NextResponse.redirect(loginUrl)
      }
    }
  } catch (error) {
    if (DEBUG) console.log('[Middleware] Error parsing token:', error)
    // If we can't parse the token, let it through and let the backend validate
  }

  if (DEBUG) console.log('[Middleware] Valid token found, allowing access')
  
  // Continue with the request
  return NextResponse.next()
}

// Configure which routes use this middleware
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api/backend/auth (auth endpoints)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api/backend/auth|_next/static|_next/image|favicon.ico).*)',
  ],
}