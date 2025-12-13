resource "proxmox_virtual_environment_vm" "worker" {
  count     = var.worker_node_count
  name      = "${var.cluster_name}-worker-${count.index + 1}"
  node_name = var.proxmox_node
  tags      = concat(var.tags, ["worker", "talos-${var.talos_version}", "flux-${var.flux_version}"])

  agent {
    enabled = true
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
    file_id = "local:iso/talos-v1.8.1-6ebbfe35c8225645c05d4d19eaad385bd1ec795954932d0ada671388272fec19.iso"
  }

  operating_system {
    type = "l26" # Linux 2.6+
  }
}
