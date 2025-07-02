# Obsidian Backup and Restoration

This document describes the automated backup and restoration system for Obsidian in your homelab Kubernetes cluster.

## 🔄 Automatic Backup

Backups are automatically created daily at 3 AM using a CronJob that:
1. Creates a compressed tar.gz archive of all Obsidian data
2. Uploads the backup to Backblaze B2 cloud storage
3. Cleans up local temporary files

**Backup Location**: `cloud-homelab-backups` bucket under `obsidian/` prefix
**Backup Format**: `obsidian_backup_YYYYMMDD_HHMMSS.tar.gz`

## 🚀 Automatic Restoration

### Init Container Restoration
The Obsidian deployment includes an init container that automatically restores from the latest backup when:
- The persistent volume is empty or contains minimal data
- The pod starts up

This ensures that if you recreate the deployment or move to a new cluster, your data is automatically restored.

### How it works:
1. **Check Data Directory**: Determines if restoration is needed
2. **Find Latest Backup**: Queries B2 for the most recent backup
3. **Download & Extract**: Downloads and extracts the backup to the data directory
4. **Start Obsidian**: The main container starts with restored data

## 🛠 Manual Restoration

For manual restoration scenarios, use the `obsidian-manual-restore` Job.

### Basic Manual Restore (Latest Backup)
```bash
kubectl apply -f apps/services/obsidian/base/restore-job.yaml
```

### Force Restore (Overwrites Existing Data)
```yaml
# Edit the restore-job.yaml and change:
- name: FORCE_RESTORE
  value: "true"
```

### Restore Specific Date
```yaml
# Edit the restore-job.yaml and set:
- name: BACKUP_DATE
  value: "20240702"  # YYYYMMDD format
```

### Monitor Restoration Progress
```bash
# Watch the job
kubectl get jobs -n services -w

# View logs
kubectl logs -n services job/obsidian-manual-restore
```

## 📋 Usage Examples

### Scenario 1: Fresh Installation
When deploying Obsidian for the first time on a new cluster:
- The init container will automatically check for existing backups
- If backups exist, it will restore the latest one
- If no backups exist, Obsidian starts fresh

### Scenario 2: Data Recovery
If your data gets corrupted or accidentally deleted:
1. Set `FORCE_RESTORE: "true"` in the restore job
2. Apply the job: `kubectl apply -f apps/services/obsidian/base/restore-job.yaml`
3. Monitor the restoration process
4. Restart the Obsidian deployment if needed

### Scenario 3: Point-in-Time Recovery
To restore from a specific date:
1. Set `BACKUP_DATE: "YYYYMMDD"` in the restore job
2. Optionally set `FORCE_RESTORE: "true"` if overwriting existing data
3. Apply the job and monitor progress

## 🔐 Security Notes

- Backblaze B2 credentials are stored in Kubernetes secrets
- Backups are encrypted in transit to B2
- Consider enabling B2 bucket encryption for data at rest
- The restoration process preserves file permissions and structure

## 🚨 Troubleshooting

### Common Issues

**Init Container Fails**
```bash
# Check init container logs
kubectl logs -n services deployment/obsidian -c obsidian-restore
```

**No Backups Found**
- Verify B2 credentials are correct
- Check that the bucket name and prefix are correct
- Ensure the backup CronJob is running successfully

**Restoration Job Stuck**
```bash
# Delete and recreate the job
kubectl delete job -n services obsidian-manual-restore
kubectl apply -f apps/services/obsidian/base/restore-job.yaml
```

**Permissions Issues**
- Ensure the restored files have correct ownership
- The Obsidian container runs as user 1000:1000

### Verification Commands

```bash
# Check backup CronJob status
kubectl get cronjobs -n services

# View recent backup job logs
kubectl logs -n services job/obsidian-backup-xxx

# List available backups in B2 (requires B2 CLI)
b2 file list cloud-homelab-backups obsidian/

# Check Obsidian deployment status
kubectl get pods -n services -l app=obsidian
```

## 🔄 Recovery Scenarios

### Complete Cluster Rebuild
1. Deploy the Obsidian resources with ArgoCD
2. The init container will automatically restore from latest backup
3. Verify data integrity after deployment

### Partial Data Loss
1. Use the manual restore job with `FORCE_RESTORE: false`
2. This will only restore if the data directory is mostly empty
3. For complete replacement, use `FORCE_RESTORE: true`

### Migration to New Storage
1. Deploy Obsidian with new PVC
2. The init container will detect empty storage and restore automatically
3. Update any references to the old PVC name if needed

## 📝 Best Practices

1. **Regular Testing**: Periodically test the restoration process
2. **Monitor Backups**: Set up alerts for backup job failures
3. **Version Control**: Keep your Kubernetes manifests in Git
4. **Documentation**: Update this document when making changes
5. **Security**: Rotate B2 credentials periodically

## 🔗 Related Resources

- `backups.yaml`: Automated backup CronJob
- `deployment.yaml`: Main deployment with init container
- `restore-job.yaml`: Manual restoration Job
- `OBSIDIAN_DEPLOYMENT.md`: General deployment documentation
