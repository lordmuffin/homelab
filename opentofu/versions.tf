terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.69.0" # Updated to a newer version as 0.38 is old
    }
    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.7.0"
    }
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
    }
  }
}

provider "proxmox" {
  endpoint  = var.pm_api_url
  api_token = "${var.pm_token_id}=${var.pm_token_secret}"
  insecure  = true

  # bpg/proxmox specific settings for performance/customization
  ssh {
    agent = true
  }
}

provider "talos" {}
