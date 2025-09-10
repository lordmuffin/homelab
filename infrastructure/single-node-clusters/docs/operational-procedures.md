# Operational Procedures for Single-Node Clusters

## 🚀 Daily Operations

### Morning Health Check Routine (5 minutes)
```bash
#!/bin/bash
# Daily health check script

echo "🌅 Morning Health Check - $(date)"

# Check external load balancer
echo "📊 Load Balancer Status:"
curl -s http://10.0.1.100:8404/stats | grep -E "(Status|Active)" | head -5

# Check all cluster nodes
for node in node1-compute node2-storage node3-general; do
    echo "🔍 Checking ${node}:"
    ssh root@$(echo ${node} | cut -d'-' -f1 | sed 's/node1/10.0.1.101/;s/node2/10.0.1.102/;s/node3/10.0.1.103/') \
        "kubectl get nodes --no-headers | grep Ready && echo '✅ Cluster healthy'"
done

# Check critical services
echo "🛠️  Critical Services:"
kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml get pods -A | grep -E "(argocd|traefik|democratic-csi)" | grep Running | wc -l
echo "services running"

echo "✅ Health check completed"
```

### Evening Backup Verification (3 minutes)
```bash
#!/bin/bash
# Verify daily backups

echo "🌙 Evening Backup Check - $(date)"

# Check Velero backup status
kubectl get backups -n velero --sort-by=.metadata.creationTimestamp | tail -5

# Verify NFS connectivity
showmount -e 10.0.1.200 | head -3

# Check storage utilization
df -h | grep -E "(nfs|storage)" 

echo "💾 Backup verification completed"
```

## 🔧 Weekly Maintenance (30 minutes)

### System Updates and Patching
```bash
#!/bin/bash
# Weekly maintenance script

LOG_FILE="/var/log/weekly-maintenance.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "🔄 Weekly Maintenance - $(date)"

# Update package repositories
echo "📦 Updating package repositories..."
apt-get update -qq

# Check for security updates
echo "🔒 Checking security updates..."
apt list --upgradable | grep -i security

# Update K3s if newer version available
CURRENT_K3S=$(k3s --version | head -1 | awk '{print $3}')
LATEST_K3S=$(curl -s https://api.github.com/repos/k3s-io/k3s/releases/latest | jq -r .tag_name)

if [[ "$CURRENT_K3S" != "$LATEST_K3S" ]]; then
    echo "⬆️  K3s update available: $CURRENT_K3S -> $LATEST_K3S"
    echo "Run: curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=$LATEST_K3S sh -"
fi

# Resource utilization report
echo "📊 Resource Utilization:"
kubectl top nodes || echo "Metrics server not available"

# Storage cleanup
echo "🧹 Storage Cleanup:"
docker system prune -f
kubectl delete pods --field-selector=status.phase=Succeeded -A

echo "✅ Weekly maintenance completed"
```

### Performance Analysis
```bash
#!/bin/bash
# Weekly performance analysis

echo "📈 Performance Analysis - $(date)"

# CPU and Memory trends (last 7 days)
echo "💻 Resource Usage Trends:"
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory

# Top resource consuming pods
echo "🔝 Top Resource Consumers:"
kubectl top pods --all-namespaces --sort-by=memory | head -10

# Network statistics
echo "🌐 Network Statistics:"
ss -tuln | grep -E ":80|:443|:6443" | wc -l
echo "active connections"

# Storage usage by namespace
echo "💾 Storage Usage by Namespace:"
kubectl get pv -o custom-columns=NAME:.metadata.name,SIZE:.spec.capacity.storage,STATUS:.status.phase | grep Bound

echo "📊 Analysis completed"
```

## 🚨 Incident Response Procedures

### Service Outage Response (15 minutes)

#### 1. Initial Assessment
```bash
#!/bin/bash
# Incident response - initial assessment

INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="/var/log/incidents/${INCIDENT_ID}.log"
mkdir -p /var/log/incidents
exec 1> >(tee -a "$LOG_FILE")

echo "🚨 INCIDENT RESPONSE - $INCIDENT_ID"
echo "Start Time: $(date)"

# Check external load balancer
echo "1️⃣ Load Balancer Status:"
curl -s --max-time 5 http://10.0.1.100:8404/stats > /tmp/lb-status.html
if [[ $? -eq 0 ]]; then
    echo "✅ Load balancer responding"
    grep -E "UP|DOWN" /tmp/lb-status.html
else
    echo "❌ Load balancer not responding"
fi

# Check cluster connectivity
echo "2️⃣ Cluster Connectivity:"
for node in 10.0.1.101 10.0.1.102 10.0.1.103; do
    if ping -c 1 -W 3 $node > /dev/null 2>&1; then
        echo "✅ Node $node reachable"
    else
        echo "❌ Node $node unreachable"
    fi
done

# Check Kubernetes API
echo "3️⃣ Kubernetes API Status:"
for node in 10.0.1.101 10.0.1.102 10.0.1.103; do
    if ssh root@$node "kubectl get nodes" > /dev/null 2>&1; then
        echo "✅ K8s API on $node working"
    else
        echo "❌ K8s API on $node failed"
    fi
done

echo "📋 Initial assessment completed - $INCIDENT_ID"
```

