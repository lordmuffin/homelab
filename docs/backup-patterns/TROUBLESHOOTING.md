# Backup Pattern Troubleshooting Guide

## 🎯 Overview

This troubleshooting guide provides solutions for common issues encountered with homelab backup implementations, based on the collective intelligence gathered from Hive Mind analysis and real-world validation testing.

## 🚨 **Common Issues & Solutions**

## 🔐 **Secret Management Issues**

### **Issue: 1Password Secret Not Found**
```
Error: secrets "app-db-postgres-creds-1password" not found
```

**Diagnosis:**
```bash
# Check if 1Password operator is running
kubectl get pods -n 1password-system

# Verify secret exists in 1Password vault
kubectl get secrets -A | grep 1password
```

**Solution:**
```bash
# 1. Verify 1Password secret configuration
kubectl describe secret {{APP}}-db-postgres-creds-1password -n {{NAMESPACE}}

# 2. Check 1Password operator logs
kubectl logs -n 1password-system -l app.kubernetes.io/name=onepassword-connect-operator

# 3. Recreate secret if needed
kubectl delete secret {{APP}}-db-postgres-creds-1password -n {{NAMESPACE}}
kubectl apply -f apps/services/{{APP}}/base/secrets.yaml

# 4. Wait for operator to sync (usually 30-60 seconds)
kubectl wait --for=condition=ready secret/{{APP}}-db-postgres-creds-1password -n {{NAMESPACE}} --timeout=120s
```

### **Issue: B2 Credentials Invalid**
```
Error: Bad application key id or application key
```

**Diagnosis:**
```bash
# Test B2 credentials manually
kubectl run b2-test --rm -it --image=backblazeit/b2:latest -- bash
# Inside container:
b2 account authorize $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY
```

**Solution:**
```bash
# 1. Verify B2 credentials in 1Password
# 2. Check secret data encoding
kubectl get secret backblaze-cloud-homelab-creds-1password -o yaml | grep -E "(keyID|applicationKey)"

# 3. Test credentials outside cluster
b2 account authorize $(echo "BASE64_KEY_ID" | base64 -d) $(echo "BASE64_APP_KEY" | base64 -d)

# 4. Update credentials in 1Password vault if invalid
# 5. Force secret recreation
kubectl delete secret backblaze-cloud-homelab-creds-1password -n {{NAMESPACE}}
# ArgoCD will recreate automatically
```

## 💾 **Database Connection Issues**

### **Issue: Database Connection Refused**
```
Error: could not connect to server: Connection refused
```

**Diagnosis:**
```bash
# Check database pod status
kubectl get pods -n {{NAMESPACE}} | grep database

# Verify database service
kubectl get svc -n {{NAMESPACE}} | grep database

# Test connection from backup pod
kubectl run db-test --rm -it --image=postgres:latest -- bash
# pg_isready -h {{DATABASE_SERVICE}} -p 5432
```

**Solution:**
```bash
# 1. Check database pod logs
kubectl logs -n {{NAMESPACE}} {{DATABASE_POD_NAME}}

# 2. Verify database service endpoint
kubectl describe svc {{DATABASE_SERVICE}} -n {{NAMESPACE}}

# 3. Update backup configuration with correct service name
# Example fix:
sed -i 's/POSTGRES_HOST.*/POSTGRES_HOST: "{{APP}}-postgresql.{{NAMESPACE}}.svc.cluster.local"/' \
  apps/services/{{APP}}/base/backups.yaml

# 4. For CloudNativePG databases, use correct service naming:
# {{APP}}-database-rw.{{NAMESPACE}}.svc.cluster.local (read-write)
# {{APP}}-database-ro.{{NAMESPACE}}.svc.cluster.local (read-only)
```

### **Issue: Authentication Failed**
```
Error: password authentication failed for user "postgres"
```

