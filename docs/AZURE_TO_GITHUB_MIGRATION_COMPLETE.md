# Azure Pipelines to GitHub Actions Migration Guide

## 🎯 Migration Overview

This document provides a complete guide for migrating from Azure DevOps Pipelines to GitHub Actions for your homelab infrastructure management. The migration includes multi-environment support, comprehensive security scanning, and advanced deployment workflows.

## 📋 Migration Summary

### What Was Migrated

| Azure DevOps Component | GitHub Actions Equivalent | Status |
|------------------------|----------------------------|---------|
| `azure-pipelines.yml` | `.github/workflows/terraform-main.yml` | ✅ Complete |
| `terraform-plan.yml` | Plan jobs in main workflow | ✅ Complete |
| `terraform-apply.yml` | Apply jobs with environment protection | ✅ Complete |
| `terraform-setup.yml` | `.github/actions/terraform-setup/` | ✅ Complete |
| `security-scanning.yml` | `.github/actions/security-scan/` | ✅ Complete |
| `shared-variables.yml` | Environment variables & secrets | ✅ Complete |
| Variable Groups | Repository/Environment secrets | 📋 Setup Required |
| Agent Pool | GitHub hosted runners | ✅ Complete |

### New Capabilities Added

✨ **Enhanced Features:**
- **Environment-specific workflows** for faster dev feedback
- **Automated drift detection** with issue creation
- **Cost analysis workflow** (placeholder for Azure Cost Management)
- **Comprehensive security reporting** with scoring
- **Pull request integration** with plan summaries
- **Matrix deployments** with dependency management

## 🏗️ Architecture Overview

### Workflow Structure

```
.github/
├── workflows/
│   ├── terraform-main.yml       # 🏗️ Main production workflow
│   ├── terraform-dev.yml        # 🧪 Development environment
│   └── terraform-cleanup.yml    # 🧹 Maintenance & drift detection
└── actions/
    ├── terraform-setup/         # 🛠️ Terraform configuration
    └── security-scan/           # 🛡️ Security scanning
```

### Environment Strategy

