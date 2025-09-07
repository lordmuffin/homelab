# K3s HA Cluster - Complete Deployment Guide

## Prerequisites Checklist

### Infrastructure Requirements
- [ ] Proxmox VE 8.0+ cluster with 3+ nodes
- [ ] 200GB+ total storage available  
- [ ] Network: 10.10.0.0/16 with VLAN support
- [ ] Internet access for package downloads
- [ ] DNS resolution configured

### Required Tools
- [ ] Terraform 1.5+ installed
- [ ] Ansible 2.15+ with kubernetes.core collection
- [ ] Packer 1.9+ installed
- [ ] kubectl 1.28+ installed
- [ ] SSH key pair generated
- [ ] Git repository access

### Account Requirements
- [ ] Proxmox API credentials with VM management permissions
- [ ] Backblaze B2 account with API keys (optional but recommended)
- [ ] Domain for ingress (optional)

## Phase 1: VM Image Management

### Step 1.1: Build K3s Base Image

```bash
# Navigate to Packer directory
cd infrastructure/proxmox/packer

# Configure Packer variables
cp ubuntu-k3s.pkr.hcl.example ubuntu-k3s.pkr.hcl

# Edit configuration for your environment
vim ubuntu-k3s.pkr.hcl
```

**Required Configuration:**
```hcl
# Proxmox connection
proxmox_url = "https://your-proxmox:8006/api2/json"
proxmox_username = "root@pam"
proxmox_password = "your-password"
proxmox_node = "proxmox-node-1"

# VM settings
vm_id = 9000
vm_name = "ubuntu-k3s-template"
template_description = "Ubuntu 22.04 K3s Ready Template"

# Network settings
bridge = "vmbr0"
vlan_tag = "10"

# Storage settings
storage_pool = "local-zfs"
disk_size = "32G"

# SSH settings
ssh_username = "ubuntu"
ssh_public_key_file = "~/.ssh/homelab.pub"
```

### Step 1.2: Execute Packer Build

```bash
# Validate Packer template
packer validate ubuntu-k3s.pkr.hcl

# Build the template (takes 15-20 minutes)
packer build ubuntu-k3s.pkr.hcl

# Verify template creation in Proxmox UI
# Template should appear as "ubuntu-k3s-template" (ID: 9000)
```

### Step 1.3: Validate Template

```bash
# Clone template to test VM
qm clone 9000 999 --name test-k3s
qm set 999 --sockets 2 --cores 2 --memory 4096
qm start 999

# Test SSH access
ssh ubuntu@<test-vm-ip> -i ~/.ssh/homelab

# Verify K3s prerequisites
ubuntu@test-vm:~$ docker --version
ubuntu@test-vm:~$ systemctl status containerd
ubuntu@test-vm:~$ ls -la /opt/k3s-prep/

# Cleanup test VM
qm stop 999 && qm destroy 999
```

## Phase 2: Infrastructure Deployment

### Step 2.1: Configure Terraform

```bash
# Navigate to Terraform directory
cd infrastructure/proxmox/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
```

**Configure terraform.tfvars:**
```hcl
# Proxmox Configuration
proxmox_api_url = "https://your-proxmox:8006/api2/json"
proxmox_api_token_id = "terraform@pam!terraform"
proxmox_api_token_secret = "your-api-token"

# Cluster Configuration
cluster_name = "homelab-k3s"
environment = "production"  # or "development"

# Network Configuration
network_bridge = "vmbr0"
network_vlan = 10
network_gateway = "192.168.11.1"
network_nameservers = ["192.168.11.1", "8.8.8.8"]

# Template Configuration
template_name = "ubuntu-k3s-template"

# SSH Configuration
ssh_public_key = file("~/.ssh/homelab.pub")
ssh_private_key_path = "~/.ssh/homelab"

# Node Configuration - Production
master_nodes = {
  "k3s-master-01" = { ip = "192.168.11.10", cores = 4, memory = 8192, disk_size = "60G" }
  "k3s-master-02" = { ip = "192.168.11.11", cores = 4, memory = 8192, disk_size = "60G" }
  "k3s-master-03" = { ip = "192.168.11.12", cores = 4, memory = 8192, disk_size = "60G" }
}

worker_nodes = {
  "k3s-worker-01" = { ip = "192.168.11.20", cores = 4, memory = 16384, disk_size = "100G" }
  "k3s-worker-02" = { ip = "192.168.11.21", cores = 4, memory = 16384, disk_size = "100G" }
  "k3s-worker-03" = { ip = "192.168.11.22", cores = 8, memory = 32768, disk_size = "200G" }
  "k3s-worker-04" = { ip = "192.168.11.23", cores = 8, memory = 32768, disk_size = "200G" }
  "k3s-worker-05" = { ip = "192.168.11.24", cores = 4, memory = 16384, disk_size = "150G" }
}

gpu_worker_nodes = {
  "k3s-gpu-01" = { ip = "192.168.11.30", cores = 8, memory = 32768, disk_size = "200G" }
  "k3s-gpu-02" = { ip = "192.168.11.31", cores = 8, memory = 32768, disk_size = "200G" }
}

# Storage Configuration
storage_pool = "local-zfs"
backup_storage = "backup-nas"

# Load Balancer Configuration
metallb_ip_range = "192.168.11.100-192.168.11.200"
```

