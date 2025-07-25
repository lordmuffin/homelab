# Homelab Backup Strategy

## Overview

This document outlines the comprehensive backup strategy for the Kubernetes homelab infrastructure, ensuring data protection and disaster recovery capabilities across all critical services.

## Design Principles

### Core Philosophy
- **3-2-1 Backup Strategy**: 3 copies of data, 2 different storage types, 1 offsite location
- **Automated & Reliable**: Zero-touch backups with robust error handling
- **Service-Aware**: Tailored backup approaches for different service types
- **Resource Conscious**: Optimized scheduling and resource allocation
- **Disaster Recovery Ready**: Point-in-time restoration capabilities

### Architecture Goals
- **Consistency**: Standardized patterns across all services
- **Reliability**: Exponential backoff retry logic and integrity verification
- **Observability**: Comprehensive logging and error reporting
- **Maintainability**: Clean, documented code with robust JSON processing
- **Scalability**: Easy addition of new services following established patterns

## Backup Architecture

### Infrastructure Components

#### Storage Backend
- **Primary**: Backblaze B2 Cloud Storage (`cloud-homelab-backups` bucket)
- **Encryption**: Client-side encryption via B2 native capabilities
- **Retention**: 30-day automated retention policy with intelligent cleanup
- **Access Control**: 1Password-managed B2 credentials with least-privilege access

#### Container Strategy
- **Multi-container Jobs**: Separate containers for database, files, and B2 operations
- **Resource Isolation**: Dedicated resource quotas per container type
- **Failure Isolation**: Independent container failures don't affect others
- **Signal Coordination**: File-based completion signals between containers

### Backup Types

#### Database Backup (PostgreSQL)
- **Method**: `pg_dump` with compression (gzip)
- **Format**: SQL dumps with `--no-owner --no-privileges` flags
- **Validation**: Connection testing with exponential backoff retry
- **Integrity**: gzip compression validation post-backup

#### File Backup
- **Method**: `tar` with gzip compression
- **Scope**: Service-specific persistent volumes
- **Validation**: tar file integrity verification
- **Efficiency**: Incremental approach for large datasets

#### Hybrid Backup Services
Services requiring both database and file backups use coordinated multi-container approach:
- Database and file backups run in parallel
- B2 uploader waits for both completions
- Atomic upload ensures consistency

## Service-Specific Configurations

### Paperless-ngx
```yaml
Schedule: "30 2 * * *" (2:30 AM daily)
Type: Database Only
Components:
  - PostgreSQL database backup
Volumes: None
```

**Rationale**: Paperless backup has been simplified to database-only. While the media directory contains processed documents, the database contains sufficient metadata for document management. File backup can be added later if needed.

### n8n
```yaml
Schedule: "45 2 * * *" (2:45 AM daily)
Type: Hybrid (Database + Files)
Components:
  - PostgreSQL database backup (workflows, credentials)
  - Workflow files backup
Volumes: n8n-storage
```

**Rationale**: n8n stores workflow definitions and execution logs in persistent storage that complement the database metadata.

### LiteLLM
```yaml
Schedule: "0 3 * * *" (3:00 AM daily)
Type: Hybrid (Database + Files)
Components:
  - PostgreSQL database backup (configurations, usage data)
  - Configuration files backup
Volumes: litellm-data-pvc
```

**Rationale**: LiteLLM stores runtime configurations and cached data in persistent volumes alongside database state.

## Resource Management

### Standardized Resource Allocations

#### postgres-backup containers
```yaml
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

#### file-backup containers
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

#### b2-uploader containers
```yaml
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 100m
    memory: 128Mi
