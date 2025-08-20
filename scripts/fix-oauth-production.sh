#!/bin/bash

# Script to fix OAuth redirect URI in production
# This updates the Kubernetes secret with the correct redirect URI

set -e

echo "OAuth Production Configuration Fix"
echo "================================="
echo ""
echo "This script will help you update the OAuth redirect URI in production."
echo ""
echo "Current issue: OAuth redirect URI is set to api.sopher.ai which causes cookie domain mismatch."
echo "Solution: Change redirect URI to route through frontend proxy at sopher.ai"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster"
    echo "Please ensure you have the correct kubeconfig set"
    exit 1
fi

echo "Step 1: Current Configuration"
echo "-----------------------------"
echo "Checking current OAuth configuration..."
echo ""

# Get current config from the API
CURRENT_CONFIG=$(curl -s https://sopher.ai/api/backend/auth/config/status 2>/dev/null || echo "{}")
if [ "$CURRENT_CONFIG" != "{}" ]; then
    echo "Current redirect URI from API:"
    echo "$CURRENT_CONFIG" | grep -o '"redirect_uri":"[^"]*"' | cut -d'"' -f4
    echo ""
fi

echo "Step 2: Update Google Cloud Console"
echo "-----------------------------------"
echo "Please update the authorized redirect URI in Google Cloud Console to:"
echo ""
echo "  https://sopher.ai/api/backend/auth/callback/google"
echo ""
echo "Navigate to: https://console.cloud.google.com/apis/credentials"
echo "Edit your OAuth 2.0 Client ID and update the redirect URI"
echo ""
read -p "Press Enter when you've updated Google Cloud Console..."

echo ""
echo "Step 3: Update Kubernetes Secret"
echo "--------------------------------"
echo "This will update the GOOGLE_OAUTH_REDIRECT_URI in the Kubernetes secret"
echo ""

# Check if secret exists
if kubectl get secret sopherai-secrets -n sopher-ai &> /dev/null; then
    echo "Found existing secret 'sopherai-secrets' in namespace 'sopher-ai'"
    
    # Get current secret data
    echo "Backing up current secret..."
    kubectl get secret sopherai-secrets -n sopher-ai -o yaml > oauth-secret-backup-$(date +%Y%m%d-%H%M%S).yaml
    
    echo ""
    echo "Enter your Google OAuth credentials (or press Enter to keep existing):"
    read -p "GOOGLE_CLIENT_ID (leave empty to keep current): " CLIENT_ID
    read -s -p "GOOGLE_CLIENT_SECRET (leave empty to keep current): " CLIENT_SECRET
    echo ""
    
    # Build the patch command
    if [ -n "$CLIENT_ID" ] || [ -n "$CLIENT_SECRET" ]; then
        echo "Updating OAuth configuration..."
        
        # Create new secret with updated values
        PATCH_JSON='{"data":{'
        
        if [ -n "$CLIENT_ID" ]; then
            PATCH_JSON+='"GOOGLE_CLIENT_ID":"'$(echo -n "$CLIENT_ID" | base64)'",'
        fi
        
        if [ -n "$CLIENT_SECRET" ]; then
            PATCH_JSON+='"GOOGLE_CLIENT_SECRET":"'$(echo -n "$CLIENT_SECRET" | base64)'",'
        fi
        
        # Always update the redirect URI
        PATCH_JSON+='"GOOGLE_OAUTH_REDIRECT_URI":"'$(echo -n "https://sopher.ai/api/backend/auth/callback/google" | base64)'"'
        PATCH_JSON+='}}'
        
        kubectl patch secret sopherai-secrets -n sopher-ai --type='merge' -p="$PATCH_JSON"
    else
        # Just update the redirect URI
        echo "Updating redirect URI only..."
        kubectl patch secret sopherai-secrets -n sopher-ai --type='json' \
            -p='[{"op": "replace", "path": "/data/GOOGLE_OAUTH_REDIRECT_URI", "value": "'$(echo -n "https://sopher.ai/api/backend/auth/callback/google" | base64)'"}]'
    fi
    
    echo "Secret updated successfully!"
else
    echo "Error: Secret 'sopherai-secrets' not found in namespace 'sopher-ai'"
    echo ""
    echo "To create the secret, run:"
    echo ""
    echo "kubectl create secret generic sopherai-secrets -n sopher-ai \\"
    echo "  --from-literal=GOOGLE_CLIENT_ID=\"your-client-id\" \\"
    echo "  --from-literal=GOOGLE_CLIENT_SECRET=\"your-client-secret\" \\"
    echo "  --from-literal=GOOGLE_OAUTH_REDIRECT_URI=\"https://sopher.ai/api/backend/auth/callback/google\""
    exit 1
fi

echo ""
echo "Step 4: Restart Backend Pods"
echo "----------------------------"
echo "Restarting backend pods to pick up new configuration..."

kubectl rollout restart deployment/sopher-backend -n sopher-ai 2>/dev/null || \
    kubectl rollout restart deployment/backend -n sopher-ai 2>/dev/null || \
    echo "Warning: Could not restart backend deployment. Please restart manually."

echo ""
echo "Step 5: Verify Configuration"
echo "----------------------------"
echo "Waiting for pods to restart (30 seconds)..."
sleep 30

echo "Checking new configuration..."
NEW_CONFIG=$(curl -s https://sopher.ai/api/backend/auth/config/status 2>/dev/null || echo "{}")
if [ "$NEW_CONFIG" != "{}" ]; then
    echo "New configuration:"
    echo "$NEW_CONFIG" | python3 -m json.tool 2>/dev/null || echo "$NEW_CONFIG"
    
    # Check if redirect URI is correct
    if echo "$NEW_CONFIG" | grep -q "https://sopher.ai/api/backend/auth/callback/google"; then
        echo ""
        echo "✅ Success! OAuth redirect URI has been updated correctly."
    else
        echo ""
        echo "⚠️  Warning: Redirect URI may not be updated yet. Please check manually."
    fi
else
    echo "Could not verify configuration. Please check manually."
fi

echo ""
echo "Step 6: Test OAuth Flow"
echo "-----------------------"
echo "Please test the OAuth flow:"
echo "1. Clear all cookies for sopher.ai and api.sopher.ai"
echo "2. Navigate to https://sopher.ai/login"
echo "3. Click 'Sign in with Google'"
echo "4. Complete the OAuth flow"
echo "5. Verify you're redirected to the home page (not back to login)"
echo ""
echo "Done!"