### Step 2.2: Deploy Infrastructure

```bash
# Plan deployment
terraform plan -out=deployment.tfplan

# Review the plan carefully
# Should show creation of 10 VMs (3 masters, 5 workers, 2 GPU workers)

# Apply deployment (takes 10-15 minutes)
terraform apply deployment.tfplan

# Verify VM creation
terraform output -json | jq '.cluster_ips.value'
```

### Step 2.3: Generate Ansible Inventory

```bash
# Generate dynamic inventory from Terraform output
terraform output -json > terraform-outputs.json

# Generate Ansible inventory
cd ../../k3s/ansible

# Create inventory from template
python3 scripts/generate-inventory.py \
  --terraform-output ../../../proxmox/terraform/terraform-outputs.json \
  --template inventory/hosts.yml \
  --output inventory/hosts-generated.yml
```

## Phase 3: K3s Cluster Deployment

### Step 3.1: Configure Ansible Variables

```bash
# Review and customize global variables
vim group_vars/all.yml
```

**Key configurations to verify:**
```yaml
# Cluster identification
k3s_cluster_name: "homelab-k3s"
k3s_version: "v1.28.5+k3s1"

# Network configuration
k3s_cluster_cidr: "10.42.0.0/16"
k3s_service_cidr: "10.43.0.0/16"

# MetalLB configuration
metallb_config:
  address_pools:
    - name: "homelab-pool"
      protocol: "layer2"
      addresses:
        - "192.168.11.100-192.168.11.200"

# Backup configuration (if using Backblaze B2)
backup_config:
  enabled: true
  provider: "backblaze"
  s3_endpoint: "s3.us-west-004.backblazeb2.com"
  s3_bucket: "homelab-backups"

# Integration flags
homelab_integration:
  prometheus_enabled: true
  grafana_enabled: true
  argocd_enabled: true
  longhorn_enabled: true
```

### Step 3.2: Configure Secrets

```bash
# Create secrets file (never commit this!)
vim group_vars/secrets.yml

# Add backup credentials (if using Backblaze B2)
backblaze_access_key_id: "your-access-key"
backblaze_secret_access_key: "your-secret-key"

# Encrypt secrets file
ansible-vault encrypt group_vars/secrets.yml
```

### Step 3.3: Pre-deployment Validation

```bash
# Test connectivity to all nodes
ansible all -i inventory/hosts-generated.yml -m ping

# Verify SSH access and sudo permissions
ansible all -i inventory/hosts-generated.yml -m shell -a "sudo whoami"

# Check system requirements
ansible-playbook -i inventory/hosts-generated.yml playbooks/validate-requirements.yml
```

### Step 3.4: Deploy K3s Cluster

```bash
# Deploy the complete cluster (takes 20-30 minutes)
ansible-playbook -i inventory/hosts-generated.yml \
  --ask-vault-pass \
  --extra-vars "@group_vars/secrets.yml" \
  playbooks/configure-k3s.yml

# Monitor deployment progress
tail -f /var/log/ansible.log  # if logging is configured
```

### Step 3.5: Verify Cluster Deployment

