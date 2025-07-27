# Infrastructure Deployment Checklist & Runbooks

## Pre-Deployment Checklist

### Environment Preparation
- [ ] Kubernetes cluster is healthy and accessible
- [ ] Required namespaces exist (tandoor, monitoring, kube-system)
- [ ] Storage classes are configured (sata, democratic-csi)
- [ ] Network policies allow required communication
- [ ] DNS resolution is working within cluster

### Secrets and Configuration
- [ ] 1Password operator is installed and configured
- [ ] Required secrets exist in 1Password:
  - [ ] `tandoor-db-postgres-creds-1password`
  - [ ] `tandoor-secret-creds-1password`
  - [ ] `backblaze-cloud-homelab-creds-1password`
- [ ] ConfigMaps are applied for application configuration
- [ ] RBAC permissions are correctly configured

### Resource Requirements
- [ ] Node resources available:
  - [ ] Tandoor app: 300m CPU, 256Mi-768Mi memory
  - [ ] PostgreSQL: 300m CPU, 256Mi-768Mi memory
  - [ ] Backup jobs: 200m CPU, 512Mi memory (peak)
- [ ] Storage available:
  - [ ] Database: 20Gi persistent storage
  - [ ] Static files: Configurable via PVC
  - [ ] Media files: Configurable via PVC

## Deployment Runbook

### Step 1: Database Deployment
```bash
# Apply PostgreSQL cluster
kubectl apply -f apps/services/tandoor/base/db.yaml

# Wait for database to be ready
kubectl wait --for=condition=Ready pod -l cnpg.io/cluster=tandoor-database -n tandoor --timeout=300s

# Verify database connectivity
kubectl run db-test --image=postgres:16 --rm -it --restart=Never -- \
  psql -h tandoor-database-rw.tandoor.svc.cluster.local -U tandoor -d tandoor -c "SELECT version();"
```

### Step 2: Backup System Deployment
```bash
# Apply backup CronJobs
kubectl apply -f apps/services/tandoor/base/backups.yaml
kubectl apply -f apps/services/tandoor/base/media-backup.yaml

# Verify backup job configuration
kubectl describe cronjob postgres-backup -n tandoor
kubectl describe cronjob tandoor-media-backup -n tandoor

# Test backup execution (optional)
kubectl create job --from=cronjob/postgres-backup manual-backup-test -n tandoor
```

### Step 3: Application Deployment
```bash
# Apply application manifests
kubectl apply -k apps/services/tandoor/base/

# Wait for deployment
kubectl wait --for=condition=Available deployment/tandoor -n tandoor --timeout=300s

# Verify pods are running
kubectl get pods -n tandoor -o wide
```

### Step 4: Service and Ingress
```bash
# Apply services and ingress
kubectl apply -f apps/services/tandoor/base/svc.yaml
kubectl apply -f apps/services/tandoor/base/ingress.yaml

# Test service connectivity
kubectl run service-test --image=alpine --rm -it --restart=Never -- \
  wget -qO- http://tandoor.tandoor.svc.cluster.local:8080/
```

### Step 5: Validation
```bash
# Run comprehensive validation
kubectl apply -f validation-framework.yaml
kubectl wait --for=condition=Complete job/infrastructure-validation -n kube-system --timeout=600s
kubectl logs -f job/infrastructure-validation -n kube-system
```

## Post-Deployment Verification

### Application Health Checks
- [ ] Web interface is accessible and responsive
- [ ] Database connections are working
- [ ] User authentication functions correctly
- [ ] File uploads work (static and media)
- [ ] Recipe creation/editing works
- [ ] Search functionality works

### Backup Verification
- [ ] Database backup job completes successfully
- [ ] Backup files are uploaded to Backblaze B2
- [ ] Media backup job completes successfully
- [ ] Backup retention policies are working
- [ ] Restore procedure has been tested

### Monitoring and Observability
- [ ] Prometheus is scraping application metrics
- [ ] PostgreSQL metrics are available
- [ ] Alert rules are configured and firing appropriately
- [ ] Grafana dashboards show application data
- [ ] Log aggregation is collecting application logs

