# OAuth Configuration Update Required

## Production Configuration Change

To fix the OAuth login redirect issue, the following environment variable needs to be updated in production:

### Current (Problematic) Configuration
```
GOOGLE_OAUTH_REDIRECT_URI=https://api.sopher.ai/auth/callback/google
```

### New (Fixed) Configuration
```
GOOGLE_OAUTH_REDIRECT_URI=https://sopher.ai/api/backend/auth/callback/google
```

## Why This Change Is Needed

1. **Current Issue**: When OAuth callback goes directly to `api.sopher.ai`, cookies are set with domain `.sopher.ai` but there may be issues with cross-subdomain cookie sharing in some browsers.

2. **Solution**: By using `sopher.ai/api/backend/auth/callback/google` (which proxies to the backend), cookies are set directly on the `sopher.ai` domain, ensuring they are accessible when the user is redirected to the main application.

## Google OAuth Console Update

This change also requires updating the authorized redirect URI in the Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services > Credentials
3. Edit your OAuth 2.0 Client ID
4. Update the Authorized redirect URIs:
   - Remove: `https://api.sopher.ai/auth/callback/google`
   - Add: `https://sopher.ai/api/backend/auth/callback/google`
5. Save the changes

## Kubernetes Secret Update

Update the Kubernetes secret with the new redirect URI:

```bash
kubectl edit secret sopher-ai-secrets -n sopher-ai
```

Then update the `GOOGLE_OAUTH_REDIRECT_URI` value (base64 encoded).

Or use this command:
```bash
kubectl patch secret sopher-ai-secrets -n sopher-ai --type='json' \
  -p='[{"op": "replace", "path": "/data/GOOGLE_OAUTH_REDIRECT_URI", "value": "'$(echo -n "https://sopher.ai/api/backend/auth/callback/google" | base64)'"}]'
```

## Testing

After making these changes:
1. Restart the API pods to pick up the new configuration
2. Test the OAuth flow by logging in with Google
3. Verify that users are redirected to the main application (not back to login)