#### 2. Service Recovery
```bash
#!/bin/bash
# Service recovery procedures

echo "🔧 RECOVERY PROCEDURES"

# Restart failed services
echo "♻️  Restarting Critical Services:"

# Check and restart HAProxy
if ! pgrep haproxy > /dev/null; then
    echo "Restarting HAProxy..."
    systemctl restart haproxy
fi

# Check and restart K3s on each node
for node in 10.0.1.101 10.0.1.102 10.0.1.103; do
    if ! ssh root@$node "systemctl is-active --quiet k3s"; then
        echo "Restarting K3s on $node..."
        ssh root@$node "systemctl restart k3s"
    fi
done

# Force Flux reconciliation
echo "🔄 Forcing Flux Reconciliation:"
flux reconcile source git homelab-gitops
flux reconcile kustomization --all

# Verify service restoration
echo "✅ Service Verification:"
sleep 30
curl -s http://10.0.1.100:8404/stats | grep -E "UP.*OPEN" | wc -l
echo "services restored"

echo "🎯 Recovery procedures completed"
```

### Data Recovery Procedures

#### Database Recovery
```bash
#!/bin/bash
# Database recovery from NFS backup

DB_NAME="$1"
RESTORE_DATE="$2"

if [[ -z "$DB_NAME" || -z "$RESTORE_DATE" ]]; then
    echo "Usage: $0 <db-name> <YYYY-MM-DD>"
    exit 1
fi

echo "💾 Database Recovery: $DB_NAME from $RESTORE_DATE"

# Mount backup location
mkdir -p /tmp/db-restore
mount -t nfs 10.0.1.200:/volume1/backups /tmp/db-restore

# Find backup file
BACKUP_FILE="/tmp/db-restore/databases/${DB_NAME}-${RESTORE_DATE}.sql.gz"

if [[ -f "$BACKUP_FILE" ]]; then
    echo "✅ Backup file found: $BACKUP_FILE"
    
    # Create recovery pod
    kubectl run db-restore-pod --rm -i --image=postgres:13 -- bash -c "
        gunzip < /backup/${DB_NAME}-${RESTORE_DATE}.sql.gz | psql -h postgresql.default -U admin
    " --overrides='
    {
        "spec": {
            "volumes": [
                {
                    "name": "backup-vol",
                    "nfs": {
                        "server": "10.0.1.200",
                        "path": "/volume1/backups/databases"
                    }
                }
            ],
            "containers": [
                {
                    "name": "db-restore-pod",
                    "image": "postgres:13",
                    "volumeMounts": [
                        {
                            "name": "backup-vol",
                            "mountPath": "/backup"
                        }
                    ]
                }
            ]
        }
    }'
    
    echo "✅ Database restore completed"
else
    echo "❌ Backup file not found: $BACKUP_FILE"
    echo "Available backups:"
    ls -la /tmp/db-restore/databases/${DB_NAME}-*
fi

umount /tmp/db-restore
```

#### Application Data Recovery
```bash
#!/bin/bash
# Application data recovery

APP_NAME="$1"
NAMESPACE="${2:-default}"

echo "📱 Application Data Recovery: $APP_NAME in $NAMESPACE"

# Scale down application
echo "⏸️  Scaling down application..."
kubectl scale deployment/$APP_NAME --replicas=0 -n $NAMESPACE

# Wait for pods to terminate
kubectl wait --for=delete pod -l app=$APP_NAME -n $NAMESPACE --timeout=300s

# Restore data from backup
echo "💾 Restoring data from backup..."
kubectl create job restore-$APP_NAME-$(date +%s) --image=alpine:latest -n $NAMESPACE -- sh -c "
    apk add --no-cache rsync
    rsync -av /backup/$APP_NAME/ /data/
" --overrides='
{
    "spec": {
        "template": {
            "spec": {
                "volumes": [
                    {
                        "name": "backup-vol",
                        "nfs": {
                            "server": "10.0.1.200",
                            "path": "/volume1/backups"
                        }
                    },
                    {
                        "name": "data-vol",
                        "persistentVolumeClaim": {
                            "claimName": "'$APP_NAME'-data"
                        }
                    }
                ],
                "containers": [
                    {
                        "name": "restore",
                        "image": "alpine:latest",
                        "volumeMounts": [
                            {
                                "name": "backup-vol",
                                "mountPath": "/backup"
                            },
                            {
                                "name": "data-vol",
                                "mountPath": "/data"
                            }
                        ]
                    }
                ]
            }
        }
    }
}'

# Scale up application
echo "▶️  Scaling up application..."
kubectl scale deployment/$APP_NAME --replicas=1 -n $NAMESPACE

# Verify restoration
kubectl wait --for=condition=available deployment/$APP_NAME -n $NAMESPACE --timeout=300s
echo "✅ Application data recovery completed"
```

