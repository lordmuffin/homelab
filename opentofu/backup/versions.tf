terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.69.0"
    }
    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.7.0"
    }
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
    }
    flux = {
      source  = "fluxcd/flux"
      version = "~> 1.2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27.0"
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

# Providers for Flux and Kubernetes will be configured in flux.tf
# or here if we want global config, but they rely on resources that don't exist yet
# (the kubeconfig).
# However, provider configs in Terraform are static.
# We usually pass the config via the provider block using resource attributes.
