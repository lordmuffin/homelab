# Backup Pattern Implementation Guide

## 🎯 Step-by-Step Deployment Guide

This guide provides detailed instructions for implementing the proven backup patterns discovered through Hive Mind analysis.

## 🏗️ **Prerequisites**

### ✅ **Infrastructure Requirements**
- **Kubernetes Cluster** - Working K8s environment
- **ArgoCD** - GitOps deployment (already configured)
- **1Password** - Secret management (already configured)
- **B2 Storage** - Backblaze cloud storage account

### ✅ **Existing Infrastructure**
Your homelab already has these components configured:
- ✅ **Velero** - Cluster-level backup system
- ✅ **1Password Secrets** - `backblaze-cloud-homelab-creds-1password`
- ✅ **B2 Bucket** - `cloud-homelab-backups`
- ✅ **ArgoCD** - GitOps deployment pipeline

## 🚀 **Implementation Phases**

### **Phase 1: Deploy Production-Ready Configurations**

These applications have complete, validated backup configurations ready for immediate deployment:

#### 📰 **Wallabag** (Single Database Pattern)
```bash
# Deploy Wallabag backup configuration
kubectl apply -f apps/services/wallabag/base/backups.yaml

# Verify deployment
kubectl get cronjobs -n wallabag
kubectl describe cronjob wallabag-backup -n wallabag
```

#### 📄 **Paperless** (Multi-Database Pattern)  
```bash
# Deploy Paperless backup configuration
kubectl apply -f apps/services/paperless/base/backups.yaml

# Verify deployment
kubectl get cronjobs -n paperless
kubectl logs -n paperless job/paperless-backup-$(date +%s) --follow
```

#### 🔄 **N8N** (Single Database Pattern)
```bash
# Deploy N8N backup configuration  
kubectl apply -f apps/services/n8n/base/backups.yaml

# Verify deployment
kubectl get cronjobs -n n8n
kubectl describe cronjob n8n-backup -n n8n
```

#### ✅ **Tandoor** (Reference Pattern)
Already excellent - no changes needed! ✨

### **Phase 2: Fix Minor Issues**

#### 📝 **Blinko** (Needs Resource Specs)
```bash
# Current issue: Missing resource specifications
# Fix: Add resource limits to backup containers

# Edit the backup configuration:
kubectl edit cronjob blinko-backup -n blinko

# Add these resource specifications:
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi" 
    cpu: "500m"
```

#### 🏗️ **Enhanced Velero** (Infrastructure)
```bash
# Install missing Velero CRDs
kubectl apply -f apps/argocd-cloud/base/data/velero.yaml

# Verify Velero status
kubectl get backups -n velero
kubectl get schedules -n velero
```

### **Phase 3: Complex Implementations**

These require more advanced setup but templates are ready:

#### 🔧 **Gitea** (Large File Pattern)
```bash
# Deploy complex backup with Git LFS support
kubectl apply -f apps/services/gitea/base/backups.yaml

# Monitor multi-stage backup process
kubectl logs -n gitea -l job-name=gitea-backup --follow
```

#### 💪 **Wger** (Multi-Database Pattern)
```bash
# Deploy coordinated PostgreSQL + Redis backup
kubectl apply -f apps/services/wger/base/backups.yaml

# Verify both database backups
kubectl get jobs -n wger | grep backup
```

#### 📦 **ArchiveBox** (Large File Pattern)
```bash
# Deploy SQLite + file archive backup
kubectl apply -f apps/services/archivebox/base/backups.yaml

# Monitor incremental backup process
kubectl logs -n archivebox -l app=archivebox-backup --follow
```

#### 🌡️ **Grill-Stats** (Complex Multi-Service)
```bash
# Deploy IoT system backup (PostgreSQL + InfluxDB + Redis)
kubectl apply -f apps/services/grill-stats/base/backups.yaml

# Monitor coordinated multi-database backup
kubectl get jobs -n grill-stats | grep backup
```

## 📋 **Configuration Templates**

### **Single Database Pattern Template**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{APP}}-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            # PostgreSQL Backup Container
            - name: postgres-backup
              image: postgres:latest
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: {{APP}}-db-postgres-creds-1password
                      key: password
              # ... (complete configuration in patterns/)
            
            # B2 Upload Container  
            - name: b2-uploader
              image: backblazeit/b2:latest
              # ... (complete configuration in patterns/)
