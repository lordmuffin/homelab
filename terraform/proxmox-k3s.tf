# Proxmox providers configuration
# Define individual providers with static aliases
provider "proxmox" {
  alias    = "pve"
  endpoint = "https://192.168.1.13:8006/"
  username = "terraform@pve"
  password = var.proxmox_password
  insecure = true

  ssh {
    agent    = true
    username = var.vm_user
  }
}

provider "proxmox" {
  alias    = "pve2"
  endpoint = "https://192.168.1.14:8006/"
  username = "terraform@pve"
  password = var.proxmox_password
  insecure = true

  ssh {
    agent    = true
    username = var.vm_user
  }
}

provider "proxmox" {
  alias    = "pve_nas_01"
  endpoint = "https://192.168.1.15:8006/"
  username = "terraform@pve"
  password = var.proxmox_password
  insecure = true

  ssh {
    agent    = true
    username = var.vm_user
  }
}

# Proxmox K3s cluster deployment
# Migrated from Pulumi k3s-nodes implementation
module "proxmox_k3s" {
  source = "./modules/proxmox-k3s"

  providers = {
    proxmox.pve        = proxmox.pve
    proxmox.pve2       = proxmox.pve2
    proxmox.pve_nas_01 = proxmox.pve_nas_01
  }

  proxmox_providers = var.proxmox_providers
  vms              = var.proxmox_vms

  proxmox_password = var.proxmox_password
  ssh_private_key  = var.ssh_private_key
  ssh_public_key   = var.ssh_public_key

  template_vm_id = var.template_vm_id
  k3s_version    = var.k3s_version
  k3s_options    = var.k3s_options
  vm_user        = var.vm_user
  vm_password    = var.vm_password
}