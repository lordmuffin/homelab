variable "api_key" {
  description = "Rackspace Spot authentication token"
  type        = string
  sensitive   = true
}

# Proxmox Configuration Variables
variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
  default     = null
}

variable "proxmox_user" {
  description = "Proxmox username for API access"
  type        = string
  default     = "root@pam"
}

variable "proxmox_password" {
  description = "Proxmox password for API access"
  type        = string
  sensitive   = true
  default     = null
}

variable "PM_API_TOKEN_ID" {
  description = "Proxmox API Token ID"
  type        = string
  sensitive   = true
  default     = null
}

variable "PM_API_TOKEN_SECRET" {
  description = "Proxmox API Token Secret"
  type        = string
  sensitive   = true
  default     = null
}

variable "proxmox_node" {
  description = "Primary Proxmox node name"
  type        = string
  default     = null
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS verification for Proxmox API"
  type        = bool
  default     = false
}

# Cluster Configuration
variable "environment" {
  description = "Environment name (prod, staging, dev, non-prod)"
  type        = string
  default     = null
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = null
}

# SSH Configuration
variable "ssh_public_keys" {
  description = "List of SSH public keys for VM access"
  type        = list(string)
  default     = []
}

variable "ssh_private_key_file" {
  description = "Path to SSH private key file for provisioning"
  type        = string
  default     = null
}

# Network Configuration
variable "network_config" {
  description = "Network configuration for VMs"
  type = object({
    bridge         = string
    vlan_id        = optional(number)
    model          = string
    firewall       = bool
    rate_limit     = optional(number)
    dhcp           = bool
    ip_range_start = optional(string)
    ip_range_end   = optional(string)
    gateway        = optional(string)
    dns_servers    = list(string)
    domain         = string
  })
  default = null
}

# Control Plane Configuration
variable "control_plane_config" {
  description = "Control plane node configuration"
  type = object({
    count       = number
    vm_id_start = number
    cpu_cores   = number
    cpu_sockets = number
    memory_mb   = number
    disk_size   = string
    storage     = string
  })
  default = null
}

# Worker Node Configuration
variable "worker_nodes_config" {
  description = "Worker node configuration"
  type = object({
    count       = number
    vm_id_start = number
    cpu_cores   = number
    cpu_sockets = number
    memory_mb   = number
    disk_size   = string
    storage     = string
  })
  default = null
}

# Kairos Configuration
variable "kairos_config" {
  description = "Kairos-specific configuration"
  type = object({
    bundles          = list(string)
    k3s_version      = string
    k3s_extra_args   = list(string)
    p2p_enable       = bool
    auto_install     = bool
    reboot_strategy  = string
    upgrade_strategy = string
  })
  default = null
}

# Tags
variable "cluster_tags" {
  description = "Tags to apply to cluster resources"
  type        = list(string)
  default     = []
}

# Kairos ISO Configuration
variable "kairos_iso_name" {
  description = "Name of the Kairos ISO file in Proxmox storage"
  type        = string
  default     = "kairos-ubuntu-22.04-standard-amd64-generic-v1.1.0-k3sv1.33.3_k3s1.iso"
}

variable "kairos_iso_storage" {
  description = "Proxmox storage location for ISO files"
  type        = string
  default     = "local"
}

# Proxmox K3s Variables
variable "proxmox_providers" {
  description = "List of Proxmox provider configurations"
  type = list(object({
    name        = string
    node_name   = string
    endpoint    = string
    username    = string
    insecure    = bool
    hostpcis    = string
  }))
  default = []
}

variable "proxmox_vms" {
  description = "List of VM configurations for K3s cluster"
  type = list(object({
    name            = string
    count           = number
    node_name       = string
    vm_type         = string
    environment     = string
    resource_name   = string
    suffix          = string
    vm_id           = number
    tls_san         = string
    agent = object({
      enabled = bool
      type    = string
    })
    bios          = string
    ignore_changes = list(string)
    cpu = object({
      cores   = number
      sockets = number
    })
    cloud_init = object({
      type         = string
      interface    = string
      datastore_id = string
      dns = object({
        domain  = string
        servers = list(string)
      })
      ip_configs = list(object({
        ipv4 = object({
          address = string
          gateway = string
        })
      }))
      user_account = object({
        username = string
        password = string
        keys     = list(string)
      })
    })
    disks = list(object({
      disk1 = object({
        interface    = string
        datastore_id = string
        size         = number
        file_format  = string
        cache        = string
      })
    }))
    memory = object({
      dedicated = number
    })
    network_devices = list(object({
      net1 = object({
        bridge  = string
        model   = string
        vlan_id = number
      })
    }))
    on_boot = bool
  }))
  default = []
}