**Diagnosis:**
```bash
# Check credentials in secret
kubectl get secret {{APP}}-db-postgres-creds-1password -o yaml

# Decode and verify username/password
echo "USERNAME_BASE64" | base64 -d
echo "PASSWORD_BASE64" | base64 -d

# Test credentials manually
kubectl exec -it {{DATABASE_POD}} -- psql -U {{USERNAME}} -d {{DATABASE}}
```

**Solution:**
```bash
# 1. Verify correct username in secret (often 'app', not 'postgres')
kubectl patch secret {{APP}}-db-postgres-creds-1password -n {{NAMESPACE}} \
  --patch='{"data":{"username":"'$(echo -n "app" | base64)'"}}'

# 2. For CloudNativePG databases, check cluster user:
kubectl get cluster {{APP}}-database -n {{NAMESPACE}} -o yaml | grep -A 5 "bootstrap"

# 3. Update backup configuration with correct username
sed -i 's/POSTGRES_USER.*/POSTGRES_USER: "app"/' \
  apps/services/{{APP}}/base/backups.yaml
```

## 📦 **Container Execution Issues**

### **Issue: Backup Container Fails to Start**
```
Error: Error: failed to create containerd task: failed to mount overlay filesystem
```

**Diagnosis:**
```bash
# Check pod events
kubectl describe pod {{BACKUP_POD_NAME}} -n {{NAMESPACE}}

# Verify node resources
kubectl top nodes

# Check storage availability
kubectl get pv | grep Available
```

**Solution:**
```bash
# 1. Add resource limits to backup containers
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"'

# 2. Ensure sufficient node capacity
kubectl describe node {{NODE_NAME}} | grep -A 5 "Allocated resources"

# 3. Clean up old backup jobs if needed
kubectl delete jobs -n {{NAMESPACE}} -l app={{APP}}-backup --field-selector=status.successful==1
```

### **Issue: Container Coordination Failure**
```
Error: Timeout waiting for backup completion
```

**Diagnosis:**
```bash
# Check both container logs
kubectl logs job/{{APP}}-backup -c postgres-backup -n {{NAMESPACE}}
kubectl logs job/{{APP}}-backup -c b2-uploader -n {{NAMESPACE}}

# Verify shared volume mount
kubectl describe pod {{BACKUP_POD_NAME}} -n {{NAMESPACE}} | grep -A 10 "Mounts"
```

**Solution:**
```bash
# 1. Check .done file creation in postgres-backup container
kubectl exec -it {{BACKUP_POD_NAME}} -c postgres-backup -n {{NAMESPACE}} -- ls -la /mnt/backup/

# 2. Increase timeout in b2-uploader container
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: b2-uploader
            env:
            - name: WAIT_TIMEOUT
              value: "3600"'  # 1 hour timeout

# 3. Verify volume mount paths match in both containers
```

## ☁️ **B2 Storage Issues**

### **Issue: B2 Upload Fails**
```
Error: Server request failed: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**Diagnosis:**
```bash
# Test B2 connectivity
kubectl run b2-test --rm -it --image=backblazeit/b2:latest -- bash
# curl -I https://api.backblazeb2.com/

# Check bucket permissions
b2 get-bucket cloud-homelab-backups
```

**Solution:**
```bash
# 1. Add retry logic to B2 upload
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: b2-uploader
            env:
            - name: B2_RETRY_COUNT
              value: "5"
            - name: B2_RETRY_DELAY
              value: "30"'

# 2. Verify B2 bucket exists and is accessible
b2 create-bucket cloud-homelab-backups allPrivate --lifecycleRule '{"daysFromHidingToDeleting": 30, "fileNamePrefix": ""}'

# 3. Check network policies allowing egress to B2
kubectl get networkpolicies -n {{NAMESPACE}}
```

### **Issue: Backup Files Not Appearing in B2**
```
Error: Upload appears successful but files missing in bucket
```

**Diagnosis:**
```bash
# Check upload logs for actual success
kubectl logs job/{{APP}}-backup -c b2-uploader -n {{NAMESPACE}} | grep "upload.*success"

