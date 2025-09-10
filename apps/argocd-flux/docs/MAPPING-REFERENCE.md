# ArgoCD to FluxCD Mapping Reference

This document provides detailed mappings between ArgoCD and FluxCD concepts, with specific examples from your homelab conversion.

## Core Concept Mappings

### Application Types

| ArgoCD Pattern | FluxCD Pattern | Use Case |
|---------------|----------------|----------|
| Application (Git + Kustomize) | GitRepository + Kustomization | Raw Kubernetes YAML |
| Application (Git + Helm) | GitRepository + HelmRelease | Git-stored Helm charts |
| Application (Helm Registry) | HelmRepository + HelmRelease | Public/private Helm repos |
| ApplicationSet | GitRepository + Kustomization (templated) | Multi-app/cluster deployments |

### Resource Organization

| ArgoCD Concept | FluxCD Equivalent | Purpose |
|----------------|-------------------|---------|
| AppProject | RBAC + Namespace Labels | Security boundaries |
| Application | Kustomization/HelmRelease | Application deployment |
| Repository | GitRepository/HelmRepository | Source configuration |
| Cluster | Kustomization targetNamespace | Deployment target |

## Detailed Conversion Examples

### 1. Git-based Applications

**ArgoCD Application (Original):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: homepage
spec:
  project: apps
  source:
    repoURL: 'https://github.com/lordmuffin/homelab.git'
    path: apps/services/homepage
    targetRevision: main
  destination:
    namespace: homepage
    name: in-cluster
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: true
    syncOptions:
    - CreateNamespace=true
    - Validate=false
    retry:
      limit: 5
      backoff:
        duration: 20s
        factor: 2
        maxDuration: 15m
```

**FluxCD Conversion:**
```yaml
# GitRepository (shared across multiple apps)
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: GitRepository
metadata:
  name: homelab-main
  namespace: flux-system
spec:
  interval: 1m0s
  ref:
    branch: main
  url: https://github.com/lordmuffin/homelab.git

---
# Kustomization (per application)
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: homepage
  namespace: flux-system
spec:
  interval: 10m0s
  path: ./apps/services/homepage
  prune: true
  sourceRef:
    kind: GitRepository
    name: homelab-main
  targetNamespace: homepage
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: homepage
      namespace: homepage
  retryInterval: 2m0s
  timeout: 15m0s
  patches:
    - patch: |
        apiVersion: v1
        kind: Namespace
        metadata:
          name: homepage
          labels:
            managed-by: flux
      target:
        kind: Namespace
        name: homepage
```

### 2. Helm Applications

**ArgoCD Application (Original):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: traefik
spec:
  project: networking
  source:
    repoURL: https://traefik.github.io/charts
    chart: traefik
    targetRevision: v26.0.0
    helm:
      values: |
        deployment:
          replicas: 5
        service:
          type: LoadBalancer
  destination:
    namespace: traefik
    name: in-cluster
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
```

**FluxCD Conversion:**
```yaml
# HelmRepository
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: traefik
  namespace: flux-system
spec:
  interval: 10m0s
  url: https://traefik.github.io/charts

---
# HelmRelease  
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: traefik
  namespace: flux-system
spec:
  interval: 10m0s
  chart:
    spec:
      chart: traefik
      version: '26.0.0'
      sourceRef:
        kind: HelmRepository
        name: traefik
  targetNamespace: traefik
  createNamespace: true
  values:
    deployment:
      replicas: 5
    service:
      type: LoadBalancer
  upgrade:
    remediation:
      retries: 5
      remediateLastFailure: true
```

### 3. AppProject to RBAC

**ArgoCD AppProject (Original):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: core
spec:
  description: Core Project
  sourceRepos:
  - '*'
  destinations:
  - namespace: kube-system
    server: https://kubernetes.default.svc
  - namespace: argocd
    server: https://kubernetes.default.svc
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
```

**FluxCD Conversion:**
```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: flux-core-sa
  namespace: flux-system

---
# ClusterRole (scoped to needed permissions)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: flux-core-role
rules:
  - apiGroups: ["*"]
    resources: ["*"] 
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: flux-core-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: flux-core-role
subjects:
  - kind: ServiceAccount
    name: flux-core-sa
    namespace: flux-system
