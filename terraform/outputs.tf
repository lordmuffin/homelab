# Proxmox K3s Cluster Outputs
output "k3s_cluster_details" {
  description = "Details of the K3s cluster deployment"
  value       = try(module.proxmox_k3s.vm_details, {})
}

output "k3s_server_ips" {
  description = "IP addresses of K3s server nodes"
  value       = try(module.proxmox_k3s.server_ips, [])
}

output "k3s_agent_ips" {
  description = "IP addresses of K3s agent nodes"  
  value       = try(module.proxmox_k3s.agent_ips, [])
}

output "k3s_primary_server_ip" {
  description = "Primary K3s server IP address"
  value       = try(module.proxmox_k3s.primary_server_ip, null)
}

output "k3s_cluster_endpoint" {
  description = "K3s cluster endpoint URL"
  value       = try(module.proxmox_k3s.cluster_endpoint, null)
}

output "k3s_gpu_agents" {
  description = "GPU-enabled agent node details"
  value       = try(module.proxmox_k3s.gpu_agents, {})
}