# Removed duplicate - already defined above

variable "ssh_private_key" {
  description = "SSH private key for VM provisioning"
  type        = string
  sensitive   = true
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  default     = ""
}

variable "template_vm_id" {
  description = "Template VM ID to clone from"
  type        = number
  default     = 8006
}

variable "k3s_version" {
  description = "K3s version to install"
  type        = string
  default     = "v1.28.2+k3s1"
}

variable "k3s_options" {
  description = "Additional K3s installation options"
  type        = string
  default     = "--flannel-backend=none --no-flannel --disable-kube-proxy --disable servicelb --disable-network-policy"
}

variable "vm_user" {
  description = "Default VM user for provisioning"
  type        = string
  default     = "ubuntu"
}

variable "vm_password" {
  description = "Default VM password"
  type        = string
  sensitive   = true
  default     = "ubuntu"
}

# Removed duplicate - already defined above

# variable "unifi_site_name" {
#   type        = string
#   description = "<sub>Unifi site name. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs/resources/site#name)</sub>"
#   default     = "default"
# }

# variable "unifi_username" {
#   type        = string
#   description = "<sub>Provides a username for your Unifi controller. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs#username).</sub>"
#   default     = "example"
#   sensitive   = true
#   validation {
#     condition     = can(regex("^[a-z0-9][-a-z0-9]*[a-z0-9]$", var.unifi_username))
#     error_message = "Error: unifi_username value only allows characters a-z, A-Z and 0-9 to be used."
#   }   
# }

# variable "unifi_password" {
#   type        = string
#   description = "<sub>Providers a password for your Unifi controller. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs#password)</sub>"
#   default     = ""
#   sensitive   = true
# }

# variable "unifi_api_url" {
#   type        = string
#   description = "<sub>Provides a connection URI to bridge Terraform with Unifi's controller. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs#api_url)</sub>"
#   default     = ""
#   sensitive   = true
# }

# variable "unifi_insecure" {
#   type        = string
#   description = "<sub>Skip TLS verification when trying to access the API. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs#allow_insecure)</sub>"
#   default     = ""
#   sensitive   = true
# }

# variable "unifi_upstream_dns" {
#   type        = list(any)
#   description = "<sub>Skip TLS verification when trying to access the API. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs#allow_insecure)</sub>"
#   default     = ["8.8.8.8", "1.1.1.1"]
#   sensitive   = true
# }

# variable "unifi_wlan_pass" {
#   type        = string
#   description = "<sub>Main WLAN password. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs/resources/wlan#security)</sub>"
#   sensitive   = true
# }

# variable "unifi_guest_pass" {
#   type        = string
#   description = "<sub>Guest WLAN password. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs/resources/wlan#security)</sub>"
#   sensitive   = true
# }

# variable "unifi_smart_pass" {
#   type        = string
#   description = "<sub>mart Devices-exclusive WLAN password. [Reference](https://registry.terraform.io/providers/paultyng/unifi/latest/docs/resources/wlan#security)</sub>"
#   sensitive   = true
# }


# variable "vault_username" {
#   type        = string
#   default     = "gruber"
#   description = "<sub>Vault plaintext username to login.</sub>"
#   validation {
#     condition     = can(regex("^[a-z0-9][-a-z0-9]*[a-z0-9]$", var.vault_username))
#     error_message = "Error: Your Vault username contains invalid characters."
#   }
# }

# variable "vault_api_url" {
#   type        = string
#   description = "<sub>Vault API URL Address. [Reference](https://registry.terraform.io/providers/hashicorp/vault/latest/docs#address)</sub>"
#   sensitive   = true
# }

# variable "vault_token" {
#   type        = string
#   description = "<sub>Vault root access token. [Reference](https://registry.terraform.io/providers/hashicorp/vault/latest/docs#token_name)</sub>"
#   sensitive   = true
# }

# variable "vault_password" {
#   type        = string
#   description = "<sub>Vault password for the main user, used for login purposes.</sub>"
#   default     = ""
#   sensitive   = true
# }
