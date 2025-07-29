# PostgreSQL Database Deployment for Grill Stats

This directory contains the comprehensive PostgreSQL database deployment configuration for the Grill Stats application. The deployment supports multiple environments (dev-lab, prod-lab) with different configurations for development and production use.

## Architecture Overview

The PostgreSQL deployment includes:

- **Primary Database**: Main PostgreSQL instance with complete schema
- **High Availability**: Master-replica configuration for production
- **Backup System**: Automated daily backups with verification
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Security**: Role-based access control and 1Password integration

## Database Schema

The database schema supports all user stories:

### User Management (Authentication)
- `users` - User accounts and authentication
- `sessions` - JWT token management
- `login_attempts` - Security audit logging

### Device Management
- `devices` - BBQ device registration and configuration
- `device_health` - Device status and health monitoring
- `device_configuration` - Device-specific settings
- `device_channels` - Temperature probe configuration

### Live Data
- `live_temperature_readings` - Real-time temperature data
- `device_status_log` - Device event logging

### Historical Data
- `historical_temperature_readings` - Time-series temperature data
- `historical_data_summary` - Aggregated analytics data
- `data_retention_policies` - Data lifecycle management

### Secure Credentials
- `user_credentials` - Encrypted credential storage
- `encryption_keys` - Key management
- `credential_audit` - Security audit trail

## Environment Configuration

### Development (dev-lab)
```yaml
# Resource allocation
CPU: 100m-500m
Memory: 256Mi-512Mi
Storage: 10Gi

# Configuration
Authentication: md5 (relaxed)
SSL: disabled
Logging: verbose (DEBUG level)
Connections: 50 max
```

### Production (prod-lab)
```yaml
# Resource allocation
CPU: 1000m-2000m
Memory: 2Gi-4Gi
Storage: 100Gi

# Configuration
Authentication: scram-sha-256 (hardened)
SSL: enabled
Logging: structured (INFO level)
Connections: 200 max
High Availability: Master-replica setup
```

## Deployment Instructions

### Prerequisites
1. Kubernetes cluster with persistent volume support
2. 1Password Connect operator installed
3. Prometheus operator (for monitoring)
4. Cert-manager (for SSL certificates)

### 1. Configure 1Password Secrets

Create the following items in your 1Password vault:

```bash
# PostgreSQL secrets
op create item Login \
  --category=Database \
  --title="PostgreSQL Production Secrets" \
  --vault="grill-stats" \
  --url="postgresql://..." \
  postgres-user="postgres" \
  postgres-password="<secure-password>" \
  database-name="grill_stats" \
  database-user="grill_stats_user" \
  database-password="<secure-password>" \
  auth-service-user="auth_service" \
  auth-service-password="<secure-password>" \
  device-service-user="device_service" \
  device-service-password="<secure-password>" \
  encryption-service-user="encryption_service" \
  encryption-service-password="<secure-password>" \
  temperature-service-user="temperature_service" \
  temperature-service-password="<secure-password>" \
  historical-service-user="historical_service" \
  historical-service-password="<secure-password>" \
  readonly-user="readonly_user" \
  readonly-password="<secure-password>" \
  backup-user="backup_user" \
  backup-password="<secure-password>" \
  monitoring-user="monitoring_user" \
  monitoring-password="<secure-password>" \
  replication-user="replication_user" \
  replication-password="<secure-password>"
```

### 2. Deploy Database Secrets

```bash
# Deploy 1Password secrets
kubectl apply -f ../../apps/secrets/grill-stats/databases-1password.yaml

# Verify secret creation
kubectl get secrets -n grill-stats | grep postgresql
```

### 3. Deploy Database Configuration

```bash
# Deploy base configuration
kubectl apply -k .

# For development environment
kubectl apply -k ../../overlays/dev-lab

# For production environment
kubectl apply -k ../../overlays/prod-lab

# For production with high availability
kubectl apply -f ../../overlays/prod-lab/postgresql-ha.yaml
```

### 4. Verify Deployment

```bash
# Check PostgreSQL pods
kubectl get pods -n grill-stats | grep postgresql

# Check services
kubectl get svc -n grill-stats | grep postgresql

# Check persistent volumes
kubectl get pvc -n grill-stats | grep postgresql

# Test database connectivity
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT version();"
```

