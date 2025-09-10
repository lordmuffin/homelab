# Migration Scripts

This directory contains automation scripts for the ArgoCD to FluxCD migration.

## Scripts

### `migrate.sh`
Complete migration automation script with the following capabilities:

**Features:**
- Prerequisites validation (kubectl, flux CLI, GitHub token)
- Automated FluxCD bootstrap
- ArgoCD backup creation
- Phased application deployment
- Health validation
- Status reporting

**Usage:**
```bash
export GITHUB_TOKEN=ghp_xxxxx
./migrate.sh install          # Full installation
./migrate.sh deploy core      # Deploy specific category
./migrate.sh validate         # Check deployment health
./migrate.sh status           # Show summary
./migrate.sh backup          # Backup ArgoCD only
```

### `validate.sh`
Comprehensive validation script for FluxCD deployment health:

**Features:**
- FluxCD system component validation
- Source repository health checks
- Application deployment validation
- RBAC configuration verification
- Resource usage monitoring
- Network connectivity tests
- Category-specific validations

**Usage:**
```bash
./validate.sh              # Run all tests
./validate.sh system       # FluxCD system only
./validate.sh apps         # Applications only
./validate.sh networking   # Networking category
```

## Environment Variables

### Required
- `GITHUB_TOKEN` - GitHub personal access token with repo permissions

### Optional
- `GITHUB_USER` - GitHub username (default: lordmuffin)
- `GITHUB_REPO` - Repository name (default: homelab)
- `BRANCH` - Git branch (default: main)
- `FLUX_PATH` - Path in repository (default: apps/argocd-flux)

## Migration Workflow

### 1. Preparation
```bash
# Set up environment
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Create backup
./migrate.sh backup
```

### 2. Installation
```bash
# Full FluxCD installation
./migrate.sh install

# Validate installation
./validate.sh system
```

### 3. Phased Deployment
```bash
# Deploy by category
./migrate.sh deploy core
./validate.sh core

./migrate.sh deploy networking  
./validate.sh networking

./migrate.sh deploy monitoring
./validate.sh monitoring

# Continue with other categories...
```

### 4. Validation
```bash
# Comprehensive validation
./validate.sh all

# Monitor status
./migrate.sh status
```

## Troubleshooting

### Common Issues

**Bootstrap Failure:**
```bash
# Check prerequisites
flux check --pre

# Verify GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

**Application Sync Issues:**
```bash
# Check sources
flux get sources git
flux logs --follow --level=error

# Force reconciliation
flux reconcile kustomization flux-system --with-source
```

**Permission Errors:**
```bash
# Check RBAC
kubectl get clusterroles | grep flux
kubectl describe clusterrolebinding flux-system
```

### Recovery Procedures

**Emergency Rollback:**
```bash
# Suspend FluxCD
flux suspend kustomization flux-system

# Restore ArgoCD (if backed up)
kubectl apply -f backup/argocd-applications-YYYYMMDD-HHMMSS.yaml
```

**Reset Migration:**
```bash
# Uninstall FluxCD
flux uninstall --namespace=flux-system

# Clean repository
git rm -r apps/argocd-flux/
git commit -m "Reset FluxCD migration"

# Start over
./migrate.sh install
```

## Logging and Monitoring

Scripts generate timestamped logs with color-coded output:
- 🟢 **GREEN**: Success messages and progress
- 🟡 **YELLOW**: Warnings (non-fatal issues)
- 🔴 **RED**: Errors (require attention)
- 🔵 **BLUE**: Information (status updates)

### Log Locations
- Migration logs: stdout/stderr (redirect as needed)
- FluxCD logs: `flux logs --follow`
- Kubernetes events: `kubectl get events --sort-by=.metadata.creationTimestamp`

### Monitoring Commands
```bash
# Watch FluxCD status
watch flux get all -A

# Monitor specific category
watch kubectl get kustomizations -A

# Check resource usage
kubectl top pods -n flux-system
```

## Best Practices

1. **Always backup** before making changes
2. **Test in non-production** first if possible
3. **Deploy incrementally** by category
4. **Validate thoroughly** at each step
5. **Monitor closely** for 24-48 hours post-migration
6. **Keep ArgoCD available** until confident in FluxCD
7. **Document** any custom configurations or workarounds

For detailed migration procedures, see the [Migration Guide](../docs/MIGRATION-GUIDE.md).