```

### Schedule Optimization
Backup jobs are scheduled with 15-minute intervals to provide adequate spacing while maintaining efficient backup windows:
- **2:30 AM**: Paperless backup (database only)
- **2:45 AM**: n8n backup (hybrid)
- **3:00 AM**: LiteLLM backup (hybrid)

This spacing ensures:
- No concurrent database load
- Adequate cluster resources for each job
- Non-overlapping B2 upload operations
- Maintenance window compatibility

## Technical Implementation

### Error Handling & Retry Logic

#### Exponential Backoff Pattern
```bash
MAX_RETRIES=5
RETRY_COUNT=0
BASE_DELAY=10

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Attempt $RETRY_COUNT/$MAX_RETRIES: Testing database connection..."
  
  if pg_isready -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB; then
    echo "Database connection successful!"
    break
  fi
  
  if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
    # Calculate exponential backoff delay: 10, 20, 40, 80, 160 seconds
    DELAY=$((BASE_DELAY * (2 ** (RETRY_COUNT - 1))))
    echo "Database connection failed. Retrying in $DELAY seconds..."
    sleep $DELAY
  else
    echo "Database connection failed after $MAX_RETRIES attempts."
    exit 1
  fi
done
```

### JSON Processing with jq

#### Robust B2 File Listing
```bash
# Install jq for JSON processing
apk add --no-cache jq

# Use jq to extract file information and process each backup
jq -r '.[] | select(.fileName | test("^service/.*\\.(sql\\.gz|tar\\.gz)$")) | "\(.fileName) \(.fileId) \(.uploadTimestamp)"' /tmp/backup_list.json | \
while read -r file_name file_id upload_timestamp; do
  # Convert milliseconds to seconds
  file_timestamp=$((upload_timestamp / 1000))
  
  # Check if file is older than retention period
  if [ "$file_timestamp" -lt "$CUTOFF_DATE" ]; then
    file_age_days=$(( (CUTOFF_DATE - file_timestamp) / 86400 ))
    echo "Deleting old backup: $file_name (age: ${file_age_days} days)"
    
    if b2v4 delete-file-version "$file_name" "$file_id"; then
      deleted_count=$((deleted_count + 1))
    else
      echo "Error deleting $file_name"
    fi
  else
    kept_count=$((kept_count + 1))
  fi
done
```

### B2 Authentication
All services use explicit B2 authentication for clarity and reliability:
```bash
b2v4 authorize-account "$B2_APPLICATION_KEY_ID" "$B2_APPLICATION_KEY"
```

### Backup Integrity Verification
- **Database backups**: `gzip -t` validation
- **File backups**: `tar -tf` validation
- **Completion signaling**: `.db_done`, `.files_done` markers
- **Size reporting**: Human-readable backup sizes logged

## Restoration Architecture

### Automated Restoration System
Each service includes restoration init containers that automatically restore from backups during pod initialization:

#### Database Restoration Logic
1. **Connection validation** with exponential backoff
2. **Existing data detection** to prevent accidental overwrites
3. **Backup download** from B2 with latest file selection
4. **Schema validation** post-restoration
5. **Integrity verification** of restored data

#### File Restoration Logic
1. **Directory validation** and permissions check
2. **Existing data assessment** to prevent data loss
3. **Backup extraction** with integrity verification
4. **Permission normalization** for application access

### Data Loss Prevention
- **User data detection**: Services check for existing user data before restoration
- **Threshold-based decisions**: Different thresholds per service type
- **Safe defaults**: Skip restoration when in doubt to prevent data loss

Example thresholds:
- **Paperless**: Skip if >0 documents or >10 tags
- **n8n**: Skip if user configurations exist
- **LiteLLM**: Skip if >5 spend records or >0 configurations

## Operational Procedures

### Monitoring & Alerting

#### CronJob Status Monitoring
```bash
# Check backup job status
kubectl get cronjobs -n services
kubectl get cronjobs -n paperless

# View recent job executions
kubectl get jobs -n services --sort-by=.metadata.creationTimestamp
kubectl describe job <job-name> -n <namespace>
```

#### Log Analysis
```bash
# View backup logs
kubectl logs -n services <pod-name> -c postgres-backup
kubectl logs -n services <pod-name> -c file-backup
kubectl logs -n services <pod-name> -c b2-uploader
```

### Manual Backup Execution
```bash
# Trigger manual backup job
kubectl create job --from=cronjob/<cronjob-name> <manual-job-name> -n <namespace>

