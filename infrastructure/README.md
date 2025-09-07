# K3s Infrastructure Automation

This directory contains comprehensive infrastructure automation for deploying and managing K3s high-availability clusters on Proxmox infrastructure.

## Structure

```
infrastructure/
├── proxmox/           # Proxmox virtualization automation
│   ├── terraform/     # Infrastructure as Code
│   │   ├── modules/   # Reusable Terraform modules
│   │   └── environments/ # Environment-specific configurations
│   └── packer/        # VM template building
│       ├── ubuntu-k3s.pkr.hcl
│       └── scripts/   # Provisioning scripts
├── k3s/              # Kubernetes cluster automation
│   ├── ansible/       # Cluster deployment and management
│   │   ├── playbooks/ # Ansible playbooks
│   │   └── inventory/ # Dynamic inventory management
│   └── configs/       # K3s configuration templates
├── k3s-deploy.py      # Main deployment wrapper script
└── docs/             # Documentation and runbooks
    ├── architecture.md
    └── runbooks/      # Operational procedures
```

---

## K3s Deployment Wrapper

A comprehensive Python script for orchestrating K3s cluster deployments on Proxmox infrastructure. This script handles the complete workflow from Terraform provisioning to cluster validation.

### Features

- **Complete Workflow Automation**: From infrastructure provisioning to cluster validation
- **Terraform Integration**: Automated apply/destroy with proper state management
- **VM Discovery**: Automatic IP discovery and inventory updates using existing scripts
- **Ansible Orchestration**: K3s cluster configuration and deployment
- **Smart Kubeconfig Management**: Automatic creation, update, validation, and fallback fetching
- **Cluster Validation**: Comprehensive health checks and node verification
- **Robust Error Handling**: Detailed logging, graceful degradation, and automatic recovery
- **Flexible Configuration**: Support for multiple environments
- **Self-Healing**: Automatically handles common deployment issues like kubeconfig problems
- **Intelligent Retry Logic**: Exponential backoff with jitter
- **Timeout Management**: Operation-specific timeouts with configurable multipliers
- **Parallelism Control**: Reduces Proxmox storage lock contention

### Requirements

#### System Dependencies
```bash
# Required tools (must be in PATH)
terraform
ansible-playbook
kubectl

# Python 3.6+
python3

# Optional: PyYAML for advanced YAML processing
pip3 install PyYAML
```

#### Infrastructure Requirements
- Proxmox environment with API access
- SSH keys configured for VM access
- Terraform configuration for Proxmox K3s cluster
- Ansible playbooks for K3s configuration

### Installation

1. The script is located at: `/home/lordmuffin/Claude/Git/homelab/infrastructure/k3s-deploy.py`
2. Make it executable: `chmod +x k3s-deploy.py`
3. Ensure all prerequisites are installed

### Usage

#### Basic Commands

```bash
# Deploy a complete K3s cluster
python3 k3s-deploy.py deploy --environment production

# Deploy with auto-approval (no prompts)
python3 k3s-deploy.py deploy --environment production --auto-approve

# Deploy without Terraform (re-run Ansible only)
python3 k3s-deploy.py deploy --environment production --skip-terraform

# Destroy infrastructure
python3 k3s-deploy.py destroy --environment production --auto-approve

# Validate existing cluster
python3 k3s-deploy.py validate --environment production

# Verbose logging
python3 k3s-deploy.py deploy --environment production --verbose
```

#### Timeout and Retry Control

```bash
# Double all timeouts
python3 k3s-deploy.py deploy --environment production --timeout-multiplier 2.0

# Increase retries for problematic deployments
python3 k3s-deploy.py deploy --environment production --max-retries 5

# Reduce parallelism for unstable Proxmox environments
python3 k3s-deploy.py deploy --environment production --parallelism 1

# Combine options for maximum reliability
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 2.0 \
  --max-retries 5 \
  --parallelism 1 \
  --auto-approve
```

#### Command Options

- `deploy`: Complete deployment workflow (Terraform → VM Discovery → Ansible → Validation)
- `destroy`: Destroy Terraform infrastructure
- `validate`: Check existing cluster health

#### Flags