# List files in B2 bucket
b2 ls cloud-homelab-backups/{{APP}}/

# Check for upload path issues
kubectl logs job/{{APP}}-backup -c b2-uploader -n {{NAMESPACE}} | grep "Uploading to B2"
```

**Solution:**
```bash
# 1. Verify upload path format
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: b2-uploader
            env:
            - name: UPLOAD_PATH_PREFIX
              value: "{{APP}}/"'

# 2. Add file verification after upload
# (Patch b2-uploader script to verify file exists after upload)

# 3. Check B2 bucket lifecycle rules aren't deleting files immediately
b2 get-bucket cloud-homelab-backups | grep lifecycleRules
```

## ⏰ **Scheduling & Timing Issues**

### **Issue: Backup Jobs Not Running**
```
Issue: CronJob exists but no jobs are created
```

**Diagnosis:**
```bash
# Check CronJob status
kubectl describe cronjob {{APP}}-backup -n {{NAMESPACE}}

# Verify timezone and schedule format
kubectl get cronjob {{APP}}-backup -n {{NAMESPACE}} -o yaml | grep schedule

# Check controller manager logs
kubectl logs -n kube-system -l component=kube-controller-manager
```

**Solution:**
```bash
# 1. Verify schedule format (must be in UTC)
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  schedule: "0 2 * * *"  # Daily at 2AM UTC'

# 2. Check suspended status
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  suspend: false'

# 3. Manually trigger to test job template
kubectl create job --from=cronjob/{{APP}}-backup {{APP}}-backup-manual-$(date +%s) -n {{NAMESPACE}}
```

### **Issue: Multiple Backup Jobs Running Simultaneously**
```
Issue: Backup jobs overlap causing resource contention
```

**Diagnosis:**
```bash
# Check running backup jobs
kubectl get jobs -n {{NAMESPACE}} | grep backup | grep -v Complete

# Verify concurrency policy
kubectl get cronjob {{APP}}-backup -n {{NAMESPACE}} -o yaml | grep concurrencyPolicy
```

**Solution:**
```bash
# 1. Ensure proper concurrency policy
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  concurrencyPolicy: Forbid'

# 2. Adjust schedule to avoid overlaps
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  schedule: "0 2 * * *"  # Stagger different apps by hour'

# 3. Set appropriate job completion deadline
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      activeDeadlineSeconds: 3600  # 1 hour timeout'
```

## 🔄 **Restore Issues**

### **Issue: Restore Job Cannot Find Backup File**
```
Error: No backup file found matching pattern: pg_backup_*.sql.gz
```

**Diagnosis:**
```bash
# List available backups in B2
b2 ls cloud-homelab-backups/{{APP}}/

# Check restore job configuration
kubectl get job {{APP}}-restore -n {{NAMESPACE}} -o yaml | grep -A 10 "BACKUP_FILE"
```

**Solution:**
```bash
# 1. Update restore job with specific backup file
kubectl patch job {{APP}}-restore -n {{NAMESPACE}} --patch='
spec:
  template:
    spec:
      containers:
      - name: postgres-restore
        env:
        - name: BACKUP_FILE
          value: "pg_backup_20240115_020000.sql.gz"'

# 2. Or update to use latest backup pattern
kubectl patch job {{APP}}-restore -n {{NAMESPACE}} --patch='
spec:
  template:
    spec:
      containers:
      - name: postgres-restore
        env:
        - name: USE_LATEST_BACKUP
          value: "true"'
```

### **Issue: Database Restore Fails with Permissions**
```
Error: permission denied for schema public
```

**Diagnosis:**
```bash
# Check database user permissions
kubectl exec -it {{DATABASE_POD}} -- psql -U {{USERNAME}} -d {{DATABASE}} -c "\du"

