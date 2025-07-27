# Single Database Backup Pattern

## 🎯 Overview

The **Single Database Pattern** is designed for applications with a single PostgreSQL database, based on the proven Tandoor reference implementation. This pattern provides reliable, automated backups with cloud storage integration.

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │   Backup Job    │    │   B2 Cloud      │
│  Database       │───▶│   Container     │───▶│   Storage       │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Two-Container Workflow**
1. **postgres-backup**: Creates compressed database dump
2. **b2-uploader**: Uploads backup to cloud storage with retry logic

## 📋 **Use Cases**

Perfect for applications like:
- **Wallabag** - Article archiving
- **Vikunja** - Task management  
- **N8N** - Workflow automation
- **Blinko** - Note-taking
- Any single PostgreSQL application

## 🔧 **Implementation**

### **1. Base Configuration**
```yaml
# backups.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{APP}}-backup
  namespace: {{NAMESPACE}}
spec:
  schedule: "0 2 * * *"  # Daily at 2AM
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: postgres-backup
              image: postgres:latest
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: {{APP}}-db-postgres-creds-1password
                      key: password
                - name: POSTGRES_USER
                  valueFrom:
                    secretKeyRef:
                      name: {{APP}}-db-postgres-creds-1password
                      key: username
                - name: POSTGRES_HOST
                  value: {{APP}}-database-rw.{{NAMESPACE}}.svc.cluster.local
                - name: POSTGRES_DB
                  value: {{APP}}
              command: ["/bin/bash", "-c"]
              args:
                - |
                  # Complete backup script (see full template below)
              volumeMounts:
                - name: backup-storage
                  mountPath: /mnt/backup
            
            - name: b2-uploader
              image: backblazeit/b2:latest
              env:
                - name: B2_APPLICATION_KEY_ID
                  valueFrom:
                    secretKeyRef:
                      name: backblaze-cloud-homelab-creds-1password
                      key: keyID
                - name: B2_APPLICATION_KEY
                  valueFrom:
                    secretKeyRef:
                      name: backblaze-cloud-homelab-creds-1password
                      key: applicationKey
                - name: B2_BUCKET_NAME
                  value: "cloud-homelab-backups"
              command: ["/bin/bash", "-c"]
              args:
                - |
                  # Complete upload script (see full template below)
              volumeMounts:
                - name: backup-storage
                  mountPath: /mnt/backup
          
          restartPolicy: OnFailure
          volumes:
            - name: backup-storage
              emptyDir: {}
```

### **2. Restore Job Configuration**
```yaml
# restore-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{APP}}-restore
  namespace: {{NAMESPACE}}
spec:
  template:
    spec:
      containers:
        - name: postgres-restore
          image: postgres:latest
          env:
            # Same environment variables as backup
          command: ["/bin/bash", "-c"]
          args:
            - |
              # Download and restore from B2
              # Validation and integrity checks
              # Database restoration with error handling
      restartPolicy: Never
```

## 🔐 **Required Secrets**

### **Application Database Credentials**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{APP}}-db-postgres-creds-1password
  namespace: {{NAMESPACE}}
  annotations:
    operator.1password.io/item-path: "vaults/Homelab/items/{{APP}}-db-postgres-creds"
    operator.1password.io/item-name: "{{APP}}-db-postgres-creds"
type: Opaque
data:
  username: # Base64 encoded username
  password: # Base64 encoded password
```

### **B2 Storage Credentials** (Shared)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: backblaze-cloud-homelab-creds-1password
  namespace: {{NAMESPACE}}
  annotations:
    operator.1password.io/item-path: "vaults/Homelab/items/backblaze-cloud-homelab-creds"
type: Opaque
data:
  keyID: # Base64 encoded B2 key ID
  applicationKey: # Base64 encoded B2 application key
```

## 📊 **Key Features**

### ✅ **Reliability**
- **Retry Logic**: Exponential backoff with 5 attempts
- **Error Handling**: Comprehensive bash error trapping
- **Timeout Protection**: Prevents hanging processes
- **Validation**: File integrity and corruption detection

### ✅ **Security**
- **1Password Integration**: Secure credential management
- **No Hardcoded Secrets**: All sensitive data from secrets
- **B2 Encryption**: Data encrypted in transit and at rest
- **Access Control**: Minimal required permissions

