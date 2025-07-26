# Azure DevOps Terraform Pipelines

This directory contains Azure DevOps pipelines converted from Gitea Actions workflows for managing Terraform infrastructure with Azure Storage backend.

## Overview

The pipelines provide automated Terraform plan and apply capabilities with the following features:

- **Azure Storage Backend**: Remote state storage in Azure Storage Account
- **Multi-Environment Support**: Separate configurations for `dev-lab` and `prod-lab`
- **Module-Based Architecture**: Support for individual Terraform modules
- **Security**: Azure service principal authentication and security scanning
- **PR Integration**: Plan results integration with pull requests
- **Safety Controls**: Multiple validation steps and approval gates

## Directory Structure

```
.azure-pipelines/
├── pipelines/
│   ├── terraform-plan.yml      # Plan validation pipeline
│   └── terraform-apply.yml     # Deployment pipeline
├── templates/
│   ├── terraform-setup.yml     # Shared setup template
│   └── terraform-security-scan.yml # Security scanning template
└── README.md                   # This documentation
```

## Pipelines

### 🔍 terraform-plan.yml

**Purpose**: Validates Terraform configurations and generates plans for review

**Triggers**:
- Pull requests targeting `main` or `develop` branches
- Pushes to `main`, `develop`, or `feature/*` branches
- Changes to `terraform/**` or `.azure-pipelines/**`

**Features**:
- Matrix strategy for parallel execution across environments and modules
- Terraform format, validation, and planning
- Security scanning with tfsec (optional: checkov and terrascan)
- Plan results posted as pull request comments
- Artifact publishing for plan files

**Matrix Configuration**:
```yaml
strategy:
  matrix:
    DevLab_Main:
      Environment: 'dev-lab'
      Module: 'main'
    # ... additional combinations
```

### 🚀 terraform-apply.yml

**Purpose**: Applies Terraform changes to infrastructure

**Triggers**:
- Pushes to `main` branch (automatic deployment)
- Manual pipeline runs with parameters

**Features**:
- Pre-apply security checks and validations
- Deployment environments for approval gates
- Plan-before-apply with change detection
- Artifact publishing for apply results
- Teams notifications (optional)
- Post-apply verification steps

**Manual Deployment Parameters**:
- `environment`: Target environment (`dev-lab` or `prod-lab`)
- `module`: Target module (`main`, `vault`, `unifi`, `vultr`, `b2`)
- `confirmApply`: Must type "apply" to confirm
- `deploymentMode`: `automatic` or `manual`

## Templates

### 🔧 terraform-setup.yml

**Purpose**: Shared template for common Terraform setup steps

**Features**:
- Parameter validation and path computation
- Azure backend access verification
- Terraform installation and configuration
- Format checking and environment setup
- Reusable across both plan and apply pipelines

**Parameters**:
```yaml
parameters:
  - name: azureServiceConnection
  - name: terraformVersion
  - name: workingDirectory
  - name: environment
  - name: module
  - name: stateKey
```

### 🛡️ terraform-security-scan.yml

**Purpose**: Comprehensive security scanning template

**Features**:
- Multiple security tools: tfsec, checkov, terrascan
- Configurable scan levels: basic, standard, comprehensive
- Severity-based failure thresholds
- Security report generation
- Artifact publishing for scan results

**Scan Levels**:
- **Basic**: tfsec only
- **Standard**: tfsec with enhanced reporting
- **Comprehensive**: tfsec + checkov + terrascan

## Required Azure Resources

### Service Connections

Create an Azure service connection named `azure-terraform-backend` with the following permissions:

- **Storage Account**: Contributor access to the storage account
- **Resource Group**: Reader access to the resource group
- **Subscription**: Reader access for validation

### Variable Groups

Create variable groups for each environment:

#### terraform-dev-lab
```
AZURE_BACKEND_RESOURCE_GROUP     # Resource group name
AZURE_BACKEND_STORAGE_ACCOUNT    # Storage account name
AZURE_BACKEND_CONTAINER_NAME     # Container name
RACKSPACE_API_KEY               # Rackspace API key
TEAMS_WEBHOOK_URL               # Teams notification webhook (optional)
```

