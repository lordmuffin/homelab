variable "proxmox_endpoint" {
  description = "The endpoint for the Proxmox API"
  type        = string
}

variable "proxmox_api_token" {
  description = "The API token for Proxmox authentication (USER@REALM!TOKENID=UUID)"
  type        = string
  sensitive   = true
}

variable "proxmox_insecure" {
  description = "Allow insecure SSL connections to Proxmox"
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "The Proxmox node to deploy resources on"
  type        = string
}

variable "cluster_name" {
  description = "Name of the cluster (overrides auto-generated name if provided)"
  type        = string
  default     = null
}

variable "cluster_env" {
  description = "Environment (p, np, dev)"
  type        = string
  default     = "np"
}

variable "cluster_loc" {
  description = "Location (home, aws, az, gcp, lnd, rs)"
  type        = string
  default     = "home"
}

variable "cluster_purpose" {
  description = "Purpose of the cluster"
  type        = string
  default     = "homelab"
}

variable "talos_version" {
  description = "Talos version to use"
  type        = string
  default     = "v1.11.1" # Example default, adjust as needed
}

variable "control_plane_count" {
  description = "Number of control plane nodes"
  type        = number
  default     = 3
}

variable "node_cpu" {
  description = "CPU cores per node"
  type        = number
  default     = 2
}

variable "node_memory" {
  description = "Memory (MB) per node"
  type        = number
  default     = 4096
}

variable "node_disk_size" {
  description = "Disk size (GB) per node"
  type        = number
  default     = 20
}

variable "storage_pool" {
  description = "Proxmox storage pool for disks"
  type        = string
  default     = "local-lvm"
}

variable "iso_storage_pool" {
  description = "Proxmox storage pool for ISOs"
  type        = string
  default     = "local"
}

variable "network_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "control_plane_ips" {
  description = "List of static IPs for control plane nodes (CIDR format)"
  type        = list(string)
  # Example: ["192.168.1.10/24", "192.168.1.11/24", "192.168.1.12/24"]
}

variable "gateway" {
  description = "Network gateway IP"
  type        = string
}

variable "cluster_vip" {
  description = "Virtual IP for the Kubernetes API"
  type        = string
}

variable "tags" {
  description = "Tags to apply to the virtual machine"
  type        = list(string)
  default     = ["talos", "k8s"]
}

variable "worker_node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 1
}

variable "worker_node_cpu" {
  description = "CPU cores per worker node"
  type        = number
  default     = 4
}

variable "worker_node_memory" {
  description = "Memory (MB) per worker node"
  type        = number
  default     = 8192
}

variable "worker_node_ips" {
  description = "List of static IPs for worker nodes (CIDR format)"
  type        = list(string)
  # Example: ["192.168.1.20/24"]
}
variable "github_owner" {
  description = "GitHub owner (username or organization)"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository name"
  type        = string
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}

variable "flux_version" {
  description = "Flux version to tag resources with"
  type        = string
  default     = "v2.4.0"
}