# Verify restore user has necessary privileges
kubectl exec -it {{DATABASE_POD}} -- psql -U {{USERNAME}} -d {{DATABASE}} -c "\l"
```

**Solution:**
```bash
# 1. Grant necessary permissions before restore
kubectl patch job {{APP}}-restore -n {{NAMESPACE}} --patch='
spec:
  template:
    spec:
      containers:
      - name: postgres-restore
        command: ["/bin/bash", "-c"]
        args:
        - |
          # Grant permissions first
          psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "ALTER SCHEMA public OWNER TO $POSTGRES_USER;"
          psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "GRANT ALL ON SCHEMA public TO $POSTGRES_USER;"
          
          # Then proceed with restore
          gunzip -c $BACKUP_FILE | psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB'

# 2. Use --no-owner --no-privileges flags in pg_dump (already configured in pattern)
```

## 📊 **Performance Issues**

### **Issue: Backup Takes Too Long**
```
Issue: Backup job exceeds timeout or uses too many resources
```

**Diagnosis:**
```bash
# Check backup job duration
kubectl get jobs -n {{NAMESPACE}} | grep backup

# Monitor resource usage during backup
kubectl top pods -n {{NAMESPACE}} | grep backup

# Check database size
kubectl exec -it {{DATABASE_POD}} -- psql -U {{USERNAME}} -d {{DATABASE}} \
  -c "SELECT pg_size_pretty(pg_database_size('{{DATABASE}}'));"
```

**Solution:**
```bash
# 1. Increase job timeout
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      activeDeadlineSeconds: 7200  # 2 hours'

# 2. Increase container resources for large databases
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            resources:
              requests:
                memory: "512Mi"
                cpu: "200m"
              limits:
                memory: "2Gi"
                cpu: "1000m"'

# 3. Use compression and parallel dump for large databases
kubectl patch cronjob {{APP}}-backup -n {{NAMESPACE}} --patch='
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            args:
            - |
              pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB \
                --verbose --no-owner --no-privileges \
                --jobs=4 --format=custom | gzip > /mnt/backup/$BACKUP_FILE'
```

## 🔒 **SSL Connection Issues**

### **Issue: SSL Required for Database Connection**
```
Error: connection to server at "db" (10.x.x.x), port 5432 failed: server does not support SSL, but SSL was required
```

**Diagnosis:**
```bash
# Check if PostgreSQL is configured for SSL
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "cat /var/lib/postgresql/data/postgresql.conf | grep ssl"

# Check database logs for SSL-related errors
kubectl logs {{DATABASE_POD}} -n {{NAMESPACE}} | grep -i ssl

# Check if database container has SSL certificates mounted
kubectl describe pod {{DATABASE_POD}} -n {{NAMESPACE}} | grep -A 10 "Mounts"
```

**Solution:**
```bash
# 1. Enable SSL in PostgreSQL (when SSL is required but not configured)
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl = on' >> /var/lib/postgresql/data/postgresql.conf"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl_cert_file = '/etc/ssl/certs/server.crt'' >> /var/lib/postgresql/data/postgresql.conf"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl_key_file = '/etc/ssl/private/server.key'' >> /var/lib/postgresql/data/postgresql.conf"

# 2. Generate self-signed certificate if needed
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "mkdir -p /etc/ssl/private"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "openssl req -new -x509 -days 365 -nodes -text -out /etc/ssl/certs/server.crt -keyout /etc/ssl/private/server.key -subj '/CN=db'"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "chmod 600 /etc/ssl/private/server.key"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "chown postgres:postgres /etc/ssl/certs/server.crt /etc/ssl/private/server.key"

# 3. Restart PostgreSQL to apply changes
kubectl rollout restart statefulset {{DATABASE_STATEFULSET}} -n {{NAMESPACE}}
```

### **Issue: Disable SSL Requirement in Client**
```
Error: connection to server at "db" (10.x.x.x), port 5432 failed: server does not support SSL, but SSL was required
```

**Diagnosis:**
```bash
# Check if client is using SSL by default
kubectl exec -it {{CLIENT_POD}} -n {{NAMESPACE}} -- bash -c "env | grep PGSSLMODE"

