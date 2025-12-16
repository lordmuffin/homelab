terraform {
  required_version = ">= 1.8.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = ">= 0.66.0"
    }
    talos = {
      source  = "siderolabs/talos"
      version = ">= 0.9.0"
    }
    flux = {
      source  = "fluxcd/flux"
      version = ">= 1.2"
    }
    github = {
      source  = "integrations/github"
      version = ">= 6.0"
    }
  }

  backend "s3" {
    endpoint                    = "http://192.168.1.10:9000"
    bucket                      = "prod-homelab-state"
    key                         = "talos-cluster/terraform.tfstate"
    region                      = "main"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    use_path_style              = true
  }
}

provider "proxmox" {
  endpoint = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure = var.proxmox_insecure
  
  ssh {
    agent = true
  }
}

provider "talos" {
  # Configuration is often handled via env vars or config file for the provider itself,
  # but strictly it doesn't need much if we are just generating config.
}

provider "flux" {
  kubernetes = {
    config_path = "${path.module}/kubeconfig" 
    insecure    = true 
  }
  git = {
    url = "ssh://git@github.com/${var.github_owner}/${local.cluster_name}.git"
    ssh = {
      username    = "git"
      private_key = tls_private_key.flux.private_key_pem
    }
  }
}

provider "github" {
  owner = var.github_owner
  token = var.github_token
}