### 5. Initialize Database

```bash
# The database will be automatically initialized with:
# - Complete schema for all user stories
# - Database users with appropriate permissions
# - Sample data for testing
# - Functions and triggers for data management

# Verify schema creation
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "\dt"
```

## Database Users and Permissions

### Application Users
- `grill_stats_user` - Main application user with full access
- `auth_service` - Authentication service (users, sessions, credentials)
- `device_service` - Device management (devices, health, configuration)
- `encryption_service` - Encryption and key management
- `temperature_service` - Temperature data (live readings)
- `historical_service` - Historical data and analytics

### System Users
- `readonly_user` - Read-only access for reporting
- `backup_user` - Backup operations
- `monitoring_user` - Metrics and monitoring
- `replication_user` - High availability replication

## Backup and Recovery

### Automated Backups
- **Schedule**: Daily at 2:00 AM
- **Retention**: 7 days
- **Types**: Full, schema-only, data-only
- **Verification**: Automated backup verification at 3:00 AM

### Manual Backup
```bash
# Create manual backup
kubectl create job --from=cronjob/postgresql-backup manual-backup-$(date +%Y%m%d-%H%M%S) -n grill-stats

# List available backups
kubectl exec -it postgresql-backup-pvc-mount -- ls -la /backup/
```

### Restore Procedures
```bash
# Restore from backup
kubectl exec -it postgresql-0 -n grill-stats -- /scripts/restore.sh /backup/postgresql_backup_20240115_020000.sql.gz

# Point-in-time recovery
kubectl exec -it postgresql-0 -n grill-stats -- /scripts/point-in-time-recovery.sh '2024-01-15 14:30:00'
```

## Monitoring and Alerting

### Prometheus Metrics
- Connection usage and performance
- Database size and growth
- Query performance and slow queries
- Replication lag and health
- Backup status and verification

### Grafana Dashboard
- Database overview and health
- Connection and performance metrics
- Table statistics and growth
- Alert status and history

### Alerting Rules
- Database down or unreachable
- High connection usage (>80%)
- Replication lag (>60 seconds)
- Backup failures or overdue
- Slow queries or high checkpoint times

## Security Features

### Authentication
- SCRAM-SHA-256 password encryption
- Role-based access control
- Connection source restrictions
- Session management and timeout

### Encryption
- SSL/TLS for connections (production)
- Encrypted credential storage
- Key rotation and management
- Audit logging for security events

### Network Security
- Network policies for database access
- Service mesh integration
- Ingress restrictions
- VPN-only access for external connections

## Maintenance Tasks

### Regular Maintenance
```bash
# Update database statistics
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "ANALYZE;"

# Check for unused indexes
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;"

# Run vacuum to reclaim space
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "VACUUM ANALYZE;"
```

### Data Retention
```bash
# Archive old data (automated via function)
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT archive_old_data();"

# Check retention policies
kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT * FROM data_retention_policies;"
```

## Troubleshooting

### Common Issues

1. **Pod Won't Start**
   ```bash
   # Check logs
   kubectl logs postgresql-0 -n grill-stats

   # Check persistent volume
   kubectl describe pvc postgresql-pvc -n grill-stats
   ```

2. **Connection Issues**
   ```bash
   # Test connectivity
   kubectl exec -it postgresql-0 -n grill-stats -- pg_isready -U postgres

   # Check service
   kubectl get svc postgresql-service -n grill-stats
   ```

3. **Performance Issues**
   ```bash
   # Check slow queries
   kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"

   # Check database size
   kubectl exec -it postgresql-0 -n grill-stats -- psql -U postgres -d grill_stats -c "SELECT pg_size_pretty(pg_database_size('grill_stats'));"
   ```

### Support Contacts
- Database Administrator: admin@homelab.local
- DevOps Team: devops@homelab.local
- On-call: oncall@homelab.local

## Migration and Upgrades

### Version Upgrades
1. Create full backup
2. Test upgrade in development
3. Schedule maintenance window
4. Perform rolling upgrade
5. Verify functionality

### Schema Changes
1. Create migration script
2. Test in development
3. Apply to staging
4. Deploy to production
5. Monitor performance impact

This comprehensive PostgreSQL deployment provides enterprise-grade database capabilities for the Grill Stats application with proper security, monitoring, and operational procedures.