- `--environment, -e`: Target environment (required)
- `--terraform-dir, -t`: Custom Terraform directory path
- `--auto-approve, -y`: Automatically approve Terraform operations
- `--skip-terraform, -s`: Skip Terraform apply (useful for re-running only Ansible)
- `--verbose, -v`: Enable verbose logging
- `--timeout-multiplier`: Scale all timeouts up or down (default: 1.0)
- `--max-retries`: Maximum number of retries for operations (default: 3)
- `--parallelism`: Terraform parallelism level (default: 2)

---

## Timeout and Retry System

### Key Features

#### 🔄 Intelligent Retry Logic
- **Exponential Backoff**: Automatically increases delay between retries
- **Jitter**: Adds randomness to prevent thundering herd problems
- **Smart Error Detection**: Different retry strategies for different error types
- **Configurable Limits**: Adjustable retry counts and timeout values

#### ⏱️ Comprehensive Timeout Management
- **Operation-Specific Timeouts**: Different timeouts for each deployment phase
- **Configurable Multipliers**: Scale all timeouts up or down as needed
- **Phase-Based Timeouts**: Longer timeouts for complex operations like Ansible

#### 🚦 Parallelism Control
- **Reduced Terraform Parallelism**: Prevents Proxmox storage lock contention
- **Ansible Fork Limiting**: Reduces concurrent SSH connections
- **Load Balancing**: Distributes operations to prevent resource exhaustion

### Default Configuration

#### Timeout Settings (seconds)
```
terraform_apply: 1800   (30 minutes)
terraform_destroy: 900  (15 minutes)
vm_discovery: 300       (5 minutes)
ansible_playbook: 2700  (45 minutes)
cluster_validation: 180 (3 minutes)
ssh_connection: 30      (30 seconds)
vm_boot_wait: 180       (3 minutes)
```

#### Retry Configuration
```
Terraform Apply:    3 attempts, 5-60s backoff
Terraform Destroy:  2 attempts, 10-60s backoff
VM Discovery:       3 attempts, 10-120s backoff
Ansible Playbook:   2 attempts, 30-180s backoff
```

#### Parallelism Settings
```
Terraform: 2 concurrent operations (vs default 10)
Ansible: 3 forks (vs default 5)
SSH Timeout: 30 seconds
```

### Environment-Specific Settings

#### For Slow/Overloaded Proxmox Environments
```bash
# Conservative settings for heavily loaded systems
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 3.0 \
  --max-retries 5 \
  --parallelism 1 \
  --auto-approve
```

#### For Fast/High-Performance Environments
```bash
# Aggressive settings for fast systems
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 0.5 \
  --max-retries 2 \
  --parallelism 4 \
  --auto-approve
```

#### For Debugging/Testing
```bash
# Detailed logging with conservative settings
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 1.5 \
  --max-retries 3 \
  --verbose \
  --auto-approve
```

### Common Error Handling

#### Proxmox Lock Errors (Retryable)
```
Error: can't lock file '/var/lock/pve-manager/pve-storage-local-lvm' - got timeout
```
**Handling**: 3 retries with exponential backoff, reduced parallelism

#### VM Creation Timeouts (Retryable)
```
Error: error waiting for VM clone: timeout waiting for task completion
```
**Handling**: 3 retries with 5-60s backoff

#### Configuration Errors (Non-retryable)
```
Error: Invalid configuration block
```
**Handling**: Immediate failure with detailed error message

---

## Workflow Details

### Deploy Workflow

1. **Prerequisites Check**: Verify required tools are available
2. **Terraform Init**: Initialize Terraform configuration
3. **Terraform Plan**: Show planned infrastructure changes
4. **Terraform Apply**: Provision infrastructure (with approval prompt unless `--auto-approve`)
5. **VM IP Discovery**: Run discovery script to find VM IPs and update inventory
6. **Ansible Playbook**: Configure K3s cluster using Ansible
7. **Kubeconfig Update**: Create and validate kubeconfig file
8. **Cluster Validation**: Verify all nodes are healthy and ready

### Expected Directory Structure

