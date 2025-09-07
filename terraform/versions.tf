terraform {
  required_version = ">= 0.13"
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "3.23.0"
    }
    unifi = {
      source  = "paultyng/unifi"
      version = "0.41.0"
    }
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.69"
    }
    spot = {
      source  = "rackerlabs/spot"
      version = "~> 0.1"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
  # backend "pg" {
  # }
}

# provider "vault" {
#   address = var.vault_api_url
#   token   = var.vault_token
# }

# provider "unifi" {
#   username       = var.unifi_username
#   password       = var.unifi_password
#   api_url        = var.unifi_api_url
#   allow_insecure = var.unifi_insecure
#   site           = "default"
# }

# Proxmox provider configuration
provider "proxmox" {
  endpoint  = var.proxmox_api_url
  username  = var.proxmox_user
  password  = var.proxmox_password
  insecure  = var.proxmox_tls_insecure
  
  # Use either password OR API token authentication, not both
  # api_token = var.PM_API_TOKEN_SECRET
  
  ssh {
    agent    = true
    username = "root"
  }
}

# Spot provider configuration
provider "spot" {
  token = var.api_key
}
