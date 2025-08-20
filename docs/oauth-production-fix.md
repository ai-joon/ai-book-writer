# OAuth Production Configuration Fix

## Problem
The OAuth redirect is failing in production because:
1. The redirect URI is set to `https://api.sopher.ai/auth/callback/google`
2. This causes cookies to be set on `api.sopher.ai` domain
3. The frontend at `sopher.ai` cannot access these cookies due to cross-domain restrictions
4. Users are redirected back to login page

## Solution

### 1. Update Google Cloud Console
Update the authorized redirect URI in Google Cloud Console to:
```
https://sopher.ai/api/backend/auth/callback/google
```

### 2. Update Production Environment Variables

The `GOOGLE_OAUTH_REDIRECT_URI` must be set to route through the frontend proxy:

```bash
# INCORRECT (current production setting)
GOOGLE_OAUTH_REDIRECT_URI=https://api.sopher.ai/auth/callback/google

# CORRECT (should be)
GOOGLE_OAUTH_REDIRECT_URI=https://sopher.ai/api/backend/auth/callback/google
```

### 3. Update Kubernetes Secret

```bash
kubectl create secret generic sopherai-secrets \
  --from-literal=GOOGLE_CLIENT_ID="your-client-id" \
  --from-literal=GOOGLE_CLIENT_SECRET="your-client-secret" \
  --from-literal=GOOGLE_OAUTH_REDIRECT_URI="https://sopher.ai/api/backend/auth/callback/google" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 4. Update GitHub Actions Secrets

In GitHub repository settings, update the secret:
- `GOOGLE_OAUTH_REDIRECT_URI`: `https://sopher.ai/api/backend/auth/callback/google`

### 5. Verify Configuration

After deployment, verify the configuration:

```bash
# Check the redirect URI being used
curl -s https://sopher.ai/api/backend/auth/config/status | jq .

# Expected output:
{
  "google_oauth_configured": true,
  "client_id_set": true,
  "client_secret_set": true,
  "redirect_uri": "https://sopher.ai/api/backend/auth/callback/google",
  "message": "OAuth is properly configured"
}
```

## Why This Fix Works

1. **Frontend Proxy**: The OAuth callback goes through the frontend's Next.js proxy at `/api/backend/*`
2. **Correct Domain**: Cookies are set on `sopher.ai` domain, accessible to the frontend
3. **Middleware Access**: Next.js middleware can read the `access_token` cookie for authentication checks
4. **No Cross-Domain Issues**: Both frontend and API cookies are on the same domain

## Testing

1. Clear all cookies for `sopher.ai` and `api.sopher.ai`
2. Navigate to https://sopher.ai/login
3. Click "Sign in with Google"
4. Complete OAuth flow
5. Verify redirect to home page (not back to login)

## Cookie Verification

```bash
# After successful login, verify cookies are set correctly
curl -s https://sopher.ai/api/backend/auth/verify \
  -H "Cookie: access_token=your_token_here" | jq .
```

## Rollback Plan

If issues occur, revert the `GOOGLE_OAUTH_REDIRECT_URI` back to the previous value and update Google Cloud Console accordingly.