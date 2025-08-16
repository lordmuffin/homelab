variable "rackspace_spot_token" {
  description = "Rackspace Spot authentication token"
  type        = string
  sensitive   = true
}

variable "cloudspace_name" {
  description = "Name of the cloudspace"
  type        = string
}

variable "region" {
  description = "Rackspace Spot region"
  type        = string
  default     = "us-central-ord-1"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31.1"
}

variable "cni" {
  description = "Container Network Interface"
  type        = string
  default     = "cilium"
}

variable "ha_control_plane" {
  description = "Enable HA control plane (3 control plane nodes)"
  type        = bool
  default     = true
}

variable "preemption_webhook" {
  description = "Webhook URL for preemption notifications"
  type        = string
  default     = ""
}

variable "wait_until_ready" {
  description = "Wait until cluster is ready"
  type        = bool
  default     = true
}

variable "control_plane_server_class" {
  description = "Server class for control plane nodes"
  type        = string
  default     = "gp.vs1.large-ord"
}

variable "worker_node_pools" {
  description = "Configuration for worker node pools"
  type = list(object({
    name             = string
    server_class     = string
    bid_price        = number
    min_nodes        = number
    max_nodes        = number
    desired_nodes    = optional(number)
    labels           = optional(map(string))
    taints           = optional(list(object({
      key    = string
      value  = string
      effect = string
    })))
  }))
  default = [
    {
      name         = "general"
      server_class = "gp.vs1.xlarge-ord"
      bid_price    = 0.025
      min_nodes    = 3
      max_nodes    = 6
      desired_nodes = 3
      labels = {
        "node-type" = "general"
      }
    }
  ]
}

variable "common_labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    "managed-by" = "terraform"
  }
}

variable "network_policy_enabled" {
  description = "Enable network policies for segmentation"
  type        = bool
  default     = true
}