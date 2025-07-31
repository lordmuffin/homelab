# KASM Deployment Solution: Resolving Resource Conflicts

## Problem Summary

The original KASM setup had two ArgoCD applications (`kasm.yaml` and `kasm-utils.yaml`) trying to manage overlapping Kubernetes resources, causing sync conflicts. Both applications attempted to manage the same namespace, secrets, configmaps, and deployments.

## Root Cause

- **Resource Ownership Conflicts**: ArgoCD couldn't determine which application should own shared resources
- **Deployment Dependencies**: Patches and utilities needed to run after the base Helm chart deployment
- **Sync Race Conditions**: Both applications would sync simultaneously, causing conflicts

## Solutions Provided

### Solution 1: Unified Application with Multiple Sources (Recommended)

**File**: `kasm-unified.yaml`

This approach uses ArgoCD's Multiple Sources feature to deploy both the Helm chart and utilities from a single application:

- **Source 1**: KASM Helm chart (provides base deployment)
- **Source 2**: Git repository with patches and utilities
- **Benefits**: 
  - Single resource ownership
  - Unified sync policy
  - Comprehensive ignoreDifferences configuration
  - Server-side apply for better conflict resolution

### Solution 2: App-of-Apps Pattern with Sync Waves

**Files**: 
- `kasm-app-of-apps.yaml` (parent application)
- `overlays/kasm-apps/kasm-base-app.yaml` (Helm chart)
- `overlays/kasm-apps/kasm-utils-app.yaml` (utilities)

This approach uses explicit sync waves to control deployment order:

- **Wave 0**: Deploy KASM Helm chart
- **Wave 1**: Apply patches and utilities
- **Benefits**: 
  - Clear deployment ordering
  - Explicit dependency management
  - Better troubleshooting visibility

## Key Improvements Made

### 1. Sync Wave Annotations

Added proper sync wave annotations to resources:

```yaml
# Wave -1: Prerequisites (storage, RBAC, secrets)
- persistent-volume.yaml
- rbac.yaml
- secrets.yaml

# Wave 0: Core application (Helm chart)
# Automatically handled by ArgoCD

# Wave 1: Custom routing and ingress
- ingressroute.yaml

# Wave 2: Database initialization jobs
- api-init-job.yaml
- db-label-job.yaml

# Wave 3: Application configuration jobs
- kasm-db-complete-init-job.yaml
- kasm-secrets-sync-job.yaml

# Wave 4: Post-deployment fixes
- kasm-admin-password-fix-job.yaml
```

### 2. Enhanced ignoreDifferences

Comprehensive ignoreDifferences configuration to prevent spurious sync issues:

```yaml
ignoreDifferences:
  # Secrets managed externally
  - group: ""
    kind: Secret
    name: kasm-secrets
    namespace: kasm
  
  # Jobs that may be recreated
  - group: "batch"
    kind: Job
    name: "*"
    namespace: kasm
    jsonPointers:
    - /status
  
  # Deployments that may be patched
  - group: "apps"
    kind: Deployment
    name: "*"
    namespace: kasm
    jsonPointers:
    - /spec/template/spec/containers/*/env
```

### 3. Strategic Merge Patches

Updated kustomization.yaml to use strategic merge patches for better conflict resolution:

```yaml
patchesStrategicMerge:
  - |
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: kasm-api-deployment
      annotations:
        argocd.argoproj.io/sync-wave: "2"
    $patch: replace
```

### 4. Server-Side Apply

Enabled server-side apply for better conflict resolution:

```yaml
syncOptions:
  - ServerSideApply=true
  - RespectIgnoreDifferences=true
```

## Migration Steps

### For Unified Application Approach:

1. **Deploy the unified application**:
   ```bash
   kubectl apply -f apps/argocd-cloud/base/services/kasm-unified.yaml
   ```

2. **Verify deployment order**:
   - Watch ArgoCD UI for sync waves progression
   - Ensure Helm chart deploys first, then utilities

3. **Remove old applications** (after verification):
   ```bash
   kubectl delete application kasm -n argocd
   kubectl delete application kasm-utils -n argocd
   ```

### For App-of-Apps Approach:

1. **Deploy the app-of-apps**:
   ```bash
   kubectl apply -f apps/argocd-cloud/base/services/kasm-app-of-apps.yaml
   ```

2. **Monitor sync waves**:
   - Wave 0: kasm-base application
   - Wave 1: kasm-utils application

## Benefits Achieved

✅ **Eliminated Resource Conflicts**: Single source of truth for resource ownership  
✅ **Proper Dependency Management**: Sync waves ensure correct deployment order  
✅ **Better Error Handling**: Comprehensive ignoreDifferences prevent false positives  
✅ **Improved Stability**: Server-side apply reduces sync conflicts  
✅ **Cleaner Architecture**: Modern ArgoCD best practices  
✅ **Easier Maintenance**: Single application to manage instead of two  

## Monitoring and Troubleshooting

### Key Metrics to Watch:

1. **Sync Status**: All resources should sync without conflicts
2. **Health Status**: Applications should report healthy
3. **Sync Waves**: Observe proper wave progression in ArgoCD UI
4. **Resource Drift**: ignoreDifferences should prevent spurious diffs

### Common Issues:

- **Sync Wave Timing**: Increase delays if resources aren't ready
- **Patch Conflicts**: Check strategic merge vs JSON patch format
- **Health Checks**: Ensure resource health checks are properly configured

## Recommendation

**Use the Unified Application approach** (`kasm-unified.yaml`) as it:
- Simplifies management with a single application
- Leverages ArgoCD's modern Multiple Sources feature
- Provides better resource ownership semantics
- Reduces operational complexity

The App-of-Apps approach is available as an alternative if you need more explicit control over individual application lifecycles.