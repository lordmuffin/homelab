# K3s HA Cluster - Troubleshooting Guide

## Quick Diagnostics

### Emergency Triage Commands

```bash
# Set environment
export KUBECONFIG=~/.kube/k3s-config

# Quick cluster status
kubectl get nodes --no-headers | wc -l  # Should be 10
kubectl get nodes | grep -v Ready       # Should be empty
kubectl get pods -A | grep -E "Error|CrashLoop|Pending" | wc -l  # Should be 0

# Critical service check
kubectl get pods -n kube-system | grep -E "coredns|metrics-server"
kubectl get pods -n longhorn-system | grep -E "longhorn-manager|longhorn-driver"
kubectl get pods -n metallb-system | grep -E "controller|speaker"

# Resource pressure check
kubectl top nodes | grep -E "[89][0-9]%|100%"  # High CPU/Memory usage
kubectl get pv | grep -E "Released|Failed"      # Storage issues
```

### Gathering Diagnostic Information

```bash
# Comprehensive cluster dump
kubectl cluster-info dump --output-directory=/tmp/k3s-diagnostics-$(date +%Y%m%d-%H%M)

# Node-specific diagnostics
ansible all -i infrastructure/k3s/ansible/inventory/hosts-generated.yml \
  -m shell -a "sudo journalctl -u k3s -n 50" > /tmp/k3s-logs-$(date +%Y%m%d).txt

# System resource snapshot
kubectl top nodes > /tmp/nodes-resources-$(date +%Y%m%d).txt
kubectl top pods -A > /tmp/pods-resources-$(date +%Y%m%d).txt
kubectl get events -A --sort-by='.lastTimestamp' | tail -50 > /tmp/recent-events-$(date +%Y%m%d).txt
```

## Node Issues

### Node Not Ready

**Symptoms:**
- Node shows "NotReady" status
- Pods not scheduling on the node
- Network connectivity issues

**Diagnosis:**
```bash
# Check node status details
kubectl describe node <node-name>

# Check K3s service status
ssh ubuntu@<node-ip> sudo systemctl status k3s
ssh ubuntu@<node-ip> sudo journalctl -u k3s -n 50

# Check system resources
ssh ubuntu@<node-ip> "df -h && free -h && uptime"

# Check container runtime
ssh ubuntu@<node-ip> sudo systemctl status containerd
```

**Common Causes & Solutions:**

1. **Disk Space Full:**
```bash
# Check disk usage
ssh ubuntu@<node-ip> df -h

# Clean container images
ssh ubuntu@<node-ip> sudo k3s ctr images prune
ssh ubuntu@<node-ip> sudo docker system prune -af  # if docker is installed

# Clean logs
ssh ubuntu@<node-ip> sudo journalctl --vacuum-time=7d
```

2. **Memory Pressure:**
```bash
# Check memory usage
ssh ubuntu@<node-ip> free -h

# Check OOM killer activity
ssh ubuntu@<node-ip> sudo dmesg | grep -i "killed process"

# Restart kubelet to free memory
ssh ubuntu@<node-ip> sudo systemctl restart k3s
```

3. **Network Issues:**
```bash
# Test connectivity to masters
ssh ubuntu@<node-ip> ping -c 3 <master-ip>
ssh ubuntu@<node-ip> telnet <master-ip> 6443

# Check CNI status
ssh ubuntu@<node-ip> sudo ip link show flannel.1
ssh ubuntu@<node-ip> sudo iptables -L | grep flannel

# Restart networking
ssh ubuntu@<node-ip> sudo systemctl restart k3s
```

4. **Certificate Issues:**
```bash
# Check certificate expiry
ssh ubuntu@<node-ip> sudo openssl x509 -in /var/lib/rancher/k3s/agent/client-ca.crt -text -noout | grep "Not After"

# Regenerate certificates (last resort)
ssh ubuntu@<node-ip> sudo rm -rf /var/lib/rancher/k3s/agent/client-*
ssh ubuntu@<node-ip> sudo systemctl restart k3s-agent
```

### Node High Resource Usage

**Diagnosis:**
```bash
# Identify resource-heavy processes
ssh ubuntu@<node-ip> top -o %CPU
ssh ubuntu@<node-ip> ps aux --sort=-%mem | head -20

# Check pod resource usage on node
kubectl top pods -A --sort-by=cpu --field-selector=spec.nodeName=<node-name>
kubectl top pods -A --sort-by=memory --field-selector=spec.nodeName=<node-name>
```

