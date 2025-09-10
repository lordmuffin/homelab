# FluxCD v2 Installation Guide

This guide provides step-by-step instructions for installing FluxCD v2 and migrating from your existing ArgoCD setup.

## Prerequisites

- Kubernetes cluster (v1.21+)
- `kubectl` configured with cluster access
- `flux` CLI installed (v2.0.0+)
- Git access to your homelab repository
- GitHub personal access token with repo permissions

### Install FluxCD CLI

```bash
# Install flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Verify installation
flux --version
```

## Phase 1: FluxCD Bootstrap

### 1.1 Prepare GitHub Repository

```bash
# Create GitHub token with full repo permissions
export GITHUB_TOKEN=<your-token>
export GITHUB_USER=lordmuffin
export GITHUB_REPO=homelab
```

### 1.2 Bootstrap FluxCD

```bash
# Bootstrap FluxCD to your cluster
flux bootstrap github \
  --owner=$GITHUB_USER \
  --repository=$GITHUB_REPO \
  --branch=main \
  --path=apps/argocd-flux \
  --personal \
  --components-extra=image-reflector-controller,image-automation-controller
```

This will:
- Install FluxCD components in `flux-system` namespace
- Create deploy key in GitHub repository
- Configure FluxCD to sync from `apps/argocd-flux` path
- Enable image automation (optional)

### 1.3 Verify Bootstrap

```bash
# Check FluxCD components
kubectl get pods -n flux-system

# Verify GitRepository sync
flux get sources git

# Check initial Kustomization
flux get kustomizations
```

## Phase 2: Initial Deployment

### 2.1 Deploy Core Components

The FluxCD system will automatically detect and apply the converted manifests:

```bash
# Monitor deployment
watch kubectl get kustomizations -A

# Check application status  
flux get helmreleases -A
flux get kustomizations -A
```

### 2.2 Verify Namespace Creation

```bash
# Core namespaces should be created
kubectl get namespaces | grep -E "(traefik|cert-manager|monitoring)"
```

### 2.3 Check RBAC Policies

```bash
# Verify FluxCD RBAC
kubectl get clusterroles | grep flux
kubectl get clusterrolebindings | grep flux
```

## Phase 3: Application Migration Strategy

### 3.1 Phased Migration Approach

**Option A: Parallel Run (Recommended)**
1. Keep ArgoCD running alongside FluxCD
2. Migrate applications category by category
3. Validate each category before proceeding  
4. Gradually disable ArgoCD applications

**Option B: Big Bang Migration**
1. Scale down ArgoCD
2. Deploy all FluxCD applications at once
3. Validate and fix issues

### 3.2 Migration Order (Recommended)

1. **Core Infrastructure** (ArgoCD, 1Password, CSI drivers)
2. **Networking** (Traefik, Cilium, cert-manager)
3. **Monitoring** (Prometheus, Grafana)
4. **Services** (Applications and utilities)
5. **Specialized** (ML/AI, Matrix, Media)

### 3.3 Enable Applications Gradually

Edit `/apps/argocd-flux/kustomization.yaml` to enable categories:

```yaml
resources:
  # Start with these
  - apps/core/
  - apps/networking/
  - apps/monitoring/
  
  # Add gradually  
  # - apps/services/
  # - apps/data/
  # - apps/utilities/
```

## Phase 4: ArgoCD Transition

### 4.1 Monitor Both Systems

```bash
# ArgoCD applications
kubectl get applications -n argocd

# FluxCD resources
flux get all -A
```

### 4.2 Validate Application Health

```bash
# Use provided validation script
./scripts/validate.sh

# Manual health checks
kubectl get pods -A | grep -v Running
kubectl get events --sort-by=.metadata.creationTimestamp
```

### 4.3 Disable ArgoCD Applications

Once FluxCD applications are healthy:

```bash
# Scale down ArgoCD (optional)
kubectl scale deployment argocd-server --replicas=0 -n argocd
kubectl scale deployment argocd-repo-server --replicas=0 -n argocd
kubectl scale statefulset argocd-application-controller --replicas=0 -n argocd
```

## Phase 5: Cleanup and Optimization

### 5.1 Remove ArgoCD Resources (When Ready)

```bash
# Remove ArgoCD applications (preserve resources)
kubectl patch app argocd -n argocd -p '{"metadata":{"finalizers":[]}}' --type=merge
kubectl delete applications --all -n argocd

# Optionally remove ArgoCD entirely
kubectl delete namespace argocd
```

### 5.2 Optimize FluxCD Configuration

```bash
# Adjust sync intervals for production
# Edit individual Kustomization/HelmRelease intervals

# Enable notifications (optional)
flux create alert-provider slack \
  --type=slack \
  --webhook-url=$SLACK_WEBHOOK

flux create alert flux-system \
  --provider-ref=slack \
  --event-severity=info \
  --event-source='GitRepository/*,Kustomization/*,HelmRelease/*'
```

## Troubleshooting

### Common Issues

**FluxCD Bootstrap Fails**
```bash
# Check prerequisites
flux check --pre

# Verify GitHub token permissions
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

**Applications Not Syncing**
```bash
# Check source repositories
flux get sources git
flux logs --follow --level=error

# Verify paths exist in repository
ls -la apps/argocd-flux/
```

**Resource Conflicts**  
```bash
# Check for resource conflicts with ArgoCD
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20

# Force reconciliation
flux reconcile kustomization flux-system --with-source
```

### Recovery Procedures

**Rollback FluxCD Changes**
```bash
# Suspend FluxCD (emergency)
flux suspend kustomization flux-system

# Restore from backup (if available)
kubectl apply -f backup/argocd-applications.yaml
```

**Reset FluxCD Bootstrap**
```bash
# Uninstall FluxCD
flux uninstall --namespace=flux-system

# Remove from Git
git rm -r apps/argocd-flux/
git commit -m "Remove FluxCD migration"

# Re-bootstrap with fixes
flux bootstrap github ...
```

## Validation Commands

```bash
# Health check script  
./scripts/validate.sh

# Manual validation
flux get all -A
kubectl get pods -A | grep -v Running
kubectl top nodes
kubectl top pods -A --sort-by=memory

# Performance monitoring
kubectl get events --sort-by=.metadata.creationTimestamp | tail -50
```

## Next Steps

1. **Monitor** applications for 24-48 hours
2. **Tune** sync intervals based on change frequency  
3. **Enable** alerting and notifications
4. **Document** any custom configurations or workarounds
5. **Train** team on FluxCD operations and troubleshooting

For operational procedures, see the [Migration Guide](./MIGRATION-GUIDE.md).