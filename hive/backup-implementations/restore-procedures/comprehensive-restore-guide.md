# Comprehensive Restore Procedures Guide

## Overview
This guide provides step-by-step restore procedures for all backup implementations created for the homelab infrastructure.

## Database Restore Procedures

### PostgreSQL Database Restore (Universal Pattern)
Used by: wallabag, wger, gitea, n8n, paperless, tandoor, vikunja, blinko, litellm, grill-stats

#### Quick Restore
```bash
# 1. Stop the application (scale to 0)
kubectl scale deployment <app-name> --replicas=0 -n <namespace>

# 2. Run restore job with date parameter
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: <app>-restore-$(date +%Y%m%d-%H%M%S)
  namespace: <namespace>
spec:
  template:
    spec:
      containers:
        - name: restore-db
          image: postgres:latest
          env:
            - name: RESTORE_DATE
              value: "LATEST"  # or specific date like "20241127"
            # ... other env vars from backup job
          # ... rest of restore configuration
EOF

# 3. Monitor restore progress
kubectl logs -f job/<app>-restore-<timestamp> -n <namespace>

# 4. Restart application
kubectl scale deployment <app-name> --replicas=1 -n <namespace>
```

#### Emergency Restore from B2
```bash
# Download latest backup manually
b2 file download cloud-homelab-backups <app>/pg_backup_LATEST.sql.gz ./restore.sql.gz

# Extract and restore
gunzip restore.sql.gz
kubectl exec -i <postgres-pod> -n <namespace> -- psql -U <user> -d <database> < restore.sql
```

### Multi-Database Restore (Grill-Stats)

#### Full System Restore
```bash
# 1. Stop all grill-stats services
kubectl scale deployment grill-stats-web --replicas=0 -n grill-stats
kubectl scale deployment grill-stats-api --replicas=0 -n grill-stats

# 2. Restore PostgreSQL
kubectl apply -f restore-jobs/grill-stats-postgres-restore.yaml

# 3. Restore InfluxDB
kubectl apply -f restore-jobs/grill-stats-influxdb-restore.yaml

# 4. Restore Redis
kubectl apply -f restore-jobs/grill-stats-redis-restore.yaml

# 5. Wait for all restores to complete
kubectl wait --for=condition=complete job/grill-stats-postgres-restore -n grill-stats --timeout=600s
kubectl wait --for=condition=complete job/grill-stats-influxdb-restore -n grill-stats --timeout=600s
kubectl wait --for=condition=complete job/grill-stats-redis-restore -n grill-stats --timeout=600s

# 6. Restart services
kubectl scale deployment grill-stats-web --replicas=1 -n grill-stats
kubectl scale deployment grill-stats-api --replicas=1 -n grill-stats
```

## File-Based Restore Procedures

### Git Repository Restore (Gitea)
```bash
# 1. Stop Gitea
kubectl scale deployment gitea --replicas=0 -n gitea

# 2. Download and extract repository backup
b2 file download cloud-homelab-backups gitea/repositories/gitea_repos_backup_LATEST.tar.gz ./repos.tar.gz
kubectl exec -i gitea-data-pod -n gitea -- tar -xzf - -C /data < repos.tar.gz

# 3. Restore database
kubectl apply -f restore-jobs/gitea-db-restore.yaml

# 4. Wait for completion and restart
kubectl wait --for=condition=complete job/gitea-db-restore -n gitea --timeout=600s
kubectl scale deployment gitea --replicas=1 -n gitea
```

### Archive Data Restore (ArchiveBox)
```bash
# 1. Stop ArchiveBox
kubectl scale deployment archivebox --replicas=0 -n archivebox

# 2. Restore index database
kubectl apply -f restore-jobs/archivebox-index-restore.yaml

# 3. Restore archive data (optional, large files)
kubectl apply -f restore-jobs/archivebox-data-restore.yaml

# 4. Wait and restart
kubectl wait --for=condition=complete job/archivebox-index-restore -n archivebox --timeout=300s
kubectl scale deployment archivebox --replicas=1 -n archivebox
```

## Volume Snapshot Restore (Velero)

### Cluster-Wide Restore
```bash
# 1. Create restore from backup
velero restore create restore-$(date +%Y%m%d-%H%M%S) \
  --from-backup full-backup-YYYYMMDD-HHMMSS \
  --wait

# 2. Monitor restore progress
velero restore describe restore-$(date +%Y%m%d-%H%M%S)
kubectl get pods --all-namespaces

# 3. Verify applications
kubectl get deployments --all-namespaces
```

### Selective Namespace Restore
```bash
# Restore specific namespace
velero restore create restore-namespace-$(date +%Y%m%d-%H%M%S) \
  --from-backup full-backup-YYYYMMDD-HHMMSS \
  --include-namespaces <namespace> \
  --wait
```

