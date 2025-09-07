# Production Environment Outputs for K3s Homelab Cluster

# Cluster Information
output "cluster_name" {
  description = "Name of the deployed K3s cluster"
  value       = local.cluster_name
}

output "environment" {
  description = "Environment name"
  value       = local.environment
}

# Aggregated Cluster Information from Available Nodes
output "cluster_nodes" {
  description = "Information about all cluster nodes across all Proxmox nodes"
  value = merge(
    module.k3s_cluster_pve2.cluster_nodes,
    module.k3s_cluster_pve_nas_01.cluster_nodes,
    module.k3s_cluster_pve4.cluster_nodes
  )
}

output "k3s_token" {
  description = "K3s cluster token"
  value       = module.k3s_cluster_pve2.k3s_token
  sensitive   = true
}

output "master_nodes" {
  description = "Master node information from all nodes"
  value = concat(
    module.k3s_cluster_pve2.master_nodes,
    module.k3s_cluster_pve_nas_01.master_nodes,
    module.k3s_cluster_pve4.master_nodes
  )
}

output "worker_nodes" {
  description = "Worker node information from all nodes"
  value = concat(
    module.k3s_cluster_pve2.worker_nodes,
    module.k3s_cluster_pve_nas_01.worker_nodes,
    module.k3s_cluster_pve4.worker_nodes
  )
}

output "cluster_size_per_node" {
  description = "Cluster size summary per Proxmox node"
  value = {
    pve2       = module.k3s_cluster_pve2.node_cluster_size
    pve-nas-01 = module.k3s_cluster_pve_nas_01.node_cluster_size
    pve4       = module.k3s_cluster_pve4.node_cluster_size
  }
}

output "total_cluster_size" {
  description = "Total cluster size summary across all nodes"
  value = {
    total_vms = (
      module.k3s_cluster_pve2.node_cluster_size.total_vms_on_node +
      module.k3s_cluster_pve_nas_01.node_cluster_size.total_vms_on_node +
      module.k3s_cluster_pve4.node_cluster_size.total_vms_on_node
    )
    total_masters = (
      module.k3s_cluster_pve2.node_cluster_size.masters_on_node +
      module.k3s_cluster_pve_nas_01.node_cluster_size.masters_on_node +
      module.k3s_cluster_pve4.node_cluster_size.masters_on_node
    )
    total_workers = (
      module.k3s_cluster_pve2.node_cluster_size.workers_on_node +
      module.k3s_cluster_pve_nas_01.node_cluster_size.workers_on_node +
      module.k3s_cluster_pve4.node_cluster_size.workers_on_node
    )
    total_gpu_workers = (
      module.k3s_cluster_pve2.node_cluster_size.gpu_workers_on_node +
      module.k3s_cluster_pve_nas_01.node_cluster_size.gpu_workers_on_node +
      module.k3s_cluster_pve4.node_cluster_size.gpu_workers_on_node
    )
    environment = local.environment
  }
}

# Legacy outputs for compatibility
output "master_ips" {
  description = "IP addresses of K3s master nodes (DHCP assigned)"
  value       = "Check cluster_nodes output for VM details"
}

output "worker_ips" {
  description = "IP addresses of K3s worker nodes (DHCP assigned)"
  value       = "Check cluster_nodes output for VM details"
}

output "kubeconfig_commands" {
  description = "Commands to access the K3s cluster"
  value = {
    info = "VMs use DHCP - check Proxmox console for actual IPs"
    general_access = "ssh ubuntu@<vm-ip> and use /etc/rancher/k3s/k3s.yaml"
  }
}

output "k3s_server_url" {
  description = "K3s server URL for additional nodes"
  value       = "Will be available after VMs boot - check master node IPs"
}

output "ssh_access" {
  description = "SSH access information for all nodes"
  value       = "VMs use DHCP - check Proxmox console for actual IPs, then ssh ubuntu@<vm-ip>"
}