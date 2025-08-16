# Lab Environment Terraform Configuration
# This deploys a lab/development Kubernetes cluster with cost optimization

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
  #   key    = "lab/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Lab cluster configuration with HA control plane
module "lab_cluster" {
  source = "../../modules/rackspace-spot"

  # Cluster configuration
  cloudspace_name    = var.lab_cloudspace_name
  region             = var.region
  kubernetes_version = var.kubernetes_version
  cni                = var.cni
  ha_control_plane   = var.ha_control_plane  # Configurable for lab
  
  # Monitoring (optional webhook for lab)
  preemption_webhook    = var.preemption_webhook
  wait_until_ready      = true
  network_policy_enabled = var.enable_network_policies
  
  # Authentication
  rackspace_spot_token = var.rackspace_spot_token

  # Lab node pools optimized for cost and experimentation
  worker_node_pools = [
    # General purpose worker nodes (smaller and fewer for cost savings)
    {
      name         = "general"
      server_class = var.general_worker_server_class
      bid_price    = var.general_worker_bid_price
      min_nodes    = var.general_worker_min_nodes
      max_nodes    = var.general_worker_max_nodes
      desired_nodes = var.general_worker_desired_nodes
      labels = {
        "node-type"    = "general"
        "environment"  = "lab"
        "workload"     = "general"
        "cost-tier"    = "low"
      }
    },
    # Experimental/testing nodes (can be preempted more often)
    {
      name         = "experimental"
      server_class = var.experimental_worker_server_class
      bid_price    = var.experimental_worker_bid_price
      min_nodes    = var.experimental_worker_min_nodes
      max_nodes    = var.experimental_worker_max_nodes
      desired_nodes = var.experimental_worker_desired_nodes
      labels = {
        "node-type"    = "experimental"
        "environment"  = "lab"
        "workload"     = "testing"
        "preemptible"  = "true"
      }
      taints = [
        {
          key    = "workload"
          value  = "experimental"
          effect = "NoSchedule"
        }
      ]
    }
  ]

  # Common labels for all resources
  common_labels = merge(var.common_labels, {
    "environment" = "lab"
    "cluster"     = var.lab_cloudspace_name
    "tier"        = "development"
    "cost-tier"   = "optimized"
  })
}

# Optional network policies for lab environment (less restrictive than prod)
resource "kubernetes_network_policy" "lab_default_allow" {
  count = var.enable_network_policies && var.lab_network_policy_mode == "permissive" ? 1 : 0
  
  metadata {
    name      = "default-allow-intra-namespace"
    namespace = "default"
    labels = {
      "environment" = "lab"
      "policy-type" = "permissive"
    }
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress"]
    
    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = "default"
          }
        }
      }
    }
  }
  
  depends_on = [module.lab_cluster]
}

# Restrictive network policies for lab (when needed for testing security)
resource "kubernetes_network_policy" "lab_default_deny" {
  count = var.enable_network_policies && var.lab_network_policy_mode == "restrictive" ? 1 : 0
  
  metadata {
    name      = "default-deny-all"
    namespace = "default"
    labels = {
      "environment" = "lab"
      "policy-type" = "security-testing"
    }
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
  
  depends_on = [module.lab_cluster]
}

# Development namespace with relaxed policies
resource "kubernetes_namespace" "lab_development" {
  count = var.create_dev_namespace ? 1 : 0
  
  metadata {
    name = "development"
    labels = {
      "environment"     = "lab"
      "purpose"         = "development"
      "network-policy"  = "permissive"
    }
  }
  
  depends_on = [module.lab_cluster]
}

# Testing namespace with experimental workloads
resource "kubernetes_namespace" "lab_testing" {
  count = var.create_test_namespace ? 1 : 0
  
  metadata {
    name = "testing"
    labels = {
      "environment"     = "lab"
      "purpose"         = "testing"
      "network-policy"  = "experimental"
    }
  }
  
  depends_on = [module.lab_cluster]
}