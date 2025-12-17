data "talos_cluster_health" "this" {
  depends_on = [
    talos_machine_configuration_apply.controlplane,
    talos_machine_bootstrap.this
  ]
  skip_kubernetes_checks = true
  client_configuration   = talos_machine_secrets.this.client_configuration
  control_plane_nodes    = [for ip in var.control_plane_ips : split("/", ip)[0]]
  worker_nodes           = [for ip in var.worker_node_ips : split("/", ip)[0]]
  endpoints              = [for ip in var.control_plane_ips : split("/", ip)[0]]
  timeouts = {
    read = "10m"
  }
}

resource "tls_private_key" "flux" {
  algorithm = "ED25519"
}

resource "github_repository" "this" {
  name               = local.cluster_name
  visibility         = "private"
  auto_init          = true
  archive_on_destroy = true
}

resource "github_repository_deploy_key" "flux" {
  title      = "flux-deploy-key"
  repository = github_repository.this.name
  key        = tls_private_key.flux.public_key_openssh
  read_only  = false
}

resource "flux_bootstrap_git" "this" {
  depends_on = [
    github_repository_deploy_key.flux,
    data.talos_cluster_health.this,
    talos_machine_bootstrap.this
  ]

  embedded_manifests = true
  path               = "clusters/${local.cluster_name}"

}