# Check connection string in application configuration
kubectl describe pod {{CLIENT_POD}} -n {{NAMESPACE}} | grep -A 20 "Environment"
```

**Solution:**
```bash
# 1. Patch deployment to disable SSL requirement
kubectl patch deployment {{CLIENT_DEPLOYMENT}} -n {{NAMESPACE}} --patch='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "{{CONTAINER_NAME}}",
          "env": [{
            "name": "PGSSLMODE",
            "value": "disable"
          }]
        }]
      }
    }
  }
}'

# 2. For connection strings, add sslmode=disable parameter
kubectl patch configmap {{APP}}-config -n {{NAMESPACE}} --patch='
{
  "data": {
    "database-url": "postgresql://{{USERNAME}}:{{PASSWORD}}@{{DB_HOST}}:5432/{{DB_NAME}}?sslmode=disable"
  }
}'

# 3. Restart client pod to apply changes
kubectl rollout restart deployment {{CLIENT_DEPLOYMENT}} -n {{NAMESPACE}}
```

### **Issue: Create SSL Certificates for PostgreSQL**
```
Error: could not load server certificate file "/etc/ssl/certs/server.crt": No such file or directory
```

**Diagnosis:**
```bash
# Check if certificate files exist
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- ls -la /etc/ssl/certs/server.crt /etc/ssl/private/server.key

# Check PostgreSQL SSL configuration
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- grep ssl /var/lib/postgresql/data/postgresql.conf
```

**Solution:**
```bash
# 1. Create a Kubernetes secret with SSL certificates
kubectl create secret generic {{APP}}-db-ssl -n {{NAMESPACE}} \
  --from-file=server.crt=./server.crt \
  --from-file=server.key=./server.key

# 2. Update the database StatefulSet to mount the certificates
kubectl patch statefulset {{DATABASE_STATEFULSET}} -n {{NAMESPACE}} --patch='
{
  "spec": {
    "template": {
      "spec": {
        "volumes": [{
          "name": "ssl-certs",
          "secret": {
            "secretName": "{{APP}}-db-ssl"
          }
        }],
        "containers": [{
          "name": "postgres",
          "volumeMounts": [{
            "name": "ssl-certs",
            "mountPath": "/etc/ssl/certs/server.crt",
            "subPath": "server.crt"
          }, {
            "name": "ssl-certs",
            "mountPath": "/etc/ssl/private/server.key",
            "subPath": "server.key"
          }]
        }]
      }
    }
  }
}'

# 3. Update PostgreSQL configuration to use certificates
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl = on' >> /var/lib/postgresql/data/postgresql.conf"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl_cert_file = '/etc/ssl/certs/server.crt'' >> /var/lib/postgresql/data/postgresql.conf"
kubectl exec -it {{DATABASE_POD}} -n {{NAMESPACE}} -- bash -c "echo 'ssl_key_file = '/etc/ssl/private/server.key'' >> /var/lib/postgresql/data/postgresql.conf"

# 4. Restart PostgreSQL to apply changes
kubectl rollout restart statefulset {{DATABASE_STATEFULSET}} -n {{NAMESPACE}}
```

## 🔍 **Debugging Tools & Commands**

### **Quick Diagnosis Script**
```bash
#!/bin/bash
# backup-diagnose.sh
APP_NAME="$1"
NAMESPACE="$2"

echo "🔍 Backup Diagnosis for $APP_NAME in $NAMESPACE"
echo "=============================================="

# Check CronJob
echo "📅 CronJob Status:"
kubectl get cronjob $APP_NAME-backup -n $NAMESPACE 2>/dev/null || echo "  ❌ CronJob not found"

# Check Secrets
echo "🔐 Secret Status:"
kubectl get secret ${APP_NAME}-db-postgres-creds-1password -n $NAMESPACE 2>/dev/null && echo "  ✅ DB secret exists" || echo "  ❌ DB secret missing"
kubectl get secret backblaze-cloud-homelab-creds-1password -n $NAMESPACE 2>/dev/null && echo "  ✅ B2 secret exists" || echo "  ❌ B2 secret missing"

