variable "proxmox_providers" {
  description = "List of Proxmox provider configurations"
  type = list(object({
    name        = string
    node_name   = string
    endpoint    = string
    username    = string
    insecure    = bool
    hostpcis    = string
  }))
}

variable "vms" {
  description = "List of VM configurations"
  type = list(object({
    name            = string
    count           = number
    node_name       = string
    vm_type         = string
    environment     = string
    resource_name   = string
    suffix          = string
    vm_id           = number
    tls_san         = string
    agent = object({
      enabled = bool
      type    = string
    })
    bios          = string
    ignore_changes = list(string)
    cpu = object({
      cores   = number
      sockets = number
    })
    cloud_init = object({
      type         = string
      interface    = string
      datastore_id = string
      dns = object({
        domain  = string
        servers = list(string)
      })
      ip_configs = list(object({
        ipv4 = object({
          address = string
          gateway = string
        })
      }))
      user_account = object({
        username = string
        password = string
        keys     = list(string)
      })
    })
    disks = list(object({
      disk1 = object({
        interface    = string
        datastore_id = string
        size         = number
        file_format  = string
        cache        = string
      })
    }))
    memory = object({
      dedicated = number
    })
    network_devices = list(object({
      net1 = object({
        bridge  = string
        model   = string
        vlan_id = number
      })
    }))
    on_boot = bool
  }))
}

variable "proxmox_password" {
  description = "Proxmox VE password for authentication"
  type        = string
  sensitive   = true
}

variable "ssh_private_key" {
  description = "SSH private key for VM provisioning"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
}

variable "vm_user" {
  description = "Default VM user for provisioning"
  type        = string
  default     = "ubuntu"
}

variable "vm_password" {
  description = "Default VM password"
  type        = string
  sensitive   = true
  default     = "ubuntu"
}

variable "template_vm_id" {
  description = "Template VM ID to clone from"
  type        = number
  default     = 8006
}

variable "k3s_version" {
  description = "K3s version to install"
  type        = string
  default     = "v1.28.2+k3s1"
}

variable "k3s_options" {
  description = "Additional K3s installation options"
  type        = string
  default     = "--flannel-backend=none --no-flannel --disable-kube-proxy --disable servicelb --disable-network-policy"
}