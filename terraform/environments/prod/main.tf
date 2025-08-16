# Production Environment Terraform Configuration
# This deploys a production Kubernetes cluster with HA control plane

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    spot = {
      source  = "rackerlabs/spot"
      version = "~> 1.0"
    }
  }
  
  # Uncomment and configure for remote state
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Production cluster configuration with HA control plane
module "prod_cluster" {
  source = "../../modules/rackspace-spot"

  # Cluster configuration
  cloudspace_name    = var.prod_cloudspace_name
  region             = var.region
  kubernetes_version = var.kubernetes_version
  cni                = var.cni
  ha_control_plane   = true  # HA control plane for production
  
  # Security and monitoring
  preemption_webhook    = var.preemption_webhook
  wait_until_ready      = true
  network_policy_enabled = true
  
  # Authentication
  rackspace_spot_token = var.rackspace_spot_token

  # Production node pools with multiple worker types
  worker_node_pools = [
    # General purpose worker nodes
    {
      name         = "general"
      server_class = var.general_worker_server_class
      bid_price    = var.general_worker_bid_price
      min_nodes    = var.general_worker_min_nodes
      max_nodes    = var.general_worker_max_nodes
      desired_nodes = var.general_worker_desired_nodes
      labels = {
        "node-type"    = "general"
        "environment"  = "production"
        "workload"     = "general"
      }
    },
    # High-memory nodes for data processing
    {
      name         = "memory-optimized"
      server_class = var.memory_worker_server_class
      bid_price    = var.memory_worker_bid_price
      min_nodes    = var.memory_worker_min_nodes
      max_nodes    = var.memory_worker_max_nodes
      desired_nodes = var.memory_worker_desired_nodes
      labels = {
        "node-type"    = "memory-optimized"
        "environment"  = "production"
        "workload"     = "data-processing"
      }
      taints = [
        {
          key    = "workload"
          value  = "memory-intensive"
          effect = "NoSchedule"
        }
      ]
    },
    # GPU nodes for ML/AI workloads (if needed)
    {
      name         = "gpu"
      server_class = var.gpu_worker_server_class
      bid_price    = var.gpu_worker_bid_price
      min_nodes    = var.gpu_worker_min_nodes
      max_nodes    = var.gpu_worker_max_nodes
      desired_nodes = var.gpu_worker_desired_nodes
      labels = {
        "node-type"     = "gpu"
        "environment"   = "production"
        "workload"      = "ml-ai"
        "accelerator"   = "gpu"
      }
      taints = [
        {
          key    = "workload"
          value  = "gpu-intensive"
          effect = "NoSchedule"
        }
      ]
    }
  ]

  # Common labels for all resources
  common_labels = merge(var.common_labels, {
    "environment" = "production"
    "cluster"     = var.prod_cloudspace_name
    "tier"        = "production"
  })
}

# Network policies for production environment
resource "kubernetes_network_policy" "prod_default_deny" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "default-deny-all"
    namespace = "default"
    labels = {
      "environment" = "production"
      "policy-type" = "security"
    }
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
  
  depends_on = [module.prod_cluster]
}

# Network policy for system namespaces
resource "kubernetes_network_policy" "prod_system_allow" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "system-allow"
    namespace = "kube-system"
    labels = {
      "environment" = "production"
      "policy-type" = "system"
    }
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
    
    ingress {
      from = []
    }
    
    egress {
      to = []
    }
  }
  
  depends_on = [module.prod_cluster]
}