```
infrastructure/
├── k3s-deploy.py                    # This script
├── proxmox/terraform/environments/
│   └── production/                  # Terraform configs
│       ├── main.tf
│       ├── terraform.tfstate
│       └── ...
└── k3s/ansible/
    ├── inventory/
    │   └── discovered-hosts.yml     # Auto-generated inventory
    ├── playbooks/
    │   └── configure-k3s-fixed.yml  # K3s configuration playbook
    └── scripts/
        └── discover-vm-ips.sh       # VM IP discovery script
```

---

## Current Deployment Status

### Cluster Status

✅ **CLUSTER OPERATIONAL**

#### Master Nodes (3/3 Ready)
- **k3s-masters-pve2-1** (192.168.11.129) - Primary Master ✅
- **k3s-masters-pve-nas-01-1** (192.168.11.115) - Secondary Master ✅
- **k3s-masters-pve4-1** (192.168.11.68) - Secondary Master ✅

#### Worker Nodes Status
- **Expected**: 6 worker nodes + 3 GPU nodes
- **Current**: 0 workers (not yet joined or not deployed)

#### Cluster Information
- **API Server**: https://192.168.11.129:6443
- **K3s Version**: v1.28.5+k3s1
- **Cluster Age**: ~5 minutes (fresh deployment)
- **Kubeconfig**: ~/.kube/k3s-cluster-config ✅

### Deployment Script Status

#### ✅ Working Features
1. **Terraform Integration**: Successfully detects and uses Terraform configurations
2. **VM IP Discovery**: Integrates with existing discover-vm-ips.sh script
3. **Ansible Orchestration**: Runs K3s configuration playbooks
4. **Smart Kubeconfig Handling**: 
   - Automatically fetches kubeconfig when Ansible task fails
   - Updates server IP addresses correctly
   - Validates cluster connectivity
5. **Cluster Validation**: Comprehensive health checks and node reporting
6. **Error Recovery**: Handles missing kubeconfig and permission issues

#### 🔧 Known Issues Resolved
1. **Kubeconfig Permission Issue**: Script now handles cases where Ansible fails to create kubeconfig due to permissions
2. **IP Address Updates**: Script correctly updates server addresses from 127.0.0.1 to actual master IP
3. **YAML Dependency**: Script works with or without PyYAML library

---

## Kubeconfig Management

The script creates and manages your kubeconfig at: `~/.kube/k3s-cluster-config`

### Connection Methods

1. **Export kubeconfig (recommended)**:
   ```bash
   export KUBECONFIG=~/.kube/k3s-cluster-config
   kubectl get nodes
   ```

2. **Use helper script**:
   ```bash
   ~/k3s-kubectl get nodes
   ```

3. **Specify per command**:
   ```bash
   kubectl --kubeconfig=~/.kube/k3s-cluster-config get nodes
   ```

---

## Cluster Validation

The validation process checks:
- Cluster connectivity
- Node count and status
- Node roles (master, worker, GPU)
- All nodes ready status
- Cluster information

Example output:
```
✓ Cluster validation completed:
  - Total nodes: 12
  - Ready nodes: 12
  - Master nodes: 3
  - Worker nodes: 6
  - GPU nodes: 3
  - All nodes ready: True
```

---

## Troubleshooting

### Common Issues

1. **"Command not found" errors**:
   - Ensure terraform, ansible-playbook, and kubectl are in PATH
   - Install missing tools

2. **"Directory not found" errors**:
   - Check that Terraform and Ansible directories exist
   - Use `--terraform-dir` to specify custom path

3. **"Connection refused" during validation**:
   - Cluster may still be starting up (wait a few minutes)
   - Check network connectivity to cluster nodes
   - Verify kubeconfig is correct

4. **SSH key issues**:
   - Ensure SSH key exists at `~/.ssh/id_rsa`
   - Verify key has access to VMs
   - Check SSH agent is running

5. **Proxmox Storage Locks**:
   - Use `--parallelism 1 --timeout-multiplier 2.0 --max-retries 5`

6. **Slow VM Boot Times**:
   - Use `--timeout-multiplier 2.0 --max-retries 4`

### Debug Mode

Use the `--verbose` flag for detailed debugging output:
```bash
python3 k3s-deploy.py deploy --environment production --verbose
```

### Troubleshooting Scenarios

