# OAuth Redirect URI Configuration Fix

## Problem
The OAuth login flow was failing because of a mismatch between the OAuth redirect URI configuration and the actual routing between `sopher.ai` (frontend) and `api.sopher.ai` (backend).

## Solution

### 1. Update Google Cloud Console

Navigate to your Google Cloud Console OAuth 2.0 Client configuration and update the authorized redirect URI:

**OLD (incorrect):**
```
https://sopher.ai/api/backend/auth/callback/google
```

**NEW (correct):**
```
https://api.sopher.ai/auth/callback/google
```

### 2. Update Backend Environment Variable

Update the `GOOGLE_OAUTH_REDIRECT_URI` environment variable in your production deployment:

```bash
# For Kubernetes deployment
kubectl edit configmap backend-config

# Or update your secret/configmap YAML
GOOGLE_OAUTH_REDIRECT_URI=https://api.sopher.ai/auth/callback/google
```

### 3. Frontend Changes (Already Applied)

The frontend login page has been updated to redirect directly to the API subdomain:

```typescript
// OLD: window.location.href = '/api/backend/auth/login/google'
// NEW: 
window.location.href = 'https://api.sopher.ai/auth/login/google'
```

## OAuth Flow After Fix

1. User clicks "Sign in with Google" on `sopher.ai/login`
2. Frontend redirects to `https://api.sopher.ai/auth/login/google`
3. Backend redirects to Google OAuth consent page
4. Google redirects back to `https://api.sopher.ai/auth/callback/google`
5. Backend processes OAuth, sets cookies with domain `.sopher.ai`
6. Backend redirects to `https://sopher.ai/` with auth cookies
7. Frontend middleware validates cookies and allows access

## Cookie Configuration

Cookies are set with:
- Domain: `.sopher.ai` (allows sharing between sopher.ai and api.sopher.ai)
- SameSite: `none` (for cross-subdomain in production)
- Secure: `true` (required for SameSite=none)
- HttpOnly: `false` for access_token (so frontend can validate)

## Testing

After applying these changes:

1. Clear browser cookies for sopher.ai
2. Navigate to https://sopher.ai/login
3. Click "Sign in with Google"
4. Complete OAuth flow
5. Verify you're redirected to the main application (not back to login)
6. Check DevTools → Application → Cookies to verify cookies are set

## Troubleshooting

If login still fails after these changes:

1. Check backend logs for OAuth errors:
   ```bash
   kubectl logs deployment/backend --tail=50 | grep -i oauth
   ```

2. Verify the redirect URI in backend:
   ```bash
   curl https://api.sopher.ai/auth/config/status
   ```

3. Check if cookies are being set in browser DevTools Network tab
4. Ensure Google Cloud Console has the exact redirect URI (no trailing slashes)