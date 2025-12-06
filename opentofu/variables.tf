################################################################################
# Proxmox Connection Variables
################################################################################

variable "pm_api_url" {
  description = "The URL of the Proxmox API (e.g., https://192.168.1.10:8006/api2/json)"
  type        = string
}

variable "pm_token_id" {
  description = "The Proxmox API Token ID (e.g., user@pam!tokenid)"
  type        = string
}

variable "pm_token_secret" {
  description = "The Proxmox API Token Secret"
  type        = string
  sensitive   = true
}

variable "target_node" {
  description = "The name of the Proxmox node to deploy the VMs on (e.g., pve-host-01)"
  type        = string
}

variable "storage_pool" {
  description = "The name of the storage pool for disks"
  type        = string
  default     = "local-lvm"
}

variable "pm_vmid_base" {
  description = "The starting QEMU ID for the control plane VMs (e.g., 900)"
  type        = number
  default     = 900
}

variable "network_bridge" {
  description = "The network bridge to attach the VMs to"
  type        = string
  default     = "vmbr0"
}

################################################################################
# Talos Cluster Variables
################################################################################

variable "cluster_name" {
  description = "The name of the Kubernetes/Talos cluster"
  type        = string
  default     = "talos-ha-cluster"
}

variable "vip_ip" {
  description = "The Virtual IP (VIP) address for the Kube API server on eth0"
  type        = string
}

variable "control_plane_count" {
  description = "The number of control plane nodes (Must be 3 for HA)"
  type        = number
  default     = 3
}

variable "talos_version" {
  description = "The version of Talos to use (e.g., v1.8.1)"
  type        = string
  default     = "v1.8.1"
}

################################################################################
# VM Specification Variables
################################################################################

variable "cp_vcpus" {
  description = "Number of vCPUs for each control plane node"
  type        = number
  default     = 2
}

variable "cp_ram_mb" {
  description = "RAM in MB for each control plane node"
  type        = number
  default     = 4096 # 4GB
}

variable "cp_disk_size" {
  description = "Disk size for the root volume of each control plane node (e.g., 20G)"
  type        = number
  default     = 20
}

################################################################################
# Flux / GitHub Variables
################################################################################

variable "github_token" {
  description = "GitHub token for Flux bootstrap"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub organization or user for the repository"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository name"
  type        = string
}