```bash
# Copy kubeconfig from first master
scp -i ~/.ssh/homelab ubuntu@192.168.11.10:/etc/rancher/k3s/k3s.yaml ~/.kube/k3s-config

# Update server address in kubeconfig
sed -i 's/127.0.0.1/192.168.11.10/g' ~/.kube/k3s-config

# Set KUBECONFIG environment variable
export KUBECONFIG=~/.kube/k3s-config

# Verify all nodes are ready
kubectl get nodes -o wide

# Expected output:
# NAME             STATUS   ROLES                       AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   
# k3s-master-01    Ready    control-plane,etcd,master   10m   v1.28.5+k3s1   192.168.11.10   <none>        
# k3s-master-02    Ready    control-plane,etcd,master   9m    v1.28.5+k3s1   192.168.11.11   <none>        
# k3s-master-03    Ready    control-plane,etcd,master   9m    v1.28.5+k3s1   192.168.11.12   <none>        
# k3s-worker-01    Ready    <none>                      8m    v1.28.5+k3s1   192.168.11.20   <none>        
# k3s-worker-02    Ready    <none>                      8m    v1.28.5+k3s1   192.168.11.21   <none>        
# k3s-worker-03    Ready    <none>                      8m    v1.28.5+k3s1   192.168.11.22   <none>        
# k3s-worker-04    Ready    <none>                      8m    v1.28.5+k3s1   192.168.11.23   <none>        
# k3s-worker-05    Ready    <none>                      8m    v1.28.5+k3s1   192.168.11.24   <none>        
# k3s-gpu-01       Ready    <none>                      7m    v1.28.5+k3s1   192.168.11.30   <none>        
# k3s-gpu-02       Ready    <none>                      7m    v1.28.5+k3s1   192.168.11.31   <none>
```

## Phase 4: Core Services Validation

### Step 4.1: Verify Core Components

```bash
# Check system pods
kubectl get pods -n kube-system

# Verify Longhorn storage
kubectl get pods -n longhorn-system
kubectl get storageclass

# Check MetalLB load balancer
kubectl get pods -n metallb-system
kubectl get ipaddresspool -n metallb-system

# Verify cert-manager
kubectl get pods -n cert-manager

# Check GPU device plugin (on GPU nodes)
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
```

### Step 4.2: Test Storage Classes

```bash
# Create test PVC for each storage class
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-nvme-critical
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn-nvme-critical
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-ssd-standard  
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn-ssd-standard
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-bulk
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn-bulk
  resources:
    requests:
      storage: 1Gi
EOF

# Verify PVCs are bound
kubectl get pvc

# Cleanup test PVCs
kubectl delete pvc test-nvme-critical test-ssd-standard test-bulk
```

### Step 4.3: Test Load Balancer

```bash
# Create test load balancer service
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: test-nginx
  template:
    metadata:
      labels:
        app: test-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: test-nginx-lb
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: test-nginx
EOF

# Wait for external IP assignment
kubectl get svc test-nginx-lb -w

# Test connectivity (should get nginx welcome page)
curl http://<EXTERNAL-IP>

# Cleanup test resources
kubectl delete deployment test-nginx
kubectl delete service test-nginx-lb
```

### Step 4.4: Test GPU Functionality

```bash
# Create GPU test pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  nodeSelector:
    nvidia.com/gpu: "true"
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  containers:
  - name: gpu-test
    image: nvidia/cuda:11.8-runtime-ubuntu22.04
    command: ["/bin/bash"]
    args: ["-c", "nvidia-smi && sleep 30"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

# Check GPU test results
kubectl logs gpu-test

# Expected output should show GPU information
# Cleanup test pod
kubectl delete pod gpu-test
```

## Phase 5: Integration with Existing Services

### Step 5.1: Configure Ingress Integration

```bash
# Update existing Traefik configuration to use LoadBalancer
# This integrates with your existing ingress setup
kubectl patch service traefik -n traefik-system -p '{"spec": {"type": "LoadBalancer"}}'

# Verify Traefik gets external IP
kubectl get svc -n traefik-system
```

### Step 5.2: Set Up Monitoring Integration

```bash
# Deploy cluster-specific monitoring components
kubectl apply -f kubernetes/infrastructure/monitoring/k3s-servicemonitors.yaml
kubectl apply -f kubernetes/infrastructure/monitoring/k3s-dashboards.yaml

# Verify new metrics are being collected
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Visit http://localhost:9090 and check for K3s metrics
```

### Step 5.3: Configure ArgoCD Integration