**Solutions:**
```bash
# Set resource limits on problematic pods
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"limits":{"cpu":"500m","memory":"1Gi"}}}]}}}}'

# Move pods to other nodes
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node-name>

# Scale down resource-heavy applications
kubectl scale deployment <deployment-name> -n <namespace> --replicas=1
```

## Cluster Network Issues

### Pod-to-Pod Communication Failure

**Symptoms:**
- Pods cannot communicate with each other
- Service discovery not working
- DNS resolution failures

**Diagnosis:**
```bash
# Test DNS resolution
kubectl run test-pod --image=busybox --rm -it -- nslookup kubernetes.default.svc.cluster.local

# Test pod-to-pod connectivity
kubectl run test-pod --image=busybox --rm -it -- ping <other-pod-ip>

# Check CNI plugin status
kubectl get pods -n kube-system -l k8s-app=flannel
kubectl logs -n kube-system -l k8s-app=flannel

# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

**Solutions:**

1. **DNS Issues:**
```bash
# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system

# Check DNS configuration
kubectl get configmap coredns -n kube-system -o yaml

# Test DNS from nodes
ansible all -i inventory/hosts-generated.yml -m shell -a "nslookup kubernetes.default.svc.cluster.local"
```

2. **CNI Issues:**
```bash
# Restart Flannel
kubectl delete pods -n kube-system -l app=flannel

# Check VXLAN interface
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo ip link show flannel.1"

# Reset CNI (nuclear option)
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo systemctl stop k3s && sudo rm -rf /var/lib/cni && sudo systemctl start k3s"
```

### Load Balancer Not Working

**Symptoms:**
- LoadBalancer services stuck in "Pending"
- External IP not assigned
- Cannot reach services from outside cluster

**Diagnosis:**
```bash
# Check MetalLB status
kubectl get pods -n metallb-system
kubectl logs -n metallb-system deployment/metallb-controller
kubectl logs -n metallb-system daemonset/metallb-speaker

# Check IP pool configuration
kubectl get ipaddresspool -n metallb-system -o yaml
kubectl get l2advertisement -n metallb-system -o yaml

# Check service status
kubectl get svc -A --field-selector=spec.type=LoadBalancer
kubectl describe svc <service-name> -n <namespace>
```

**Solutions:**

1. **IP Pool Issues:**
```bash
# Verify IP range is available
nmap -sn 10.10.200.100-200  # Should show available IPs

# Update IP pool
kubectl patch ipaddresspool homelab-pool -n metallb-system --type='merge' -p='{"spec":{"addresses":["10.10.200.100-10.10.200.150"]}}'

# Check pool assignment
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 5 annotations
```

2. **L2 Advertisement Issues:**
```bash
# Check speaker logs for ARP issues
kubectl logs -n metallb-system daemonset/metallb-speaker | grep -i arp

# Verify network connectivity
ping -c 3 <assigned-external-ip>

# Check if IP conflicts exist
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo arping -c 1 <assigned-external-ip>"
```

## Storage Issues

### Longhorn Volume Problems

**Symptoms:**
- PVCs stuck in "Pending"
- Pods stuck in "ContainerCreating"
- Storage performance issues

**Diagnosis:**
```bash
# Check Longhorn system status
kubectl get pods -n longhorn-system
kubectl get nodes.longhorn.io -n longhorn-system

# Check PV and PVC status
kubectl get pv,pvc -A
kubectl describe pvc <pvc-name> -n <namespace>

# Access Longhorn UI
kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80
# Visit http://localhost:8080
```

**Solutions:**

1. **Volume Creation Issues:**
```bash
# Check storage node availability
kubectl get nodes.longhorn.io -n longhorn-system -o wide

# Verify node disk space
ansible workers -i inventory/hosts-generated.yml -m shell -a "df -h /var/lib/longhorn"

# Check for scheduling issues
kubectl describe pvc <pvc-name> -n <namespace>
kubectl get events -n <namespace> --field-selector=involvedObject.name=<pvc-name>
```

2. **Performance Issues:**
```bash
# Check disk I/O
ansible workers -i inventory/hosts-generated.yml -m shell -a "iostat -x 1 3"

# Verify volume replica health
kubectl get volumes.longhorn.io -n longhorn-system
kubectl get replicas.longhorn.io -n longhorn-system

