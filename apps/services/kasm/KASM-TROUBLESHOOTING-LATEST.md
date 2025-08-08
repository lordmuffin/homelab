# KASM Troubleshooting Guide - Latest

## 📋 Document Overview

**Date**: 2025-07-31T10:57:00Z  
**Status**: 🔧 ACTIVE TROUBLESHOOTING  
**Scope**: Comprehensive KASM deployment troubleshooting and resolution  
**Environment**: Kubernetes with ArgoCD, OnePassword integration  

---

## 🚨 Current Critical Issues

### Active Problems (as of latest check)
- ❌ **kasm-api-deployment**: CrashLoopBackOff (5 restarts)
- ❌ **kasm-admin-password-fix-job**: CreateContainerConfigError
- ❌ **kasm-db-permissions-job**: CreateContainerConfigError  
- ❌ **kasm-db-user-setup-job**: CreateContainerConfigError
- ❌ **Multiple deployments**: Stuck in Init container stages
- ✅ **kasm-database**: Running (PostgreSQL operational)
- ✅ **kasm-redis**: Running (Redis operational)

### Severity Assessment
- **High**: API deployment failures (service unavailable)
- **Medium**: Database job failures (setup incomplete)
- **Low**: Some initialization jobs (may be one-time)

---

## 🔍 Root Cause Analysis

### Primary Issues Identified

#### 1. Secret Name Mismatch (PARTIALLY RESOLVED)
**Problem**: Pods reference `kasm-database-postgres-creds` but secret is `kasm-db-postgres-creds`
**Status**: Alias created but issues persist
**Impact**: CreateContainerConfigError across multiple components

**Evidence**:
```yaml
# Expected by pods:
secretKeyRef:
  name: kasm-database-postgres-creds
  key: db-password

# Actual secret name:
metadata:
  name: kasm-db-postgres-creds
```

#### 2. Database Authentication Failures
**Problem**: SQLAlchemy connection errors due to credential mismatches
**Status**: Ongoing after secret fix
**Impact**: API pods crash with authentication errors

**Error Pattern**:
```
sqlalchemy.exc.OperationalError: connection to server at "db" failed: 
FATAL: password authentication failed for user "kasmapp"
```

#### 3. OnePassword Integration Issues
**Problem**: Secret synchronization timing and dependency issues
**Status**: Secrets exist but references fail
**Impact**: Jobs cannot access required credentials

#### 4. Init Container Dependencies
**Problem**: Init containers wait for conditions that may not be met
**Status**: Multiple deployments stuck in Init stages
**Impact**: Services never reach running state

#### 5. ArgoCD Sync Wave Conflicts
**Problem**: Resource creation order causes dependency failures
**Status**: Wave annotations may not be sufficient
**Impact**: Resources created before dependencies are ready

---

## 🛠️ Troubleshooting Workflow

### Phase 1: Immediate Assessment (5 minutes)

#### Step 1: Check Pod Status
```bash
# Get current pod status
kubectl get pods -n kasm

# Look for these patterns:
# - CrashLoopBackOff
# - CreateContainerConfigError  
# - Init:0/X (stuck init containers)
# - ImagePullBackOff
```

#### Step 2: Identify Failed Components
```bash
# Check failing pods details
kubectl describe pod <pod-name> -n kasm

# Look for:
# - Event messages
# - Container exit codes
# - Secret/ConfigMap references
# - Resource requests/limits
```

#### Step 3: Secret Verification
```bash
# Verify critical secrets exist
kubectl get secrets -n kasm | grep -E "(kasm-db|kasm-secrets|kasm-database)"

# Check secret data completeness
kubectl describe secret kasm-db-postgres-creds -n kasm
kubectl describe secret kasm-database-postgres-creds -n kasm
kubectl describe secret kasm-secrets -n kasm
```

### Phase 2: Deep Diagnosis (15 minutes)

#### Step 4: Container Log Analysis
```bash
# API deployment logs
kubectl logs deployment/kasm-api-deployment -n kasm --previous

# Job logs (if running)
kubectl logs job/kasm-admin-password-fix-job -n kasm
kubectl logs job/kasm-db-permissions-job -n kasm
kubectl logs job/kasm-db-user-setup-job -n kasm

# Init container logs
kubectl logs <pod-name> -c <init-container-name> -n kasm
```

#### Step 5: Database Connectivity Test
```bash
# Test database connection from a debug pod
kubectl run debug-pod --rm -it --image=postgres:13 -n kasm -- bash

# Inside the pod:
PGPASSWORD=<password> psql -h db -U kasmapp -d kasm -c "SELECT 1;"
```

#### Step 6: Secret Data Validation
```bash
# Decode and verify secret contents
kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.db-password}' | base64 -d
kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d

# Compare values - they should match
```

