# Google OAuth Configuration Fix

## Problem
The Google OAuth callback is failing with a 500 error because the required Google OAuth credentials are not configured in the environment.

## Root Cause
- `GOOGLE_CLIENT_ID` environment variable is not set
- `GOOGLE_CLIENT_SECRET` environment variable is not set

## Solution

### Step 1: Create .env file
```bash
cp .env.example .env
```

### Step 2: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
5. Configure the OAuth consent screen if not already done:
   - Choose "External" user type
   - Fill in the required application information
   - Add test users if needed
6. For Application type, select **Web application**
7. Add authorized redirect URIs:
   - For local development: `http://localhost:3000/api/backend/auth/callback/google`
   - For production: `https://api.sopher.ai/auth/callback/google`
8. Click **CREATE**
9. Copy the **Client ID** and **Client Secret**

### Step 3: Configure Environment Variables

Edit your `.env` file and add:

```env
# Google OAuth (required for authentication)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/api/backend/auth/callback/google
```

For production deployment, use:
```env
GOOGLE_OAUTH_REDIRECT_URI=https://api.sopher.ai/auth/callback/google
```

### Step 4: Restart the Backend Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Step 5: Test the Authentication

1. Navigate to http://localhost:3000
2. Click on the "Sign in with Google" button
3. You should be redirected to Google's OAuth consent screen
4. After authorization, you should be redirected back to the application

## Verification

Run the test script to verify configuration:

```bash
cd backend
python3 test_oauth_config.py
```

You should see:
```
✅ GOOGLE_CLIENT_ID: [your-client-id]...
✅ GOOGLE_CLIENT_SECRET: ******** (hidden)
✅ OAuth configuration looks good!
```

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Ensure the redirect URI in your Google Cloud Console matches exactly with `GOOGLE_OAUTH_REDIRECT_URI`
- Check for trailing slashes and protocol (http vs https)

### Error: "Invalid state parameter"
- This usually means the OAuth state expired (10-minute TTL)
- Try initiating the login flow again

### Error: "Failed to authenticate with Google"
- Check that your Google Cloud project has the necessary APIs enabled:
  - Google+ API
  - Google Identity Toolkit API
- Verify the OAuth consent screen is properly configured

## Security Notes

1. **Never commit `.env` file to version control** - it's already in `.gitignore`
2. **Keep your Client Secret secure** - treat it like a password
3. **Use HTTPS in production** - OAuth requires secure connections in production
4. **Rotate credentials regularly** - especially if exposed

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) - for testing