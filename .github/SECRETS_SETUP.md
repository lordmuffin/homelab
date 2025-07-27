# 🔐 GitHub Actions Secrets & Variables Setup Guide

This guide provides step-by-step instructions for configuring all required secrets and variables for the Terraform GitHub Actions workflows.

## 📋 Required Secrets Configuration

### 1. Azure Authentication (OIDC)

Navigate to `Settings > Secrets and variables > Actions > Secrets` and add:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AZURE_CLIENT_ID` | Azure AD Application (Client) ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `87654321-4321-4321-4321-210987654321` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `abcdef12-3456-7890-abcd-ef1234567890` |

### 2. Terraform Backend Configuration

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AZURE_BACKEND_RESOURCE_GROUP` | Resource group containing Terraform state storage | `rg-terraform-state` |
| `AZURE_BACKEND_STORAGE_ACCOUNT` | Storage account for Terraform state | `tfstatehomelabprod` |
| `AZURE_BACKEND_CONTAINER_NAME` | Storage container for state files | `tfstate` |

### 3. External Service APIs (Optional)

| Secret Name | Description | Required For |
|-------------|-------------|--------------|
| `RACKSPACE_API_KEY` | Rackspace Cloud API key | Rackspace provider modules |

## 🌍 Environment-Specific Configuration

### Repository Variables

Navigate to `Settings > Secrets and variables > Actions > Variables` and add:

| Variable Name | Description | Example Value |
|---------------|-------------|---------------|
| `TEAMS_WEBHOOK_URL` | Microsoft Teams incoming webhook URL | `https://outlook.office.com/webhook/...` |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | `https://hooks.slack.com/services/...` |

### Environment Protection Setup

#### 1. Create Environments

1. Go to `Settings > Environments`
2. Click `New environment`
3. Create the following environments:

##### Production Environment: `production-terraform`
- **Protection Rules:**
  - ✅ Required reviewers: Add team members who can approve deployments
  - ✅ Wait timer: 5 minutes (optional)
  - ✅ Prevent self-review: Enabled
- **Environment secrets:** None (inherits from repository)

##### Development Environment: `dev-lab`
- **Protection Rules:** None (for fast feedback loops)
- **Environment secrets:** None (inherits from repository)

##### Production Environment: `prod-lab`
- **Protection Rules:**
  - ✅ Required reviewers: Add senior team members
  - ✅ Wait timer: 10 minutes
  - ✅ Prevent self-review: Enabled
- **Environment secrets:** None (inherits from repository)

## 🔧 Azure OIDC Setup Script

Use this script to configure Azure OIDC authentication:

```bash
#!/bin/bash

# Configuration
REPO_OWNER="lordmuffin"
REPO_NAME="homelab"
APP_NAME="GitHub-OIDC-Terraform-Homelab"
SUBSCRIPTION_ID="your-subscription-id"

echo "🔐 Setting up Azure OIDC for GitHub Actions"

# 1. Create Azure AD Application
echo "📝 Creating Azure AD Application..."
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --identifier-uris "api://github-oidc-$REPO_NAME" \
  --query appId \
  --output tsv)

echo "✅ Application created with ID: $APP_ID"

# 2. Create Service Principal
echo "👤 Creating Service Principal..."
SP_ID=$(az ad sp create \
  --id $APP_ID \
  --query id \
  --output tsv)

echo "✅ Service Principal created with ID: $SP_ID"

# 3. Configure Federated Credentials for main branch
echo "🔗 Configuring federated credentials for main branch..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# 4. Configure Federated Credentials for develop branch
echo "🔗 Configuring federated credentials for develop branch..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-develop", 
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':ref:refs/heads/develop",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# 5. Configure Federated Credentials for pull requests
echo "🔗 Configuring federated credentials for pull requests..."
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-pr",
    "issuer": "https://token.actions.githubusercontent.com", 
    "subject": "repo:'$REPO_OWNER'/'$REPO_NAME':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# 6. Assign Azure Contributor role
echo "🛡️ Assigning Contributor role..."
az role assignment create \
  --assignee $SP_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"

# 7. Get Tenant ID
TENANT_ID=$(az account show --query tenantId --output tsv)

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Add these secrets to your GitHub repository:"
echo "   AZURE_CLIENT_ID: $APP_ID"
echo "   AZURE_TENANT_ID: $TENANT_ID"
echo "   AZURE_SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
echo ""
echo "🔗 GitHub Repository Settings:"
echo "   https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
```

## 🧪 Testing Authentication

Create a simple test workflow to verify authentication:

```yaml
# .github/workflows/test-auth.yml
name: 🧪 Test Azure Authentication

on:
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  test-auth:
    runs-on: ubuntu-latest
    steps:
      - name: 🔐 Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: ✅ Test Azure CLI
        run: |
          az account show
          az group list --output table
```

Run this workflow to verify your authentication setup works correctly.

## 🔍 Validation Checklist

### ✅ Pre-Deployment Checklist

- [ ] All required secrets are configured
- [ ] OIDC federated credentials are set up for main, develop, and PR branches
- [ ] Service principal has Contributor role on subscription
- [ ] Environment protection rules are configured
- [ ] Backend storage account and container exist
- [ ] Test authentication workflow passes

### ✅ Security Validation

- [ ] No secrets contain placeholder values
- [ ] Service principal permissions follow least privilege
- [ ] Environment reviewers are configured
- [ ] Repository access is restricted to authorized users
- [ ] Webhook URLs are valid and secure

### ✅ Functionality Testing

- [ ] Development workflow runs successfully
- [ ] Production workflow requires approval
- [ ] Security scans complete without errors
- [ ] Terraform plans generate correctly
- [ ] Notifications are delivered (if configured)

## 🚨 Security Best Practices

### Secrets Management
1. **Rotate secrets regularly** (every 90 days recommended)
2. **Use environment-specific secrets** when needed
3. **Never commit secrets** to version control
4. **Limit secret access** to required workflows only

### Service Principal Security
1. **Scope permissions** to specific resource groups when possible
2. **Use managed identities** where available
3. **Monitor service principal usage** with Azure activity logs
4. **Enable conditional access** for enhanced security

### Repository Security
1. **Enable branch protection** on main and develop branches
2. **Require PR reviews** for all changes
3. **Enable dependency scanning** and security alerts
4. **Restrict workflow permissions** to minimum required

## 🔧 Troubleshooting

### Common Authentication Issues

#### Issue: "OIDC token validation failed"
**Cause:** Federated credential configuration mismatch  
**Solution:** Verify subject claims match your repository and branch names exactly

#### Issue: "Insufficient privileges to complete the operation"
**Cause:** Service principal lacks required permissions  
**Solution:** Verify Contributor role assignment and scope

#### Issue: "Backend initialization failed"
**Cause:** Storage account access issues  
**Solution:** Check service principal has Storage Blob Data Contributor role on storage account

### Debugging Steps

1. **Verify secrets:** Check all required secrets are configured with correct values
2. **Test authentication:** Run the test workflow to isolate auth issues
3. **Check permissions:** Verify service principal roles in Azure portal
4. **Review logs:** Examine workflow logs for specific error messages
5. **Validate OIDC:** Check federated credentials in Azure AD application

## 📞 Support Resources

- **Azure OIDC Documentation:** [Configure OpenID Connect in Azure](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
- **GitHub Secrets Documentation:** [Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- **Terraform Backend Documentation:** [Azure Backend Configuration](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/service_principal_oidc)

---

**🎯 Next Step:** Once all secrets are configured and validated, proceed to test your first GitHub Actions workflow deployment!