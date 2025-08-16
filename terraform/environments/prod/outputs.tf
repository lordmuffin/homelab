# Production Environment Outputs

# Cluster Information
output "cluster_name" {
  description = "Name of the production cluster"
  value       = module.prod_cluster.cloudspace_name
}

output "cluster_id" {
  description = "ID of the production cluster"
  value       = module.prod_cluster.cloudspace_id
}

output "cluster_region" {
  description = "Region where the production cluster is deployed"
  value       = module.prod_cluster.region
}

output "kubernetes_version" {
  description = "Kubernetes version of the production cluster"
  value       = module.prod_cluster.kubernetes_version
}

output "ha_control_plane_enabled" {
  description = "Whether HA control plane is enabled"
  value       = module.prod_cluster.ha_control_plane
}

# Node Pool Information
output "worker_pools_summary" {
  description = "Summary of all worker node pools"
  value = {
    for name, pool in module.prod_cluster.worker_pools : name => {
      server_class         = pool.server_class
      bid_price            = pool.bid_price
      desired_server_count = pool.desired_server_count
      min_nodes            = pool.min_nodes
      max_nodes            = pool.max_nodes
    }
  }
}

output "general_worker_pool" {
  description = "General worker pool details"
  value       = module.prod_cluster.worker_pools["general"]
}

output "memory_worker_pool" {
  description = "Memory-optimized worker pool details"
  value       = module.prod_cluster.worker_pools["memory-optimized"]
}

output "gpu_worker_pool" {
  description = "GPU worker pool details"
  value       = module.prod_cluster.worker_pools["gpu"]
}

# Kubeconfig
output "kubeconfig" {
  description = "Kubeconfig for accessing the production cluster"
  value       = module.prod_cluster.kubeconfig
  sensitive   = true
}

output "kubeconfig_base64" {
  description = "Base64 encoded kubeconfig for CI/CD systems"
  value       = module.prod_cluster.kubeconfig_base64
  sensitive   = true
}

# Connection Information
output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = "Generated from kubeconfig - use kubectl with provided kubeconfig"
}

# Resource Information
output "total_min_nodes" {
  description = "Total minimum nodes across all pools"
  value = sum([
    var.general_worker_min_nodes,
    var.memory_worker_min_nodes,
    var.gpu_worker_min_nodes
  ])
}

output "total_max_nodes" {
  description = "Total maximum nodes across all pools"
  value = sum([
    var.general_worker_max_nodes,
    var.memory_worker_max_nodes,
    var.gpu_worker_max_nodes
  ])
}

output "total_desired_nodes" {
  description = "Total desired nodes across all pools"
  value = sum([
    var.general_worker_desired_nodes,
    var.memory_worker_desired_nodes,
    var.gpu_worker_desired_nodes
  ])
}

# Cost Estimation
output "estimated_monthly_cost_usd" {
  description = "Estimated monthly cost in USD (based on desired nodes at bid prices)"
  value = {
    general_workers = var.general_worker_desired_nodes * var.general_worker_bid_price * 24 * 30
    memory_workers  = var.memory_worker_desired_nodes * var.memory_worker_bid_price * 24 * 30
    gpu_workers     = var.gpu_worker_desired_nodes * var.gpu_worker_bid_price * 24 * 30
    total          = (
      var.general_worker_desired_nodes * var.general_worker_bid_price * 24 * 30 +
      var.memory_worker_desired_nodes * var.memory_worker_bid_price * 24 * 30 +
      var.gpu_worker_desired_nodes * var.gpu_worker_bid_price * 24 * 30
    )
  }
}

# Network Policy Status
output "network_policies_enabled" {
  description = "Whether network policies are enabled for security"
  value       = var.enable_network_policies
}