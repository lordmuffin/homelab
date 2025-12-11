# ------------------------------------------------------------------------------
# Security / Cryptography: Deploy Key Generation
# ------------------------------------------------------------------------------
# Generate a secure ED25519 SSH key for Flux to access the GitHub repository.
resource "tls_private_key" "flux" {
  algorithm = "ED25519"
}

# ------------------------------------------------------------------------------
# GitHub Integration: Deploy Key Upload
# ------------------------------------------------------------------------------
# Upload the generated public key to the specified GitHub repository.
# This key allows Flux to read/write to the repo (required for image automation).
resource "github_repository_deploy_key" "flux" {
  title      = "flux-deploy-key-${var.cluster_name}"
  repository = var.github_repository
  key        = tls_private_key.flux.public_key_openssh
  read_only  = false
}

# ------------------------------------------------------------------------------
# Cluster Health Check: Dependency Barrier
# ------------------------------------------------------------------------------
# Ensure the Talos cluster is healthy and the Kubernetes API is reachable
# before attempting to bootstrap Flux. This prevents race conditions where
# the cluster is technically "up" but k8s services aren't ready.
data "talos_cluster_health" "flux" {
  client_configuration = var.talos_client_configuration
  control_plane_nodes  = var.node_ips
  endpoints            = var.node_ips # Using node IPs as endpoints to check connectivity directly

  timeouts = {
    read = "10m"
  }
}

# ------------------------------------------------------------------------------
# Flux Bootstrap
# ------------------------------------------------------------------------------
# Bootstrap FluxCD onto the cluster.
# This installs the Flux controllers and configures the GitRepository CRD.
resource "flux_bootstrap_git" "this" {
  # Explicitly depend on health check and deploy key to ensure:
  # 1. Cluster is ready (health check)
  # 2. Key exists on GitHub so Flux can clone (deploy key)
  depends_on = [
    data.talos_cluster_health.flux,
    github_repository_deploy_key.flux
  ]

  embedded_manifests = true
  path               = "clusters/${var.cluster_name}"
}