# Example: Manual n8n backup
kubectl create job --from=cronjob/n8n-backup n8n-backup-manual -n services
```

### Restoration Procedures

#### Emergency Database Restoration
1. **Stop the application pod** to prevent data corruption
2. **Identify target backup** from B2 bucket
3. **Execute restoration init container** manually or redeploy pod
4. **Verify restoration** before resuming operations

#### Point-in-Time Recovery
1. **List available backups** with timestamps
2. **Download specific backup** from B2
3. **Restore to temporary database** for validation
4. **Promote to production** after verification

### Troubleshooting

#### Common Issues

**Backup Job Failures**
- Check database connectivity and credentials
- Verify B2 authentication and bucket permissions
- Review resource allocation and cluster capacity
- Examine persistent volume mount status

**Restoration Issues**
- Validate backup file integrity before restoration
- Check database schema compatibility
- Verify persistent volume claims and mounts
- Review application-specific data validation logic

**B2 Upload Problems**
- Confirm B2 credentials and bucket access
- Check network connectivity to B2 endpoints
- Verify backup file sizes and B2 quotas
- Review retention policy and cleanup operations

#### Diagnostic Commands
```bash
# Check CronJob configuration
kubectl describe cronjob <cronjob-name> -n <namespace>

# Review failed job pods
kubectl get pods -n <namespace> | grep -E "(Error|Failed)"
kubectl logs <failed-pod-name> -n <namespace> -c <container-name>

# Validate B2 connectivity
kubectl run -it --rm debug --image=backblazeit/b2:latest -- /bin/sh
b2v4 authorize-account $KEY_ID $KEY
b2v4 ls cloud-homelab-backups
```

## Security Considerations

### Credential Management
- **1Password Integration**: All secrets managed via 1Password Connect
- **Least Privilege**: B2 keys limited to specific bucket operations
- **Secret Rotation**: Regular credential rotation following security policies
- **Encryption**: All backups encrypted in transit and at rest

### Access Control
- **RBAC**: Kubernetes service accounts with minimal required permissions
- **Network Policies**: Restricted network access for backup operations
- **Audit Logging**: Comprehensive audit trail for all backup operations

## Maintenance & Evolution

### Adding New Services

To add backup capability to a new service:

1. **Assess data types**: Determine if database-only or hybrid backup needed
2. **Create backup CronJob**: Follow established patterns in `apps/services/<service>/base/backups.yaml`
3. **Add restoration logic**: Implement init containers in deployment
4. **Update kustomization**: Include backup resource in `kustomization.yaml`
5. **Schedule coordination**: Choose non-conflicting backup time
6. **Test thoroughly**: Validate both backup and restoration procedures

### Performance Optimization
- **Incremental backups**: Consider for services with large data sets
- **Compression tuning**: Optimize compression levels for size vs. speed
- **Parallel operations**: Leverage concurrent backup containers where beneficial
- **Resource scaling**: Adjust resource allocations based on observed usage

### Disaster Recovery Testing
- **Regular DR drills**: Monthly restoration testing from backups
- **Cross-region testing**: Validate restoration in different environments
- **Documentation updates**: Keep runbooks current with infrastructure changes
- **Team training**: Ensure team members understand restoration procedures

## Compliance & Governance

### Retention Policies
- **Standard retention**: 30 days for all services
- **Legal holds**: Process for extending retention for compliance
- **Data classification**: Different retention for different data types
- **Automated cleanup**: Reliable deletion of expired backups

### Backup Validation
- **Integrity checks**: Automated validation of backup file integrity
- **Restoration testing**: Regular testing of restoration procedures
- **Data completeness**: Verification that all critical data is backed up
- **Performance metrics**: Monitoring of backup success rates and timing

This backup strategy provides a robust, automated, and maintainable approach to data protection across the homelab infrastructure, ensuring business continuity and disaster recovery capabilities.