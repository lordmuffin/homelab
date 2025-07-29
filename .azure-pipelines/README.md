# Azure DevOps Pipelines

This directory contains Azure DevOps pipeline definitions for the homelab infrastructure, converted from the Gitea workflow structure.

## Structure

```
.azure-pipelines/
├── azure-pipelines.yml          # Main pipeline entry point
├── pipelines/
│   ├── terraform-plan.yml       # Terraform plan validation
│   └── terraform-apply.yml      # Terraform apply deployment
├── templates/
│   └── terraform-setup.yml      # Common Terraform setup steps
└── README.md                    # This file
```

## Pipeline Features

### terraform-plan.yml
- **Matrix Strategy**: Tests 8 environment/module combinations (dev-lab and prod-lab environments)
- **Excluded Combinations**: dev-lab/b2 (aligned with Gitea workflow)
- **Validation Steps**: Format check, init, validate, plan, security scan
- **Artifacts**: Plan files and outputs uploaded for review
- **PR Comments**: Automatic plan output commenting on pull requests
- **Security Scanning**: tfsec integration for Terraform security analysis

### terraform-apply.yml
- **Deployment Jobs**: Uses Azure DevOps environments for approval gates
- **Plan Artifacts**: Downloads and applies previously generated plans
- **Matrix Strategy**: Same combinations as plan stage
- **Conditional**: Only runs on main branch or manual dispatch

## Environment Setup

### Required Variable Groups
- `terraform-dev-lab`: Variables for dev-lab environment
- `terraform-prod-lab`: Variables for prod-lab environment

### Required Variables
- `AZURE_BACKEND_RESOURCE_GROUP`: Azure storage account resource group
- `AZURE_BACKEND_STORAGE_ACCOUNT`: Azure storage account name
- `AZURE_BACKEND_CONTAINER_NAME`: Storage container for Terraform state
- `RACKSPACE_API_KEY`: API key for Rackspace resources

### Service Connections
- `azure-terraform-backend`: Azure Resource Manager connection for backend storage

## Triggers

### Branch Triggers
- `main`, `develop`, `feature/*` branches
- Path filters: `terraform/**`, `.azure-pipelines/**`

### Pull Request Triggers
- Target branches: `main`, `develop`
- Same path filters as branch triggers

## Comparison with Gitea Workflow

### Similarities
- Same matrix strategy and environment combinations
- Identical security scanning with tfsec
- Equivalent plan output generation and artifact handling
- Similar PR commenting functionality
- Same working directory logic for modules

### Azure DevOps Specific Features
- Native Azure authentication with service connections
- Deployment jobs with environment approval gates
- Pipeline artifacts instead of GitHub Actions artifacts
- Azure DevOps API for PR commenting
- Template structure for code reuse

### Key Differences
- Uses TerraformCLI@0 task instead of hashicorp/setup-terraform action
- PowerShell scripts instead of bash for cross-platform compatibility
- Azure-specific backend configuration handling
- Environment-based deployment approvals for apply operations

## Usage

1. Import the pipeline in Azure DevOps pointing to `azure-pipelines.yml`
2. Configure required variable groups and service connections
3. Set up Azure DevOps environments for deployment approvals
4. Trigger via push to monitored branches or create pull requests

The pipeline will automatically validate Terraform configurations and provide plan outputs for review.