### PVC-Only Restore
```bash
# Restore persistent volumes only
velero restore create restore-pvcs-$(date +%Y%m%d-%H%M%S) \
  --from-backup pvc-backup-YYYYMMDD-HHMMSS \
  --include-resources persistentvolumeclaims,persistentvolumes \
  --wait
```

## Emergency Disaster Recovery

### Complete Infrastructure Loss
1. **Restore Kubernetes Cluster**
   ```bash
   # Use Velero to restore cluster state
   velero restore create disaster-recovery-$(date +%Y%m%d) \
     --from-backup critical-apps-LATEST \
     --wait
   ```

2. **Restore ArgoCD Configuration**
   ```bash
   # ArgoCD will automatically sync applications once restored
   kubectl get applications -n argocd
   ```

3. **Validate Database Restoration**
   ```bash
   # Run database restore jobs for critical applications
   for app in tandoor paperless n8n gitea; do
     kubectl apply -f restore-jobs/${app}-restore.yaml
   done
   ```

4. **Verify Application Health**
   ```bash
   # Check all pods are running
   kubectl get pods --all-namespaces | grep -v Running
   
   # Test application endpoints
   curl -I https://tandoor.lab-apj.dev
   curl -I https://paperless.lab-apj.dev
   ```

## Backup Validation

### Automated Backup Testing
```bash
# Test restore in temporary namespace
kubectl create namespace backup-test

# Restore to test namespace
velero restore create test-restore-$(date +%Y%m%d) \
  --from-backup database-backup-LATEST \
  --namespace-mappings tandoor:backup-test \
  --wait

# Validate data integrity
kubectl exec -n backup-test deployment/tandoor -- python manage.py check

# Cleanup test namespace
kubectl delete namespace backup-test
```

### Manual Backup Verification
```bash
# Download and test backup file integrity
b2 file download cloud-homelab-backups tandoor/pg_backup_LATEST.sql.gz ./test.sql.gz

# Test file integrity
gzip -t test.sql.gz && echo "✅ Backup file is valid" || echo "❌ Backup file is corrupted"

# Test SQL restore (dry run)
gunzip -c test.sql.gz | head -100 | grep -E "(CREATE|INSERT)" && echo "✅ SQL content looks valid"
```

## Monitoring and Alerting

### Backup Status Monitoring
```bash
# Check recent backup jobs
kubectl get cronjobs --all-namespaces | grep backup

# View backup job logs
kubectl logs -l job-name=postgres-backup -n tandoor --tail=100

# Check Velero backup status
velero backup get
```

### Failure Alerts Setup
```yaml
# Prometheus alert for backup failures
- alert: BackupJobFailed
  expr: kube_job_status_failed{job_name=~".*backup.*"} > 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Backup job {{ $labels.job_name }} failed in namespace {{ $labels.namespace }}"
```

## Recovery Time Objectives (RTO)

| Component | RTO Target | Notes |
|-----------|------------|-------|
| PostgreSQL DBs | 15 minutes | Small databases, automated restore |
| Gitea Repositories | 30 minutes | Includes large git data |
| ArchiveBox | 60 minutes | Large archive files |
| Grill-Stats | 45 minutes | Multi-database complexity |
| Full Cluster | 2 hours | Complete infrastructure rebuild |

## Recovery Point Objectives (RPO)

| Component | RPO Target | Backup Frequency |
|-----------|------------|-----------------|
| Databases | 24 hours | Daily backups |
| File Data | 24 hours | Daily backups |
| Cluster Config | 24 hours | Daily Velero backups |
| Critical Data | 4 hours | Enhanced monitoring triggers |

## Troubleshooting Common Issues

### Database Connection Failures
```bash
# Check database pods
kubectl get pods -l app.kubernetes.io/component=database

# Test database connectivity
kubectl exec -it <postgres-pod> -- pg_isready -h localhost -U <user>
```

### B2 Upload Failures
```bash
# Check B2 credentials
kubectl get secret backblaze-cloud-homelab-creds-1password -o yaml

# Test B2 connectivity
b2 account authorize <key-id> <key>
b2 bucket list
```

### Velero Issues
```bash
# Check Velero pod logs
kubectl logs -n velero deployment/velero

# Verify backup location
velero backup-location get

# Check CSI driver for volume snapshots
kubectl get csidriver
```

## Best Practices

1. **Test Restores Regularly**: Monthly restore tests in isolated environment
2. **Monitor Backup Size**: Track backup growth and optimize retention
3. **Validate Integrity**: Automated backup file integrity checks
4. **Document Changes**: Update restore procedures when apps are modified
5. **Security**: Encrypt sensitive backups and secure B2 credentials
6. **Automation**: Use ArgoCD to manage backup and restore manifests
7. **Monitoring**: Set up alerts for backup failures and storage quota issues