## 🔄 Backup and Recovery

### Automated Backup Schedule

#### Daily Backups (Automated)
```yaml
# CronJob for daily application backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-app-backup
  namespace: backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: velero/velero:latest
            command:
            - /bin/sh
            - -c
            - |
              # Application data backup
              velero backup create daily-$(date +%Y%m%d) \
                --include-namespaces default,argocd,monitoring \
                --storage-location nfs-backup
              
              # Database backup
              kubectl exec -n default postgres-0 -- pg_dumpall -U admin | \
                gzip > /backup/postgres-$(date +%Y%m%d).sql.gz
              
              # Cleanup old backups (keep 7 days)
              find /backup -name "*.gz" -mtime +7 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            nfs:
              server: "10.0.1.200"
              path: "/volume1/backups"
          restartPolicy: OnFailure
```

#### Weekly System Backups
```bash
#!/bin/bash
# Weekly full system backup

echo "📦 Weekly System Backup - $(date)"

BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/mnt/backup/weekly/$BACKUP_DATE"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Kubernetes resources
echo "☸️  Backing up Kubernetes resources..."
for node in 10.0.1.101 10.0.1.102 10.0.1.103; do
    node_name=$(ssh root@$node hostname)
    kubectl --server=https://$node:6443 get all --all-namespaces -o yaml > \
        $BACKUP_DIR/k8s-${node_name}-resources.yaml
done

# Backup configurations
echo "⚙️  Backing up configurations..."
cp -r /etc/rancher/k3s $BACKUP_DIR/k3s-config
cp -r /home/lordmuffin/Claude/Git/homelab/infrastructure/single-node-clusters $BACKUP_DIR/cluster-configs

# Backup certificates
echo "🔐 Backing up certificates..."
cp -r /etc/ssl/certs/homelab $BACKUP_DIR/certificates

# Create archive
echo "🗜️  Creating backup archive..."
tar -czf /mnt/backup/weekly/system-backup-$BACKUP_DATE.tar.gz -C /mnt/backup/weekly $BACKUP_DATE

# Cleanup
rm -rf $BACKUP_DIR

# Verify backup
if [[ -f "/mnt/backup/weekly/system-backup-$BACKUP_DATE.tar.gz" ]]; then
    echo "✅ Weekly backup completed: system-backup-$BACKUP_DATE.tar.gz"
    ls -lh /mnt/backup/weekly/system-backup-$BACKUP_DATE.tar.gz
else
    echo "❌ Weekly backup failed!"
fi
```

## 🔍 Monitoring and Alerting

### Custom Health Metrics
```bash
#!/bin/bash
# Custom metrics collection for Prometheus

METRICS_DIR="/var/lib/node_exporter/textfile_collector"
mkdir -p $METRICS_DIR

# Cluster health metric
if kubectl get nodes | grep -q "Ready"; then
    echo "homelab_cluster_health 1" > $METRICS_DIR/cluster_health.prom
else
    echo "homelab_cluster_health 0" > $METRICS_DIR/cluster_health.prom
fi

# Service availability metrics
for service in argocd traefik democratic-csi prometheus grafana; do
    if kubectl get pods -A -l app.kubernetes.io/name=$service | grep -q Running; then
        echo "homelab_service_available{service=\"$service\"} 1" >> $METRICS_DIR/service_health.prom
    else
        echo "homelab_service_available{service=\"$service\"} 0" >> $METRICS_DIR/service_health.prom
    fi
done

# Storage capacity metrics
df -h /var/lib/rancher | tail -1 | awk '{
    gsub(/%/, "", $5)
    print "homelab_storage_used_percent " $5
}' > $METRICS_DIR/storage_usage.prom

# Load balancer backend health
curl -s http://10.0.1.100:8404/stats | grep "UP" | wc -l | awk '{
    print "homelab_lb_backends_up " $1
}' > $METRICS_DIR/lb_health.prom
```

