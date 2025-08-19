#!/bin/bash
# Force redeployment by triggering a new CI run with a timestamp tag

echo "Forcing redeployment of sopher.ai backend..."
echo "============================================"

# Create a lightweight tag to trigger CI
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG_NAME="deploy-${TIMESTAMP}"

echo "Creating deployment tag: ${TAG_NAME}"
git tag -a "${TAG_NAME}" -m "Force redeployment to update OAuth configuration"

echo "Pushing tag to trigger CI/CD..."
git push origin "${TAG_NAME}"

echo ""
echo "Tag created and pushed. This will trigger a new CI/CD run."
echo "Monitor the deployment at:"
echo "https://github.com/cheesejaguar/sopher.ai/actions"
echo ""
echo "After deployment completes (5-10 minutes), verify OAuth is configured:"
echo "curl https://api.sopher.ai/auth/config/status | python3 -m json.tool"