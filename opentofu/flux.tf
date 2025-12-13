data "talos_cluster_health" "this" {
  depends_on = [
    talos_machine_configuration_apply.controlplane,
    talos_machine_bootstrap.this
  ]
  skip_kubernetes_checks = false
  client_configuration   = talos_machine_secrets.this.client_configuration
  control_plane_nodes    = [for ip in var.control_plane_ips : split("/", ip)[0]]
  endpoints              = [for ip in var.control_plane_ips : split("/", ip)[0]]
  timeouts = {
    read = "10m"
  }
}

resource "tls_private_key" "flux" {
  algorithm = "ED25519"
}

resource "github_repository_deploy_key" "flux" {
  title      = "flux-deploy-key"
  repository = var.github_repository
  key        = tls_private_key.flux.public_key_openssh
  read_only  = true
}

resource "flux_bootstrap_git" "this" {
  depends_on = [
    github_repository_deploy_key.flux,
    data.talos_cluster_health.this,
    talos_machine_bootstrap.this
  ]

  embedded_manifests = true
  path               = "clusters/${var.cluster_name}"
}