### Alert Response Playbooks

#### High CPU Usage Alert
```bash
#!/bin/bash
# Response to high CPU usage alert

NODE="$1"
THRESHOLD="$2"

echo "🔥 High CPU Alert Response - Node: $NODE, Threshold: $THRESHOLD%"

# Identify top CPU consumers
echo "🔍 Top CPU Consumers:"
ssh root@$NODE "kubectl top pods --all-namespaces --sort-by=cpu | head -10"

# Check for resource-intensive jobs
echo "⚙️  Checking for batch jobs:"
kubectl get jobs -A | grep -E "(Running|Active)"

# CPU throttling check
echo "🎯 CPU Throttling Status:"
ssh root@$NODE "grep throttled /sys/fs/cgroup/cpu/cpu.stat || echo 'No throttling detected'"

# Recommendations
echo "💡 Recommendations:"
echo "1. Consider scaling down non-critical workloads"
echo "2. Check for runaway processes"
echo "3. Evaluate resource requests and limits"

# Auto-remediation (if enabled)
if [[ "$AUTO_REMEDIATE" == "true" ]]; then
    echo "🤖 Auto-remediation enabled - scaling down low-priority workloads..."
    kubectl scale deployment -l priority=low --replicas=0 -A
fi
```

#### Storage Space Alert
```bash
#!/bin/bash
# Response to storage space alert

MOUNT_POINT="$1"
USAGE_PERCENT="$2"

echo "💾 Storage Space Alert - Mount: $MOUNT_POINT, Usage: $USAGE_PERCENT%"

# Analyze disk usage
echo "📊 Disk Usage Analysis:"
du -sh /var/lib/rancher/k3s/* | sort -hr | head -10

# Check for old container images
echo "🐳 Container Images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -10

# Clean up recommendations
echo "🧹 Cleanup Recommendations:"
echo "1. docker system prune -a"
echo "2. kubectl delete pods --field-selector=status.phase=Succeeded -A"
echo "3. Clean up old log files"

# Auto-cleanup (if safe)
if [[ "$USAGE_PERCENT" -gt 90 ]]; then
    echo "🚨 Critical storage usage - performing automatic cleanup..."
    docker system prune -f
    kubectl delete pods --field-selector=status.phase=Succeeded -A
    journalctl --vacuum-time=7d
fi

echo "✅ Storage alert response completed"
```

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Pod Stuck in Pending State
```bash
#!/bin/bash
# Debug pod scheduling issues

POD_NAME="$1"
NAMESPACE="${2:-default}"

echo "🔍 Debugging Pod Scheduling: $POD_NAME in $NAMESPACE"

# Get pod details
kubectl describe pod $POD_NAME -n $NAMESPACE

# Check resource availability
echo "📊 Node Resource Availability:"
kubectl describe nodes | grep -A5 "Allocated resources"

# Check for taints and tolerations
echo "🏷️  Node Taints:"
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

# Check PVC status if applicable
echo "💾 PVC Status:"
kubectl get pvc -n $NAMESPACE | grep -E "(Pending|Lost)"

# Recommendations
echo "💡 Troubleshooting Steps:"
echo "1. Check resource requests vs available resources"
echo "2. Verify node selectors and affinity rules"
echo "3. Check for unsatisfied PVC requirements"
echo "4. Verify image pull secrets"
```

#### Issue: Service Not Accessible
```bash
#!/bin/bash
# Debug service accessibility issues

SERVICE_NAME="$1"
NAMESPACE="${2:-default}"

echo "🌐 Debugging Service Accessibility: $SERVICE_NAME in $NAMESPACE"

# Check service status
kubectl get svc $SERVICE_NAME -n $NAMESPACE -o wide

# Check endpoints
kubectl get endpoints $SERVICE_NAME -n $NAMESPACE

# Check pod status
kubectl get pods -l $(kubectl get svc $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector}' | sed 's/[{}]//g; s/:/=/g; s/ /,/g') -n $NAMESPACE

# Test internal connectivity
echo "🔗 Testing Internal Connectivity:"
kubectl run test-pod --rm -i --image=busybox --restart=Never -- nslookup $SERVICE_NAME.$NAMESPACE.svc.cluster.local

# Check ingress if applicable
if kubectl get ingress -n $NAMESPACE | grep -q $SERVICE_NAME; then
    echo "📡 Ingress Status:"
    kubectl get ingress -n $NAMESPACE | grep $SERVICE_NAME
fi

echo "✅ Service debugging completed"
```

This operational procedures guide provides comprehensive day-to-day management capabilities for the single-node cluster architecture, ensuring reliable operation and quick issue resolution.