# Cloudspace outputs
output "cloudspace_name" {
  description = "Name of the created cloudspace"
  value       = resource.spot_cloudspace.main.cloudspace_name
}

output "cloudspace_id" {
  description = "ID of the created cloudspace"
  value       = resource.spot_cloudspace.main.id
}

output "region" {
  description = "Region where the cloudspace is deployed"
  value       = resource.spot_cloudspace.main.region
}

output "kubernetes_version" {
  description = "Kubernetes version deployed"
  value       = resource.spot_cloudspace.main.kubernetes_version
}

output "ha_control_plane" {
  description = "Whether HA control plane is enabled"
  value       = resource.spot_cloudspace.main.hacontrol_plane
}

# Node pool outputs
output "worker_pools" {
  description = "Worker node pool information"
  value = {
    for name, pool in spot_spotnodepool.worker_pools : name => {
      id                   = pool.id
      server_class         = pool.server_class
      bid_price            = pool.bid_price
      desired_server_count = pool.desired_server_count
      min_nodes            = pool.autoscaling.min_nodes
      max_nodes            = pool.autoscaling.max_nodes
      labels               = pool.labels
    }
  }
}

# Kubeconfig output
output "kubeconfig" {
  description = "Kubeconfig for accessing the cluster"
  value       = data.spot_kubeconfig.main.raw
  sensitive   = true
}

output "kubeconfig_base64" {
  description = "Base64 encoded kubeconfig"
  value       = base64encode(data.spot_kubeconfig.main.raw)
  sensitive   = true
}

# Server classes information
output "available_server_classes" {
  description = "Available server classes meeting filter criteria"
  value       = data.spot_serverclasses.all.names
}