```

### **Multi-Database Pattern Template**
```yaml
# Supports PostgreSQL + Redis coordination
containers:
  - name: postgres-backup
    # Primary database backup
  - name: redis-backup  
    # Cache/session backup
  - name: coordinator
    # Ensures both complete before upload
  - name: b2-uploader
    # Cloud storage upload
```

## 🔐 **Secret Management**

All backup configurations use 1Password for secure credential management:

### **Required Secrets**
```yaml
# Database credentials (per application)
{{APP}}-db-postgres-creds-1password:
  - username: Database username
  - password: Database password

# B2 cloud storage credentials (shared)
backblaze-cloud-homelab-creds-1password:
  - keyID: B2 application key ID
  - applicationKey: B2 application key
```

### **Secret Validation**
```bash
# Verify 1Password secrets exist
kubectl get secrets -A | grep "1password"

# Test secret access
kubectl get secret {{APP}}-db-postgres-creds-1password -o yaml
```

## 📊 **Monitoring & Validation**

### **Backup Job Monitoring**
```bash
# Check all backup CronJobs
kubectl get cronjobs -A | grep backup

# Monitor specific backup execution
kubectl logs -n {{NAMESPACE}} -l job-name={{APP}}-backup --follow

# Check backup job history
kubectl get jobs -n {{NAMESPACE}} | grep backup
```

### **B2 Storage Verification**
```bash
# List backups in B2 bucket
b2 ls cloud-homelab-backups

# Verify recent backups
b2 ls cloud-homelab-backups/{{APP}}/
```

### **Restore Testing**
```bash
# Test backup integrity (example for PostgreSQL)
kubectl run restore-test --rm -it --image=postgres:latest -- bash
# Inside container:
# pg_restore --list /path/to/backup.sql.gz
```

## ⚡ **Automation & GitOps**

### **ArgoCD Integration**
All backup configurations integrate seamlessly with your existing ArgoCD setup:

```yaml
# Each service's kustomization.yaml includes:
resources:
  - backups.yaml  # Backup CronJob configuration
  - restore-job.yaml  # Manual restore procedures
```

### **Automatic Deployment**
```bash
# Trigger ArgoCD sync for backup updates
argocd app sync {{APP}}

# Monitor ArgoCD application status
argocd app get {{APP}}
```

## 🔧 **Customization Options**

### **Backup Scheduling**
```yaml
# Customize backup frequency
spec:
  schedule: "0 2 * * *"     # Daily at 2AM (default)
  schedule: "0 2 * * 0"     # Weekly on Sunday  
  schedule: "0 2 1 * *"     # Monthly on 1st
```

### **Retention Policies**
```yaml
# Customize retention in B2 lifecycle rules
# Default: 30 days for daily backups
# Adjust in B2 bucket settings
```

### **Resource Allocation**
```yaml
# Adjust container resources based on database size
resources:
  requests:
    memory: "256Mi"    # Small DBs
    memory: "1Gi"      # Large DBs
  limits:
    memory: "1Gi"      # Small DBs  
    memory: "4Gi"      # Large DBs
```

## 🚨 **Emergency Procedures**

### **Immediate Backup**
```bash
# Trigger manual backup immediately
kubectl create job --from=cronjob/{{APP}}-backup {{APP}}-backup-manual-$(date +%s)
```

### **Quick Restore**
```bash
# Deploy restore job
kubectl apply -f apps/services/{{APP}}/base/restore-job.yaml

# Monitor restore progress
kubectl logs -f job/{{APP}}-restore
```

## 📈 **Success Metrics**

### **Key Performance Indicators**
- ✅ **Backup Success Rate**: >99% successful executions
- ✅ **Recovery Time Objective**: <30 minutes for critical apps
- ✅ **Recovery Point Objective**: <24 hours data loss maximum
- ✅ **Storage Efficiency**: >70% compression ratio
- ✅ **Cost Optimization**: <$10/month B2 storage costs

### **Monitoring Dashboards**
```bash
# Set up Prometheus/Grafana monitoring
# Track backup job success/failure rates
# Monitor B2 storage usage and costs
# Alert on backup failures
```

---

## 🐝 **Implementation Support**

This implementation guide is backed by the collective intelligence of the Hive Mind analysis. Each pattern has been:

- 🔍 **Analyzed** against the proven Tandoor reference
- 🧠 **Validated** for security and reliability  
- 🔧 **Tested** for Kubernetes compatibility
- ✅ **Verified** for ArgoCD GitOps integration

For additional support, refer to:
- [Pattern Templates](./patterns/) - Detailed configuration files
- [Validation Guide](./VALIDATION.md) - Testing procedures
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions