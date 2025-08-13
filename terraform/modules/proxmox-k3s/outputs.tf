output "vm_details" {
  description = "Details of all created VMs"
  value = {
    for key, vm in proxmox_virtual_environment_vm.k3s_nodes : key => {
      id          = vm.id
      name        = vm.name
      node_name   = vm.node_name
      vm_id       = vm.vm_id
      vm_type     = local.vm_instances[key].vm_type
      environment = local.vm_instances[key].environment
      ip_address  = local.vm_instances[key].ip_address
      status      = vm.status
    }
  }
}

output "server_ips" {
  description = "IP addresses of K3s server nodes"
  value = [
    for vm in local.server_vms : vm.ip_address
  ]
}

output "agent_ips" {
  description = "IP addresses of K3s agent nodes"
  value = [
    for vm in local.agent_vms : vm.ip_address
  ]
}

output "primary_server_ip" {
  description = "IP address of the primary K3s server"
  value       = local.primary_server != null ? local.primary_server.ip_address : null
}

output "cluster_endpoint" {
  description = "K3s cluster endpoint"
  value       = local.primary_server != null ? local.primary_server.tls_san : null
}

output "vm_ids" {
  description = "Map of VM names to their Proxmox VM IDs"
  value = {
    for key, vm in proxmox_virtual_environment_vm.k3s_nodes : vm.name => vm.vm_id
  }
}

output "kubeconfig_path" {
  description = "Path to retrieve kubeconfig from primary server"
  value       = local.primary_server != null ? "/home/${var.vm_user}/.kube/config" : null
}

output "gpu_agents" {
  description = "Details of GPU-enabled agent nodes"
  value = {
    for key, vm in proxmox_virtual_environment_vm.k3s_nodes : key => {
      name       = vm.name
      ip_address = local.vm_instances[key].ip_address
      node_name  = vm.node_name
    }
    if local.vm_instances[key].vm_type == "gpu-agent"
  }
}