resource "talos_machine_secrets" "controlplane_secrets" {
    talos_version = var.talos_version
}

data "talos_machine_configuration" "controlplane" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.vip_ip}:6443"
  machine_type     = "controlplane"
  machine_secrets  = talos_machine_secrets.controlplane_secrets.machine_secrets
  talos_version    = var.talos_version
}

resource "talos_image_factory_schematic" "this" {
  schematic = yamlencode({
    customization = {
      systemExtensions = {
        officialExtensions = [
          "siderolabs/qemu-guest-agent",
          "siderolabs/iscsi-tools",
        ]
      }
    }
  })
}

locals {
  # Helper to parse the generated config once
  base_config = yamldecode(data.talos_machine_configuration.controlplane.machine_configuration)

  # Merge the generated config with our customizations
  controlplane_config = [
    for i in range(var.control_plane_count) : yamlencode(merge(
      local.base_config,
      {
        machine = merge(local.base_config.machine, {
          network = merge(try(local.base_config.machine.network, {}), {
            interfaces = [
              {
                interface = "eth0"
                dhcp = true
                vip = {
                  ip = var.vip_ip
                }
              }
            ]
          })
          install = merge(try(local.base_config.machine.install, {}), {
            disk = "/dev/sda"
            image = "factory.talos.dev/installer/${talos_image_factory_schematic.this.id}:${var.talos_version}"
          })
        })
        cluster = merge(local.base_config.cluster, {
          network = merge(try(local.base_config.cluster.network, {}), {
            cni = {
              name = "none"
            }
          })
        })
      }
    ))
  ]
}

resource "proxmox_virtual_environment_download_file" "talos_iso" {
  content_type = "iso"
  datastore_id = "local"
  node_name    = var.target_node
  url          = "https://factory.talos.dev/image/${talos_image_factory_schematic.this.id}/${var.talos_version}/nocloud-amd64.iso"
  file_name    = "talos-${var.talos_version}-${talos_image_factory_schematic.this.id}.iso"
}

resource "proxmox_virtual_environment_file" "talos_config" {
  count       = var.control_plane_count
  content_type = "snippets"
  datastore_id = "local"
  node_name    = var.target_node

  source_raw {
    data      = local.controlplane_config[count.index]
    file_name = "talos-config-cp-${count.index}.yaml"
  }
}

resource "proxmox_virtual_environment_vm" "controlplane" {
  count     = var.control_plane_count
  name      = "${var.cluster_name}-cp-${count.index + 1}"
  node_name = var.target_node
  vm_id     = var.pm_vmid_base + count.index

  agent {
    enabled = true
  }

  bios = "ovmf"

  # Required for OVMF
  efi_disk {
    datastore_id = var.storage_pool
    file_format  = "raw"
    type         = "4m"
  }

  cpu {
    cores = var.cp_vcpus
    type  = "host"
  }

  memory {
    dedicated = var.cp_ram_mb
  }

  disk {
    datastore_id = var.storage_pool
    file_format  = "raw"
    interface    = "scsi0"
    size         = var.cp_disk_size
    discard      = "on"
    ssd          = true
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    user_data_file_id = proxmox_virtual_environment_file.talos_config[count.index].id
  }

  network_device {
    bridge = var.network_bridge
  }

  operating_system {
    type = "l26"
  }

  cdrom {
    file_id = proxmox_virtual_environment_download_file.talos_iso.id
  }

  started = true
}

# ------------------------------------------------------------------------------
# Talos Bootstrap & Access
# ------------------------------------------------------------------------------

resource "talos_machine_bootstrap" "this" {
  depends_on = [proxmox_virtual_environment_vm.controlplane]

  # We use the first node's IP for bootstrapping
  node = try(proxmox_virtual_environment_vm.controlplane[0].ipv4_addresses[1][0], "")

  client_configuration = talos_machine_secrets.controlplane_secrets.client_configuration
}

resource "talos_cluster_kubeconfig" "this" {
  depends_on = [talos_machine_bootstrap.this]

  client_configuration = talos_machine_secrets.controlplane_secrets.client_configuration
  node                 = try(proxmox_virtual_environment_vm.controlplane[0].ipv4_addresses[1][0], "")
}