#### terraform-prod-lab
```
AZURE_BACKEND_RESOURCE_GROUP     # Resource group name
AZURE_BACKEND_STORAGE_ACCOUNT    # Storage account name
AZURE_BACKEND_CONTAINER_NAME     # Container name
RACKSPACE_API_KEY               # Rackspace API key
TEAMS_WEBHOOK_URL               # Teams notification webhook (optional)
```

## State Management

### State File Organization
```
Azure Container Structure:
├── dev-lab/
│   ├── main.tfstate
│   ├── vault.tfstate
│   ├── unifi.tfstate
│   ├── vultr.tfstate
│   └── b2.tfstate
└── prod-lab/
    ├── main.tfstate
    ├── vault.tfstate
    ├── unifi.tfstate
    ├── vultr.tfstate
    └── b2.tfstate
```

### Backend Configuration
The pipelines automatically generate backend configuration:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "your-resource-group"
    storage_account_name = "your-storage-account"
    container_name       = "terraform-state"
    key                  = "dev-lab/main.tfstate"
  }
}
```

## Environment Setup

### Deployment Environments

Configure deployment environments in Azure DevOps for approval gates:

#### dev-lab Environment
- **Approvers**: Development team members
- **Branch Control**: Allow deployments from `main` and feature branches
- **Business Hours**: No restrictions

#### prod-lab Environment
- **Approvers**: Senior engineers and operations team
- **Branch Control**: Only allow deployments from `main` branch
- **Business Hours**: Restrict to business hours (optional)

### Security Configuration

#### Branch Policies
- Require pull request reviews before merging to `main`
- Require plan pipeline completion before PR completion
- Require status checks from security scans

#### Pipeline Permissions
- Limit pipeline execution to authorized users
- Require manual approval for production deployments
- Audit pipeline run history

## Usage Examples

### Typical Workflow

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/add-new-infrastructure
   ```

2. **Make Terraform Changes**:
   ```bash
   # Edit terraform files
   vim terraform/main.tf
   ```

3. **Push Changes**:
   ```bash
   git add .
   git commit -m "Add new infrastructure"
   git push origin feature/add-new-infrastructure
   ```

4. **Create Pull Request**:
   - Plan pipeline automatically runs
   - Review plan results in pipeline logs and artifacts
   - Review security scan results

5. **Merge to Main**:
   - Apply pipeline automatically runs on merge
   - Infrastructure deployed to all environments

### Manual Deployment

For controlled deployments to specific environments:

1. Navigate to **Pipelines** → **terraform-apply**
2. Click **Run pipeline**
3. Select parameters:
   - **environment**: `dev-lab` or `prod-lab`
   - **module**: `main`, `vault`, `unifi`, `vultr`, or `b2`
   - **confirmApply**: Type `apply`
   - **deploymentMode**: Select `manual`
4. Click **Run**

### Emergency Procedures

#### Plan-Only Validation
```bash
# Create a PR to see plans without applying
git checkout -b emergency/review-changes
# Make temporary changes to trigger planning
git push origin emergency/review-changes
# Review plan outputs in pipeline artifacts
```

#### Infrastructure Rollback
```bash
# Use manual deployment with previous configuration
# Or restore from version control:
git revert <commit-hash>
git push origin main
```

## Migration from Gitea Actions

### Key Differences

| Feature | Gitea Actions | Azure DevOps |
|---------|---------------|---------------|
| **Triggers** | `on:` syntax | `trigger:` and `pr:` |
| **Matrix Strategy** | `strategy.matrix` | `strategy.matrix` |
| **Secrets** | `${{ secrets.NAME }}` | Variable groups |
| **Artifacts** | `actions/upload-artifact` | `PublishPipelineArtifact` |
| **Comments** | GitHub API | Azure DevOps REST API |
| **Environments** | `environment:` | Deployment jobs |

### Converted Features

