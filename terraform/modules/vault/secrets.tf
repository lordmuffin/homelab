
# kv secret engine
resource "vault_mount" "kv" {
  path        = "kv"
  type        = "kv-v2"
  description = "kv backend"
}

resource "vault_generic_secret" "secrets" {
  depends_on = [vault_mount.kv]
  for_each   = fileset("${path.module}/secrets/", "**")
  path       = "kv/${dirname(each.key)}"
  data_json  = file("${path.module}/secrets/${each.key}")
}

# Transit secrets engine for encryption-as-a-service
resource "vault_mount" "transit" {
  path        = "transit"
  type        = "transit"
  description = "Transit secrets engine for encryption-as-a-service"
}

# Encryption key for ThermoWorks user credentials
resource "vault_transit_secret_backend_key" "thermoworks_credentials" {
  backend = vault_mount.transit.path
  name    = "thermoworks-user-credentials"
  type    = "aes256-gcm96"
  
  # Enable key rotation and versioning
  deletion_allowed = false
  exportable       = false
  allow_plaintext_backup = false
  
  # Enable key rotation
  auto_rotate_period = "2160h" # 90 days
}
