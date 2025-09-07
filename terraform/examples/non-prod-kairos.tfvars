# Non-Production Environment Kairos Cluster Configuration
# This example shows a staging/testing setup with moderate resources

# Proxmox Configuration (provide these values at runtime)
proxmox_api_url      = "https://staging-proxmox:8006/api2/json"
proxmox_user         = "terraform@pve"
proxmox_tls_insecure = true

# ISO
kairos_iso_name      = "kairos-ubuntu-22.04-standard-amd64-generic-v1.1.0-k3sv1.33.3+k3s1.iso"

# Multiple nodes for testing HA features
proxmox_nodes = ["pve-01", "pve-02"]

# Cluster Configuration
environment  = "non-prod"
cluster_name = "staging"

# Control Plane (3 nodes for HA testing)
control_plane_config = {
  count       = 3
  vm_id_start = 150
  cpu_cores   = 2
  cpu_sockets = 1
  memory_mb   = 4096
  disk_size   = "50G"
  storage     = "local-lvm"
}

# Worker Nodes (2 nodes for testing)
worker_nodes_config = {
  count       = 2
  vm_id_start = 250
  cpu_cores   = 4
  cpu_sockets = 1
  memory_mb   = 8192
  disk_size   = "100G"
  storage     = "local-lvm"
}

# Network Configuration - Mix of static and DHCP
network_config = {
  bridge         = "vmbr0"
  vlan_id        = 200  # Staging VLAN
  model          = "virtio"
  firewall       = false  # Relaxed for testing
  dhcp           = false
  ip_range_start = "192.168.200.10/24"
  gateway        = "192.168.200.1"
  dns_servers    = ["192.168.1.1", "8.8.8.8"]
  domain         = "staging.local"
}

# SSH Configuration
ssh_public_keys = [
  # Staging SSH keys
  # "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... staging@company.com"
]

# Optional: Path to private key for provisioning
ssh_private_key_file = "~/.ssh/staging_rsa"

# Kairos Configuration - Testing features
kairos_config = {
  bundles = [
    "quay.io/kairos/community-bundles:system-upgrade-controller_latest",
    "quay.io/kairos/community-bundles:cert-manager_latest"
  ]
  k3s_version    = "v1.33.3+k3s1"
  k3s_extra_args = [
    "--disable=traefik",
    "--disable=servicelb",
    "--cluster-cidr=10.52.0.0/16",
    "--service-cidr=10.53.0.0/16"
  ]
  p2p_enable       = false
  auto_install     = true
  reboot_strategy  = "kured"
  upgrade_strategy = "system-upgrade-controller"
}

# Configuration for testing HA features
enable_ha_control_plane = true
enable_anti_affinity    = true
vm_startup_delay        = 30

# Tags
cluster_tags = ["staging", "testing", "kubernetes", "kairos", "non-prod"]