```bash
# Add cluster to ArgoCD (if not using in-cluster ArgoCD)
argocd cluster add k3s-homelab --kubeconfig ~/.kube/k3s-config

# Deploy applications to new cluster
kubectl apply -f kubernetes/applications/production/
```

## Phase 6: Validation and Testing

### Step 6.1: Comprehensive Health Check

```bash
# Run comprehensive cluster validation
cd infrastructure/k3s/ansible
ansible-playbook -i inventory/hosts-generated.yml playbooks/validate-cluster.yml

# Check cluster info
kubectl cluster-info
kubectl get componentstatus
kubectl get nodes --show-labels
```

### Step 6.2: Performance Baseline

```bash
# Install performance testing tools
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: network-test
spec:
  containers:
  - name: netperf
    image: networkstatic/netperf
    command: ["/bin/bash"]
    args: ["-c", "sleep 3600"]
EOF

# Test inter-node network performance
kubectl exec -it network-test -- netperf -H k3s-worker-02.local
```

### Step 6.3: Backup Validation

```bash
# Test etcd backup functionality
kubectl exec -it -n kube-system etcd-k3s-master-01 -- etcdctl snapshot save /tmp/test-backup.db

# Test Longhorn backup (if configured)
kubectl apply -f - <<EOF
apiVersion: longhorn.io/v1beta1
kind: BackupTarget
metadata:
  name: test-backup
  namespace: longhorn-system
spec:
  backupTargetURL: s3://homelab-backups@s3.us-west-004.backblazeb2.com/
  credentialSecret: longhorn-backup-secret
EOF
```

## Phase 7: Documentation and Handover

### Step 7.1: Generate Cluster Documentation

```bash
# Generate cluster inventory
kubectl get nodes -o yaml > cluster-nodes.yaml
kubectl get namespaces -o yaml > cluster-namespaces.yaml
kubectl get storageclass -o yaml > cluster-storage.yaml

# Create cluster access documentation
cat > cluster-access.md <<EOF
# K3s Cluster Access

## Kubectl Configuration
export KUBECONFIG=~/.kube/k3s-config

## Cluster Endpoints
- API Server: https://192.168.11.10:6443
- Longhorn UI: https://longhorn.yourdomain.com
- Grafana: https://grafana.yourdomain.com

## Emergency Contacts
- Cluster Admin: admin@yourdomain.com
- Infrastructure Team: infra@yourdomain.com
EOF
```

### Step 7.2: Set Up Monitoring Alerts

```bash
# Deploy cluster-specific alerting rules
kubectl apply -f kubernetes/infrastructure/monitoring/k3s-alerts.yaml

# Verify alerts are loaded in Prometheus
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Check Alerts tab in Prometheus UI
```

## Troubleshooting Common Issues

### Issue: Nodes Not Ready
```bash
# Check node status
kubectl describe node <node-name>

# Check K3s service status
ssh ubuntu@<node-ip> sudo systemctl status k3s
ssh ubuntu@<node-ip> sudo journalctl -u k3s -f

# Check network connectivity
kubectl exec -it <pod-name> -- ping <other-node-ip>
```

### Issue: Pods Stuck in Pending
```bash
# Check pod events
kubectl describe pod <pod-name>

# Check resource constraints
kubectl top nodes
kubectl describe node <node-name>

# Check storage availability
kubectl get pv,pvc
```

### Issue: Load Balancer Not Getting External IP
```bash
# Check MetalLB status
kubectl get pods -n metallb-system
kubectl logs -n metallb-system deployment/metallb-controller

# Verify IP pool configuration
kubectl get ipaddresspool -n metallb-system -o yaml
```

## Post-Deployment Checklist

- [ ] All nodes show "Ready" status
- [ ] All system pods are running
- [ ] Storage classes are available and working
- [ ] Load balancer assigns external IPs
- [ ] GPU nodes can schedule GPU workloads
- [ ] Monitoring is collecting metrics
- [ ] Backup system is functional
- [ ] Documentation is complete and accessible
- [ ] Emergency procedures are documented
- [ ] Team access is configured

## Next Steps

1. **Deploy Applications**: Start deploying your applications using GitOps
2. **Set Up Monitoring**: Configure application-specific monitoring
3. **Implement Backup Strategy**: Schedule regular backups and test restore procedures
4. **Security Hardening**: Implement additional security policies as needed
5. **Performance Tuning**: Optimize based on workload requirements

Congratulations! Your K3s HA cluster is now ready for production workloads.