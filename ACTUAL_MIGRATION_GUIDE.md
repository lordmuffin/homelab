# Actual Budget: File-Based to PostgreSQL Migration Guide

Complete guide for migrating Actual Budget from file-based storage to PostgreSQL with automated backup and restoration.

## Overview

This migration upgrades Actual Budget from file-based storage to a PostgreSQL database with:
- **Automated daily backups** to Backblaze B2 cloud storage
- **Automatic restoration** from backups during deployment
- **Data protection** mechanisms to prevent accidental data loss
- **Enterprise-grade reliability** with CloudNativePG

## Prerequisites

### Required Tools
- `kubectl` configured for your cluster
- `bash` shell environment
- Access to the `services` namespace
- 1Password Connect deployed and configured

### Required Credentials
- **Database credentials** in 1Password vault: `actual-db-postgres-creds`
  - `username`: PostgreSQL username (typically `actual`)
  - `password`: Strong PostgreSQL password
- **Backup credentials** in 1Password vault: `backblaze-cloud-homelab-creds`
  - `keyID`: Backblaze B2 application key ID
  - `applicationKey`: Backblaze B2 application key
  - `region`: Backblaze B2 region (e.g., `us-west-004`)

### Current State Verification
1. **Check current Actual Budget deployment**:
   ```bash
   kubectl get deployment actual -n services
   kubectl get pvc actual-storage -n services
   ```

2. **Verify data exists**:
   ```bash
   kubectl exec deployment/actual -n services -- ls -la /data/
   ```

## Migration Process

### Phase 1: Backup Current Data 📋

1. **Create backup directory**:
   ```bash
   mkdir -p ./actual-backups
   cd /path/to/homelab
   ```

2. **Run backup script**:
   ```bash
   ./actual-backup-script.sh
   ```

3. **Verify backup contents**:
   ```bash
   ls -la ./actual-backups/
   # Should show: actual-data-backup-YYYYMMDD_HHMMSS.tar.gz
   # Plus inventory files
   ```

4. **Review backup inventory**:
   ```bash
   cat ./actual-backups/file-inventory-*.txt
   cat ./actual-backups/database-tables-*.txt
   ```

### Phase 2: Deploy PostgreSQL Infrastructure 🛢️

1. **Deploy database and secrets**:
   ```bash
   kubectl apply -f apps/services/finances/actual/base/database.yaml
   kubectl apply -f apps/services/finances/actual/base/actual-db-postgres-creds-1password.yaml
   ```

2. **Wait for database to be ready**:
   ```bash
   kubectl wait --for=condition=Ready cluster/actual-database -n services --timeout=600s
   ```

3. **Verify database deployment**:
   ```bash
   kubectl get cluster actual-database -n services
   kubectl get pods -n services -l cnpg.io/cluster=actual-database
   ```

### Phase 3: Data Migration 🔄

1. **Run migration script**:
   ```bash
   ./actual-migration-script.sh
   ```

2. **Review migration output** - The script will:
   - Analyze your backup data structure
   - Test PostgreSQL connectivity
   - Provide migration strategy recommendations
   - Prepare the database for Actual Budget

3. **Expected migration outcome**:
   - PostgreSQL database ready for Actual Budget
   - Data analysis completed
   - Migration strategy identified

### Phase 4: Deploy New Application 🚀

1. **Deploy backup system**:
   ```bash
   kubectl apply -f apps/services/finances/actual/base/backups.yaml
   ```

2. **Deploy new Actual Budget**:
   ```bash
   kubectl apply -f apps/services/finances/actual/base/deployment.yaml
   ```

3. **Monitor deployment**:
   ```bash
   kubectl get pods -n services -l app=actual -w
   ```

4. **Check restoration logs**:
   ```bash
   kubectl logs deployment/actual -c restore-db-backup -n services
   ```

### Phase 5: Validation and Testing ✅

1. **Run validation script**:
   ```bash
   ./actual-validation-script.sh
   ```

2. **Test application access**:
   ```bash
   kubectl port-forward deployment/actual 5006:5006 -n services
   # Access http://localhost:5006
   ```

3. **Verify backup system**:
   ```bash
   kubectl create job --from=cronjob/actual-postgres-backup actual-test-backup -n services
   kubectl logs job/actual-test-backup -n services -f
   ```

## Data Import Methods

Since Actual Budget's data structure is complex, choose the appropriate method:

### Method A: Fresh Start with Manual Import
1. **Access new Actual Budget** at your configured URL
2. **Create new budget** with same structure as before
3. **Manually re-enter** key budget data
4. **Import transactions** using CSV if available

### Method B: Actual Budget Import Features
1. **Export data** from backup files (if Actual Budget format)
2. **Use Actual Budget's import features** in the web interface
3. **Import budget files** directly

### Method C: Manual Data Reconstruction
1. **Examine backup files** using the inventory
2. **Extract key data** (accounts, budgets, transactions)
3. **Recreate budget structure** in new instance
4. **Import historical data** as needed

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database pod status
kubectl get pods -n services -l cnpg.io/cluster=actual-database

# Check database logs
kubectl logs -l cnpg.io/cluster=actual-database -n services

# Test connectivity
kubectl exec -it deployment/actual-database-1 -n services -- psql -U postgres -d actual
```

#### Backup Failures
```bash
# Check backup pod logs
kubectl logs job/actual-postgres-backup-<timestamp> -n services

# Check B2 credentials
kubectl get secret backblaze-cloud-homelab-creds-1password -n services

