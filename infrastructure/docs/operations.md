# K3s HA Cluster - Operations Guide

## Daily Operations

### Health Check Routine

```bash
# Set up environment
export KUBECONFIG=~/.kube/k3s-config

# Quick cluster health check
kubectl get nodes
kubectl get pods --all-namespaces --field-selector=status.phase!=Running
kubectl top nodes
kubectl top pods -A --sort-by=cpu

# Check critical services
kubectl get pods -n kube-system
kubectl get pods -n longhorn-system  
kubectl get pods -n metallb-system
kubectl get pods -n monitoring

# Verify storage health
kubectl get pv | grep -v "Bound\|Available"
kubectl get pvc -A | grep -v "Bound"

# Check load balancer services
kubectl get svc -A --field-selector=spec.type=LoadBalancer
```

### Resource Monitoring

```bash
# Node resource utilization
kubectl describe nodes | grep -A 5 "Allocated resources"

# Storage utilization
kubectl exec -n longhorn-system deployment/longhorn-ui -- \
  curl -s localhost:8000/v1/nodes | jq '.[].disks[].storageAvailable'

# Pod resource consumption
kubectl top pods -A --sort-by=memory --no-headers | head -10
kubectl top pods -A --sort-by=cpu --no-headers | head -10

# Persistent Volume usage
df -h $(kubectl get pv -o jsonpath='{.items[*].spec.hostPath.path}' | tr ' ' '\n' | sort -u)
```

## Weekly Operations

### System Updates

```bash
# Update K3s on all nodes (rolling update)
cd infrastructure/k3s/ansible

# Check current versions
ansible all -i inventory/hosts-generated.yml -m shell -a "k3s --version"

# Update to latest version (edit group_vars/all.yml first)
vim group_vars/all.yml  # Update k3s_version

# Perform rolling update
ansible-playbook -i inventory/hosts-generated.yml playbooks/update-k3s.yml

# Verify update success
kubectl get nodes -o wide
kubectl version --client --server
```

### Security Updates

```bash
# Update all nodes with security patches
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo apt update && sudo apt list --upgradable"

# Apply security updates (requires maintenance window)
ansible-playbook -i inventory/hosts-generated.yml playbooks/security-updates.yml

# Reboot nodes if required (one at a time for HA)
ansible masters -i inventory/hosts-generated.yml -m reboot --limit 'k3s-master-01'
# Wait for node to rejoin, then proceed to next master
```

### Backup Verification

```bash
# Check etcd backup status
kubectl exec -n kube-system k3s-master-01 -- \
  ls -la /var/lib/rancher/k3s/server/db/snapshots/

# Verify Longhorn backups (if configured)
kubectl exec -n longhorn-system deployment/longhorn-manager -- \
  curl -s localhost:9500/v1/backupvolumes

# Test backup restoration (non-production)
# See disaster-recovery.md for full procedures
```

### Performance Review

```bash
# Analyze cluster performance trends
kubectl top nodes --use-protocol-buffers
kubectl get --raw "/apis/metrics.k8s.io/v1beta1/nodes" | jq '.items[].usage'

# Review resource quotas and limits
kubectl describe resourcequota -A

# Check for resource-constrained pods
kubectl get pods -A -o wide --field-selector=status.phase=Pending
kubectl describe pods -A | grep -A 5 "Warning.*FailedScheduling"
```

## Monthly Operations

### Capacity Planning

```bash
# Generate capacity report
cat > capacity-report.sh <<'EOF'
#!/bin/bash
echo "=== K3s Cluster Capacity Report ===" 
echo "Date: $(date)"
echo ""

echo "Node Resources:"
kubectl describe nodes | grep -A 3 "Capacity:\|Allocatable:"
echo ""

echo "Storage Utilization:"
kubectl get pv -o custom-columns="NAME:.metadata.name,SIZE:.spec.capacity.storage,USED:.status.phase"
echo ""

echo "Top Resource Consumers:"
kubectl top pods -A --sort-by=cpu --no-headers | head -5
echo ""

echo "Namespace Resource Usage:"
kubectl get pods -A -o json | jq -r '.items[] | select(.status.phase=="Running") | "\(.metadata.namespace) \(.spec.containers[0].resources.requests.cpu // "0") \(.spec.containers[0].resources.requests.memory // "0")"' | sort | uniq -c
EOF

chmod +x capacity-report.sh
./capacity-report.sh > reports/capacity-$(date +%Y%m).txt
```

### Certificate Management

```bash
# Check certificate expiration
kubectl get secrets -A -o json | jq -r '.items[] | select(.type=="kubernetes.io/tls") | "\(.metadata.namespace)/\(.metadata.name) \(.data."tls.crt" | @base64d | split("\n")[1] | @base64d | tostring | split("Not After : ")[1] | split(" GMT")[0])"'

# Verify cert-manager certificates
kubectl get certificates -A
kubectl describe certificates -A | grep -A 5 "Events"

# Check K3s internal certificates
sudo ls -la /var/lib/rancher/k3s/server/tls/
```

### Log Management

