# Development Environment Kairos Cluster Configuration
# This example shows a minimal single-node setup for development

# Proxmox Configuration (provide these values at runtime)
proxmox_api_url      = "https://192.168.1.37:8006/api2/json"
proxmox_user         = "root@pam"
proxmox_node         = "pve4"
proxmox_tls_insecure = true

# ISO
kairos_iso_name      = "kairos-ubuntu-22.04-standard-amd64-generic-v1.1.0-k3sv1.33.3_k3s1.iso"

# Cluster Configuration
environment  = "dev"
cluster_name = "dev-cluster"

# Single control plane node (no workers for dev)
control_plane_config = {
  count       = 1
  vm_id_start = 100
  cpu_cores   = 2
  cpu_sockets = 1
  memory_mb   = 4096
  disk_size   = "50G"
  storage     = "local-lvm"
}

# No worker nodes for development
worker_nodes_config = {
  count       = 0
  vm_id_start = 200
  cpu_cores   = 2
  cpu_sockets = 1
  memory_mb   = 4096
  disk_size   = "50G"
  storage     = "local-lvm"
}

# Network Configuration - DHCP for simplicity
network_config = {
  bridge      = "vmbr0"
  model       = "virtio"
  firewall    = false
  dhcp        = true
  dns_servers = ["8.8.8.8", "8.8.4.4"]
  domain      = "dev.local"
}

# SSH Configuration
ssh_public_keys = [
  # Add your SSH public keys here
  # "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... user@host"
]

# VM User Configuration
vm_password = "kairos123"  # Set a password for console login

# Optional: Path to private key for provisioning
# ssh_private_key_file = "~/.ssh/id_rsa"

# Kairos Configuration - Minimal for development
kairos_config = {
  bundles          = []
  k3s_version      = "v1.33.3+k3s1"
  k3s_extra_args   = ["--disable=traefik"]
  p2p_enable       = false
  auto_install     = true
  reboot_strategy  = "immediate"
  upgrade_strategy = "manual"
}

# Tags
cluster_tags = ["development", "single-node", "k3s"]