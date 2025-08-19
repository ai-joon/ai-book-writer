# Production OAuth Configuration Guide

## Current Issue
The production server at `api.sopher.ai` is returning 500 errors for Google OAuth callbacks because the required environment variables are not set.

## Diagnosis
You can verify the OAuth configuration status by visiting:
```
https://api.sopher.ai/auth/config/status
```

## Production Setup Steps

### 1. Access Production Environment

For Kubernetes deployment:
```bash
kubectl get pods -n sopher-ai
kubectl exec -it <backend-pod-name> -n sopher-ai -- /bin/sh
```

For direct server access:
```bash
ssh <production-server>
```

### 2. Set Environment Variables

#### Option A: Kubernetes Secrets (Recommended)

1. Create a secret with OAuth credentials:
```bash
kubectl create secret generic google-oauth \
  --from-literal=GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  --from-literal=GOOGLE_CLIENT_SECRET="your-client-secret" \
  --from-literal=GOOGLE_OAUTH_REDIRECT_URI="https://api.sopher.ai/auth/callback/google" \
  -n sopher-ai
```

2. Update the deployment to use the secret:
```yaml
# In your backend deployment yaml
spec:
  containers:
  - name: backend
    envFrom:
    - secretRef:
        name: google-oauth
```

3. Apply the deployment:
```bash
kubectl apply -f backend-deployment.yaml
kubectl rollout restart deployment/backend -n sopher-ai
```

#### Option B: GitHub Secrets (for GitHub Actions deployment)

1. Go to your repository settings: https://github.com/cheesejaguar/sopher.ai/settings/secrets/actions
2. Add the following secrets:
   - `GOOGLE_CLIENT_ID`: Your OAuth client ID
   - `GOOGLE_CLIENT_SECRET`: Your OAuth client secret
   - `GOOGLE_OAUTH_REDIRECT_URI`: `https://api.sopher.ai/auth/callback/google`

3. Update `.github/workflows/ci.yml` to pass these secrets to the deployment:
```yaml
- name: Deploy to GKE
  env:
    GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
    GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
    GOOGLE_OAUTH_REDIRECT_URI: ${{ secrets.GOOGLE_OAUTH_REDIRECT_URI }}
```

#### Option C: Direct Environment Variables

If using Docker Compose or direct deployment:
```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_OAUTH_REDIRECT_URI="https://api.sopher.ai/auth/callback/google"
```

### 3. Configure Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** > **Credentials**
4. Click on your OAuth 2.0 Client ID
5. Add the following to **Authorized redirect URIs**:
   - `https://api.sopher.ai/auth/callback/google`
   - `https://sopher.ai/api/backend/auth/callback/google` (if using frontend proxy)
6. Click **Save**

### 4. Verify Configuration

After setting the environment variables and restarting the service:

1. Check the configuration status:
```bash
curl https://api.sopher.ai/auth/config/status
```

Expected response:
```json
{
  "google_oauth_configured": true,
  "client_id_set": true,
  "client_secret_set": true,
  "redirect_uri": "https://api.sopher.ai/auth/callback/google",
  "message": "OAuth is properly configured"
}
```

2. Test the OAuth flow:
   - Visit https://sopher.ai
   - Click "Sign in with Google"
   - Complete the OAuth flow

### 5. Monitor Logs

Check backend logs for any issues:
```bash
# Kubernetes
kubectl logs -f deployment/backend -n sopher-ai

# Docker
docker logs -f sopher-ai-backend

# Direct
tail -f /var/log/sopher-ai/backend.log
```

## Security Considerations

1. **Never commit credentials**: Keep OAuth credentials in secrets management
2. **Use HTTPS only**: Production OAuth must use HTTPS
3. **Rotate credentials regularly**: Update OAuth credentials every 90 days
4. **Limit redirect URIs**: Only add necessary redirect URIs in Google Console
5. **Monitor access logs**: Watch for unusual authentication patterns

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Ensure the redirect URI in Google Console exactly matches `GOOGLE_OAUTH_REDIRECT_URI`
- Check for trailing slashes and protocol (https vs http)

### Error: "Invalid state parameter"
- OAuth state has 10-minute TTL
- User should retry the login flow

### Error: "Failed to authenticate with Google"
- Check that required Google APIs are enabled:
  - Google+ API
  - People API
- Verify OAuth consent screen is configured

### Error: 500 Internal Server Error
- Check environment variables are set: `https://api.sopher.ai/auth/config/status`
- Review backend logs for specific error messages
- Ensure database connection is working

## Quick Test Script

Save this as `test_oauth.sh`:
```bash
#!/bin/bash

echo "Testing OAuth Configuration..."
echo "=============================="

# Check config status
echo "1. Checking configuration status..."
curl -s https://api.sopher.ai/auth/config/status | python3 -m json.tool

# Check health endpoint
echo -e "\n2. Checking health endpoint..."
curl -s https://api.sopher.ai/healthz

# Try to initiate OAuth flow
echo -e "\n3. Testing OAuth initiation..."
curl -I -s https://api.sopher.ai/auth/login/google | head -n 1

echo -e "\n=============================="
echo "OAuth configuration test complete"
```

Run with:
```bash
chmod +x test_oauth.sh
./test_oauth.sh
```

## Contact

For additional help with production deployment:
- Check logs at https://api.sopher.ai/logs (if configured)
- Review Kubernetes events: `kubectl get events -n sopher-ai`
- Check GitHub Actions logs for deployment issues