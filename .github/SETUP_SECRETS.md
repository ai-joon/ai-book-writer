# GitHub Actions Secrets Setup Guide

This guide explains how to configure GitHub repository secrets for the CI/CD pipeline.

## Repository Secrets Overview

The CI/CD pipeline uses GitHub secrets to securely store sensitive information like API keys and credentials. These secrets are encrypted and only exposed to workflows during execution.

## Required vs Optional Secrets

### Core Secrets (Tests & Builds Work Without These)
The pipeline is designed to run tests and build Docker images without any secrets configured. Only deployment steps require secrets.

### Optional Secrets for Full Pipeline

#### 1. Google Cloud Platform (GCP) Deployment
If you want to deploy to GCP/GKE, you need to create a service account with proper permissions.

**Quick Setup**: Use our automated script:
```bash
./scripts/setup-gcp-service-account.sh
```

**Manual Setup**: See [`docs/GCP_SETUP.md`](../docs/GCP_SETUP.md) for detailed instructions.

**Required GitHub Secrets**:
| Secret Name | Description | How to Obtain |
|-------------|-------------|---------------|
| `GCP_SA_KEY` | Service account JSON key | Complete output from service account key creation |
| `GKE_CLUSTER` | Kubernetes cluster name | Example: `sopher-ai-cluster` |
| `GKE_ZONE` | GCP zone | Example: `us-central1-a` |
| `GCP_PROJECT` | GCP project ID | Your GCP project ID (e.g., `my-project-123456`) |

#### 2. API Keys for Integration Tests (Optional)
These are only needed if you want to run integration tests with real LLM APIs:

| Secret Name | Description | Provider Dashboard |
|-------------|-------------|-------------------|
| `ANTHROPIC_API_KEY` | Claude API access | [Anthropic Console](https://console.anthropic.com/) |
| `OPENAI_API_KEY` | OpenAI API access | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `GOOGLE_API_KEY` | Google AI API access | [Google AI Studio](https://makersuite.google.com/app/apikey) |

## How to Add Secrets to Your Repository

1. **Navigate to Repository Settings**
   - Go to your GitHub repository
   - Click on "Settings" tab
   - In the left sidebar, expand "Secrets and variables"
   - Click on "Actions"

2. **Add a New Secret**
   - Click "New repository secret"
   - Enter the secret name (e.g., `GCP_SA_KEY`)
   - Paste the secret value
   - Click "Add secret"

3. **Verify Secret is Added**
   - The secret name will appear in the list
   - The value is hidden and encrypted
   - You can update but not view the value

## Security Best Practices

1. **Principle of Least Privilege**
   - Only grant necessary permissions to service accounts
   - Use separate service accounts for different environments

2. **Secret Rotation**
   - Rotate secrets regularly (every 90 days recommended)
   - Update both the provider and GitHub when rotating

3. **Access Control**
   - Limit who can manage repository secrets
   - Use environments for production secrets with required reviewers

4. **Never Commit Secrets**
   - Never commit secrets to code, even temporarily
   - Use `.gitignore` to exclude `.env` files
   - If a secret is accidentally committed, rotate it immediately

## Environment-Specific Configuration

### Development Environment
- No GitHub secrets needed
- Use `.env.example` as template for local `.env`
- Tests run with mocked services

### Staging Environment
- Create a separate set of secrets with `-STAGING` suffix
- Use less privileged service accounts
- Point to staging infrastructure

### Production Environment
- Use GitHub environments feature for additional protection
- Require manual approval for production deployments
- Use dedicated production service accounts

## Troubleshooting

### Error: "google-github-actions/auth failed"
**Cause**: `GCP_SA_KEY` secret is not configured or is invalid.

**Solution**: 
- Verify the secret is added to your repository
- Check that the JSON is valid and complete
- Ensure the service account has necessary permissions

### Error: "Secret not found"
**Cause**: Secret name mismatch or not configured.

**Solution**:
- Check exact secret name (case-sensitive)
- Verify secret is added to correct repository
- For forks, secrets need to be added to the fork

### Deployment Skipped
**Cause**: This is intentional - deployment only runs for the main repository.

**Solution**:
- This is expected behavior for forks and PRs
- To deploy your own instance, add the required secrets to your fork

## CI/CD Pipeline Behavior

The pipeline is designed to be flexible:

1. **Without Secrets**: 
   - ✅ Code quality checks run
   - ✅ Tests execute with mocked services
   - ✅ Docker images build
   - ✅ Security scans run
   - ⏭️ Deployment steps are skipped

2. **With Secrets**:
   - All above plus:
   - ✅ Images push to registry
   - ✅ Deploy to GKE cluster
   - ✅ Run smoke tests

## Getting Help

- Check the [main README](../README.md) for general setup
- Review `.env.example` for local development variables
- See `infra/.env.production.template` for production configuration
- Open an issue for CI/CD problems

## Example: Minimal Fork Setup

If you're forking this repository and want basic CI/CD:

1. Fork the repository
2. No secrets needed - tests and builds will work
3. Optionally add your own API keys for integration tests
4. For deployment, add GCP secrets pointing to your infrastructure

The pipeline will automatically detect available secrets and adjust its behavior accordingly.