terraform {
  required_version = ">= 0.13"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
      configuration_aliases = [
        proxmox.pve,
        proxmox.pve2,
        proxmox.pve_nas_01
      ]
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}