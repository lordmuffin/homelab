# Terraform Environments

This directory contains environment-specific Terraform configurations for deploying Kubernetes clusters using Rackspace Spot. Each environment is designed for specific use cases with appropriate cost optimization and security configurations.

## 📁 Directory Structure

```
terraform/environments/
├── prod/                     # Production environment
│   ├── main.tf              # Main configuration
│   ├── variables.tf         # Variable definitions
│   ├── outputs.tf           # Output definitions
│   └── terraform.tfvars.example  # Example configuration
├── lab/                      # Lab/Development environment
│   ├── main.tf              # Main configuration
│   ├── variables.tf         # Variable definitions
│   ├── outputs.tf           # Output definitions
│   └── terraform.tfvars.example  # Example configuration
└── README.md                # This documentation
```

## 🏗️ Architecture Overview

Both environments use the enhanced `rackspace-spot` module which provides:

- **HA Control Plane**: 3 control plane nodes for high availability
- **Multiple Node Pools**: Different worker node types for various workloads
- **Network Segmentation**: Environment-specific network policies
- **Cost Optimization**: Configurable bid prices and node counts
- **Auto-scaling**: Dynamic scaling based on workload demands

## 🚀 Production Environment

### Features
- **High Availability**: HA control plane with 3 control nodes
- **Multi-tier Workers**: General, memory-optimized, and GPU node pools
- **Enhanced Security**: Restrictive network policies by default
- **Production-grade**: Optimized for reliability and performance
- **Cost Monitoring**: Built-in cost estimation and tracking

### Node Pools
1. **General Workers** (4 vCPU, 16GB): General workloads
2. **Memory-Optimized** (8 vCPU, 32GB): Data processing
3. **GPU Workers** (GPU-enabled): ML/AI workloads

### Quick Start
```bash
cd terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

## 🧪 Lab Environment

### Features
- **Cost Optimized**: Lower bid prices and smaller instance types
- **Configurable HA**: Can disable HA control plane for cost savings
- **Experimental Ready**: Support for experimental features and testing
- **Flexible Security**: Permissive network policies for easier development
- **Development Namespaces**: Pre-configured dev and test namespaces

### Node Pools
1. **General Workers** (2 vCPU, 8GB): Development workloads
2. **Experimental** (1 vCPU, 4GB): Testing and experiments

### Quick Start
```bash
cd terraform/environments/lab
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

## 🔧 Configuration

### Required Variables
- `rackspace_spot_token`: Your Rackspace Spot authentication token

### Common Configuration Options

#### Production Environment
```hcl
# High availability with robust worker pools
prod_cloudspace_name = "prod-homelab"
general_worker_desired_nodes = 4
memory_worker_desired_nodes = 2
gpu_worker_desired_nodes = 1
enable_network_policies = true
```

#### Lab Environment
```hcl
# Cost-optimized for development
lab_cloudspace_name = "lab-homelab"
ha_control_plane = true  # Can be false for cost savings
general_worker_desired_nodes = 3
experimental_worker_desired_nodes = 1
enable_network_policies = false  # More permissive
```

## 💰 Cost Comparison

| Configuration | Production | Lab (HA) | Lab (Single CP) |
|---------------|------------|----------|-----------------|
| Control Plane | 3 nodes | 3 nodes | 1 node |
| Worker Nodes | 7 nodes | 4 nodes | 4 nodes |
| Monthly Cost* | ~$120 | ~$40 | ~$25 |
| Use Case | Production | Development | Testing |

*Estimated costs based on default configurations and bid prices

## 🛡️ Security Features

### Production
- **Default Deny**: All traffic blocked by default
- **Namespace Isolation**: Strict network segmentation
- **Taint/Tolerations**: Workload isolation
- **RBAC Ready**: Prepared for role-based access control

### Lab
- **Permissive Mode**: Allow intra-namespace communication
- **Experimental Security**: Can enable restrictive mode for testing
- **Development Friendly**: Easier access for development workflows

## 🔄 Network Segmentation

### Environment Isolation
Each environment deploys to a separate Rackspace Spot cloudspace:
- **Production**: `prod-homelab` cloudspace
- **Lab**: `lab-homelab` cloudspace

### Intra-environment Segmentation
- **Node Pool Labels**: Automatic labeling for workload placement
- **Taints/Tolerations**: Dedicated nodes for specific workloads
- **Network Policies**: Kubernetes-native network segmentation
- **Namespace Isolation**: Logical separation of applications

## 📊 Monitoring and Observability

### Built-in Outputs
- Cluster information and endpoints
- Node pool status and capacity
- Cost estimation and tracking
- Kubeconfig for cluster access

### Integration Ready
- Prometheus monitoring labels
- Cost center tagging
- Environment classification
- Resource usage tracking

## 🚀 Deployment Workflows

### Initial Deployment
1. Choose environment (prod or lab)
2. Copy and configure `terraform.tfvars`
3. Initialize Terraform: `terraform init`
4. Plan deployment: `terraform plan`
5. Apply configuration: `terraform apply`

### Environment Updates
1. Modify `terraform.tfvars` as needed
2. Plan changes: `terraform plan`
3. Apply updates: `terraform apply`

### Cluster Access
```bash
# Get kubeconfig (example for production)
terraform output -raw kubeconfig > ~/.kube/config-prod
export KUBECONFIG=~/.kube/config-prod
kubectl cluster-info
```

## 🔧 Customization

### Adding Node Pools
Modify the `worker_node_pools` variable in your environment configuration:

```hcl
worker_node_pools = [
  {
    name         = "custom-pool"
    server_class = "gp.vs1.large-ord"
    bid_price    = 0.020
    min_nodes    = 1
    max_nodes    = 5
    desired_nodes = 2
    labels = {
      "workload-type" = "custom"
    }
    taints = [
      {
        key    = "custom"
        value  = "true"
        effect = "NoSchedule"
      }
    ]
  }
]
```

### Environment-specific Customization
- **Production**: Focus on reliability, security, and performance
- **Lab**: Optimize for cost, flexibility, and experimentation

## 📋 Best Practices

### Cost Management
1. **Lab Environment**: Start with minimal configuration and scale up
2. **Production**: Use appropriate bid prices for cost vs. availability balance
3. **Monitoring**: Regularly review cost outputs and actual usage

### Security
1. **Network Policies**: Enable appropriate level for environment
2. **Taints/Tolerations**: Use for workload isolation
3. **RBAC**: Implement role-based access control post-deployment

### Operations
1. **State Management**: Use remote state for production environments
2. **Version Control**: Keep environment configurations in version control
3. **Change Management**: Always plan before applying changes

## 🆘 Troubleshooting

### Common Issues
1. **Authentication**: Verify Rackspace Spot token is valid
2. **Resources**: Check regional availability of server classes
3. **Networking**: Verify network policies allow required traffic

### Validation
```bash
# Validate configuration
terraform validate

# Check planning
terraform plan

# Verify cluster health
kubectl get nodes
kubectl get pods --all-namespaces
```

## 📚 Additional Resources

- [Rackspace Spot Documentation](https://docs.rackspace.com/spot/)
- [Terraform Documentation](https://www.terraform.io/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Module Source](../../modules/rackspace-spot/)

## 🤝 Contributing

When modifying these environments:
1. Test changes in lab environment first
2. Update documentation for significant changes
3. Validate configurations with `terraform validate`
4. Consider cost impacts of changes