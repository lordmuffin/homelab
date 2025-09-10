# ArgoCD to FluxCD Migration Guide

This guide covers the complete migration process from ArgoCD to FluxCD v2, including parallel operations, validation, and cutover procedures.

## Pre-Migration Checklist

### Infrastructure Readiness
- [ ] Kubernetes cluster healthy (>= v1.21)
- [ ] Sufficient cluster resources (CPU: 2 cores, Memory: 4GB minimum)
- [ ] Git repository access configured
- [ ] FluxCD CLI installed and verified
- [ ] GitHub/Git credentials configured
- [ ] Backup of existing ArgoCD applications
- [ ] Monitoring and alerting prepared

### ArgoCD Health Check
```bash
# Verify current ArgoCD health
kubectl get applications -n argocd
argocd app list
argocd app get argocd --show-params

# Export current state for backup
kubectl get applications -n argocd -o yaml > backup/argocd-applications.yaml
kubectl get appprojects -n argocd -o yaml > backup/argocd-projects.yaml
```

### Resource Assessment
```bash
# Check cluster resource usage
kubectl top nodes
kubectl top pods -A --sort-by=memory

# Identify high-resource applications
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount'
```

## Migration Strategy

### Strategy 1: Parallel Migration (Recommended)

**Benefits:**
- Zero downtime migration
- Easy rollback capability  
- Gradual risk management
- Production-safe approach

**Process:**
1. Install FluxCD alongside ArgoCD
2. Migrate applications category by category
3. Validate each category thoroughly  
4. Disable ArgoCD applications after validation
5. Complete cutover when confident

### Strategy 2: Blue-Green Migration

**Benefits:**
- Clean separation of environments
- Full validation before cutover
- Quick rollback if needed

**Process:**
1. Create separate cluster or namespace
2. Deploy complete FluxCD setup
3. Test thoroughly in isolation
4. Scheduled cutover with downtime window

## Phase 1: Parallel Setup

### 1.1 Install FluxCD (Keep ArgoCD Running)

```bash
# Bootstrap FluxCD
flux bootstrap github \
  --owner=lordmuffin \
  --repository=homelab \
  --branch=main \
  --path=apps/argocd-flux \
  --personal

# Verify both systems running
kubectl get pods -n argocd
kubectl get pods -n flux-system
```

### 1.2 Initial State Management

```bash
# Suspend FluxCD initially to prevent conflicts
flux suspend kustomization flux-system

# Enable core components only
kubectl apply -f apps/argocd-flux/flux-system/
kubectl apply -f apps/argocd-flux/sources/
kubectl apply -f apps/argocd-flux/namespaces/
kubectl apply -f apps/argocd-flux/rbac/
```

## Phase 2: Category-by-Category Migration

### 2.1 Core Infrastructure Migration

**Applications to Migrate:**
- ArgoCD itself (self-managing)
- 1Password operator
- CSI drivers  
- NVIDIA operators

```bash
# Enable core applications in FluxCD
flux resume kustomization core-apps

# Validate core health
./scripts/validate.sh core

# Disable ArgoCD equivalents (after validation)
argocd app sync argocd --dry-run  # Test first
argocd app delete argocd-core-apps --yes
```

### 2.2 Networking Migration

**Applications to Migrate:**
- Traefik (high priority - affects ingress)
- Cilium (CNI - be very careful)
- cert-manager 
- External DNS

```bash
# Pre-migration validation
kubectl get ingressroutes -A
kubectl get certificates -A

# Enable FluxCD networking
flux resume kustomization networking-apps

# Validate traffic flow
curl -k https://your-app.lab.apj.dev
kubectl get certificates --all-namespaces

# Disable ArgoCD networking (carefully!)
argocd app delete traefik --cascade=false  # Preserve resources
```

### 2.3 Monitoring Migration

**Applications to Migrate:**
- Prometheus stack
- Grafana
- Loki
- Alerting rules

```bash
# Enable FluxCD monitoring
flux resume kustomization monitoring-apps

# Validate metrics collection
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Check Prometheus targets at http://localhost:9090

# Validate Grafana dashboards
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Migrate after validation
argocd app delete prometheus-stack --cascade=false
```

### 2.4 Services Migration

**Applications to Migrate:**
- Homepage
- Development tools
- Productivity applications
- Media stack

```bash
# Lower risk applications - can migrate in batches
flux resume kustomization services-apps

# Validate application health
kubectl get ingresses -A
./scripts/validate.sh services

# Batch disable ArgoCD applications
argocd app delete homepage gitea n8n --yes
```

## Phase 3: Validation Procedures

### 3.1 Automated Validation

```bash
# Run comprehensive validation
./scripts/validate.sh all

# Check FluxCD health
flux get all -A

# Verify resource reconciliation
flux logs --follow --level=error
```

### 3.2 Application Health Checks

```bash
# Check application-specific health
kubectl get pods -A | grep -v Running
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20

# Validate ingress and certificates
kubectl get ingresses -A
kubectl get certificates -A --no-headers | grep -v True

# Test application functionality
curl -k https://traefik.lab.apj.dev
curl -k https://grafana.lab.apj.dev
```

### 3.3 Performance Validation

