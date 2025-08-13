# Configure Proxmox providers
provider "proxmox" {
  for_each = { for p in var.providers : p.name => p }

  alias    = each.key
  endpoint = each.value.endpoint
  username = each.value.username
  password = var.proxmox_password
  insecure = each.value.insecure

  ssh {
    agent    = true
    username = var.vm_user
  }
}

# Create VMs
resource "proxmox_virtual_environment_vm" "k3s_nodes" {
  for_each = { for vm in local.vm_instances : vm.key => vm }

  provider = proxmox[each.value.provider_config.name]

  name      = each.value.name
  node_name = each.value.node_name
  vm_id     = each.value.vm_id

  description = "K3s ${each.value.vm_type} node - ${each.value.environment}"

  # Agent configuration
  agent {
    enabled = each.value.agent.enabled
    type    = each.value.agent.type
  }

  # BIOS
  bios = each.value.bios

  # CPU configuration
  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = "x86-64-v2-AES"
  }

  # Memory configuration
  memory {
    dedicated = each.value.memory.dedicated
  }

  # Clone from template
  clone {
    vm_id      = var.template_vm_id
    full       = true
    datastore_id = "local-lvm"
    node_name  = each.value.node_name
  }

  # Disk configuration
  dynamic "disk" {
    for_each = each.value.disks
    content {
      interface    = disk.value.disk1.interface
      datastore_id = disk.value.disk1.datastore_id
      size         = disk.value.disk1.size
      file_format  = disk.value.disk1.file_format
      cache        = disk.value.disk1.cache
    }
  }

  # Network configuration
  dynamic "network_device" {
    for_each = each.value.network_devices
    content {
      bridge  = network_device.value.net1.bridge
      model   = network_device.value.net1.model
      vlan_id = network_device.value.net1.vlan_id
    }
  }

  # Cloud-init configuration
  initialization {
    type         = each.value.cloud_init.type
    interface    = each.value.cloud_init.interface
    datastore_id = each.value.cloud_init.datastore_id

    dns {
      domain  = each.value.cloud_init.dns.domain
      servers = each.value.cloud_init.dns.servers
    }

    ip_config {
      ipv4 {
        address = each.value.ip_cidr
        gateway = each.value.gateway
      }
    }

    user_account {
      username = each.value.cloud_init.user_account.username
      password = each.value.cloud_init.user_account.password
      keys     = each.value.cloud_init.user_account.keys
    }

    user_data_file_id = proxmox_virtual_environment_file.cloud_init[each.key].id
  }

  # GPU passthrough for GPU agents
  dynamic "hostpci" {
    for_each = each.value.vm_type == "gpu-agent" && each.value.provider_config.hostpcis != "" ? [1] : []
    content {
      device  = "hostpci0"
      mapping = each.value.provider_config.hostpcis
    }
  }

  # Boot configuration
  on_boot = each.value.on_boot
  started = true

  lifecycle {
    ignore_changes = var.ignore_changes
  }

  depends_on = [
    proxmox_virtual_environment_file.cloud_init
  ]
}

# Cloud-init configuration files
resource "proxmox_virtual_environment_file" "cloud_init" {
  for_each = { for vm in local.vm_instances : vm.key => vm }

  content_type = "snippets"
  datastore_id = "local"
  node_name    = each.value.node_name

  source_raw {
    data = templatefile("${path.module}/templates/cloud-init.yaml.tpl", {
      hostname     = each.value.name
      username     = var.vm_user
      password     = var.vm_password
      ssh_keys     = var.ssh_public_key
      k3s_version  = var.k3s_version
      k3s_options  = var.k3s_options
      vm_type      = each.value.vm_type
      environment  = each.value.environment
      tls_san      = each.value.tls_san
    })
    
    file_name = "${each.value.name}-cloud-init.yaml"
  }
}

# K3s cluster initialization for primary server
resource "null_resource" "k3s_init" {
  count = local.primary_server != null ? 1 : 0

  triggers = {
    server_id = proxmox_virtual_environment_vm.k3s_nodes[local.primary_server.key].id
  }

  connection {
    type        = "ssh"
    host        = local.primary_server.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh install ${local.primary_server.tls_san} ${local.primary_server.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${local.primary_server.tls_san}"
    ]
  }

  provisioner "file" {
    source      = "${path.module}/templates/cilium_install.sh"
    destination = "/tmp/cilium_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/cilium_install.sh",
      "/tmp/cilium_install.sh ${local.primary_server.tls_san}"
    ]
  }

  depends_on = [
    proxmox_virtual_environment_vm.k3s_nodes
  ]
}

# Join additional servers to cluster
resource "null_resource" "k3s_server_join" {
  for_each = {
    for vm in local.server_vms : vm.key => vm
    if vm.suffix != "001"
  }

  triggers = {
    server_id = proxmox_virtual_environment_vm.k3s_nodes[each.key].id
    primary_init = null_resource.k3s_init[0].id
  }

  connection {
    type        = "ssh"
    host        = each.value.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh server ${each.value.tls_san} ${each.value.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${each.value.tls_san}"
    ]
  }

  depends_on = [
    null_resource.k3s_init
  ]
}

# Join agents to cluster
resource "null_resource" "k3s_agent_join" {
  for_each = { for vm in local.agent_vms : vm.key => vm }

  triggers = {
    agent_id = proxmox_virtual_environment_vm.k3s_nodes[each.key].id
    primary_init = null_resource.k3s_init[0].id
  }

  connection {
    type        = "ssh"
    host        = each.value.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh agent ${local.primary_server.tls_san} ${each.value.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${each.value.tls_san}"
    ]
  }

  depends_on = [
    null_resource.k3s_init
  ]
}