```bash
# Archive old logs (if not using centralized logging)
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo find /var/log -name '*.log' -mtime +30 -exec gzip {} \;"

# Clean container logs
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo find /var/lib/rancher/k3s/agent/containerd -name '*.log' -mtime +7 -delete"

# Review critical log entries
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo grep -i error /var/log/k3s-audit.log | tail -10"
```

## Node Management

### Adding New Nodes

```bash
# 1. Deploy new node with Terraform
cd infrastructure/proxmox/terraform

# Add new node to terraform.tfvars
vim terraform.tfvars

# Apply changes
terraform plan
terraform apply

# 2. Update Ansible inventory
python3 scripts/generate-inventory.py --update

# 3. Configure new node
cd ../../k3s/ansible
ansible-playbook -i inventory/hosts-generated.yml --limit 'new-node-name' playbooks/configure-k3s.yml

# 4. Verify node joined cluster
kubectl get nodes
kubectl describe node new-node-name
```

### Removing Nodes

```bash
# 1. Drain node gracefully
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --timeout=300s

# 2. Delete from cluster
kubectl delete node <node-name>

# 3. Clean up node (on the node itself)
ssh ubuntu@<node-ip> sudo /usr/local/bin/k3s-uninstall.sh

# 4. Remove from infrastructure
cd infrastructure/proxmox/terraform
# Remove node from terraform.tfvars
terraform plan
terraform apply

# 5. Update inventory
python3 scripts/generate-inventory.py --update
```

### Node Maintenance

```bash
# Place node in maintenance mode
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Perform maintenance (updates, hardware changes, etc.)
ssh ubuntu@<node-ip> "sudo systemctl stop k3s && sudo reboot"

# Return node to service
kubectl uncordon <node-name>

# Verify pods are rescheduled
kubectl get pods -A -o wide --field-selector=spec.nodeName=<node-name>
```

## Storage Operations

### Longhorn Management

```bash
# Access Longhorn UI
kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80
# Visit http://localhost:8080

# Check storage node health
kubectl get nodes.longhorn.io -n longhorn-system

# Create storage class
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-custom
provisioner: driver.longhorn.io
allowVolumeExpansion: true
parameters:
  numberOfReplicas: "2"
  staleReplicaTimeout: "2880"
  fromBackup: ""
  diskSelector: "ssd"
  nodeSelector: "storage"
EOF
```

### Volume Management

```bash
# List all persistent volumes
kubectl get pv -o custom-columns="NAME:.metadata.name,SIZE:.spec.capacity.storage,ACCESS:.spec.accessModes,RECLAIM:.spec.persistentVolumeReclaimPolicy,STATUS:.status.phase,CLAIM:.spec.claimRef.name,STORAGECLASS:.spec.storageClassName"

# Expand volume (if storage class allows)
kubectl patch pvc <pvc-name> -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

# Create volume snapshot
cat <<EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: <snapshot-name>
spec:
  source:
    persistentVolumeClaimName: <pvc-name>
EOF
```

### Storage Cleanup

```bash
# Find orphaned volumes
kubectl get pv | grep Released

# Clean up released volumes
kubectl get pv -o json | jq -r '.items[] | select(.status.phase == "Released") | .metadata.name' | xargs kubectl delete pv

# Check disk usage on storage nodes
ansible workers -i inventory/hosts-generated.yml -m shell -a "df -h /var/lib/longhorn"
```

## Network Operations

### MetalLB Management

```bash
# Check MetalLB status
kubectl get pods -n metallb-system
kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system

# Add new IP range
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: new-pool
  namespace: metallb-system
spec:
  addresses:
  - 10.10.201.100-10.10.201.200
EOF

# Check IP allocation
kubectl get svc -A -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,EXTERNAL-IP:.status.loadBalancer.ingress[0].ip"
```

### Network Policies

```bash
# List current network policies
kubectl get networkpolicy -A

# Test network connectivity between pods
kubectl run test-pod --image=busybox --rm -it -- /bin/sh

# Create network policy template
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF
```

## Security Operations

### RBAC Management

```bash
# List cluster roles and bindings
kubectl get clusterroles
kubectl get clusterrolebindings

# Create service account with limited permissions
kubectl create serviceaccount app-reader -n production
kubectl create rolebinding app-reader-binding --clusterrole=view --serviceaccount=production:app-reader -n production

# Generate kubeconfig for service account
kubectl create token app-reader -n production --duration=24h
```

### Secret Management

```bash
# List all secrets
kubectl get secrets -A

# Create secret from literal values
kubectl create secret generic app-secrets \
  --from-literal=database-url="postgres://user:pass@host:5432/db" \
  --from-literal=api-key="secret-key" \
  -n production

# Rotate secrets (example)
kubectl create secret generic app-secrets-new \
  --from-literal=database-url="postgres://user:newpass@host:5432/db" \
  -n production --dry-run=client -o yaml | kubectl apply -f -
```

### Security Scanning

