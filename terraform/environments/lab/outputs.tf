# Lab Environment Outputs

# Cluster Information
output "cluster_name" {
  description = "Name of the lab cluster"
  value       = module.lab_cluster.cloudspace_name
}

output "cluster_id" {
  description = "ID of the lab cluster"
  value       = module.lab_cluster.cloudspace_id
}

output "cluster_region" {
  description = "Region where the lab cluster is deployed"
  value       = module.lab_cluster.region
}

output "kubernetes_version" {
  description = "Kubernetes version of the lab cluster"
  value       = module.lab_cluster.kubernetes_version
}

output "ha_control_plane_enabled" {
  description = "Whether HA control plane is enabled"
  value       = module.lab_cluster.ha_control_plane
}

# Node Pool Information
output "worker_pools_summary" {
  description = "Summary of all worker node pools"
  value = {
    for name, pool in module.lab_cluster.worker_pools : name => {
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
  value       = module.lab_cluster.worker_pools["general"]
}

output "experimental_worker_pool" {
  description = "Experimental worker pool details"
  value       = module.lab_cluster.worker_pools["experimental"]
}

# Kubeconfig
output "kubeconfig" {
  description = "Kubeconfig for accessing the lab cluster"
  value       = module.lab_cluster.kubeconfig
  sensitive   = true
}

output "kubeconfig_base64" {
  description = "Base64 encoded kubeconfig for CI/CD systems"
  value       = module.lab_cluster.kubeconfig_base64
  sensitive   = true
}

# Development Information
output "development_namespace" {
  description = "Development namespace details"
  value = var.create_dev_namespace ? {
    name   = "development"
    labels = kubernetes_namespace.lab_development[0].metadata[0].labels
  } : null
}

output "testing_namespace" {
  description = "Testing namespace details"
  value = var.create_test_namespace ? {
    name   = "testing"
    labels = kubernetes_namespace.lab_testing[0].metadata[0].labels
  } : null
}

# Resource Information
output "total_min_nodes" {
  description = "Total minimum nodes across all pools"
  value = sum([
    var.general_worker_min_nodes,
    var.experimental_worker_min_nodes
  ])
}

output "total_max_nodes" {
  description = "Total maximum nodes across all pools"
  value = sum([
    var.general_worker_max_nodes,
    var.experimental_worker_max_nodes
  ])
}

output "total_desired_nodes" {
  description = "Total desired nodes across all pools"
  value = sum([
    var.general_worker_desired_nodes,
    var.experimental_worker_desired_nodes
  ])
}

# Cost Information
output "estimated_monthly_cost_usd" {
  description = "Estimated monthly cost in USD (based on desired nodes at bid prices)"
  value = {
    general_workers      = var.general_worker_desired_nodes * var.general_worker_bid_price * 24 * 30
    experimental_workers = var.experimental_worker_desired_nodes * var.experimental_worker_bid_price * 24 * 30
    total               = (
      var.general_worker_desired_nodes * var.general_worker_bid_price * 24 * 30 +
      var.experimental_worker_desired_nodes * var.experimental_worker_bid_price * 24 * 30
    )
    savings_vs_prod = "Estimated 60-70% cost savings compared to production configuration"
  }
}

output "cost_optimization_features" {
  description = "Cost optimization features enabled"
  value = {
    lower_bid_prices        = "Reduced bid prices for cost savings"
    smaller_node_sizes      = "Smaller server classes for development workloads"
    fewer_nodes            = "Reduced minimum and desired node counts"
    preemptible_workloads  = "Experimental nodes can be preempted more frequently"
    optional_ha_control    = "HA control plane can be disabled if needed"
  }
}

# Network and Security
output "network_policies_enabled" {
  description = "Whether network policies are enabled"
  value       = var.enable_network_policies
}

output "network_policy_mode" {
  description = "Network policy mode for lab environment"
  value       = var.lab_network_policy_mode
}

# Lab-specific Features
output "lab_features" {
  description = "Lab-specific features and configurations"
  value = {
    experimental_features_enabled = var.enable_experimental_features
    debug_mode_enabled           = var.enable_debug_mode
    auto_shutdown_planned        = var.auto_shutdown_enabled
    cost_alert_threshold         = var.cost_alert_threshold
  }
}

# Quick Access Commands
output "kubectl_config_command" {
  description = "Command to configure kubectl for this cluster"
  value       = "echo '${module.lab_cluster.kubeconfig_base64}' | base64 -d > ~/.kube/config-lab && export KUBECONFIG=~/.kube/config-lab"
}

output "cluster_info_command" {
  description = "Command to get cluster information"
  value       = "kubectl cluster-info && kubectl get nodes -o wide"
}

# Environment Comparison
output "environment_type" {
  description = "Environment characteristics"
  value = {
    type                = "lab/development"
    cost_optimized     = true
    high_availability  = var.ha_control_plane
    experimental_ready = true
    production_ready   = false
  }
}