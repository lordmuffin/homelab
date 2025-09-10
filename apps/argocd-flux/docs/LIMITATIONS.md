# ArgoCD to FluxCD Migration Limitations and Workarounds

This document outlines known limitations when migrating from ArgoCD to FluxCD v2, along with suggested workarounds and alternative approaches.

## Feature Parity Analysis

### ✅ Fully Supported Features

| ArgoCD Feature | FluxCD Equivalent | Status |
|---------------|-------------------|---------|
| Git-based Applications | GitRepository + Kustomization | ✅ Full parity |
| Helm Applications | HelmRepository + HelmRelease | ✅ Full parity |
| Automated Sync | interval-based reconciliation | ✅ Full parity |
| Manual Sync | flux reconcile commands | ✅ Full parity |
| Health Checks | healthChecks field | ✅ Full parity |
| Sync Hooks (limited) | dependsOn ordering | ✅ Basic support |
| Resource Pruning | prune: true | ✅ Full parity |
| Rollback | Git revert + Helm rollback | ✅ Full parity |
| Multi-tenancy | RBAC + namespaces | ✅ Full parity |

### ⚠️ Partially Supported Features

| ArgoCD Feature | FluxCD Limitation | Workaround |
|---------------|-------------------|------------|
| ApplicationSets | No direct equivalent | Multiple Kustomizations + templating |
| Custom Health Checks | Limited resource types | Use standard K8s health + external monitoring |
| Resource Hooks (advanced) | Basic ordering only | Use Job resources + dependsOn |
| Wave Sync | No sync waves | Use dependsOn chains for ordering |
| Server-Side Apply | Via Kustomize patches | Add SSA patches where needed |
| Ignore Differences (complex) | Basic ignore annotations | Use postRenderers + Kustomize |

### ❌ Not Supported / Major Differences

| ArgoCD Feature | FluxCD Status | Alternative |
|---------------|---------------|-------------|
| ArgoCD UI | No equivalent | Use CLI + Kubernetes dashboard + monitoring |
| Resource Actions | Not supported | Use kubectl directly or automation |
| Cluster Secrets | Different model | Bootstrap handles credentials |
| App-of-Apps Pattern | Different approach | Directory structure + multiple sources |
| Sync Status API | Different API | Use FluxCD APIs and conditions |
| Repository Webhooks (advanced) | Basic webhook support | Use polling intervals or GitHub Actions |

## Specific Migration Challenges

### 1. ApplicationSets to FluxCD

**Challenge:** ArgoCD ApplicationSets provide templated multi-application deployment.

**ArgoCD Example:**
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
  template:
    spec:
      project: services
      source:
        repoURL: '{{.path.repoURL}}'
        path: '{{.path.path}}'
```

**FluxCD Workaround:**
Create individual Kustomizations for each service:
```yaml
# Generate via script or manually
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: service-homepage
spec:
  path: ./apps/services/homepage
  # ... rest of config

---
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization  
metadata:
  name: service-gitea
spec:
  path: ./apps/services/gitea
  # ... rest of config
```

### 2. Complex Ignore Differences

**Challenge:** ArgoCD's ignoreDifferences supports complex JSONPath expressions.

**ArgoCD Example:**
```yaml
ignoreDifferences:
- group: ""
  kind: Secret
  name: kasm-secrets
  jsonPointers:
  - /data/password
  - /stringData
```

**FluxCD Workaround:**
Use postRenderers with Kustomize patches:
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

### 3. Sync Waves and Hooks

**Challenge:** ArgoCD sync waves and hooks provide fine-grained deployment ordering.

**ArgoCD Example:**
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"
    argocd.argoproj.io/hook: PreSync
```

**FluxCD Workaround:**
Use dependsOn for ordering:
```yaml
spec:
  dependsOn:
    - name: database-setup
      namespace: flux-system
```

### 4. Custom Health Checks

**Challenge:** ArgoCD supports custom health check scripts for any resource.

**ArgoCD Example:**
```yaml
# Custom health check script in ConfigMap
apiVersion: v1
kind: ConfigMap
data:
  health.lua: |
    if obj.status.phase == "Running" then
      return {status = "Healthy"}
    end
```

**FluxCD Workaround:**
Use standard healthChecks with common resource types:
```yaml
healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: my-app
    namespace: default
```
For complex health checks, use external monitoring and alerting.

## Operational Differences

### UI and Visualization

**ArgoCD Advantage:**
- Rich web UI for application management
- Visual dependency graphs  
- Real-time sync status
- Resource tree visualization
- Diff view for changes