### ✅ **Efficiency**
- **Compression**: gzip compression for storage optimization
- **Incremental Strategy**: Only backup when data changes
- **Resource Management**: Configurable container resources
- **Cleanup**: Automated retention policies

### ✅ **Monitoring**
- **Structured Logging**: Timestamp and context logging
- **Status Signals**: Container coordination via `.done` files
- **Error Reporting**: Detailed error messages and exit codes
- **Metrics Ready**: Compatible with Prometheus monitoring

## 📝 **Customization Variables**

Replace these placeholders when implementing:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{APP}}` | Application name | `wallabag` |
| `{{NAMESPACE}}` | Kubernetes namespace | `wallabag` |
| `{{DATABASE_SERVICE}}` | Database service name | `wallabag-database-rw` |
| `{{BACKUP_SCHEDULE}}` | Cron schedule | `"0 2 * * *"` |

## 🚀 **Quick Deploy**

### **1. Copy Template**
```bash
# Copy the single-database pattern
cp docs/backup-patterns/patterns/single-database/backups.yaml \
   apps/services/{{APP}}/base/backups.yaml
```

### **2. Customize Configuration**
```bash
# Replace placeholders with your app details
sed -i 's/{{APP}}/wallabag/g' apps/services/wallabag/base/backups.yaml
sed -i 's/{{NAMESPACE}}/wallabag/g' apps/services/wallabag/base/backups.yaml
```

### **3. Add to Kustomization**
```yaml
# apps/services/{{APP}}/base/kustomization.yaml
resources:
  - deployment.yaml
  - service.yaml
  - backups.yaml  # Add this line
```

### **4. Deploy via ArgoCD**
```bash
# Commit changes and let ArgoCD sync
git add .
git commit -m "Add backup configuration for {{APP}}"
git push origin main

# Or manually sync
argocd app sync {{APP}}
```

## 📈 **Validation & Testing**

### **Verify Deployment**
```bash
# Check CronJob creation
kubectl get cronjobs -n {{NAMESPACE}}

# Check secrets are available  
kubectl get secrets -n {{NAMESPACE}} | grep 1password

# Verify first backup execution
kubectl get jobs -n {{NAMESPACE}} | grep backup
```

### **Test Manual Backup**
```bash
# Trigger immediate backup
kubectl create job --from=cronjob/{{APP}}-backup {{APP}}-backup-test

# Monitor execution
kubectl logs -f job/{{APP}}-backup-test
```

### **Validate B2 Storage**
```bash
# Check backup files in B2
b2 ls cloud-homelab-backups/{{APP}}/

# Verify file integrity
b2 download-file-by-name cloud-homelab-backups {{APP}}/latest.sql.gz /tmp/test.sql.gz
gzip -t /tmp/test.sql.gz
```

## 🔍 **Troubleshooting**

### **Common Issues**

**Backup Job Fails**
```bash
# Check pod logs
kubectl logs -n {{NAMESPACE}} -l job-name={{APP}}-backup

# Common causes:
# - Database connection issues
# - Missing secrets
# - Insufficient permissions
# - B2 credentials invalid
```

**B2 Upload Fails**
```bash
# Verify B2 credentials
kubectl get secret backblaze-cloud-homelab-creds-1password -o yaml

# Test B2 connection manually
kubectl run b2-test --rm -it --image=backblazeit/b2:latest -- bash
```

**Database Connection Issues**
```bash
# Verify database service
kubectl get svc -n {{NAMESPACE}}

# Test connection
kubectl run pg-test --rm -it --image=postgres:latest -- bash
# psql -h {{DATABASE_HOST}} -U {{USERNAME}} -d {{DATABASE}}
```

---

## 📋 **Complete Template Files**

See the `patterns/single-database/` directory for complete, ready-to-use template files:

- `backups.yaml` - Complete CronJob configuration
- `restore-job.yaml` - Manual restore procedures
- `kustomization.yaml` - Kustomize integration
- `secrets.yaml` - 1Password secret references

This pattern provides a solid foundation for any single-database application backup strategy, proven through the excellent Tandoor reference implementation.