# Test storage performance
kubectl run fio-test --image=nixery.dev/shell/fio --rm -it -- \
  fio --name=test --ioengine=libaio --rw=read --bs=4k --numjobs=1 --size=1G --time_based --runtime=30 --filename=/tmp/testfile
```

3. **Backup Issues:**
```bash
# Check backup target status
kubectl get backuptargets.longhorn.io -n longhorn-system

# Test S3 connectivity
kubectl exec -n longhorn-system deployment/longhorn-manager -- \
  curl -v https://s3.us-west-004.backblazeb2.com

# Verify backup credentials
kubectl get secret longhorn-backup-secret -n longhorn-system -o yaml
```

### Storage Class Issues

**Diagnosis:**
```bash
# List storage classes
kubectl get storageclass

# Check default storage class
kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}'

# Test storage class provisioning
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: longhorn-ssd-standard
EOF

# Check provisioning
kubectl describe pvc test-pvc
```

## Pod and Application Issues

### Pods Stuck in Pending

**Diagnosis:**
```bash
# Get detailed pod information
kubectl describe pod <pod-name> -n <namespace>

# Check scheduler events
kubectl get events -n <namespace> --field-selector=involvedObject.name=<pod-name>

# Check node resources
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources"
```

**Common Causes & Solutions:**

1. **Insufficient Resources:**
```bash
# Check resource requests vs available
kubectl describe pod <pod-name> -n <namespace> | grep -A 10 "Requests"

# Scale down other applications
kubectl scale deployment <other-deployment> -n <namespace> --replicas=0

# Adjust resource requests
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"requests":{"cpu":"100m","memory":"128Mi"}}}]}}}}'
```

2. **Node Selector/Affinity Issues:**
```bash
# Check node labels
kubectl get nodes --show-labels

# Remove node selector temporarily
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"nodeSelector":null}}}}'

# Check toleration requirements
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Tolerations"
```

3. **Storage Issues:**
```bash
# Check PVC status
kubectl get pvc -n <namespace>

# Check storage class
kubectl describe storageclass <storage-class-name>

# Manual volume provisioning if needed
kubectl get pv | grep Available
```

### Pods in CrashLoopBackOff

**Diagnosis:**
```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace> --previous
kubectl logs <pod-name> -n <namespace> -c <container-name>

# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check resource limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 10 "Limits"
```

**Solutions:**

1. **Application Errors:**
```bash
# Get detailed logs
kubectl logs <pod-name> -n <namespace> --tail=100 --timestamps

# Access pod for debugging
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# Check environment variables
kubectl describe pod <pod-name> -n <namespace> | grep -A 20 "Environment"
```

2. **Resource Constraints:**
```bash
# Increase memory limits
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"limits":{"memory":"1Gi"}}}]}}}}'

# Check for OOMKilled
kubectl describe pod <pod-name> -n <namespace> | grep -i oom

# Monitor resource usage
kubectl top pod <pod-name> -n <namespace> --containers
```

### Service Discovery Issues

**Symptoms:**
- Cannot reach services by name
- DNS resolution failures
- Service endpoints not working

**Diagnosis:**
```bash
# Check service configuration
kubectl get svc <service-name> -n <namespace> -o wide
kubectl describe svc <service-name> -n <namespace>

# Check endpoints
kubectl get endpoints <service-name> -n <namespace>

# Test DNS resolution
kubectl run test-pod --image=busybox --rm -it -- nslookup <service-name>.<namespace>.svc.cluster.local
```

**Solutions:**
```bash
# Verify selector labels
kubectl get pods -n <namespace> --show-labels
kubectl describe svc <service-name> -n <namespace> | grep -A 5 "Selector"

# Check pod readiness
kubectl get pods -n <namespace> -o wide
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Readiness"

# Restart service
kubectl delete svc <service-name> -n <namespace>
kubectl apply -f <service-definition.yaml>
```

## GPU Issues

### GPU Nodes Not Detected

**Symptoms:**
- GPU device plugin pods not starting
- No GPU resources available in cluster
- NVIDIA runtime not working

**Diagnosis:**
```bash
# Check GPU nodes
kubectl get nodes -l nvidia.com/gpu=true

# Check device plugin status
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
kubectl logs -n kube-system -l name=nvidia-device-plugin-ds

# Check GPU hardware on nodes
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "nvidia-smi"
```

**Solutions:**

1. **Driver Issues:**
```bash
# Check NVIDIA driver installation
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "nvidia-smi && modprobe nvidia"

