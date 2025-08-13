# Proxmox K3s cluster deployment
# Migrated from Pulumi k3s-nodes implementation

module "proxmox_k3s" {
  source = "./modules/proxmox-k3s"

  providers = var.proxmox_providers
  vms       = var.proxmox_vms

  proxmox_password = var.proxmox_password
  ssh_private_key  = var.ssh_private_key
  ssh_public_key   = var.ssh_public_key

  template_vm_id = var.template_vm_id
  k3s_version    = var.k3s_version
  k3s_options    = var.k3s_options
  vm_user        = var.vm_user
  vm_password    = var.vm_password
}