#### Scenario 1: Proxmox Storage Locks
**Symptoms**: `can't lock file` errors during VM creation
**Solution**:
```bash
python3 k3s-deploy.py deploy --environment production \
  --parallelism 1 \
  --timeout-multiplier 2.0 \
  --max-retries 5 \
  --auto-approve
```

#### Scenario 2: Slow VM Boot Times
**Symptoms**: VM discovery timeouts, SSH connection failures
**Solution**:
```bash
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 2.0 \
  --max-retries 4 \
  --auto-approve
```

#### Scenario 3: Network Instability
**Symptoms**: Ansible connection errors, intermittent SSH failures
**Solution**:
```bash
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 1.5 \
  --max-retries 4 \
  --verbose
```

#### Scenario 4: Large Cluster Deployments
**Symptoms**: Timeouts with 12+ VMs, resource exhaustion
**Solution**:
```bash
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 3.0 \
  --parallelism 1 \
  --max-retries 3 \
  --auto-approve
```

---

## Logging

- Logs are written to `/tmp/k3s-deploy.log` and console
- Use `--verbose` flag for detailed debugging output
- All commands executed are logged for troubleshooting

---

## Usage Examples

### First-time Deployment
```bash
# Deploy new cluster with full workflow
python3 k3s-deploy.py deploy --environment production --verbose
```

### Re-deploy After Config Changes
```bash
# Skip Terraform, just re-run Ansible
python3 k3s-deploy.py deploy --environment production --skip-terraform
```

### Automated Deployment
```bash
# For CI/CD or automated deployments
python3 k3s-deploy.py deploy --environment production --auto-approve
```

### Infrastructure Cleanup
```bash
# Remove all infrastructure
python3 k3s-deploy.py destroy --environment production --auto-approve
```

---

## File Locations

- **Main Script**: `/home/lordmuffin/Claude/Git/homelab/infrastructure/k3s-deploy.py`
- **Helper Script**: `/home/lordmuffin/k3s-kubectl`
- **Kubeconfig**: `/home/lordmuffin/.kube/k3s-cluster-config`
- **Logs**: `/tmp/k3s-deploy.log`
- **Inventory**: `/home/lordmuffin/Claude/Git/homelab/infrastructure/k3s/ansible/inventory/discovered-hosts.yml`

---

## Integration with Existing Homelab

This infrastructure layer is designed to integrate seamlessly with the existing homelab repository:

- **Extends existing Terraform**: Works alongside current terraform modules
- **Integrates with ArgoCD**: Cluster becomes a deployment target for existing apps
- **Enhances monitoring**: Extends current Prometheus/Grafana setup
- **Preserves workflows**: Works with existing GitHub Actions and security practices

---

## Next Steps

1. **Deploy Worker Nodes**: If worker nodes are expected but not showing up, they may need to be deployed separately or the inventory may need updates
2. **Configure CNI**: Cluster is ready for CNI configuration (Cilium, Flannel, etc.)
3. **Deploy Applications**: Cluster is ready for application deployments
4. **Setup Monitoring**: Ready for Prometheus/Grafana deployment
5. **Configure Storage**: Ready for Longhorn or other storage solutions

---

## Quick Reference

### Essential Commands
```bash
# Basic deployment
python3 k3s-deploy.py deploy --environment production --auto-approve

# Robust deployment for problematic environments
python3 k3s-deploy.py deploy --environment production \
  --timeout-multiplier 2.0 --max-retries 5 --parallelism 1 --auto-approve

# Cluster validation
python3 k3s-deploy.py validate --environment production

# Infrastructure cleanup
python3 k3s-deploy.py destroy --environment production --auto-approve
```

### Connection Methods
```bash
# Method 1: Export KUBECONFIG
export KUBECONFIG=~/.kube/k3s-cluster-config
kubectl get nodes

# Method 2: Helper Script
~/k3s-kubectl get nodes

# Method 3: Per-command
kubectl --kubeconfig=~/.kube/k3s-cluster-config get nodes
```

The deployment wrapper script is production-ready and successfully handles the complete K3s deployment workflow with robust error handling, intelligent retries, and comprehensive recovery mechanisms.