# Reinstall drivers if needed
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "sudo apt reinstall nvidia-driver-535"

# Check kernel modules
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "lsmod | grep nvidia"
```

2. **Container Runtime Issues:**
```bash
# Check containerd configuration
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "sudo cat /etc/rancher/k3s/containerd.config.toml | grep nvidia"

# Test NVIDIA container runtime
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "sudo ctr run --runtime=nvidia --rm docker.io/nvidia/cuda:11.8-runtime-ubuntu22.04 nvidia-test nvidia-smi"

# Restart containerd
ansible gpu_workers -i inventory/hosts-generated.yml -m shell -a "sudo systemctl restart k3s"
```

3. **Device Plugin Issues:**
```bash
# Redeploy device plugin
kubectl delete daemonset nvidia-device-plugin-daemonset -n kube-system
kubectl apply -f /var/lib/rancher/k3s/server/manifests/nvidia-device-plugin.yaml

# Check node labels and taints
kubectl describe node <gpu-node-name> | grep -A 10 "Labels\|Taints"

# Test GPU pod scheduling
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  nodeSelector:
    nvidia.com/gpu: "true"
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  containers:
  - name: gpu-test
    image: nvidia/cuda:11.8-runtime-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
  restartPolicy: Never
EOF
```

## Performance Issues

### Cluster Slow Response

**Symptoms:**
- kubectl commands slow to respond
- API server timeouts
- Application response delays

**Diagnosis:**
```bash
# Check API server response time
time kubectl get nodes

# Check etcd health
kubectl exec -n kube-system etcd-k3s-master-01 -- etcdctl endpoint health --cluster

# Check system load
ansible masters -i inventory/hosts-generated.yml -m shell -a "uptime && iostat -x 1 1"

# Check network latency
kubectl run net-test --image=busybox --rm -it -- ping -c 5 <master-ip>
```

**Solutions:**

1. **API Server Performance:**
```bash
# Check API server logs
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo journalctl -u k3s | grep apiserver | tail -20"

# Increase API server resources (if needed)
# This requires modifying K3s configuration and restart

# Check certificate issues
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo openssl x509 -in /var/lib/rancher/k3s/server/tls/server-ca.crt -text -noout | grep 'Not After'"
```

2. **etcd Performance:**
```bash
# Check etcd metrics
kubectl exec -n kube-system etcd-k3s-master-01 -- etcdctl endpoint status --cluster -w table

# Check disk I/O for etcd
ansible masters -i inventory/hosts-generated.yml -m shell -a "iostat -x 1 3"

# Compact etcd if needed
kubectl exec -n kube-system etcd-k3s-master-01 -- etcdctl compact $(kubectl exec -n kube-system etcd-k3s-master-01 -- etcdctl endpoint status --write-out="json" | jq -r '.[] | .Status.header.revision')
```

### High Resource Usage

**Diagnosis:**
```bash
# Top resource consumers
kubectl top nodes --sort-by=cpu
kubectl top pods -A --sort-by=cpu | head -20
kubectl top pods -A --sort-by=memory | head -20

# Check resource quotas
kubectl describe quota -A

# Check limit ranges
kubectl describe limitrange -A
```

**Solutions:**
```bash
# Set resource limits on heavy consumers
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"limits":{"cpu":"500m","memory":"1Gi"}}}]}}}}'

# Implement pod disruption budgets
cat <<EOF | kubectl apply -f -
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: <app-name>-pdb
  namespace: <namespace>
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: <app-name>
EOF

# Set up horizontal pod autoscaler
kubectl autoscale deployment <deployment-name> -n <namespace> --cpu-percent=70 --min=2 --max=10
```

## Security Issues

### RBAC Problems

**Symptoms:**
- "Forbidden" errors when accessing resources
- Service accounts cannot perform operations
- Users cannot access cluster resources

**Diagnosis:**
```bash
# Check user/service account permissions
kubectl auth can-i <verb> <resource> --as=<user>
kubectl auth can-i --list --as=<user>

# Check existing roles and bindings
kubectl get roles,rolebindings -A
kubectl get clusterroles,clusterrolebindings

# Describe specific binding
kubectl describe rolebinding <binding-name> -n <namespace>
kubectl describe clusterrolebinding <binding-name>
```

**Solutions:**
```bash
# Grant necessary permissions
kubectl create rolebinding <binding-name> --clusterrole=<role-name> --user=<username> -n <namespace>

# Create custom role
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: <namespace>
  name: <role-name>
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
EOF