```

## Sync Policy Mappings

| ArgoCD Sync Option | FluxCD Equivalent | Notes |
|-------------------|-------------------|-------|
| `automated: prune: true` | `prune: true` | Direct mapping |
| `automated: selfHeal: true` | `interval: 10m0s` | Continuous reconciliation |
| `automated: allowEmpty: true` | `force: false` | Allow empty applications |
| `CreateNamespace=true` | `createNamespace: true` | HelmRelease only |
| `CreateNamespace=true` | `patches:` (namespace creation) | Kustomization |
| `Validate=false` | No equivalent | FluxCD validates by default |
| `Prune=true` | `prune: true` | Direct mapping |
| `PruneLast=true` | Default behavior | FluxCD prunes after apply |
| `ApplyOutOfSyncOnly=false` | Default behavior | FluxCD behavior |
| `ServerSideApply=true` | `patches:` with SSA | Via Kustomize patches |

## Retry and Backoff Mappings

| ArgoCD Pattern | FluxCD Equivalent | Example |
|---------------|-------------------|---------|
| `retry: limit: 5` | `upgrade: remediation: retries: 5` | HelmRelease |
| `retry: backoff: duration: 20s` | `retryInterval: 20s` | Kustomization |
| `retry: backoff: factor: 2` | Default exponential backoff | Built-in behavior |
| `retry: backoff: maxDuration: 15m` | `timeout: 15m0s` | Maximum wait time |

## Health Check Mappings

| ArgoCD Feature | FluxCD Equivalent | Usage |
|----------------|-------------------|-------|
| Built-in health checks | `healthChecks:` | Explicit configuration |
| Custom health scripts | Not supported | Use readiness/liveness probes |
| `ignoreDifferences:` | `postRenderers:` + patches | Via Kustomize |
| Resource hooks | `dependsOn:` | Ordering dependencies |

## Advanced Features

### 1. Ignore Differences

**ArgoCD:**
```yaml
ignoreDifferences:
- group: ""
  kind: Secret
  name: kasm-secrets
  jsonPointers:
  - /data
```

**FluxCD:**
```yaml
postRenderers:
  - kustomize:
      patches:
        - target:
            kind: Secret
            name: kasm-secrets
          patch: |
            - op: add
              path: /metadata/annotations/flux.weave.works~1ignore
              value: "true"
```

### 2. Multi-Source Applications

**ArgoCD ApplicationSet Pattern:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: services
spec:
  generators:
  - git:
      repoURL: https://github.com/lordmuffin/homelab.git
      directories:
      - path: apps/services/*
```

**FluxCD Equivalent:**
```yaml
# Multiple Kustomizations (one per service)
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: services-homepage
spec:
  path: ./apps/services/homepage
  # ... rest of config

---
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2  
kind: Kustomization
metadata:
  name: services-gitea
spec:
  path: ./apps/services/gitea
  # ... rest of config
```

## CLI Command Mappings

| ArgoCD CLI | FluxCD CLI | Purpose |
|-----------|------------|---------|
| `argocd app list` | `flux get kustomizations -A` | List applications |
| `argocd app get <app>` | `flux get kustomization <app>` | App details |
| `argocd app sync <app>` | `flux reconcile kustomization <app>` | Force sync |
| `argocd app diff <app>` | `kubectl diff -f <path>` | Show differences |
| `argocd app delete <app>` | `flux delete kustomization <app>` | Delete app |
| `argocd app set <app> --sync-policy none` | `flux suspend kustomization <app>` | Disable sync |
| `argocd repo list` | `flux get sources git` | List repositories |
| `argocd proj list` | No direct equivalent | RBAC is separate |

## Best Practices Translation

| ArgoCD Best Practice | FluxCD Equivalent |
|---------------------|-------------------|
| Use AppProjects for RBAC | Use namespace isolation + RBAC |
| Sync waves for ordering | Use `dependsOn` in Kustomizations |
| Resource hooks for jobs | Use Flux `dependsOn` + Job resources |
| Ignore differences for externally managed resources | Use `postRenderers` with ignore annotations |
| ApplicationSets for multiple apps | Multiple Kustomizations or templating |
| Repository secrets | FluxCD handles automatically via bootstrap |
| Custom health checks | Use `healthChecks` with explicit resources |
| Rollback capabilities | GitOps revert + Helm rollback |

## Performance Considerations

| Aspect | ArgoCD | FluxCD | Recommendation |
|--------|--------|--------|---------------|
| Sync Frequency | Manual + automated | Interval-based | Adjust intervals per app type |
| Repository Polling | Webhook + periodic | Interval-based | Use webhooks when possible |
| Resource Usage | Single controller | Multiple specialized controllers | Monitor controller resources |
| Parallel Operations | Limited | Native support | Leverage parallelism |
| Large Applications | Can be slow | Optimized for scale | Break into smaller apps |

This mapping should cover most conversion scenarios. For edge cases not covered here, consult the FluxCD documentation or create custom solutions using the patterns shown above.