# Production Environment Kairos Cluster Configuration
# This example shows a highly available production setup

# Proxmox Configuration (provide these values at runtime)
proxmox_api_url      = "https://proxmox.company.com:8006/api2/json"
proxmox_user         = "terraform@pve"
proxmox_tls_insecure = false  # Use proper TLS in production

# ISO
kairos_iso_name      = "kairos-ubuntu-22.04-standard-amd64-generic-v1.1.0-k3sv1.33.3+k3s1.iso"

# Multiple Proxmox nodes for HA
proxmox_nodes = ["pve-01", "pve-02", "pve-03"]

# Cluster Configuration
environment  = "prod"
cluster_name = "production"

# HA Control Plane (3 nodes for quorum)
control_plane_config = {
  count       = 3
  vm_id_start = 200
  cpu_cores   = 4
  cpu_sockets = 1
  memory_mb   = 8192
  disk_size   = "100G"
  storage     = "ceph-storage"  # Use shared storage in production
}

# Worker Nodes (6 nodes for redundancy)
worker_nodes_config = {
  count       = 6
  vm_id_start = 300
  cpu_cores   = 8
  cpu_sockets = 1
  memory_mb   = 16384
  disk_size   = "200G"
  storage     = "ceph-storage"
}

# Network Configuration - Static IPs for production
network_config = {
  bridge         = "vmbr0"
  vlan_id        = 100  # Production VLAN
  model          = "virtio"
  firewall       = true
  rate_limit     = 1000  # 1Gbps limit
  dhcp           = false
  ip_range_start = "10.0.100.10/24"
  ip_range_end   = "10.0.100.50/24"
  gateway        = "10.0.100.1"
  dns_servers    = ["10.0.1.53", "10.0.1.54", "8.8.8.8"]
  domain         = "prod.cluster.local"
}

# SSH Configuration
ssh_public_keys = [
  # Production SSH keys
  # "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... admin@company.com"
  # "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... ops@company.com"
]

# Path to private key for provisioning
ssh_private_key_file = "~/.ssh/production_rsa"

# Kairos Configuration - Production with additional bundles
kairos_config = {
  bundles = [
    "quay.io/kairos/community-bundles:system-upgrade-controller_latest",
    "quay.io/kairos/community-bundles:cert-manager_latest",
    "quay.io/kairos/community-bundles:longhorn_latest",
    "quay.io/kairos/community-bundles:kured_latest"
  ]
  k3s_version    = "v1.33.3+k3s1"
  k3s_extra_args = [
    "--disable=traefik",      # Use external load balancer
    "--disable=servicelb",    # Use MetalLB or similar
    "--disable=local-storage", # Use Longhorn
    "--cluster-cidr=10.42.0.0/16",
    "--service-cidr=10.43.0.0/16",
    "--kube-apiserver-arg=audit-log-maxage=30",
    "--kube-apiserver-arg=audit-log-maxbackup=3",
    "--kube-apiserver-arg=audit-log-maxsize=100"
  ]
  p2p_enable       = false  # Disable P2P in production
  auto_install     = true
  reboot_strategy  = "kured"  # Use kured for coordinated reboots
  upgrade_strategy = "system-upgrade-controller"
}

# Advanced Configuration
enable_ha_control_plane = true
enable_anti_affinity    = true
vm_startup_delay        = 60  # Longer delay for production

# Backup configuration
backup_storage       = "backup-storage"
cloud_init_storage   = "local"

# Tags
cluster_tags = ["production", "kubernetes", "kairos", "ha", "critical"]