# Fix service account permissions
kubectl create clusterrolebinding <binding-name> --clusterrole=cluster-admin --serviceaccount=<namespace>:<service-account>
```

### Certificate Issues

**Symptoms:**
- TLS handshake failures
- Certificate expired errors
- Cannot connect to API server

**Diagnosis:**
```bash
# Check certificate expiry dates
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo find /var/lib/rancher/k3s/server/tls -name '*.crt' -exec openssl x509 -in {} -text -noout \; | grep -A 2 'Not After'"

# Test TLS connection
openssl s_client -connect <master-ip>:6443 -servername kubernetes

# Check certificate chain
kubectl get csr
```

**Solutions:**
```bash
# Regenerate certificates (requires cluster restart)
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo systemctl stop k3s"
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo rm -rf /var/lib/rancher/k3s/server/tls"
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo systemctl start k3s"

# Update kubeconfig with new certificates
scp ubuntu@<master-ip>:/etc/rancher/k3s/k3s.yaml ~/.kube/k3s-config
sed -i 's/127.0.0.1/<master-ip>/g' ~/.kube/k3s-config
```

## Disaster Recovery

### Complete Cluster Failure

**Steps for Recovery:**

1. **Assess Damage:**
```bash
# Check what's still running
ansible all -i inventory/hosts-generated.yml -m ping
kubectl get nodes  # May fail if API server is down
```

2. **Emergency etcd Backup:**
```bash
# If any master is accessible
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo k3s etcd-snapshot save emergency-backup-$(date +%Y%m%d-%H%M).db"
```

3. **Restore from Backup:**
```bash
# Stop all K3s services
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo systemctl stop k3s k3s-agent"

# Restore etcd on first master
ansible-playbook -i inventory/hosts-generated.yml playbooks/restore-etcd.yml

# Restart cluster
ansible-playbook -i inventory/hosts-generated.yml playbooks/configure-k3s.yml
```

### Data Recovery

```bash
# List available etcd snapshots
ansible masters -i inventory/hosts-generated.yml -m shell -a "sudo ls -la /var/lib/rancher/k3s/server/db/snapshots/"

# Restore specific application data
kubectl apply -f backup/application-manifests/
kubectl get pvc -A  # Verify persistent volumes
```

## Getting Help

### Log Collection for Support

```bash
# Comprehensive log collection script
cat > collect-logs.sh <<'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d-%H%M)
LOG_DIR="/tmp/k3s-support-logs-$TIMESTAMP"
mkdir -p $LOG_DIR

# Cluster information
kubectl cluster-info dump --output-directory=$LOG_DIR/cluster-dump

# Node logs
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo journalctl -u k3s -n 1000" > $LOG_DIR/k3s-services.log
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo journalctl -u k3s-agent -n 1000" >> $LOG_DIR/k3s-services.log

# System information
kubectl get nodes -o wide > $LOG_DIR/nodes.txt
kubectl top nodes > $LOG_DIR/node-resources.txt
kubectl get pods -A -o wide > $LOG_DIR/all-pods.txt
kubectl get events -A --sort-by='.lastTimestamp' > $LOG_DIR/events.txt

# Configuration
cp -r infrastructure/k3s/ansible/group_vars $LOG_DIR/
cp infrastructure/k3s/configs/* $LOG_DIR/

# Create archive
tar -czf k3s-support-logs-$TIMESTAMP.tar.gz -C /tmp k3s-support-logs-$TIMESTAMP

echo "Support logs collected: k3s-support-logs-$TIMESTAMP.tar.gz"
EOF

chmod +x collect-logs.sh
./collect-logs.sh
```

### Escalation Contacts

- **Level 1 Support**: platform-team@company.com
- **Level 2 Support**: infrastructure-team@company.com  
- **Emergency Escalation**: on-call-manager@company.com
- **Vendor Support**: [Include relevant vendor support contacts]

### Common Troubleshooting Resources

- **K3s Documentation**: https://docs.k3s.io/
- **Longhorn Troubleshooting**: https://longhorn.io/docs/1.5.2/troubleshooting/
- **MetalLB Troubleshooting**: https://metallb.universe.tf/troubleshooting/
- **Kubernetes Troubleshooting**: https://kubernetes.io/docs/tasks/debug/

This troubleshooting guide covers the most common issues you'll encounter with the K3s HA cluster. Keep it handy during operations and update it with new issues as they're discovered and resolved.