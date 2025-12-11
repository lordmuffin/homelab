resource "talos_image_factory_schematic" "this" {
  schematic = yamlencode({
    customization = {
      systemExtensions = {
        officialExtensions = [
          "siderolabs/qemu-guest-agent",
          "siderolabs/iscsi-tools"
        ]
      }
    }
  })
}

resource "talos_machine_secrets" "this" {
  talos_version = var.talos_version
}

data "talos_machine_configuration" "controlplane" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.cluster_vip}:6443"
  machine_type     = "controlplane"
  machine_secrets  = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = "v1.31.0"
  
  config_patches = [
    yamlencode({
      machine = {
        features = {
          kubePrism = {
            enabled = true
            port    = 7445
          }
        }
      }
    })
  ]
}

resource "talos_machine_configuration_apply" "controlplane" {
  count                       = var.control_plane_count
  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  node                        = split("/", var.control_plane_ips[count.index])[0] # Strip CIDR mask
  
  depends_on = [
    proxmox_virtual_environment_vm.controlplane
  ]

  config_patches = [
    yamlencode({
      machine = {
        network = {
          interfaces = [
            {
              interface = "eth0"
              dhcp      = false
              addresses = [var.control_plane_ips[count.index]]
              routes = [
                {
                  network = "0.0.0.0/0"
                  gateway = var.gateway
                }
              ]
              vip = {
                ip = var.cluster_vip
              }
            }
          ]
        }
      }
    })
  ]
}

resource "talos_machine_bootstrap" "this" {
  depends_on = [
    talos_machine_configuration_apply.controlplane
  ]

  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = split("/", var.control_plane_ips[0])[0] # Bootstrap using the first node
}

data "talos_client_configuration" "this" {
  cluster_name         = var.cluster_name
  client_configuration = talos_machine_secrets.this.client_configuration
  endpoints            = [for ip in var.control_plane_ips : split("/", ip)[0]]
}

data "talos_machine_configuration" "worker" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.cluster_vip}:6443"
  machine_type     = "worker"
  machine_secrets  = talos_machine_secrets.this.machine_secrets
  talos_version      = var.talos_version
  kubernetes_version = "v1.31.0"
  
  config_patches = [
    yamlencode({
      machine = {
        features = {
          kubePrism = {
            enabled = true
            port    = 7445
          }
        }
      }
    })
  ]
}

resource "talos_machine_configuration_apply" "worker" {
  count                       = var.worker_node_count
  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  node                        = split("/", var.worker_node_ips[count.index])[0]
  
  depends_on = [
    proxmox_virtual_environment_vm.worker
  ]

  config_patches = [
    yamlencode({
      machine = {
        network = {
          interfaces = [
            {
              interface = "eth0"
              dhcp      = false
              addresses = [var.worker_node_ips[count.index]]
              routes = [
                {
                  network = "0.0.0.0/0"
                  gateway = var.gateway
                }
              ]
            }
          ]
        }
      }
    })
  ]
}


resource "local_file" "talosconfig" {
  content  = data.talos_client_configuration.this.talos_config
  filename = "${path.module}/talosconfig"
}