✅ **Matrix Builds**: Parallel execution across environments and modules  
✅ **Azure Authentication**: Service connections replace OIDC  
✅ **State Management**: Same Azure Storage backend  
✅ **Security Scanning**: Enhanced with multiple tools  
✅ **PR Integration**: Comments via Azure DevOps REST API  
✅ **Manual Deployment**: Pipeline parameters replace workflow dispatch  
✅ **Notifications**: Teams integration replaces GitHub notifications  
✅ **Approval Gates**: Deployment environments replace GitHub environments  

### New Features

🆕 **Enhanced Security Scanning**: Multiple tools with configurable levels  
🆕 **Teams Integration**: Native Microsoft Teams notifications  
🆕 **Deployment Environments**: Built-in approval workflows  
🆕 **Variable Groups**: Environment-specific configuration management  
🆕 **Pipeline Templates**: Reusable components for better maintainability  

## Troubleshooting

### Common Issues

#### Pipeline Failures
```bash
# Check Azure service connection
# Verify variable group configurations
# Review pipeline logs for specific errors
```

#### Authentication Issues
```bash
# Verify service principal permissions
# Check Azure resource access
# Validate storage account configuration
```

#### State Lock Issues
```bash
# Check for concurrent pipeline runs
# Manually release locks if necessary via Azure CLI
# Verify backend configuration
```

### Debugging Pipelines

1. **Enable Debug Logging**:
   - Add `system.debug: true` to pipeline variables
   - Review detailed step outputs

2. **Check Pipeline Artifacts**:
   - Download plan/apply artifacts from pipeline runs
   - Review security scan results

3. **Manual State Inspection**:
   ```bash
   # Download state file from Azure Storage
   az storage blob download \
     --container-name <container> \
     --name dev-lab/main.tfstate \
     --file local-state.tfstate \
     --account-name <account>
   ```

### Performance Optimization

#### Pipeline Efficiency
- Use parallel matrix strategies
- Cache Terraform providers (if applicable)
- Optimize security scan frequency
- Use incremental deployments

#### Resource Management
- Monitor Azure DevOps parallel job limits
- Optimize storage account performance tier
- Configure appropriate pipeline timeouts
- Implement smart triggering (path filters)

## Security Best Practices

### Authentication and Authorization
- Use Azure service principals with minimal permissions
- Rotate service principal credentials regularly
- Implement just-in-time access for production
- Audit pipeline access and modifications

### State File Security
- Enable Azure Storage encryption at rest
- Use Azure Key Vault for sensitive configuration
- Implement network access restrictions
- Regular backup of state files to separate location

### Pipeline Security
- Code review requirements for pipeline changes
- Separate permissions for plan vs apply operations
- Environment-specific approval requirements
- Regular security scanning and updates

### Compliance and Monitoring
- Log all infrastructure changes
- Implement change approval workflows
- Monitor for drift and unauthorized changes
- Regular compliance reporting

## Integration with Existing Tools

### Task Runner Integration
The pipelines complement your existing Task runner setup:

```bash
# Local development still uses Task
task terraform:plan
task terraform:apply

# CI/CD uses Azure DevOps pipelines
# Provides audit trail and approval process
```

### 1Password Integration
Consider Azure Key Vault integration:

```bash
# Pipeline variables replace manual 1Password lookups
# Azure Key Vault provides secure secret management
# Service connections handle authentication
```

### Docker Integration
Pipeline agents replace Docker containers:

```bash
# Old: docker run --rm -v ... terraform plan
# New: Azure DevOps hosted agents with Terraform tasks
```

## Monitoring and Metrics

### Pipeline Metrics
- Deployment frequency and lead time
- Success/failure rates by environment
- Security scan results trends
- Infrastructure drift detection

### Operational Metrics
- Resource utilization and costs
- Performance impact of changes
- Compliance status tracking
- Incident response times

### Alerting
- Failed deployment notifications
- Security scan threshold violations
- State file access anomalies
- Resource quota approach warnings

## Additional Resources

- [Azure DevOps Pipelines Documentation](https://docs.microsoft.com/en-us/azure/devops/pipelines/)
- [Terraform Azure Backend Documentation](https://www.terraform.io/docs/backends/types/azurerm.html)
- [Azure DevOps Service Connections](https://docs.microsoft.com/en-us/azure/devops/pipelines/library/service-endpoints)
- [Terraform Security Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)