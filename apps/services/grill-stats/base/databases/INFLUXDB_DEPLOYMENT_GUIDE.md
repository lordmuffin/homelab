# InfluxDB 2.x Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying InfluxDB 2.x for the grill-stats temperature monitoring system. The deployment is designed for high-performance time-series data storage with proper retention policies, monitoring, and security.

## Architecture

### Components
- **InfluxDB 2.x StatefulSet**: Main time-series database
- **Multiple Buckets**: Organized by retention period and use case
- **Automated Tasks**: Data downsampling and archival
- **Monitoring**: Prometheus integration and alerting
- **Backup System**: Automated backup and recovery
- **Security**: Token-based authentication and network policies

### Data Flow
```
ThermoWorks Devices → Temperature Service → InfluxDB (realtime bucket)
                                             ↓
                                          Hourly Tasks
                                             ↓
                                        Hourly Bucket
                                             ↓
                                          Daily Tasks
                                             ↓
                                         Daily Bucket
                                             ↓
                                          Archive Tasks
                                             ↓
                                        Archive Bucket
```

## Prerequisites

### Required Secrets
Ensure the following secrets are configured in 1Password:

1. **InfluxDB Admin Credentials**:
   - `influxdb-admin-user`: Admin username
   - `influxdb-admin-password`: Admin password
   - `influxdb-admin-token`: Admin API token

2. **Service Tokens**:
   - `temperature-service-token`: Write access to realtime bucket
   - `historical-service-token`: Read access to all buckets
   - `web-ui-token`: Read access to visualization buckets
   - `monitoring-token`: Read access for monitoring

3. **Database Configuration**:
   - `influxdb-org`: Organization name (default: grill-stats)
   - `influxdb-bucket`: Primary bucket name
   - `influxdb-retention`: Default retention period

### Storage Requirements

#### Development Environment
- **Database Storage**: 20Gi
- **Backup Storage**: 10Gi
- **Storage Class**: standard

#### Production Environment
- **Database Storage**: 500Gi
- **Backup Storage**: 200Gi
- **Storage Class**: fast-ssd (recommended)

### Network Requirements
- **Ingress**: Traefik with TLS termination
- **Internal Access**: Port 8086 (HTTP API)
- **Monitoring**: Port 8086 (Prometheus metrics)

## Deployment Steps

### Step 1: Prepare Secrets

```bash
# Verify 1Password secrets are configured
kubectl get secret influxdb-secrets -n grill-stats -o yaml

# Check secret values (without exposing them)
kubectl get secret influxdb-secrets -n grill-stats -o jsonpath='{.data}' | jq 'keys'
```

### Step 2: Deploy Base Configuration

```bash
# Deploy to development environment
kubectl apply -k kustomize/overlays/dev-lab

# Deploy to production environment
kubectl apply -k kustomize/overlays/prod-lab
```

### Step 3: Verify Deployment

```bash
# Check StatefulSet status
kubectl get statefulset influxdb -n grill-stats

# Check pod status
kubectl get pods -l app.kubernetes.io/name=influxdb -n grill-stats

# Check service status
kubectl get svc influxdb-service -n grill-stats
```

### Step 4: Initialize Database

```bash
# Check initialization logs
kubectl logs influxdb-0 -n grill-stats -f

# Verify buckets are created
kubectl exec influxdb-0 -n grill-stats -- influx bucket list --org grill-stats
```

### Step 5: Verify Data Ingestion

```bash
# Test data insertion
kubectl exec influxdb-0 -n grill-stats -- influx write \
  --org grill-stats \
  --bucket grill-stats-realtime \
  --precision s \
  'temperature_readings,device_id=test_device,channel_id=1,probe_type=meat temperature=165.5 1642267800'

# Verify data was written
kubectl exec influxdb-0 -n grill-stats -- influx query \
  --org grill-stats \
  'from(bucket: "grill-stats-realtime") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "temperature_readings") |> count()'
```

## Configuration Details

### Bucket Organization

| Bucket | Retention | Purpose | Write Access | Read Access |
|--------|-----------|---------|--------------|-------------|
| grill-stats-realtime | 7 days | Real-time data ingestion | temperature-service | All services |
| grill-stats-hourly | 90 days | Hourly aggregated data | Tasks only | All services |
| grill-stats-daily | 1 year | Daily aggregated data | Tasks only | All services |
| grill-stats-archive | Infinite | Long-term storage | Tasks only | historical-service |
| grill-stats-monitoring | 30 days | System monitoring | monitoring-token | monitoring-token |