### Phase 3: Resolution Actions (30 minutes)

#### Fix 1: Complete Secret Alignment
```bash
# Create/update missing secret aliases
kubectl create secret generic kasm-database-postgres-creds -n kasm \
  --from-literal=admin-password="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.admin-password}' | base64 -d)" \
  --from-literal=db-password="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.db-password}' | base64 -d)" \
  --from-literal=encryption-secret="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.encryption-secret}' | base64 -d)" \
  --from-literal=manager-token="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.manager-token}' | base64 -d)" \
  --from-literal=redis-password="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.redis-password}' | base64 -d)" \
  --from-literal=service-token="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.service-token}' | base64 -d)" \
  --from-literal=user-password="$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.user-password}' | base64 -d)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

#### Fix 2: Force Pod Recreation
```bash
# Delete failing pods to trigger recreation
kubectl delete pod -l app.kubernetes.io/name=kasm-api -n kasm
kubectl delete job kasm-admin-password-fix-job -n kasm
kubectl delete job kasm-db-permissions-job -n kasm
kubectl delete job kasm-db-user-setup-job -n kasm

# Restart deployments
kubectl rollout restart deployment/kasm-api-deployment -n kasm
kubectl rollout restart deployment/kasm-manager-deployment -n kasm
```

#### Fix 3: Database User Verification
```bash
# Manually verify/create database users
kubectl exec -it kasm-db-statefulset-0 -n kasm -- psql -U postgres -d postgres

-- In PostgreSQL:
-- Check existing users
\du

-- Create kasmapp user if missing
CREATE USER kasmapp WITH PASSWORD '<password>';
GRANT ALL PRIVILEGES ON DATABASE kasm TO kasmapp;

-- Create kasm database if missing
CREATE DATABASE kasm OWNER kasmapp;
```

#### Fix 4: ArgoCD Sync Optimization
```bash
# Force resync with proper wave ordering
argocd app sync kasm --strategy=hook --timeout=600

# Or via kubectl
kubectl annotate application kasm -n argocd argocd.argoproj.io/refresh=normal
```

### Phase 4: Verification (10 minutes)

#### Step 7: Service Health Check
```bash
# Monitor pod recovery
watch kubectl get pods -n kasm

# Check service endpoints
kubectl get svc -n kasm
kubectl get endpoints -n kasm

# Test service connectivity
kubectl port-forward svc/kasm-api 8080:80 -n kasm
# Test: curl http://localhost:8080/api/health
```

#### Step 8: Application Functionality Test
```bash
# Access KASM UI (if ingress configured)
# Test basic authentication
# Verify workspace creation capability
```

---

## 🔧 Common Resolution Patterns

### Pattern 1: Secret Reference Fixes
**When**: CreateContainerConfigError mentioning missing secrets
**Solution**: Create secret aliases or fix references
**Command**: Use kubectl create secret with --from-literal flags

### Pattern 2: Database Connection Issues  
**When**: API pods crash with SQLAlchemy errors
**Solution**: Verify database users and permissions
**Command**: Connect to DB pod and check user privileges

### Pattern 3: Init Container Loops
**When**: Pods stuck in Init:X/Y status
**Solution**: Check init container logic and dependencies
**Command**: Review init container logs and conditions

### Pattern 4: ArgoCD Sync Issues
**When**: Resources created in wrong order
**Solution**: Adjust sync waves and hooks
**Command**: Update annotations and force resync

### Pattern 5: OnePassword Sync Delays
**When**: Secrets empty or missing after OnePassword sync
**Solution**: Check operator status and item paths
**Command**: Verify OnePasswordItem resources and operator logs

---

## 📊 Monitoring & Prevention

### Health Check Commands
```bash
# Quick health check script
#!/bin/bash
echo "=== KASM Health Check ==="
echo "Pods Status:"
kubectl get pods -n kasm --no-headers | awk '{print $1 ": " $3}'

echo -e "\nFailed Pods:"
kubectl get pods -n kasm --field-selector=status.phase!=Running --no-headers

echo -e "\nSecret Status:"
kubectl get secrets -n kasm | grep kasm

echo -e "\nService Endpoints:"
kubectl get endpoints -n kasm
```

### Automated Monitoring
```yaml
# Add to monitoring system
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kasm-health
  namespace: kasm
spec:
  selector:
    matchLabels:
      app: kasm-api
  endpoints:
  - port: http
    path: /api/health
    interval: 30s