### Security Verification
- [ ] Secrets are properly mounted and not exposed
- [ ] Network policies restrict unauthorized access
- [ ] RBAC permissions follow least privilege
- [ ] Container images are from trusted sources
- [ ] Security scanning passes (if implemented)

## Rollback Procedures

### Emergency Rollback
```bash
# Scale down current deployment
kubectl scale deployment tandoor --replicas=0 -n tandoor

# Restore from backup (if needed)
# See disaster-recovery-plan.yaml for detailed procedures

# Deploy previous version
kubectl set image deployment/tandoor recipes=vabene1111/recipes:previous-tag -n tandoor
kubectl rollout undo deployment/tandoor -n tandoor

# Verify rollback
kubectl rollout status deployment/tandoor -n tandoor
```

### Database Rollback
```bash
# Create new database instance
kubectl apply -f rollback-db.yaml

# Restore from backup
# Execute restore procedure from disaster-recovery-plan.yaml

# Update application to use rollback database
kubectl patch deployment tandoor -n tandoor -p '{"spec":{"template":{"spec":{"containers":[{"name":"recipes","env":[{"name":"POSTGRES_HOST","value":"tandoor-database-rollback-rw.tandoor.svc.cluster.local"}]}]}}}}'
```

## Maintenance Procedures

### Regular Maintenance (Monthly)
- [ ] Update container images to latest stable versions
- [ ] Review and update resource requests/limits
- [ ] Clean up old backup files beyond retention period
- [ ] Update SSL certificates (if self-managed)
- [ ] Review security scan results
- [ ] Test disaster recovery procedures

### Emergency Response
1. **Application Down**: Check pod status, restart deployment
2. **Database Issues**: Check CNPG cluster status, review logs
3. **Storage Full**: Increase PVC size, clean up old data
4. **Network Issues**: Verify DNS, check network policies
5. **Backup Failures**: Check credentials, B2 connectivity

## Troubleshooting Guide

### Common Issues

#### Pod Stuck in Pending
```bash
kubectl describe pod <pod-name> -n tandoor
# Check for resource constraints, PVC mounting issues
```

#### Database Connection Failures
```bash
kubectl logs -f deployment/tandoor -n tandoor
kubectl describe clusters.postgresql.cnpg.io tandoor-database -n tandoor
```

#### Backup Job Failures
```bash
kubectl logs job/<backup-job-name> -n tandoor
# Check B2 credentials, network connectivity
```

#### Storage Issues
```bash
kubectl get pvc -n tandoor
kubectl describe pvc <pvc-name> -n tandoor
# Check storage class, available capacity
```

### Performance Tuning

#### Database Optimization
- Monitor query performance via pg_stat_statements
- Adjust shared_buffers based on available memory
- Consider read replicas for heavy read workloads

#### Application Optimization
- Adjust GUNICORN_WORKERS based on CPU cores
- Implement caching strategies
- Optimize static file serving

#### Resource Optimization
- Monitor actual resource usage vs requests/limits
- Adjust based on usage patterns
- Implement horizontal pod autoscaling if needed

## Contacts and Escalation

### Primary Contacts
- **Infrastructure Team**: homelab-infra@domain.com
- **Application Team**: tandoor-app@domain.com
- **Security Team**: security@domain.com

### Escalation Matrix
1. **Level 1**: Application restart, basic troubleshooting
2. **Level 2**: Infrastructure changes, backup restoration
3. **Level 3**: Disaster recovery, complete system rebuild

### External Dependencies
- **Backblaze B2**: backup-support@backblaze.com
- **CloudNative-PG**: GitHub issues for technical problems
- **Tandoor Recipes**: GitHub issues for application bugs

## Documentation Updates

This runbook should be updated when:
- New features are deployed
- Infrastructure changes are made
- Procedures are modified
- Issues and resolutions are discovered

Last Updated: $(date)
Version: 1.0.0