### Task Scheduling

#### Hourly Downsampling
- **Schedule**: Every hour at 5 minutes past
- **Source**: grill-stats-realtime
- **Target**: grill-stats-hourly
- **Function**: mean() aggregation

#### Daily Downsampling
- **Schedule**: Every day at 10 minutes past midnight
- **Source**: grill-stats-hourly
- **Target**: grill-stats-daily
- **Function**: mean() aggregation

#### Archive Task
- **Schedule**: Every day at 30 minutes past midnight
- **Source**: grill-stats-daily
- **Target**: grill-stats-archive
- **Function**: Direct copy

### Performance Tuning

#### Development Environment
- **CPU**: 100m - 1 core
- **Memory**: 512Mi - 2Gi
- **Query Concurrency**: 5
- **Cache Size**: 512MB

#### Production Environment
- **CPU**: 500m - 4 cores
- **Memory**: 2Gi - 8Gi
- **Query Concurrency**: 20
- **Cache Size**: 2GB

### Security Configuration

#### Authentication
- **Method**: Token-based authentication
- **Admin Token**: Full access to all operations
- **Service Tokens**: Scoped access per service

#### Network Security
- **Network Policy**: Restricts ingress to authorized services
- **TLS**: Enforced for external access
- **Ingress**: Protected by Traefik middleware

#### Authorization
- **Organization**: Single organization (grill-stats)
- **Bucket Permissions**: Service-specific access
- **Token Scoping**: Minimal required permissions

## Monitoring and Alerting

### Prometheus Metrics
- **Endpoint**: `http://influxdb-service:8086/metrics`
- **Scrape Interval**: 30 seconds
- **Service Monitor**: Automatically configured

### Key Metrics
- `influxdb_write_request_bytes_total`: Write throughput
- `influxdb_query_request_duration_seconds`: Query latency
- `influxdb_go_memstats_heap_inuse_bytes`: Memory usage
- `influxdb_task_executor_total_runs_active`: Task execution

### Alerts
- **Database Down**: InfluxDB unavailable
- **High Memory**: Memory usage > 85%
- **High Query Latency**: 99th percentile > 30s
- **Failed Tasks**: Tasks not executing
- **No Data Ingestion**: No writes for 10+ minutes

### Grafana Dashboard
- **Location**: `/kustomize/base/databases/influxdb-monitoring.yaml`
- **Panels**: Status, memory, throughput, latency, tasks, series count
- **Refresh**: 30 seconds

## Backup and Recovery

### Backup Strategy
- **Frequency**: Daily at 2 AM
- **Retention**: 7 days local, optional cloud upload
- **Method**: Native InfluxDB backup
- **Storage**: Persistent volume claim

### Backup Verification
```bash
# Check backup job status
kubectl get cronjob influxdb-backup -n grill-stats

# List recent backups
kubectl exec influxdb-0 -n grill-stats -- ls -la /backup/

# Verify backup integrity
kubectl logs job/influxdb-backup-xxxxx -n grill-stats
```

### Recovery Procedures

#### Complete Database Recovery
```bash
# 1. Stop current InfluxDB instance
kubectl scale statefulset influxdb --replicas=0 -n grill-stats

# 2. Delete existing data (if corrupted)
kubectl delete pvc influxdb-data-influxdb-0 -n grill-stats

# 3. Restart InfluxDB
kubectl scale statefulset influxdb --replicas=1 -n grill-stats

# 4. Wait for initialization
kubectl wait --for=condition=ready pod influxdb-0 -n grill-stats --timeout=300s

# 5. Restore from backup
kubectl exec influxdb-0 -n grill-stats -- /backup/restore.sh /backup/influxdb_backup_YYYYMMDD_HHMMSS.tar.gz
```

#### Partial Data Recovery
```bash
# Restore specific bucket
kubectl exec influxdb-0 -n grill-stats -- influx restore \
  --host http://localhost:8086 \
  --token $INFLUXDB_ADMIN_TOKEN \
  --org grill-stats \
  --bucket grill-stats-realtime \
  /backup/backup_directory
```

## Troubleshooting

### Common Issues

