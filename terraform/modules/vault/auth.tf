resource "vault_auth_backend" "userpass" {
  type = "userpass"
  path = "userpass"

  tune {
    max_lease_ttl      = "90000s"
    listing_visibility = "unauth"
  }
}

# Kubernetes authentication backend for service accounts
resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
  path = "kubernetes"
}

# Configure the Kubernetes auth backend
resource "vault_kubernetes_auth_backend_config" "config" {
  backend         = vault_auth_backend.kubernetes.path
  kubernetes_host = var.kubernetes_host
}

# Kubernetes auth role for grill-stats service
resource "vault_kubernetes_auth_backend_role" "grill_stats" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "grill-stats-role"
  bound_service_account_names      = ["grill-stats-service-account"]
  bound_service_account_namespaces = ["grill-stats"]
  token_ttl                        = 3600
  token_max_ttl                    = 7200
  token_policies                   = ["grill-stats-transit-policy"]
}

# Userpass Backend
resource "vault_identity_entity" "entity" {
  name = var.admin_username
  # policies = each.value.policies
  # metadata = each.value.metadata
}

resource "vault_kubernetes_secret_backend" "services" {
  path                      = "kubernetes"
  description               = "Kubernetes Secret Engine Backend"
  kubernetes_host           = var.kubernetes_host
}

resource "vault_kubernetes_secret_backend_role" "crossplane" {
  backend                       = vault_kubernetes_secret_backend.services.path
  name                          = var.service_account_name
  allowed_kubernetes_namespaces = ["*"]
  service_account_name          = var.service_account_name
}
