// Auth helper functions

export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  
  if (parts.length === 2) {
    const cookieValue = parts.pop()?.split(';').shift()
    return cookieValue || null
  }
  
  return null
}

export function hasValidAuthCookie(): boolean {
  const accessToken = getCookie('access_token')
  
  if (!accessToken) return false
  
  try {
    // Basic JWT validation
    const parts = accessToken.split('.')
    if (parts.length !== 3) return false
    
    const payload = JSON.parse(atob(parts[1]))
    const now = Math.floor(Date.now() / 1000)
    
    // Check if token is expired
    if (payload.exp && payload.exp < now) {
      console.log('[Auth] Token expired')
      return false
    }
    
    return true
  } catch (error) {
    console.error('[Auth] Error parsing token:', error)
    return false
  }
}

export async function verifyAuth(): Promise<boolean> {
  try {
    const response = await fetch('/api/backend/auth/verify', {
      credentials: 'include',
    })
    
    if (!response.ok) return false
    
    const data = await response.json()
    return data.authenticated === true
  } catch (error) {
    console.error('[Auth] Verification failed:', error)
    return false
  }
}

export function debugCookies(): void {
  if (typeof document === 'undefined') return
  
  console.log('[Auth Debug] All cookies:', document.cookie)
  console.log('[Auth Debug] Access token present:', !!getCookie('access_token'))
  console.log('[Auth Debug] Refresh token present:', !!getCookie('refresh_token'))
  console.log('[Auth Debug] Has valid auth:', hasValidAuthCookie())
}