#### Pod Not Starting
```bash
# Check pod events
kubectl describe pod influxdb-0 -n grill-stats

# Check logs
kubectl logs influxdb-0 -n grill-stats

# Check storage
kubectl get pvc -n grill-stats
```

#### High Memory Usage
```bash
# Check memory metrics
kubectl top pod influxdb-0 -n grill-stats

# Adjust resource limits
kubectl patch statefulset influxdb -n grill-stats -p '{"spec":{"template":{"spec":{"containers":[{"name":"influxdb","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

#### Slow Queries
```bash
# Check query performance
kubectl exec influxdb-0 -n grill-stats -- influx query \
  --org grill-stats \
  'from(bucket: "grill-stats-realtime") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "temperature_readings") |> count()'

# Review bucket cardinality
kubectl exec influxdb-0 -n grill-stats -- influx query \
  --org grill-stats \
  'import "influxdata/influxdb/schema" schema.measurements(bucket: "grill-stats-realtime")'
```

#### Task Failures
```bash
# Check task status
kubectl exec influxdb-0 -n grill-stats -- influx task list --org grill-stats

# View task logs
kubectl exec influxdb-0 -n grill-stats -- influx task log --org grill-stats --task-id <task-id>

# Manually run task
kubectl exec influxdb-0 -n grill-stats -- influx task run --org grill-stats --task-id <task-id>
```

### Performance Optimization

#### Query Optimization
- Use appropriate time ranges
- Filter early in the query pipeline
- Avoid high-cardinality grouping
- Use aggregateWindow() for downsampling

#### Write Optimization
- Batch writes when possible
- Use consistent tag schemas
- Avoid high-cardinality tags
- Monitor write throughput

#### Storage Optimization
- Configure appropriate retention policies
- Use downsampling for long-term storage
- Monitor disk usage
- Implement data compression

## Maintenance

### Regular Tasks

#### Weekly
- Review backup integrity
- Check task execution logs
- Monitor storage usage
- Verify alert functionality

#### Monthly
- Review performance metrics
- Update retention policies if needed
- Check for software updates
- Test disaster recovery procedures

#### Quarterly
- Review schema design
- Optimize queries
- Update documentation
- Security audit

### Upgrade Procedures

#### Minor Version Updates
```bash
# Update image tag in kustomization
kubectl patch statefulset influxdb -n grill-stats -p '{"spec":{"template":{"spec":{"containers":[{"name":"influxdb","image":"influxdb:2.8-alpine"}]}}}}'

# Monitor upgrade progress
kubectl rollout status statefulset influxdb -n grill-stats
```

#### Major Version Updates
1. **Backup**: Create full backup before upgrade
2. **Test**: Verify upgrade in development environment
3. **Maintenance Window**: Schedule downtime for production
4. **Rollback Plan**: Prepare rollback procedure
5. **Documentation**: Update configuration documentation

## Security Best Practices

### Token Management
- Rotate tokens regularly (quarterly)
- Use minimal required permissions
- Store tokens securely in Kubernetes secrets
- Monitor token usage

### Network Security
- Use network policies to restrict access
- Enable TLS for all connections
- Implement proper firewall rules
- Monitor network traffic

### Data Protection
- Enable encryption at rest
- Use secure backup storage
- Implement data retention policies
- Monitor data access patterns

## Integration Points

### Services Integration
- **Temperature Service**: Write access to realtime bucket
- **Historical Service**: Read access to all buckets
- **Web UI**: Read access for visualization
- **Monitoring**: Metrics collection and alerting

### External Systems
- **Prometheus**: Metrics collection
- **Grafana**: Dashboard visualization
- **Alertmanager**: Alert routing
- **Backup Storage**: Long-term backup retention

## Support and Contacts

### Documentation
- **InfluxDB 2.x Docs**: https://docs.influxdata.com/influxdb/v2.7/
- **Flux Language**: https://docs.influxdata.com/flux/v0.x/
- **Kubernetes**: https://kubernetes.io/docs/

### Emergency Procedures
1. **Database Unavailable**: Follow recovery procedures
2. **Data Loss**: Restore from backup
3. **Performance Issues**: Scale resources
4. **Security Breach**: Rotate tokens immediately

### Monitoring
- **Grafana Dashboard**: http://grafana.homelab.local/d/influxdb
- **Prometheus Metrics**: http://prometheus.homelab.local/targets
- **Alert Manager**: http://alertmanager.homelab.local/alerts
