# Flux Configuration

# Use the kubeconfig retrieved from Talos to configure the Kubernetes and Flux providers.
provider "kubernetes" {
  host = talos_cluster_kubeconfig.this.kubernetes_client_configuration.host
  client_certificate     = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.client_certificate)
  client_key             = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.client_key)
  cluster_ca_certificate = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.ca_certificate)
}

provider "flux" {
  kubernetes = {
    host = talos_cluster_kubeconfig.this.kubernetes_client_configuration.host
    client_certificate     = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.client_certificate)
    client_key             = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.client_key)
    cluster_ca_certificate = base64decode(talos_cluster_kubeconfig.this.kubernetes_client_configuration.ca_certificate)
  }
  git = {
    url = "https://github.com/${var.github_org}/${var.github_repository}.git"
    http = {
      username = "git" # username is ignored for token auth usually, or use 'git'
      password = var.github_token
    }
  }
}

resource "flux_bootstrap_git" "this" {
  depends_on = [
    talos_machine_bootstrap.this,
    talos_cluster_kubeconfig.this
  ]

  path = "clusters/${var.cluster_name}"
}
