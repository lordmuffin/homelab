# Production Environment Variables for K3s Homelab Cluster

# Proxmox Configuration
variable "proxmox_nodes_config" {
  description = "Map of Proxmox nodes with their API endpoints and configuration"
  type = map(object({
    api_url     = string
    ip_address  = string
    token_id    = string
    token_secret = string
  }))
  default = {
    pve2 = {
      api_url     = "https://192.168.1.14:8006/api2/json" 
      ip_address  = "192.168.1.14"
      token_id    = "terraform@pve!terraform"
      token_secret = "REPLACE_WITH_PVE2_TOKEN"
    }
    pve-nas-01 = {
      api_url     = "https://192.168.1.15:8006/api2/json"
      ip_address  = "192.168.1.15" 
      token_id    = "terraform@pve!terraform"
      token_secret = "REPLACE_WITH_PVE_NAS_TOKEN"
    }
    pve4 = {
      api_url     = "https://192.168.1.37:8006/api2/json"
      ip_address  = "192.168.1.37" 
      token_id    = "terraform@pve!terraform"
      token_secret = "REPLACE_WITH_PVE4_TOKEN"
    }
  }
  sensitive = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS verification for Proxmox API"
  type        = bool
  default     = true
}

variable "proxmox_nodes" {
  description = "List of Proxmox nodes for VM placement (derived from proxmox_nodes_config)"
  type        = list(string)
  default     = ["pve2", "pve-nas-01", "pve4"]
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the K3s cluster"
  type        = string
  default     = "k3s-homelab"
}

variable "vm_template_name" {
  description = "Name of the VM template to use (fallback when vm_template_ids not specified)"
  type        = string
  default     = "ubuntu-k3s-homelab-template"
}

variable "vm_template_ids" {
  description = "Map of template VM IDs per node (takes precedence over vm_template_name)"
  type        = map(number)
  default     = {
    pve2       = 9000
    pve-nas-01 = 9001
    pve4       = 9002
  }
}

# K3s Configuration
variable "k3s_token" {
  description = "K3s cluster join token"
  type        = string
  sensitive   = true
  default     = "my-secure-k3s-token-change-this"
}

# Master Node Configuration
variable "master_node_count" {
  description = "Number of K3s master nodes"
  type        = number
  default     = 3
  
  validation {
    condition     = var.master_node_count >= 1 && var.master_node_count <= 5
    error_message = "Master node count must be between 1 and 5."
  }
}

variable "master_cores" {
  description = "CPU cores for master nodes"
  type        = number
  default     = 2
}

variable "master_memory" {
  description = "Memory in MB for master nodes"
  type        = number
  default     = 4096
}

variable "master_disk_size" {
  description = "Disk size for master nodes"
  type        = string
  default     = "50G"
}

variable "master_ip_prefix" {
  description = "IP prefix for master nodes (e.g., '192.168.1.')"
  type        = string
  default     = "192.168.1."
}

# Worker Node Configuration
variable "worker_node_count" {
  description = "Number of K3s worker nodes"
  type        = number
  default     = 3
  
  validation {
    condition     = var.worker_node_count >= 0 && var.worker_node_count <= 10
    error_message = "Worker node count must be between 0 and 10."
  }
}

variable "worker_cores" {
  description = "CPU cores for worker nodes"
  type        = number
  default     = 4
}

variable "worker_memory" {
  description = "Memory in MB for worker nodes"
  type        = number
  default     = 8192
}

variable "worker_disk_size" {
  description = "Disk size for worker nodes"
  type        = string
  default     = "100G"
}

variable "worker_ip_prefix" {
  description = "IP prefix for worker nodes (e.g., '192.168.1.')"
  type        = string
  default     = "192.168.1."
}

# Network Configuration
variable "network_bridge" {
  description = "Network bridge for VMs"
  type        = string
  default     = "vmbr0"
}

variable "network_gateway" {
  description = "Network gateway"
  type        = string
  default     = "192.168.1.1"
}

# SSH Configuration
variable "ssh_public_keys" {
  description = "List of SSH public keys for VM access"
  type        = list(string)
  default     = ["ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7... your-key-here"]
}