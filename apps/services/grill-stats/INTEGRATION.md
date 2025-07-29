# Integrating Grill Stats with Homelab

This document explains how to integrate the Grill Stats application with your existing homelab Kubernetes cluster.

## Integration Approach

The Grill Stats application has been structured to integrate seamlessly with your existing homelab setup using Kustomize and ArgoCD. The key components have been added to the following locations:

### Core Components

1. **Application Service**:
   - Added to `kustomize/base/core-services/grill-stats.yaml`
   - Included in the core-services kustomization

2. **Database**:
   - Added to `kustomize/base/databases/grill-stats-db.yaml`
   - Included in the databases kustomization

3. **Environment-Specific Configurations**:
   - Dev environment: `kustomize/overlays/dev/`
   - Staging environment: `kustomize/overlays/staging/`
   - Production environment: `kustomize/overlays/prod/`

## Integration Steps

### 1. Set up Container Registry Access

Create a Kubernetes secret for pulling from your Gitea registry:

```bash
kubectl create secret docker-registry gitea-registry \
  --namespace grill-stats \
  --docker-server=gitea-internal \
  --docker-username=your-gitea-username \
  --docker-password=your-gitea-password
```

Also create this secret in the dev and staging namespaces if needed.

### 2. Create Application Secrets

The application requires several secrets to function properly:

```bash
# API keys
kubectl create secret generic grill-stats-secrets \
  --namespace grill-stats \
  --from-literal=thermoworks-api-key=your-api-key \
  --from-literal=homeassistant-token=your-token

# Database credentials
kubectl create secret generic grill-stats-db-credentials \
  --namespace grill-stats \
  --from-literal=username=grill-admin \
  --from-literal=password=$(openssl rand -base64 20)
```

Repeat this process for each environment as needed.

### 3. Set Up ArgoCD

1. Copy the existing files to your homelab repository:
   ```bash
   cp -r kustomize/* /path/to/your/homelab/repo/apps/services/grill-stats/
   ```

2. Create an ArgoCD Application manifest (or add to your existing Application if using App of Apps pattern):
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: grill-stats
     namespace: argocd
   spec:
     project: default  # Use your ArgoCD project name
     source:
       repoURL: https://gitea-internal/lordmuffin/homelab.git
       targetRevision: HEAD
       path: apps/services/grill-stats
     destination:
       server: https://kubernetes.default.svc
       namespace: grill-stats
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
         - CreateNamespace=true
   ```

### 4. Customization Options

The Kustomize configuration allows for several customization options:

1. **Domain Names**:
   - Edit the `*-ingress-patch.yaml` files in each overlay to set the appropriate domain names.

2. **Resource Limits**:
   - Modify the resource patches in each overlay to adjust CPU and memory allocations.

3. **Sync Intervals**:
   - The `SYNC_INTERVAL` value can be adjusted in each overlay's configMapGenerator.

4. **Storage**:
   - The storage class in the PVC definition can be modified to match your cluster's available storage classes.

## Secrets Management

For production environments, consider using a more secure secrets management approach:

1. **External Secrets Operator**:
   - If you're using External Secrets Operator, create appropriate ExternalSecret resources.

2. **Sealed Secrets**:
   - If using Sealed Secrets, seal your secrets and include them in the repository.

3. **1Password Operator**:
   - If you're using the 1Password Operator, create OnePasswordItem resources.

## Health Monitoring

The application exposes a `/health` endpoint that can be used for liveness and readiness probes. The Kubernetes manifests already include appropriate probe configurations.

## Accessing the Application

Once deployed, the application will be available at:

- Production: https://grills.lab.apj.dev
- Staging: https://grills-staging.lab.apj.dev
- Development: https://grills-dev.lab.apj.dev

Adjust these URLs as needed to match your domain structure.