**FluxCD Reality:**
- CLI-based management (`flux` command)
- Kubernetes-native resources (use kubectl)
- Integration with monitoring tools (Prometheus, Grafana)
- VSCode extension available
- Third-party UIs (Weave GitOps)

**Recommendation:**
- Set up comprehensive monitoring dashboards
- Use Grafana for FluxCD metrics visualization
- Consider Weave GitOps for UI needs
- Implement alerting for sync failures

### Debugging and Troubleshooting

**ArgoCD Approach:**
```bash
argocd app get myapp
argocd app sync myapp --dry-run
argocd app logs myapp
```

**FluxCD Approach:**
```bash
flux get kustomization myapp
kubectl describe kustomization myapp -n flux-system
flux logs --follow --level=error
```

### Repository Management

**ArgoCD:**
- Centralized repository configuration
- Built-in credential management
- Repository health monitoring

**FluxCD:**
- GitRepository/HelmRepository resources
- Bootstrap manages main repository
- Additional repos configured as needed

## Performance Considerations

### Resource Usage

**ArgoCD:**
- Single application controller
- Can be resource-intensive with many apps
- Memory usage grows with app count

**FluxCD:**
- Multiple specialized controllers
- Better resource isolation
- More efficient at scale

**Recommendations:**
- Monitor controller resource usage
- Adjust reconciliation intervals appropriately
- Use horizontal pod autoscaling if needed

### Sync Frequency

**ArgoCD:**
- Manual sync + automated sync
- Webhook support for instant sync
- Refresh intervals configurable

**FluxCD:**
- Interval-based reconciliation
- Webhook support (basic)
- Git polling intervals

**Best Practices:**
- Set appropriate intervals per application type:
  - Infrastructure: 30m
  - Applications: 10m
  - Development: 5m
- Use webhooks where possible
- Monitor sync performance

## Security Considerations

### RBAC Model

**ArgoCD:**
- AppProject-based RBAC
- User/group access controls
- Resource whitelisting

**FluxCD:**
- Kubernetes-native RBAC
- Service account based
- Namespace isolation

**Migration Notes:**
- Map AppProjects to RBAC policies
- Use namespace labels for categorization
- Implement NetworkPolicies for isolation

### Credential Management

**ArgoCD:**
- Built-in repository credentials
- Cluster connection secrets
- User authentication

**FluxCD:**
- Bootstrap handles main repository
- Standard Kubernetes secrets
- Service account tokens

## Recommended Workarounds

### 1. ApplicationSet Replacement Script

Create a script to generate multiple Kustomizations:

```bash
#!/bin/bash
# generate-services.sh
SERVICES_DIR="apps/services"
OUTPUT_DIR="apps/argocd-flux/apps/services"

for service_dir in "$SERVICES_DIR"/*; do
  if [[ -d "$service_dir" ]]; then
    service_name=$(basename "$service_dir")
    
    cat > "$OUTPUT_DIR/${service_name}-app.yaml" << EOF
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: service-${service_name}
  namespace: flux-system
spec:
  interval: 10m0s
  path: ./apps/services/${service_name}
  prune: true
  sourceRef:
    kind: GitRepository
    name: homelab-main
  targetNamespace: ${service_name}
EOF
  fi
done
```

### 2. Health Check Aggregation

Use a monitoring solution to aggregate health:

```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-health
spec:
  selector:
    matchLabels:
      app: my-application
  endpoints:
  - port: http-metrics
    path: /health
```

### 3. Complex Ordering

For complex dependencies, use multiple layers:

```yaml
# Layer 1: Infrastructure
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: infra-layer
spec:
  # ... config

---
# Layer 2: Applications (depends on infra)
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: apps-layer
spec:
  dependsOn:
    - name: infra-layer
  # ... config
```

## Migration Strategy Recommendations

### 1. Phased Approach
- Start with least critical applications
- Validate each category before proceeding
- Keep ArgoCD running in parallel initially

### 2. Comprehensive Testing
- Test in non-production environment first
- Validate all application functionality
- Performance test with full workload

### 3. Monitoring and Alerting
- Set up FluxCD metrics monitoring
- Create alerts for sync failures
- Monitor resource usage changes

### 4. Team Training
- Train team on FluxCD CLI and concepts
- Document new operational procedures
- Create troubleshooting runbooks

### 5. Gradual Feature Adoption
- Start with basic FluxCD features
- Add advanced features incrementally
- Consider third-party tools for missing functionality

For implementation details and examples, see the [Mapping Reference](./MAPPING-REFERENCE.md).