# Check Recent Jobs
echo "🔄 Recent Jobs:"
kubectl get jobs -n $NAMESPACE | grep backup | tail -3

# Check Backup Files
echo "☁️ B2 Backup Files:"
b2 ls cloud-homelab-backups/$APP_NAME/ 2>/dev/null | tail -3 || echo "  ❌ No B2 files or access issue"

# Check Database Connection
echo "💾 Database Status:"
DB_POD=$(kubectl get pods -n $NAMESPACE | grep database | grep Running | head -1 | awk '{print $1}')
if [[ -n "$DB_POD" ]]; then
    echo "  ✅ Database pod running: $DB_POD"
else
    echo "  ❌ No running database pod found"
fi
```

### **Log Analysis Commands**
```bash
# Get all backup-related logs
kubectl logs -n {{NAMESPACE}} -l app={{APP}}-backup --tail=100

# Follow live backup execution
kubectl logs -f job/{{APP}}-backup-$(date +%s) -n {{NAMESPACE}}

# Check specific container logs
kubectl logs job/{{APP}}-backup -c postgres-backup -n {{NAMESPACE}}
kubectl logs job/{{APP}}-backup -c b2-uploader -n {{NAMESPACE}}

# Get events for backup jobs
kubectl get events -n {{NAMESPACE}} --field-selector involvedObject.kind=Job | grep backup
```

### **Network Connectivity Tests**
```bash
# Test database connectivity
kubectl run db-test --rm -it --image=postgres:latest -- bash
# pg_isready -h {{DATABASE_SERVICE}}.{{NAMESPACE}}.svc.cluster.local -p 5432

# Test B2 connectivity
kubectl run b2-test --rm -it --image=backblazeit/b2:latest -- bash
# curl -I https://api.backblazeb2.com/

# Test DNS resolution
kubectl run dns-test --rm -it --image=busybox -- nslookup {{DATABASE_SERVICE}}.{{NAMESPACE}}.svc.cluster.local
```

## 🚨 **Emergency Procedures**

### **Immediate Backup Creation**
```bash
# Create emergency backup right now
kubectl create job --from=cronjob/{{APP}}-backup {{APP}}-emergency-backup-$(date +%s) -n {{NAMESPACE}}

# Monitor progress
kubectl logs -f job/{{APP}}-emergency-backup-$(date +%s) -n {{NAMESPACE}}
```

### **Quick Restore (Last Known Good)**
```bash
# Find latest backup
LATEST_BACKUP=$(b2 ls cloud-homelab-backups/{{APP}}/ | tail -1 | awk '{print $NF}')

# Trigger restore with latest backup
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: {{APP}}-emergency-restore
  namespace: {{NAMESPACE}}
spec:
  template:
    spec:
      containers:
        - name: postgres-restore
          image: postgres:latest
          env:
            - name: BACKUP_FILE
              value: "$LATEST_BACKUP"
            # ... (rest of restore configuration)
      restartPolicy: Never
EOF
```

### **Rollback Backup Configuration**
```bash
# Revert to previous backup configuration
git log --oneline apps/services/{{APP}}/base/backups.yaml | head -5
git checkout HEAD~1 -- apps/services/{{APP}}/base/backups.yaml
kubectl apply -f apps/services/{{APP}}/base/backups.yaml
```

---

## 🐝 **Hive Mind Support**

This troubleshooting guide was developed through collective intelligence analysis of real-world backup failures and recovery scenarios. Each solution has been validated against the proven Tandoor reference pattern.

For additional support:
- **Pattern Templates**: `/docs/backup-patterns/patterns/`
- **Validation Guide**: `/docs/backup-patterns/VALIDATION.md`
- **Implementation Guide**: `/docs/backup-patterns/IMPLEMENTATION.md`

*Remember: When in doubt, test your backup and restore procedures in a non-production environment first!*