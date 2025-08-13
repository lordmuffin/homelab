# Proxmox K3s Terraform Module

This Terraform module provisions a K3s cluster on Proxmox VE infrastructure, migrated from the original Pulumi implementation.

## Features

- **Multi-node K3s cluster** with configurable server and agent nodes
- **Proxmox VE integration** using the bpg/proxmox provider
- **Cloud-init automation** for VM initialization
- **GPU passthrough support** for GPU-enabled worker nodes
- **Cilium CNI** integration for advanced networking
- **Multiple Proxmox nodes** support for distributed infrastructure
- **Environment separation** (dev/prod configurations)

## Requirements

- Terraform >= 0.13
- Proxmox VE 8.x cluster
- Cloud-init enabled VM template (Ubuntu 22.04 recommended)
- SSH key pair for VM access
- Proxmox API credentials

## Usage

### Basic Example

```hcl
module "k3s_cluster" {
  source = "./modules/proxmox-k3s"

  providers = [
    {
      name        = "pve_provider"
      node_name   = "pve"
      endpoint    = "https://192.168.1.13:8006/"
      username    = "terraform@pve"
      insecure    = true
      hostpcis    = ""
    },
    {
      name        = "pve2_provider"
      node_name   = "pve2"
      endpoint    = "https://192.168.1.14:8006/"
      username    = "terraform@pve"
      insecure    = true
      hostpcis    = "gpu"
    }
  ]

  vms = [
    {
      name            = "k3s-dev"
      count           = 3
      node_name       = "pve"
      vm_type         = "server"
      environment     = "dev"
      resource_name   = "lab"
      suffix          = "001"
      vm_id           = 1100
      tls_san         = "192.168.10.10"
      # ... additional configuration
    }
  ]

  proxmox_password = var.proxmox_password
  ssh_private_key  = var.ssh_private_key
  ssh_public_key   = var.ssh_public_key
}
```

### Environment-Specific Configuration

Create `.tfvars` files for different environments:

```hcl
# dev.tfvars
environment = "dev"
cluster_name = "dev-k3s"
server_count = 1
agent_count = 2
```

## Module Configuration

### Required Variables

- `providers` - List of Proxmox provider configurations
- `vms` - List of VM configurations for the cluster
- `proxmox_password` - Proxmox authentication password
- `ssh_private_key` - SSH private key for VM provisioning
- `ssh_public_key` - SSH public key for VM access

### Optional Variables

- `template_vm_id` - Template VM ID to clone from (default: 8006)
- `k3s_version` - K3s version to install (default: v1.28.2+k3s1)
- `k3s_options` - Additional K3s options
- `vm_user` - Default VM user (default: ubuntu)

## VM Types

- **server** - K3s control plane nodes
- **agent** - K3s worker nodes  
- **gpu-agent** - GPU-enabled worker nodes with passthrough

## Outputs

- `vm_details` - Complete details of all created VMs
- `server_ips` - IP addresses of server nodes
- `agent_ips` - IP addresses of agent nodes
- `primary_server_ip` - Primary server IP for cluster access
- `cluster_endpoint` - K3s cluster endpoint
- `kubeconfig_path` - Path to kubeconfig on primary server

## Network Configuration

The module supports:
- Static IP assignment via cloud-init
- VLAN configuration
- Custom bridge interfaces
- DNS configuration

## Security

- SSH key-based authentication
- Sensitive variable handling
- Network isolation via VLANs
- Secure API token usage

## Troubleshooting

### Common Issues

1. **VM fails to start**: Check template configuration and resource allocation
2. **K3s installation fails**: Verify network connectivity and SSH access
3. **Cilium issues**: Ensure proper IP configuration and network policies

### Debugging

```bash
# Check VM status
terraform show | grep -A 5 "proxmox_virtual_environment_vm"

# SSH to nodes for debugging
ssh ubuntu@<vm-ip> -i ~/.ssh/your-key

# Check K3s status
sudo systemctl status k3s
```

## Migration from Pulumi

This module is a direct migration from the original Pulumi k3s-nodes implementation, maintaining:

- Same VM configuration patterns
- Compatible cloud-init setup
- Identical K3s and Cilium installation
- Equivalent network and storage configuration

## Contributing

When contributing to this module:

1. Follow existing code patterns
2. Update documentation for new features
3. Test with multiple Proxmox configurations
4. Ensure compatibility with existing deployments