| Environment | Triggers | Approval | Security Level |
|-------------|----------|----------|----------------|
| **dev-lab** | Push to develop, feature/* | None | Relaxed (warnings only) |
| **prod-lab** | Push to main, manual dispatch | Required | Strict (zero tolerance) |

### Matrix Deployment

**Environments & Modules:**
```yaml
dev-lab:  [main, vault, unifi, vultr]
prod-lab: [main, vault, unifi, vultr, b2]
```

**Deployment Order:**
1. `main` (Priority: Critical)
2. `vault` (Priority: High)
3. `unifi`, `vultr`, `b2` (Priority: Medium/Low)

## 🔧 Setup Instructions

### 1. Configure Repository Secrets

Add these secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

#### Azure Authentication (OIDC)
```
AZURE_CLIENT_ID         # Azure AD Application ID
AZURE_TENANT_ID         # Azure AD Tenant ID  
AZURE_SUBSCRIPTION_ID   # Azure Subscription ID
```

#### Terraform Backend
```
AZURE_BACKEND_RESOURCE_GROUP    # Backend storage resource group
AZURE_BACKEND_STORAGE_ACCOUNT   # Backend storage account name
AZURE_BACKEND_CONTAINER_NAME    # Backend storage container
```

#### External APIs (Optional)
```
RACKSPACE_API_KEY      # For Rackspace provider
```

### 2. Configure Environment Protection

#### Production Environment Setup
1. Go to `Settings > Environments`
2. Create environment: `production-terraform`
3. Enable **Required reviewers**
4. Add team members who can approve deployments
5. Set **Wait timer** if desired (e.g., 5 minutes)

#### Development Environment Setup
1. Create environment: `dev-lab`
2. No protection rules needed (for fast feedback)

### 3. Configure Repository Variables

Add these variables for notifications (`Settings > Secrets and variables > Actions > Variables`):

```
TEAMS_WEBHOOK_URL      # Microsoft Teams webhook (optional)
SLACK_WEBHOOK_URL      # Slack webhook (optional)
```

### 4. Configure Azure OIDC

Set up OIDC authentication between GitHub and Azure:

```bash
# Create Azure AD Application
az ad app create \
  --display-name "GitHub-OIDC-Terraform" \
  --identifier-uris "api://github-oidc-terraform"

# Create service principal
az ad sp create --id <APP_ID>

# Configure federated credentials
az ad app federated-credential create \
  --id <APP_ID> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:lordmuffin/homelab:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Assign Azure permissions
az role assignment create \
  --assignee <SERVICE_PRINCIPAL_ID> \
  --role "Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>"
```

## 🚀 Usage Guide

### Basic Operations

#### Trigger Development Deployment
```bash
# Push to develop branch
git checkout develop
git push origin develop

# Or trigger manually
# Go to Actions > Terraform Development > Run workflow
```

#### Trigger Production Deployment
```bash
# Push to main branch (requires approval)
git checkout main
git push origin main

# Or trigger manually with specific environment
# Go to Actions > Terraform Infrastructure > Run workflow
```

#### Run Maintenance Tasks
```bash
# Manual trigger options:
# - drift-detection: Check for infrastructure drift
# - security-audit: Run security scans
# - cost-analysis: Analyze infrastructure costs
# - full-maintenance: Run all maintenance tasks
```

### Advanced Workflows

#### Matrix Deployment Control
You can control which modules to deploy using workflow dispatch:

1. Go to `Actions > Terraform Infrastructure`
2. Click `Run workflow`
3. Select target environment
4. Enable/disable `force_apply` if needed

#### Pull Request Integration
- All PRs automatically run Terraform plan
- Plan results posted as PR comments
- Security scan results included
- No infrastructure changes applied

## 🛡️ Security Features

### Multi-Tool Security Scanning

| Tool | Purpose | Failure Threshold |
|------|---------|------------------|
| **tfsec** | Terraform security | Critical: 0, High: configurable |
| **Checkov** | Policy as code | Failed checks: configurable |
| **Terrascan** | Cloud security | Informational only |

### Security Scoring
- **Score Range:** 0-100
- **Calculation:** Weighted penalty system
  - Critical issues: -50 points each
  - High issues: -20 points each
  - Medium issues: -5 points each
  - Failed checks: -10 points each

### Environment-Specific Security
- **Development:** Relaxed (warnings only)
- **Production:** Strict (zero tolerance for critical/high)

## 📊 Monitoring & Reporting

### Automated Drift Detection
- **Schedule:** Daily at 2 AM UTC
- **Action:** Creates GitHub issues for detected drift
- **Scope:** All environments and modules

### GitHub Integration
- **Pull Request Comments:** Terraform plan summaries
- **Job Summaries:** Rich HTML reports for each run
- **Artifacts:** Plan files, security reports (30-day retention)

### Notifications
- **Teams/Slack:** Deployment status updates
- **GitHub Issues:** Drift detection alerts
- **PR Reviews:** Automated plan reviews

## 🔄 Migration Checklist

### Pre-Migration
- [ ] Set up Azure OIDC authentication
- [ ] Configure repository secrets and variables
- [ ] Create GitHub environments with protection rules
- [ ] Test authentication with a simple workflow

### Migration
- [ ] Copy workflow files to `.github/` directory
- [ ] Update any environment-specific variables
- [ ] Test development workflow first
- [ ] Test production workflow with approval
- [ ] Validate security scanning

### Post-Migration
- [ ] Disable Azure DevOps pipelines
- [ ] Update team documentation
- [ ] Train team on new workflows
- [ ] Set up monitoring dashboards (optional)
- [ ] Configure additional notification channels

## 🔧 Troubleshooting

### Common Issues

#### Authentication Failures
```
Error: Unable to authenticate with Azure
```
**Solution:** Verify OIDC setup and service principal permissions

#### State Backend Issues
```
Error: Failed to get existing workspaces
```
**Solution:** Check backend configuration secrets and storage account access

#### Security Scan Failures
```
Error: Failed to install security tools
```
**Solution:** Check runner networking and tool versions in environment variables

#### Matrix Job Failures
```
Error: Module dependency not met
```
**Solution:** Ensure main module deploys before dependent modules

### Debug Steps

1. **Check Secrets:** Verify all required secrets are configured
2. **Test Authentication:** Run a simple Azure CLI command in a workflow
3. **Validate Backend:** Ensure storage account and container exist
4. **Review Logs:** Check individual job logs for specific errors
5. **Test Locally:** Use GitHub CLI to test workflows locally

## 📈 Performance Optimizations

### Caching Strategy
- **Terraform Plugins:** Cached per runner OS and version
- **Security Tools:** Cached per tool version
- **Terraform Providers:** Cached per lock file hash

### Parallel Execution
- **Development:** Up to 5 parallel jobs
- **Production:** Sequential for dependency management
- **Security Scans:** Parallel tool execution

### Resource Management
- **Artifact Retention:** 30 days (production), 7 days (development)
- **Timeout Settings:** 45 minutes (plan), 90 minutes (apply)
- **Cache TTL:** 7 days for tools, 1 day for providers

## 🔮 Future Enhancements

### Planned Features
- [ ] Integration with Azure Cost Management APIs
- [ ] Automated dependency updates with Dependabot
- [ ] Integration testing with preview environments
- [ ] Advanced notification routing
- [ ] Custom dashboard for infrastructure metrics

### Advanced Workflows
- [ ] Blue/green deployments for zero-downtime updates
- [ ] Automated rollback on failure detection
- [ ] Integration with external monitoring systems
- [ ] Custom security policy enforcement

## 📚 Additional Resources

### Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform GitHub Actions](https://github.com/hashicorp/setup-terraform)
- [Azure OIDC Configuration](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)

### Tools
- [tfsec](https://github.com/aquasecurity/tfsec)
- [Checkov](https://github.com/bridgecrewio/checkov)
- [Terrascan](https://github.com/tenable/terrascan)

### Examples
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

---

## 🎉 Migration Complete!

Your Azure DevOps Pipelines have been successfully migrated to GitHub Actions with enhanced features:

✅ **Multi-environment support** (dev-lab, prod-lab)  
✅ **Comprehensive security scanning** (tfsec, Checkov, Terrascan)  
✅ **Automated drift detection** with issue creation  
✅ **Pull request integration** with plan comments  
✅ **Environment protection** with approval workflows  
✅ **Matrix deployments** with dependency management  
✅ **Rich reporting** and notifications  

The new GitHub Actions workflows provide better developer experience, enhanced security, and improved operational visibility compared to the original Azure DevOps setup.

**Next Steps:**
1. Complete the setup checklist
2. Test the workflows in development
3. Train your team on the new processes
4. Monitor and optimize based on usage patterns

**Questions or Issues?**
- Check the troubleshooting section
- Review GitHub Actions logs for specific errors
- Consult the additional resources for advanced topics