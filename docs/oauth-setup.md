# OAuth Setup Guide for sopher.ai

## Google Cloud Console Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth 2.0 Client ID"
5. Select "Web application" as the application type
6. Configure the OAuth client:
   - Name: `sopher.ai`
   - Authorized JavaScript origins:
     - `http://localhost:3000` (for local development)
     - `https://sopher.ai` (for production)
   - Authorized redirect URIs:
     - `http://localhost:3000/api/backend/auth/callback/google` (for local development)
     - `https://sopher.ai/api/backend/auth/callback/google` (for production)
7. Save and copy the Client ID and Client Secret

## Environment Configuration

### Local Development (.env)

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/api/backend/auth/callback/google
```

### Production Deployment

For production, set these environment variables in your deployment platform:

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=https://sopher.ai/api/backend/auth/callback/google
```

## Authentication Flow

1. User clicks "Sign in with Google" on the login page
2. Frontend redirects to `/api/backend/auth/login/google` (proxied to backend)
3. Backend generates OAuth state and PKCE challenge, redirects to Google
4. User authorizes the application on Google's consent screen
5. Google redirects back to `/api/backend/auth/callback/google` with auth code
6. Backend:
   - Validates state and exchanges code for tokens
   - Fetches user info from Google
   - Creates/updates user in database
   - Sets JWT cookies (access_token and refresh_token)
   - Redirects to frontend root path (`/`)
7. Frontend middleware checks for access_token cookie
8. If valid, user sees the main application; otherwise redirected to login

## Cookie Configuration

The backend sets cookies with these characteristics:
- **Domain**: `.sopher.ai` for production (allows subdomain access), none for localhost
- **Path**: `/` (accessible across the entire site)
- **SameSite**: `lax` (CSRF protection)
- **Secure**: `true` in production (HTTPS only)
- **HttpOnly**: `false` for access_token (allows JS access), `true` for refresh_token

## Troubleshooting

### Login Loop Issues

If users are redirected back to login after OAuth:
1. Check that `GOOGLE_OAUTH_REDIRECT_URI` matches exactly what's configured in Google Cloud Console
2. Verify cookies are being set correctly (check browser DevTools > Application > Cookies)
3. Ensure frontend and backend are using the same domain/port configuration
4. Check CORS configuration allows credentials from the frontend domain

### Cookie Not Being Set

1. Verify the backend is receiving the correct `Host` header from the proxy
2. Check that cookies aren't blocked by browser settings
3. For production, ensure HTTPS is enabled (cookies have `Secure` flag)
4. Verify domain configuration matches your deployment setup

### 401 Unauthorized Errors

1. Check that the access_token cookie is present and not expired
2. Verify the JWT_SECRET is the same across all backend instances
3. Ensure the frontend is including credentials in API requests