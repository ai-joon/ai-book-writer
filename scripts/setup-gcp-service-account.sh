#!/bin/bash
# Setup GCP Service Account for GitHub Actions
# This script creates a service account with the necessary permissions for deploying to GKE

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up GCP Service Account for GitHub Actions${NC}"
echo

# Configuration variables - MODIFY THESE FOR YOUR PROJECT
PROJECT_ID=${GCP_PROJECT_ID:-""}
SERVICE_ACCOUNT_NAME="github-actions-deployer"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="github-actions-sa-key.json"
CLUSTER_NAME=${GKE_CLUSTER:-"sopher-ai-cluster"}
CLUSTER_ZONE=${GKE_ZONE:-"us-central1-a"}

# Function to print colored output
print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project if not set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        print_error "No GCP project configured. Set it with:"
        echo "gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

print_info "Using GCP Project: ${PROJECT_ID}"
print_info "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
print_info "Cluster: ${CLUSTER_NAME} (Zone: ${CLUSTER_ZONE})"
echo

# Step 1: Enable required APIs
print_step "Enabling required Google Cloud APIs..."
gcloud services enable container.googleapis.com --project=${PROJECT_ID}
gcloud services enable compute.googleapis.com --project=${PROJECT_ID}
gcloud services enable iam.googleapis.com --project=${PROJECT_ID}

# Step 2: Create service account
print_step "Creating service account: ${SERVICE_ACCOUNT_NAME}"
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} >/dev/null 2>&1; then
    print_warning "Service account already exists, skipping creation"
else
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --description="Service account for GitHub Actions to deploy to GKE" \
        --display-name="GitHub Actions Deployer" \
        --project=${PROJECT_ID}
fi

# Step 3: Assign IAM roles
print_step "Assigning IAM roles..."

# Required roles for GKE deployment
ROLES=(
    "roles/container.developer"      # Read/write access to GKE clusters and resources
    "roles/storage.admin"           # Manage container images in GCR/Artifact Registry
    "roles/compute.viewer"          # View compute resources
    "roles/iam.serviceAccountUser"  # Use service accounts (for GKE node service accounts)
)

for role in "${ROLES[@]}"; do
    print_info "Assigning role: $role"
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
        --role="$role" \
        --quiet
done

# Step 4: Generate and download service account key
print_step "Generating service account key..."
if [ -f "$KEY_FILE" ]; then
    print_warning "Key file $KEY_FILE already exists. Creating backup..."
    mv "$KEY_FILE" "${KEY_FILE}.backup.$(date +%s)"
fi

gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SERVICE_ACCOUNT_EMAIL} \
    --project=${PROJECT_ID}

print_step "Service account key saved to: ${KEY_FILE}"

# Step 5: Test cluster access (if cluster exists)
print_step "Testing cluster access..."
if gcloud container clusters describe ${CLUSTER_NAME} --zone=${CLUSTER_ZONE} --project=${PROJECT_ID} >/dev/null 2>&1; then
    print_info "Cluster ${CLUSTER_NAME} found"
    
    # Test kubectl access with the service account
    print_info "Testing kubectl access..."
    GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE} gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone=${CLUSTER_ZONE} \
        --project=${PROJECT_ID} \
        --quiet
    
    if kubectl auth can-i '*' '*' --all-namespaces >/dev/null 2>&1; then
        print_step "Service account has cluster access"
    else
        print_warning "Service account may need additional cluster-specific permissions"
    fi
else
    print_warning "Cluster ${CLUSTER_NAME} not found in zone ${CLUSTER_ZONE}"
    print_info "You may need to create the cluster first or update the cluster name/zone"
fi

# Step 6: Display setup summary
echo
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Add the following secrets to your GitHub repository:"
echo "   - Go to GitHub repo → Settings → Secrets and variables → Actions"
echo "   - Add these repository secrets:"
echo
echo -e "${YELLOW}   GCP_SA_KEY:${NC}"
echo "   $(cat ${KEY_FILE} | base64 | tr -d '\n')"
echo
echo -e "${YELLOW}   GCP_PROJECT:${NC} ${PROJECT_ID}"
echo -e "${YELLOW}   GKE_CLUSTER:${NC} ${CLUSTER_NAME}"
echo -e "${YELLOW}   GKE_ZONE:${NC} ${CLUSTER_ZONE}"
echo
echo "2. The service account key file is saved as: ${KEY_FILE}"
echo "3. Keep this key file secure and never commit it to version control"
echo
print_warning "SECURITY NOTE: The service account key provides access to your GCP resources."
print_warning "Store it securely and rotate it regularly."

# Step 7: Cleanup instructions
echo
echo -e "${BLUE}To clean up later (optional):${NC}"
echo "gcloud iam service-accounts delete ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID}"
echo "rm ${KEY_FILE}"