# Test backup manually
kubectl create job --from=cronjob/actual-postgres-backup manual-backup-test -n services
```

#### Application Start Issues
```bash
# Check application logs
kubectl logs deployment/actual -n services

# Check init container logs
kubectl logs deployment/actual -c restore-db-backup -n services
kubectl logs deployment/actual -c wait-for-db -n services

# Check environment variables
kubectl exec deployment/actual -n services -- env | grep -E "(POSTGRES|ACTUAL)"
```

#### Restoration Issues
```bash
# Check restoration logs
kubectl logs deployment/actual -c restore-db-backup -n services

# Force restoration (DANGEROUS - will overwrite data)
kubectl patch deployment actual -n services -p '{
  "spec": {
    "template": {
      "spec": {
        "initContainers": [{
          "name": "restore-db-backup",
          "env": [{"name": "FORCE_RESTORE", "value": "true"}]
        }]
      }
    }
  }
}'
kubectl rollout restart deployment/actual -n services
```

### Recovery Procedures

#### Rollback to File-Based Storage
If migration fails, you can rollback:

1. **Stop new deployment**:
   ```bash
   kubectl scale deployment actual --replicas=0 -n services
   ```

2. **Restore original deployment** (backup your original files first)

3. **Restore data from backup**:
   ```bash
   # Extract backup to temporary location
   tar -xzf ./actual-backups/actual-data-backup-*.tar.gz -C /tmp/
   
   # Copy back to PVC (requires pod with volume mount)
   ```

#### Database Recovery
If database is corrupted:

1. **Restore from automated backup**:
   ```bash
   # Check available backups in B2
   # Use restoration init container to restore latest backup
   kubectl patch deployment actual -n services -p '{
     "spec": {
       "template": {
         "spec": {
           "initContainers": [{
             "name": "restore-db-backup",
             "env": [{"name": "FORCE_RESTORE", "value": "true"}]
           }]
         }
       }
     }
   }'
   ```

## Monitoring and Maintenance

### Backup Monitoring
```bash
# Check backup schedule
kubectl get cronjob actual-postgres-backup -n services

# View recent backup jobs
kubectl get jobs -n services --sort-by=.metadata.creationTimestamp | grep actual-backup

# Check backup logs
kubectl logs job/actual-postgres-backup-<timestamp> -n services
```

### Database Health
```bash
# Check cluster status
kubectl get cluster actual-database -n services

# Monitor database metrics
kubectl exec -it deployment/actual-database-1 -n services -- psql -U postgres -d actual -c "
SELECT 
  pg_size_pretty(pg_database_size('actual')) as db_size,
  (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count;
"
```

### Application Health
```bash
# Check application status
kubectl get deployment actual -n services

# Monitor application logs
kubectl logs deployment/actual -n services -f

# Test application connectivity
curl -I http://your-actual-url:5006/
```

## File Reference

### Created Files
- `migration-backup-pod.yaml` - Pod for backing up file data
- `actual-backup-script.sh` - Backup extraction script
- `actual-migration-script.sh` - Migration orchestration script
- `actual-validation-script.sh` - Validation and testing script
- `ACTUAL_MIGRATION_GUIDE.md` - This documentation

### Updated Files
- `apps/services/finances/actual/base/database.yaml` - PostgreSQL database
- `apps/services/finances/actual/base/deployment.yaml` - Updated deployment
- `apps/services/finances/actual/base/backups.yaml` - Backup configuration
- `apps/services/finances/actual/base/actual-db-postgres-creds-1password.yaml` - Secrets
- `apps/services/finances/actual/base/kustomization.yaml` - Resource list
- `POSTGRES_BACKUPS.md` - Updated with Actual Budget information

## Quick Reference Commands

### Migration Execution
```bash
# 1. Backup current data
./actual-backup-script.sh

# 2. Deploy PostgreSQL
kubectl apply -f apps/services/finances/actual/base/database.yaml
kubectl apply -f apps/services/finances/actual/base/actual-db-postgres-creds-1password.yaml

# 3. Run migration
./actual-migration-script.sh

# 4. Deploy application
kubectl apply -f apps/services/finances/actual/base/

# 5. Validate setup
./actual-validation-script.sh
```

### Emergency Commands
```bash
# Emergency backup
kubectl create job --from=cronjob/actual-postgres-backup emergency-backup -n services

# Force restoration
kubectl patch deployment actual -n services --type='merge' -p='{"spec":{"template":{"spec":{"initContainers":[{"name":"restore-db-backup","env":[{"name":"FORCE_RESTORE","value":"true"}]}]}}}}'
kubectl rollout restart deployment/actual -n services

# Scale down for maintenance
kubectl scale deployment actual --replicas=0 -n services

# Check backup logs
kubectl logs -f job/actual-postgres-backup-$(date +%Y%m%d) -n services
```

## Success Criteria

✅ **Migration Complete When:**
- File-based data successfully backed up
- PostgreSQL database deployed and healthy
- Application connects to PostgreSQL
- Backup system creating daily backups
- Data accessible through Actual Budget interface
- Validation script passes all checks

✅ **System Operational When:**
- Daily backups running at 4:00 AM
- Automatic restoration working
- Application performance acceptable
- Data integrity maintained
- Monitoring and alerting functional

---

**⚠️ Important Notes:**
- Always test in development environment first
- Keep file-based backups until confident in migration
- Monitor closely for first week after migration
- Document any custom configurations or data peculiarities
- Plan for potential downtime during migration