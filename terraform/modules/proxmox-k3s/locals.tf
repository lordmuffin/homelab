locals {
  # Create a map of providers for easy lookup
  provider_map = {
    for p in var.proxmox_providers : p.node_name => p
  }

  # Flatten VMs to create individual resources as a map
  vm_instances = {
    for vm_config in flatten([
      for vm in var.vms : [
        for i in range(vm.count) : {
          key              = "${vm.environment}-${vm.resource_name}-${vm.vm_type}-${format("%03d", i + 1)}"
          name             = "${vm.environment}-${vm.resource_name}-${vm.vm_type}-${format("%03d", i + 1)}"
          node_name        = vm.node_name
          vm_type          = vm.vm_type
          environment      = vm.environment
          vm_id            = vm.vm_id + i
          tls_san          = vm.tls_san
          agent            = vm.agent
          bios             = vm.bios
          ignore_changes   = vm.ignore_changes
          cpu              = vm.cpu
          cloud_init       = vm.cloud_init
          disks            = vm.disks
          memory           = vm.memory
          network_devices  = vm.network_devices
          on_boot          = vm.on_boot
          provider_config  = local.provider_map[vm.node_name]
          suffix           = format("%03d", i + 1)
          
          # Extract IP configuration
          ip_address = try(split("/", vm.cloud_init.ip_configs[0].ipv4.address)[0], "")
          ip_cidr    = vm.cloud_init.ip_configs[0].ipv4.address
          gateway    = vm.cloud_init.ip_configs[0].ipv4.gateway
        }
      ]
    ]) : vm_config.key => vm_config
  }

  # Group VMs by environment and type for dependency management
  server_vms = {
    for key, vm in local.vm_instances : key => vm
    if vm.vm_type == "server"
  }

  agent_vms = {
    for key, vm in local.vm_instances : key => vm
    if contains(["agent", "gpu-agent"], vm.vm_type)
  }

  # Primary server (first server for cluster initialization)
  primary_server = try(
    values(local.server_vms)[
      index(
        [for vm in values(local.server_vms) : vm.suffix], 
        "001"
      )
    ],
    null
  )
}