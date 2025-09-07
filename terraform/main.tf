# module "rackspace-spot" {
#   source      = "./modules/rackspace-spot"
#   cloudspace_name = "healingorganics"
#   rackspace_spot_token = var.api_key
# }

# Kairos Kubernetes cluster on Proxmox
# Uncomment and configure the module below to deploy Kairos clusters
module "kairos_cluster" {
  source = "./modules/proxmox-kairos"
  
  # Only create if required variables are provided
  count = var.proxmox_api_url != null && var.environment != null ? 1 : 0

  # Proxmox configuration (provide at runtime)
  proxmox_api_url      = var.proxmox_api_url
  proxmox_user         = var.proxmox_user
  proxmox_password     = var.proxmox_password
  proxmox_node         = var.proxmox_node
  proxmox_tls_insecure = var.proxmox_tls_insecure

  # Cluster configuration
  environment  = var.environment
  cluster_name = var.cluster_name

  # SSH configuration
  ssh_public_keys      = var.ssh_public_keys
  ssh_private_key_file = var.ssh_private_key_file

  # Network configuration
  network_config = var.network_config

  # Control plane and worker configuration
  control_plane = var.control_plane_config
  worker_nodes  = var.worker_nodes_config

  # Kairos configuration
  kairos_config = var.kairos_config
  
  # ISO configuration
  kairos_iso_name = var.kairos_iso_name

  # Tags
  tags = var.cluster_tags
}

# module "unifi" {
#   source              = "./modules/unifi"
#   site_name           = var.unifi_site_name
#   admin_username      = var.unifi_username
#   admin_password      = var.unifi_password
#   api_url             = var.unifi_api_url
#   controller_sec      = var.unifi_insecure
#   upstream_dns        = var.unifi_upstream_dns
#   wlan_password       = var.unifi_wlan_pass
#   guest_wlan_password = var.unifi_guest_pass
#   smart_wlan_password = var.unifi_smart_pass
# }

# resource "unifi_network" "vlan" {
#   name               = "main"
#   purpose            = "corporate"
#   subnet             = "192.168.1.0/24"
#   dhcp_start         = "192.168.1.6"
#   dhcp_stop          = "192.168.1.135"
#   dhcp_enabled       = true
#   dhcp_relay_enabled = false
#   network_group      = "LAN"
#   site               = module.unifi.site_id
#   dhcp_dns           = var.unifi_upstream_dns
# }

# module "vault" {
#   source         = "./modules/vault"
#   api_url        = var.vault_api_url
#   root_token     = var.vault_token
#   admin_username = var.vault_username
#   admin_password = var.vault_password
# }