```bash
# Monitor resource usage
kubectl top nodes
kubectl top pods -A --sort-by=memory

# Check reconciliation performance
flux stats

# Validate sync times
kubectl get kustomizations -A -o wide
kubectl get helmreleases -A -o wide
```

## Phase 4: Cutover Procedures

### 4.1 Pre-Cutover Checklist

- [ ] All FluxCD applications healthy
- [ ] No pending reconciliations
- [ ] Performance metrics acceptable
- [ ] Team notified of cutover
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured

### 4.2 ArgoCD Graceful Shutdown

```bash
# Stop ArgoCD sync for remaining applications
argocd app sync --dry-run -l app.kubernetes.io/part-of=argocd

# Set applications to manual sync
argocd app set * --sync-policy=none

# Scale down ArgoCD components
kubectl scale deployment argocd-server --replicas=0 -n argocd
kubectl scale deployment argocd-repo-server --replicas=0 -n argocd  
kubectl scale statefulset argocd-application-controller --replicas=0 -n argocd

# Verify no interference
kubectl get pods -n argocd
```

### 4.3 FluxCD Full Activation

```bash
# Resume all FluxCD components
flux resume kustomization flux-system
flux get kustomizations -A

# Validate complete system
./scripts/validate.sh all
flux get all -A
```

## Phase 5: Post-Migration Operations

### 5.1 Cleanup Operations

```bash
# Remove ArgoCD applications (preserve resources)  
kubectl get applications -n argocd --no-headers | awk '{print $1}' | \
  xargs -I {} kubectl patch app {} -n argocd -p '{"metadata":{"finalizers":[]}}' --type=merge

kubectl delete applications --all -n argocd

# Optional: Remove ArgoCD entirely (when confident)
# kubectl delete namespace argocd
```

### 5.2 System Optimization

```bash
# Adjust sync intervals for production workloads
# Edit Kustomization intervals based on change frequency

# Fast-changing applications (5m)
kubectl patch kustomization homepage -n flux-system -p '{"spec":{"interval":"5m0s"}}' --type=merge

# Stable infrastructure (30m)  
kubectl patch kustomization core-apps -n flux-system -p '{"spec":{"interval":"30m0s"}}' --type=merge

# Enable notifications
flux create alert-provider webhook \
  --type=generic \
  --webhook-url=https://hooks.slack.com/...

flux create alert migrations \
  --provider-ref=webhook \
  --event-severity=error \
  --event-source='GitRepository/*,Kustomization/*,HelmRelease/*'
```

### 5.3 Documentation and Training

```bash
# Document custom configurations
kubectl get kustomizations -A -o yaml > docs/production-kustomizations.yaml
kubectl get helmreleases -A -o yaml > docs/production-helmreleases.yaml

# Create operational runbooks
cp docs/MAPPING-REFERENCE.md docs/OPERATIONS.md
```

## Rollback Procedures

### Emergency Rollback to ArgoCD

```bash
# Suspend FluxCD immediately
flux suspend kustomization flux-system
kubectl scale deployment source-controller --replicas=0 -n flux-system
kubectl scale deployment kustomize-controller --replicas=0 -n flux-system

# Restore ArgoCD
kubectl scale deployment argocd-server --replicas=1 -n argocd
kubectl scale deployment argocd-repo-server --replicas=1 -n argocd
kubectl scale statefulset argocd-application-controller --replicas=1 -n argocd

# Restore ArgoCD applications
kubectl apply -f backup/argocd-applications.yaml
argocd app sync --dry-run  # Validate first
```

### Partial Rollback (Category-Specific)

```bash
# Suspend specific FluxCD category
flux suspend kustomization networking-apps

# Re-enable ArgoCD for that category
argocd app sync traefik cilium cert-manager
```

## Monitoring and Alerting

### FluxCD Native Monitoring

```bash
# Monitor reconciliation status
watch flux get all -A

# Check reconciliation logs
flux logs --follow --level=info

# Performance metrics
kubectl port-forward -n flux-system svc/source-controller 8080:8080
# Metrics at http://localhost:8080/metrics
```

### Integration with Existing Monitoring

```yaml
# Add FluxCD ServiceMonitor to Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: flux-system
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: source-controller
  endpoints:
  - port: http-prom
```

## Troubleshooting Guide

### Common Issues and Resolutions

**Issue: Resource Conflicts**
```bash
# Symptom: "resource already exists" errors
# Resolution: Add resource management annotations
kubectl annotate kustomization app-name -n flux-system \
  kustomize.toolkit.fluxcd.io/force=enabled
```

**Issue: Sync Failures**
```bash  
# Symptom: Applications not syncing from Git
# Resolution: Check source and path
flux get sources git
kubectl describe gitrepository homelab-main -n flux-system
```

**Issue: Helm Releases Failing**
```bash
# Symptom: HelmRelease in failed state
# Resolution: Check Helm-specific issues
kubectl describe helmrelease traefik -n flux-system
flux logs --level=error | grep -i helm
```

**Issue: Performance Degradation**
```bash
# Symptom: Slow reconciliation or high resource usage
# Resolution: Optimize intervals and resource limits
kubectl top pods -n flux-system
# Adjust interval and timeout values
```

For detailed troubleshooting, see the [Mapping Reference](./MAPPING-REFERENCE.md) for specific conversion patterns.