resource "proxmox_virtual_environment_vm" "worker" {
  count     = var.worker_node_count
  name      = "${local.cluster_name}-w-${format("%02d", count.index + 1)}"
  node_name = var.proxmox_node
  tags      = concat(var.tags, ["worker", "talos-${var.talos_version}", "flux-${var.flux_version}"])
  boot_order = ["scsi0", "ide2", "ide3"]

  agent {
    enabled = false
  }

  cpu {
    cores = var.worker_node_cpu
    type  = "host"
  }

  memory {
    dedicated = var.worker_node_memory
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
        address = var.worker_node_ips[count.index]
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
#    command     = "sleep 60 && talosctl --talosconfig talosconfig reboot -n ${split("/", var.worker_node_ips[count.index])[0]}"
#  }


}
