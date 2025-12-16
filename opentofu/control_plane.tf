# NOTE: ISO is manually downloaded. If you need to update it, download from:
# https://factory.talos.dev/image/${talos_image_factory_schematic.this.id}/${var.talos_version}/nocloud-amd64.iso
# and upload to Proxmox storage 'local' with filename: talos-v1.8.1-6ebbfe35c8225645c05d4d19eaad385bd1ec795954932d0ada671388272fec19.iso

# Commented out - using manually uploaded ISO instead
# resource "proxmox_virtual_environment_download_file" "talos_iso" {
#   content_type = "iso"
#   datastore_id = var.iso_storage_pool
#   node_name    = var.proxmox_node
#   verify       = false
#   
#   url = "https://factory.talos.dev/image/${talos_image_factory_schematic.this.id}/${var.talos_version}/nocloud-amd64.iso"
#   file_name = "talos-${var.talos_version}-${talos_image_factory_schematic.this.id}.iso"
# }

resource "proxmox_virtual_environment_vm" "controlplane" {
  count     = var.control_plane_count
  name      = "${local.cluster_name}-cp-${format("%02d", count.index + 1)}"
  node_name = var.proxmox_node
  tags      = concat(var.tags, ["control-plane", "talos-${var.talos_version}", "flux-${var.flux_version}"])
  boot_order = ["scsi0", "ide2", "ide3"]
  
  agent {
    enabled = false
  }

  cpu {
    cores = var.node_cpu
    type  = "host"
  }

  memory {
    dedicated = var.node_memory
  }

  disk {
    datastore_id = var.storage_pool
    file_format  = "raw"
    interface    = "scsi0"
    size         = var.node_disk_size
  }

  initialization {
    ip_config {
      ipv4 {
        address = var.control_plane_ips[count.index]
        gateway = var.gateway
      }
    }
  }

  network_device {
    bridge = var.network_bridge
  }

  cdrom {
    # Reference the manually uploaded ISO
    file_id = "local:iso/talos-v1.11.5-ce4c980550dd2ab1b17bbf2b08801c7eb59418eafe8f279833297925d67c7515.iso"
  }

  operating_system {
    type = "l26" # Linux 2.6+
  }

  depends_on = [
    local_file.talosconfig
  ]

#  provisioner "local-exec" {
#    interpreter = ["bash", "-c"]
#    command     = "sleep 60 && talosctl --talosconfig talosconfig reboot -n ${split("/", var.control_plane_ips[count.index])[0]}"
#  }


}
