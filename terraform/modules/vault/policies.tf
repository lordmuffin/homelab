# Policies document
data "vault_policy_document" "admin_access" {
  rule {
    path         = "secret/*"
    capabilities = ["create", "read", "update", "delete", "list"]
    description  = "allow all on secrets"
  }
}

data "vault_policy_document" "audit_access" {
  rule {
    path         = "secret/*"
    capabilities = [ "read",  "list"]
    description  = "allow read and list"
  }
}

# Policy for grill-stats service to access transit engine
data "vault_policy_document" "grill_stats_transit" {
  rule {
    path         = "transit/encrypt/thermoworks-user-credentials"
    capabilities = ["update"]
    description  = "allow encryption of ThermoWorks credentials"
  }
  
  rule {
    path         = "transit/decrypt/thermoworks-user-credentials"
    capabilities = ["update"]
    description  = "allow decryption of ThermoWorks credentials"
  }
  
  rule {
    path         = "transit/keys/thermoworks-user-credentials"
    capabilities = ["read"]
    description  = "allow reading key metadata"
  }
  
  rule {
    path         = "transit/keys/thermoworks-user-credentials/rotate"
    capabilities = ["update"]
    description  = "allow key rotation"
  }
}

resource "vault_policy" "admin_policy" {
  name   = "admin_policy"
  policy = file("${path.module}/policies/admin.hcl")
}

resource "vault_policy" "audit" {
  name   = "audit_policy"
  policy = "${data.vault_policy_document.audit_access.hcl}"
}

resource "vault_policy" "grill_stats_transit" {
  name   = "grill-stats-transit-policy"
  policy = data.vault_policy_document.grill_stats_transit.hcl
}
