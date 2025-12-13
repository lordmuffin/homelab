variable "github_owner" {
  description = "The owner of the GitHub repository (user or organization)."
  type        = string
}

variable "github_repository" {
  description = "The name of the GitHub repository to bootstrap Flux into."
  type        = string
}

variable "cluster_name" {
  description = "The name of the cluster, used for the directory structure in the Git repository."
  type        = string
}

variable "cluster_endpoint" {
  description = "The Kubernetes API endpoint (e.g., https://192.168.1.10:6443)."
  type        = string
}

variable "talos_client_configuration" {
  description = "The Talos client configuration data (typically secrets/certs) to talk to the nodes."
  type        = any
  sensitive   = true
}

variable "node_ips" {
  description = "List of node IP addresses to check for cluster health."
  type        = list(string)
}