```bash
# Run security benchmarks (if tools are installed)
kubectl run kube-bench --image=aquasec/kube-bench:latest --rm -it -- --benchmark k3s

# Check pod security contexts
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'

# Audit RBAC permissions
kubectl auth can-i --list --as=system:serviceaccount:default:default
```

## Monitoring and Alerting

### Metrics Collection

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Visit http://localhost:9090/targets

# Query cluster metrics
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=up'

# Custom metrics examples
kubectl get --raw /metrics | grep -i k3s
```

### Alert Management

```bash
# Check active alerts
kubectl port-forward -n monitoring svc/alertmanager 9093:80
# Visit http://localhost:9093

# Silence alerts (via API)
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{"matchers": [{"name": "alertname", "value": "NodeDown"}], "startsAt": "2024-01-01T00:00:00Z", "endsAt": "2024-01-01T01:00:00Z", "createdBy": "admin", "comment": "Planned maintenance"}'
```

### Dashboard Management

```bash
# Access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80
# Default login: admin/admin

# Import new dashboard (via ConfigMap)
kubectl create configmap custom-dashboard \
  --from-file=dashboard.json \
  -n monitoring \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Emergency Procedures

### Emergency Contacts
- **Primary On-Call**: +1-xxx-xxx-xxxx
- **Infrastructure Team**: infra@company.com  
- **Platform Team**: platform@company.com
- **Escalation Manager**: manager@company.com

### Incident Response

```bash
# 1. Assess situation
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Running

# 2. Capture diagnostics
kubectl cluster-info dump --output-directory=/tmp/k3s-diagnostics

# 3. Check recent events
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

# 4. Generate incident report
cat > incident-$(date +%Y%m%d-%H%M).txt <<EOF
Incident Date: $(date)
Cluster: homelab-k3s
Severity: [Critical/High/Medium/Low]
Impact: [Description]

Timeline:
- $(date): Incident detected
- $(date): Investigation started

Actions Taken:
- [List actions]

Resolution:
- [Description of resolution]

Root Cause:
- [Analysis]

Prevention:
- [Measures to prevent recurrence]
EOF
```

### Quick Recovery Commands

```bash
# Restart core services
kubectl rollout restart deployment/coredns -n kube-system
kubectl rollout restart daemonset/longhorn-manager -n longhorn-system

# Force pod eviction from unhealthy node
kubectl get pods -A --field-selector=spec.nodeName=<unhealthy-node> -o name | xargs kubectl delete

# Emergency cluster backup
kubectl get all -A -o yaml > emergency-backup-$(date +%Y%m%d).yaml
```

## Maintenance Windows

### Scheduled Maintenance

```bash
# 1. Pre-maintenance checklist
- [ ] Backup verification complete
- [ ] Change management approval
- [ ] Stakeholder notification sent
- [ ] Rollback plan prepared
- [ ] Emergency contacts notified

# 2. Maintenance execution
- [ ] Enable maintenance mode
- [ ] Perform planned changes
- [ ] Verify system health
- [ ] Test critical applications
- [ ] Exit maintenance mode

# 3. Post-maintenance
- [ ] System health confirmed
- [ ] Performance baseline verified
- [ ] Documentation updated
- [ ] Stakeholder notification sent
```

### Maintenance Mode

```bash
# Enable maintenance mode (prevent new scheduling)
kubectl taint nodes --all node.kubernetes.io/maintenance=true:NoSchedule

# Disable maintenance mode
kubectl taint nodes --all node.kubernetes.io/maintenance=true:NoSchedule-
```

## Performance Tuning

### Node Optimization

```bash
# Check node resource allocation
kubectl describe node <node-name> | grep -A 10 "Allocated resources"

# Optimize kubelet configuration
ssh ubuntu@<node-ip> sudo vim /etc/rancher/k3s/config.yaml
# Add kubelet args for performance tuning
```

### Application Optimization

```bash
# Set resource requests and limits
kubectl patch deployment <app-name> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"requests":{"cpu":"100m","memory":"128Mi"},"limits":{"cpu":"500m","memory":"512Mi"}}}]}}}}'

# Configure horizontal pod autoscaler
kubectl autoscale deployment <app-name> --cpu-percent=70 --min=2 --max=10
```

## Automation and Scripts

### Useful Automation Scripts

```bash
# Create cluster health check script
cat > /usr/local/bin/k3s-health-check <<'EOF'
#!/bin/bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "=== K3s Cluster Health Check ==="
echo "Timestamp: $(date)"

# Check node status
echo "Node Status:"
kubectl get nodes

# Check critical pods
echo "Critical Pods:"
kubectl get pods -n kube-system,longhorn-system,metallb-system | grep -v Running

# Check resources
echo "Resource Usage:"
kubectl top nodes

exit 0
EOF

chmod +x /usr/local/bin/k3s-health-check

# Schedule via cron
echo "0 */6 * * * /usr/local/bin/k3s-health-check > /var/log/k3s-health.log 2>&1" | crontab -
```

This operations guide provides comprehensive day-to-day, weekly, and monthly operational procedures for maintaining your K3s HA cluster. Regular execution of these procedures ensures optimal cluster health, performance, and security.