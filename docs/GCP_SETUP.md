# GCP Service Account Setup for GitHub Actions

This guide walks you through creating a Google Cloud Platform (GCP) service account with the necessary permissions to deploy the sopher.ai application to Google Kubernetes Engine (GKE) via GitHub Actions.

## Prerequisites

- Google Cloud Platform account with billing enabled
- GCP project with Kubernetes Engine API enabled
- `gcloud` CLI installed and authenticated
- Existing GKE cluster (or permissions to create one)

## Quick Setup

### Option 1: Automated Script (Recommended)

We've provided a script that automates the entire setup process:

```bash
# From the project root
./scripts/setup-gcp-service-account.sh
```

The script will:
1. Enable required Google Cloud APIs
2. Create the service account
3. Assign necessary IAM roles
4. Generate and download the service account key
5. Test cluster access
6. Display the secrets needed for GitHub

### Option 2: Manual Setup

If you prefer to run the commands manually or need to customize the setup:

## Step-by-Step Manual Setup

### 1. Set Environment Variables

```bash
# Replace with your actual values
export PROJECT_ID="your-gcp-project-id"
export SERVICE_ACCOUNT_NAME="github-actions-deployer"
export CLUSTER_NAME="sopher-ai-prod"
export CLUSTER_ZONE="us-west1-a"
```

### 2. Enable Required APIs

```bash
gcloud services enable container.googleapis.com --project=${PROJECT_ID}
gcloud services enable compute.googleapis.com --project=${PROJECT_ID}
gcloud services enable iam.googleapis.com --project=${PROJECT_ID}
```

### 3. Create Service Account

```bash
gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
    --description="Service account for GitHub Actions to deploy to GKE" \
    --display-name="GitHub Actions Deployer" \
    --project=${PROJECT_ID}
```

### 4. Assign IAM Roles

The service account needs the following roles for GKE deployment:

```bash
# Container Developer - Read/write access to GKE clusters and resources
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/container.developer"

# Storage Admin - Manage container images in GCR/Artifact Registry
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Compute Viewer - View compute resources
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/compute.viewer"

# Service Account User - Use service accounts for GKE nodes
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### 5. Generate Service Account Key

```bash
gcloud iam service-accounts keys create github-actions-sa-key.json \
    --iam-account=${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=${PROJECT_ID}
```

### 6. Test Access

```bash
# Set the service account key as the active credential
export GOOGLE_APPLICATION_CREDENTIALS="github-actions-sa-key.json"

# Test cluster access
gcloud container clusters get-credentials ${CLUSTER_NAME} \
    --zone=${CLUSTER_ZONE} \
    --project=${PROJECT_ID}

# Verify kubectl access
kubectl auth can-i create deployments --namespace=sopher-ai
```

## Configure GitHub Secrets

After creating the service account, you need to add the following secrets to your GitHub repository:

1. **Navigate to GitHub Repository Settings**:
   - Go to your repository on GitHub
   - Click "Settings" → "Secrets and variables" → "Actions"

2. **Add Repository Secrets**:

   | Secret Name | Value | Description |
   |-------------|-------|-------------|
   | `GCP_SA_KEY` | Contents of `github-actions-sa-key.json` | Complete JSON service account key |
   | `GCP_PROJECT` | Your GCP project ID | Project where resources are deployed |
   | `GKE_CLUSTER` | Your GKE cluster name | Kubernetes cluster name |
   | `GKE_ZONE` | Your GKE cluster zone | Zone where cluster is located |

3. **How to get the GCP_SA_KEY value**:
   ```bash
   cat github-actions-sa-key.json
   ```
   Copy the entire JSON content (including the outer braces) and paste it as the secret value.

## Required IAM Roles Explained

| Role | Purpose | Permissions |
|------|---------|-------------|
| `roles/container.developer` | Deploy to GKE | Create/update deployments, services, pods |
| `roles/storage.admin` | Manage container images | Push/pull images from GCR/Artifact Registry |
| `roles/compute.viewer` | View compute resources | List VMs, networks (required by GKE) |
| `roles/iam.serviceAccountUser` | Use service accounts | Required for GKE node service accounts |

## Security Best Practices

### Principle of Least Privilege
- The roles assigned provide the minimum permissions needed for deployment
- Consider using custom roles for even more restrictive access in production

### Key Management
- Store the service account key securely
- Never commit keys to version control
- Rotate keys regularly (every 90 days recommended)
- Use Google Secret Manager for additional security

### Monitoring
- Enable audit logging for the service account
- Monitor service account usage in Cloud Console
- Set up alerts for unexpected activity

## Troubleshooting

### Common Issues

**Error: "Permission denied" during deployment**
- Verify all required roles are assigned to the service account
- Check that the GKE cluster exists in the specified zone
- Ensure APIs are enabled in your GCP project

**Error: "Cluster not found"**
- Verify cluster name and zone in GitHub secrets
- Check that the service account has access to the cluster
- Ensure cluster is in the same project as the service account

**Error: "Invalid service account key"**
- Verify the JSON key is complete and properly formatted
- Check that the key hasn't expired
- Ensure no extra characters were added when copying to GitHub secrets

### Verification Commands

```bash
# Check service account exists
gcloud iam service-accounts list --project=${PROJECT_ID}

# Check assigned roles
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Test cluster access
gcloud container clusters describe ${CLUSTER_NAME} --zone=${CLUSTER_ZONE} --project=${PROJECT_ID}
```

## Cleanup

To remove the service account when no longer needed:

```bash
# Delete service account (this also invalidates all keys)
gcloud iam service-accounts delete ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=${PROJECT_ID}

# Remove local key file
rm github-actions-sa-key.json
```

## Next Steps

After setting up the service account:

1. **Test the GitHub Actions pipeline** by pushing to main branch
2. **Monitor deployments** in the GitHub Actions tab
3. **Check GKE workloads** in the GCP Console
4. **Set up monitoring** for your deployed application

For more information about the CI/CD pipeline, see [`.github/SETUP_SECRETS.md`](../.github/SETUP_SECRETS.md).