```

### Preventive Measures

#### 1. Secret Management
- ✅ Implement secret validation jobs
- ✅ Use consistent naming conventions
- ✅ Add secret existence checks in init containers

#### 2. Database Reliability
- ✅ Add database readiness probes
- ✅ Implement retry logic in applications
- ✅ Monitor connection pool health

#### 3. Deployment Order
- ✅ Use proper ArgoCD sync waves
- ✅ Add resource dependencies
- ✅ Implement health checks before dependent services

#### 4. Monitoring
- ✅ Pod failure alerts
- ✅ Database connection monitoring
- ✅ Secret expiration tracking

---

## 🚨 Emergency Procedures

### Complete Reset (Last Resort)
```bash
# 1. Scale down all deployments
kubectl scale deployment --all --replicas=0 -n kasm

# 2. Delete all jobs (they'll be recreated)
kubectl delete jobs --all -n kasm

# 3. Verify database is healthy
kubectl logs kasm-db-statefulset-0 -n kasm

# 4. Scale up core services first
kubectl scale deployment kasm-api-deployment --replicas=1 -n kasm

# 5. Wait and verify before scaling others
kubectl scale deployment --all --replicas=1 -n kasm
```

### Database Recovery
```bash
# If database corruption suspected
kubectl exec -it kasm-db-statefulset-0 -n kasm -- pg_dump -U postgres kasm > backup.sql
# Restore from backup if needed
```

---

## 📈 Performance Optimization

### Resource Tuning
```yaml
# Recommended resource limits
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Database Optimization
```sql
-- PostgreSQL tuning for KASM
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET max_connections = '200';
ALTER SYSTEM SET work_mem = '4MB';
SELECT pg_reload_conf();
```

---

## 📝 Incident Documentation Template

### For Future Issues
```markdown
## Incident: [Brief Description]
**Date**: [YYYY-MM-DD]
**Severity**: [High/Medium/Low]
**Duration**: [Start - End]

### Symptoms
- [What was observed]

### Root Cause
- [What caused the issue]

### Resolution
- [Steps taken to fix]

### Prevention
- [How to prevent recurrence]
```

---

## 🔗 References

### Key Files
- `apps/services/kasm/kustomization.yaml` - Resource orchestration
- `apps/services/kasm/api-container-patch.yaml` - API container config
- `apps/services/kasm/onepassword-items.yaml` - Secret definitions
- `apps/services/kasm/KASM-ERROR-FIX-SUMMARY.md` - Previous fixes

### Useful Commands
```bash
# Debug toolkit
alias k='kubectl'
alias kgp='kubectl get pods -n kasm'
alias kgs='kubectl get secrets -n kasm'
alias kdp='kubectl describe pod'
alias klf='kubectl logs -f'

# KASM specific
alias kasm-logs='kubectl logs deployment/kasm-api-deployment -n kasm'
alias kasm-status='kubectl get pods,svc,secrets -n kasm'
alias kasm-restart='kubectl rollout restart deployment/kasm-api-deployment -n kasm'
```

### External Resources
- [KASM Workspaces Documentation](https://kasmweb.com/docs/)
- [Kubernetes Troubleshooting Guide](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [ArgoCD Sync Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)

---

## ✅ Success Criteria

### Resolution Complete When:
- [ ] All pods in Running state
- [ ] API service responds to health checks
- [ ] Database connections successful
- [ ] KASM UI accessible
- [ ] No CrashLoopBackOff or CreateContainerConfigError
- [ ] All critical jobs completed successfully

### Monitoring Confirms:
- [ ] Zero pod restarts in 30 minutes
- [ ] Database connection pool healthy
- [ ] API response times < 2s
- [ ] No error logs for 15 minutes

### ArgoCD Management Requirements:
- [ ] All configuration changes written as YAML files in `/apps/services/kasm/`
- [ ] All fixes implemented as declarative Kubernetes resources
- [ ] Manual `kubectl` commands converted to ArgoCD-managed manifests
- [ ] Secret fixes implemented as Jobs or static Secret resources
- [ ] Database initialization scripts stored in ConfigMaps
- [ ] All troubleshooting artifacts version-controlled in Git
- [ ] ArgoCD sync waves properly configured for resource dependencies
- [ ] No imperative fixes that require manual intervention
- [ ] All resources have proper ArgoCD annotations for lifecycle management
- [ ] Configuration drift eliminated through GitOps practices

### Long-term Sustainability:
- [ ] Infrastructure as Code principles followed
- [ ] All fixes reproducible through Git repository
- [ ] ArgoCD can recreate entire KASM stack from `/apps/services/kasm/`
- [ ] No manual secret creation or database commands required
- [ ] Monitoring and alerting configured through code
- [ ] Backup and recovery procedures documented as code
- [ ] Environment-specific configurations parameterized properly

---

*Last updated: 2025-07-31T10:57:00Z*  
*Next review: 2025-08-01T10:00:00Z*  
*Document version: 1.0*