output "talos_secrets_yaml" {
  description = "The raw YAML for the Talos machine secrets."
  value       = talos_machine_secrets.controlplane_secrets.machine_secrets
  sensitive   = true
}

output "control_plane_bootstrap_ip" {
  description = "IP address of the first control plane node for bootstrapping."
  # Safely try to get the IP, defaulting to "Pending" if not yet available
  value = try(
    [for vm in proxmox_virtual_environment_vm.controlplane : vm.ipv4_addresses[1][0] if length(vm.ipv4_addresses) > 1 && length(vm.ipv4_addresses[1]) > 0][0],
    "Pending"
  )
}

output "kubernetes_vip_ip" {
  description = "The high-availability Virtual IP for the Kubernetes API server."
  value       = var.vip_ip
}

output "talos_config" {
  description = "The generated Talos client configuration"
  value       = talos_machine_secrets.controlplane_secrets.client_configuration
  sensitive   = true
}

output "talos_controlplane_config" {
  description = "The generated Talos controlplane configuration"
  value       = data.talos_machine_configuration.controlplane.machine_configuration
  sensitive   = true
}
