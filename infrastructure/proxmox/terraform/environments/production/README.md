# Multi-Node Proxmox K3s Cluster Deployment

This Terraform configuration deploys a highly available K3s cluster across multiple Proxmox nodes using individual API connections to each node.

## 🏗️ Architecture

### Multi-Provider Design
- **Separate Providers**: Individual Proxmox provider for each physical node
- **Node-Specific Deployment**: Each module deploys VMs only to its assigned node
- **Independent Authentication**: Each node can have different credentials

### VM Distribution
Per Proxmox node deployment:
- **1 Master** (K3s control plane)
- **2 Workers** (configurable via `workers_per_node`)
- **1 GPU Worker** (production only, configurable via `gpu_workers_per_node`)

**Total Production Cluster:**
```
pve:        1 master + 2 workers + 1 GPU worker = 4 VMs
pve2:       1 master + 2 workers + 1 GPU worker = 4 VMs  
pve-nas-01: 1 master + 2 workers + 1 GPU worker = 4 VMs
Total:      3 masters + 6 workers + 3 GPU workers = 12 VMs
```

## 🔧 Configuration

### Prerequisites
1. **VM Template**: Ensure `ubuntu-k3s-homelab-template` exists on all nodes
2. **Network Connectivity**: All nodes must be reachable from your Terraform host
3. **SSH Access**: Root SSH access to all Proxmox nodes for cloud-init uploads
4. **Credentials**: Valid root passwords or API tokens for all nodes

### 1. Node Configuration
Edit `terraform.tfvars` with your actual values:

```hcl
proxmox_nodes_config = {
  pve = {
    api_url      = "https://192.168.1.14:8006/api2/json"
    ip_address   = "192.168.1.14"
    token_id     = "root@pam!packer"
    token_secret = "YOUR_PVE_ROOT_PASSWORD"
  }
  pve2 = {
    api_url      = "https://192.168.1.15:8006/api2/json"
    ip_address   = "192.168.1.15" 
    token_id     = "root@pam!packer"
    token_secret = "YOUR_PVE2_ROOT_PASSWORD"
  }
  pve-nas-01 = {
    api_url      = "https://192.168.1.16:8006/api2/json"
    ip_address   = "192.168.1.16"
    token_id     = "root@pam!packer"
    token_secret = "YOUR_PVE_NAS_ROOT_PASSWORD"
  }
}
```

### 2. SSH Keys
Replace the SSH key placeholder:
```hcl
ssh_public_keys = [
  "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your-actual-key"
]
```

**Get your SSH key:**
```bash
cat ~/.ssh/id_rsa.pub
```

### 3. Network Configuration
Verify your network settings match your infrastructure:
```hcl
network_bridge  = "vmbr0"
network_gateway = "192.168.1.1"
```

## 🚀 Deployment

### Deploy
```bash
# Initialize Terraform
terraform init

# Plan deployment (review carefully)
terraform plan

# Deploy cluster
terraform apply
```

### Verification
After deployment, check outputs:
```bash
terraform output cluster_size_per_node
terraform output total_cluster_size
terraform output cluster_nodes
```

## 🔍 Troubleshooting

### Authentication Issues
- **401 Errors**: Verify node IP addresses and credentials in terraform.tfvars
- **Connection Refused**: Check if Proxmox API is accessible on specified ports
- **SSH Issues**: Ensure SSH key authentication is set up for root access

### VM Creation Issues  
- **Template Missing**: Verify VM template exists on target node
- **Resource Limits**: Check node has sufficient CPU/RAM/storage
- **Network Issues**: Verify bridge and VLAN configuration

### Cloud-Init Issues
- **Upload Failures**: Check SSH connectivity to Proxmox nodes
- **File Permissions**: Ensure /var/lib/vz/snippets exists and is writable

## 📊 Outputs

### Node-Specific Information
- `cluster_size_per_node`: VMs deployed per Proxmox node
- Individual module outputs: `module.k3s_cluster_pve.*`

### Cluster-Wide Information  
- `total_cluster_size`: Aggregated cluster statistics
- `cluster_nodes`: All VM details across all nodes
- `master_nodes`: All master node information
- `worker_nodes`: All worker node information

## 🔧 Customization

### Adjust VM Count Per Node
```hcl
# In module calls
workers_per_node = 3        # 3 workers per node
gpu_workers_per_node = 2    # 2 GPU workers per node (prod only)
```

### Change Node IP Addresses
Update the `proxmox_nodes_config` variable with your actual node IPs.

### Add Additional Nodes
1. Add new node config to `proxmox_nodes_config`
2. Create new provider block in `main.tf`  
3. Add new module call
4. Update outputs to include new node

## 🏷️ VM Naming Convention

VMs follow this pattern:
```
k3s-{type}-{node}-{instance}

Examples:
- k3s-masters-pve-1      (First master on pve)
- k3s-workers-pve2-1     (First worker on pve2)  
- k3s-gpu_workers-pve-nas-01-1  (First GPU worker on pve-nas-01)
```

## 🔄 Scaling

### Scale Workers
Modify `workers_per_node` in module calls and re-apply:
```bash
terraform apply
```

### Scale GPU Workers
Modify `gpu_workers_per_node` for production deployments:
```bash
terraform apply
```

## ⚠️ Important Notes

1. **Primary Master**: The first master on `pve` is designated as the cluster primary
2. **VM IDs**: Automatically assigned with offsets to prevent conflicts
3. **Cloud-Init**: Unique files created per VM to avoid conflicts
4. **DHCP**: VMs use DHCP - check Proxmox console for actual IP addresses
5. **GPU Support**: Only enabled in production environment

## 🔐 Security

- Keep `terraform.tfvars` secure (contains passwords)
- Use API tokens instead of passwords when possible
- Regularly rotate credentials
- Limit network access to Proxmox APIs

## 📝 Migration from Single Provider

If migrating from single-provider configuration:
1. Backup current `terraform.tfstate`
2. Run `terraform destroy` on old configuration
3. Update to new multi-provider configuration
4. Run `terraform apply` to recreate resources

The new architecture provides better isolation and reliability for multi-node Proxmox deployments.