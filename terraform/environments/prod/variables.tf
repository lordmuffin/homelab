# Production Environment Variables

# Authentication
variable "rackspace_spot_token" {
  description = "Rackspace Spot authentication token"
  type        = string
  sensitive   = true
}

# Cluster Configuration
variable "prod_cloudspace_name" {
  description = "Name of the production cloudspace"
  type        = string
  default     = "prod-homelab"
}

variable "region" {
  description = "Rackspace Spot region"
  type        = string
  default     = "us-central-ord-1"
}

variable "kubernetes_version" {
  description = "Kubernetes version for production cluster"
  type        = string
  default     = "1.31.1"
}

variable "cni" {
  description = "Container Network Interface"
  type        = string
  default     = "cilium"
}

variable "preemption_webhook" {
  description = "Webhook URL for preemption notifications"
  type        = string
  default     = ""
}

# General Worker Nodes Configuration
variable "general_worker_server_class" {
  description = "Server class for general worker nodes"
  type        = string
  default     = "gp.vs1.xlarge-ord"
}

variable "general_worker_bid_price" {
  description = "Bid price for general worker nodes"
  type        = number
  default     = 0.025
}

variable "general_worker_min_nodes" {
  description = "Minimum number of general worker nodes"
  type        = number
  default     = 3
}

variable "general_worker_max_nodes" {
  description = "Maximum number of general worker nodes"
  type        = number
  default     = 8
}

variable "general_worker_desired_nodes" {
  description = "Desired number of general worker nodes"
  type        = number
  default     = 4
}

# Memory-Optimized Worker Nodes Configuration
variable "memory_worker_server_class" {
  description = "Server class for memory-optimized worker nodes"
  type        = string
  default     = "mem.vs1.large-ord"
}

variable "memory_worker_bid_price" {
  description = "Bid price for memory-optimized worker nodes"
  type        = number
  default     = 0.035
}

variable "memory_worker_min_nodes" {
  description = "Minimum number of memory-optimized worker nodes"
  type        = number
  default     = 1
}

variable "memory_worker_max_nodes" {
  description = "Maximum number of memory-optimized worker nodes"
  type        = number
  default     = 4
}

variable "memory_worker_desired_nodes" {
  description = "Desired number of memory-optimized worker nodes"
  type        = number
  default     = 2
}

# GPU Worker Nodes Configuration
variable "gpu_worker_server_class" {
  description = "Server class for GPU worker nodes"
  type        = string
  default     = "gpu.vs1.large-ord"
}

variable "gpu_worker_bid_price" {
  description = "Bid price for GPU worker nodes"
  type        = number
  default     = 0.15
}

variable "gpu_worker_min_nodes" {
  description = "Minimum number of GPU worker nodes"
  type        = number
  default     = 0
}

variable "gpu_worker_max_nodes" {
  description = "Maximum number of GPU worker nodes"
  type        = number
  default     = 2
}

variable "gpu_worker_desired_nodes" {
  description = "Desired number of GPU worker nodes"
  type        = number
  default     = 0
}

# Network Policy Configuration
variable "enable_network_policies" {
  description = "Enable network policies for enhanced security"
  type        = bool
  default     = true
}

# Common Labels
variable "common_labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    "managed-by"   = "terraform"
    "team"         = "platform"
    "cost-center"  = "infrastructure"
  }
}

# Resource Tagging
variable "additional_tags" {
  description = "Additional tags for resource management"
  type        = map(string)
  default     = {}
}