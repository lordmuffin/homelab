# Create VMs for pve node
resource "proxmox_virtual_environment_vm" "k3s_nodes_pve" {
  provider = proxmox.pve
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve"
  }

  name      = each.value.name
  node_name = each.value.node_name
  vm_id     = each.value.vm_id

  description = "K3s ${each.value.vm_type} node - ${each.value.environment}"

  # Agent configuration
  agent {
    enabled = each.value.agent.enabled
    type    = each.value.agent.type
  }

  bios = each.value.bios

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = each.value.memory.dedicated
  }

  clone {
    vm_id      = var.template_vm_id
    full       = true
    datastore_id = "local-lvm"
    node_name  = each.value.node_name
  }

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

  dynamic "network_device" {
    for_each = each.value.network_devices
    content {
      bridge  = network_device.value.net1.bridge
      model   = network_device.value.net1.model
      vlan_id = network_device.value.net1.vlan_id
    }
  }

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

    user_data_file_id = proxmox_virtual_environment_file.cloud_init_pve[each.key].id
  }

  on_boot = each.value.on_boot
  started = true

  lifecycle {
    ignore_changes = [disk, cdrom, started]
  }

  depends_on = [
    proxmox_virtual_environment_file.cloud_init_pve
  ]
}

# Create VMs for pve2 node
resource "proxmox_virtual_environment_vm" "k3s_nodes_pve2" {
  provider = proxmox.pve2
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve2"
  }

  name      = each.value.name
  node_name = each.value.node_name
  vm_id     = each.value.vm_id

  description = "K3s ${each.value.vm_type} node - ${each.value.environment}"

  agent {
    enabled = each.value.agent.enabled
    type    = each.value.agent.type
  }

  bios = each.value.bios

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = each.value.memory.dedicated
  }

  clone {
    vm_id      = var.template_vm_id
    full       = true
    datastore_id = "local-lvm"
    node_name  = each.value.node_name
  }

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

  dynamic "network_device" {
    for_each = each.value.network_devices
    content {
      bridge  = network_device.value.net1.bridge
      model   = network_device.value.net1.model
      vlan_id = network_device.value.net1.vlan_id
    }
  }

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

    user_data_file_id = proxmox_virtual_environment_file.cloud_init_pve2[each.key].id
  }

  # GPU passthrough for GPU agents
  dynamic "hostpci" {
    for_each = each.value.vm_type == "gpu-agent" && each.value.provider_config.hostpcis != "" ? [1] : []
    content {
      device  = "hostpci0"
      mapping = each.value.provider_config.hostpcis
    }
  }

  on_boot = each.value.on_boot
  started = true

  lifecycle {
    ignore_changes = [disk, cdrom, started]
  }

  depends_on = [
    proxmox_virtual_environment_file.cloud_init_pve2
  ]
}

# Create VMs for pve-nas-01 node
resource "proxmox_virtual_environment_vm" "k3s_nodes_pve_nas_01" {
  provider = proxmox.pve_nas_01
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve-nas-01"
  }

  name      = each.value.name
  node_name = each.value.node_name
  vm_id     = each.value.vm_id

  description = "K3s ${each.value.vm_type} node - ${each.value.environment}"

  agent {
    enabled = each.value.agent.enabled
    type    = each.value.agent.type
  }

  bios = each.value.bios

  cpu {
    cores   = each.value.cpu.cores
    sockets = each.value.cpu.sockets
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = each.value.memory.dedicated
  }

  clone {
    vm_id      = var.template_vm_id
    full       = true
    datastore_id = "local-lvm"
    node_name  = each.value.node_name
  }

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

  dynamic "network_device" {
    for_each = each.value.network_devices
    content {
      bridge  = network_device.value.net1.bridge
      model   = network_device.value.net1.model
      vlan_id = network_device.value.net1.vlan_id
    }
  }

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

    user_data_file_id = proxmox_virtual_environment_file.cloud_init_pve_nas_01[each.key].id
  }

  on_boot = each.value.on_boot
  started = true

  lifecycle {
    ignore_changes = [disk, cdrom, started]
  }

  depends_on = [
    proxmox_virtual_environment_file.cloud_init_pve_nas_01
  ]
}

# Cloud-init configuration files for pve
resource "proxmox_virtual_environment_file" "cloud_init_pve" {
  provider = proxmox.pve
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve"
  }

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

# Cloud-init configuration files for pve2
resource "proxmox_virtual_environment_file" "cloud_init_pve2" {
  provider = proxmox.pve2
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve2"
  }

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

# Cloud-init configuration files for pve-nas-01
resource "proxmox_virtual_environment_file" "cloud_init_pve_nas_01" {
  provider = proxmox.pve_nas_01
  for_each = { 
    for vm in local.vm_instances : vm.key => vm 
    if vm.node_name == "pve-nas-01"
  }

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