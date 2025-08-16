# Lab Environment Variables

# Authentication
variable "rackspace_spot_token" {
  description = "Rackspace Spot authentication token"
  type        = string
  sensitive   = true
}

# Cluster Configuration
variable "lab_cloudspace_name" {
  description = "Name of the lab cloudspace"
  type        = string
  default     = "lab-homelab"
}

variable "region" {
  description = "Rackspace Spot region"
  type        = string
  default     = "us-central-ord-1"
}

variable "kubernetes_version" {
  description = "Kubernetes version for lab cluster"
  type        = string
  default     = "1.31.1"
}

variable "cni" {
  description = "Container Network Interface"
  type        = string
  default     = "cilium"
}

variable "ha_control_plane" {
  description = "Enable HA control plane (can be disabled for lab to save costs)"
  type        = bool
  default     = true
}

variable "preemption_webhook" {
  description = "Webhook URL for preemption notifications (optional for lab)"
  type        = string
  default     = ""
}

# General Worker Nodes Configuration (cost-optimized)
variable "general_worker_server_class" {
  description = "Server class for general worker nodes (smaller for lab)"
  type        = string
  default     = "gp.vs1.large-ord"  # Smaller than prod
}

variable "general_worker_bid_price" {
  description = "Bid price for general worker nodes (lower for lab)"
  type        = number
  default     = 0.015  # Lower than prod
}

variable "general_worker_min_nodes" {
  description = "Minimum number of general worker nodes"
  type        = number
  default     = 2  # Fewer than prod
}

variable "general_worker_max_nodes" {
  description = "Maximum number of general worker nodes"
  type        = number
  default     = 5  # Fewer than prod
}

variable "general_worker_desired_nodes" {
  description = "Desired number of general worker nodes"
  type        = number
  default     = 3  # Fewer than prod
}

# Experimental Worker Nodes Configuration
variable "experimental_worker_server_class" {
  description = "Server class for experimental worker nodes"
  type        = string
  default     = "gp.vs1.medium-ord"  # Even smaller for experiments
}

variable "experimental_worker_bid_price" {
  description = "Bid price for experimental worker nodes (very low)"
  type        = number
  default     = 0.010  # Very low for cost savings
}

variable "experimental_worker_min_nodes" {
  description = "Minimum number of experimental worker nodes"
  type        = number
  default     = 0  # Can scale to zero
}

variable "experimental_worker_max_nodes" {
  description = "Maximum number of experimental worker nodes"
  type        = number
  default     = 3  # Limited for cost control
}

variable "experimental_worker_desired_nodes" {
  description = "Desired number of experimental worker nodes"
  type        = number
  default     = 1  # Start with one
}

# Network Policy Configuration
variable "enable_network_policies" {
  description = "Enable network policies (can be disabled for easier lab testing)"
  type        = bool
  default     = false  # More permissive for lab
}

variable "lab_network_policy_mode" {
  description = "Network policy mode for lab environment"
  type        = string
  default     = "permissive"
  validation {
    condition     = contains(["permissive", "restrictive", "disabled"], var.lab_network_policy_mode)
    error_message = "Network policy mode must be 'permissive', 'restrictive', or 'disabled'."
  }
}

# Namespace Configuration
variable "create_dev_namespace" {
  description = "Create development namespace"
  type        = bool
  default     = true
}

variable "create_test_namespace" {
  description = "Create testing namespace"
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
    "cost-center"  = "development"
  }
}

# Cost Management
variable "auto_shutdown_enabled" {
  description = "Enable automatic shutdown during off-hours (future feature)"
  type        = bool
  default     = false
}

variable "cost_alert_threshold" {
  description = "Monthly cost threshold for alerts (USD)"
  type        = number
  default     = 50
}

# Development Features
variable "enable_experimental_features" {
  description = "Enable experimental Kubernetes features"
  type        = bool
  default     = true
}

variable "enable_debug_mode" {
  description = "Enable additional logging and debug features"
  type        = bool
  default     = true
}