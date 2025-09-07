# Proxmox K3s HA Cluster Module
# Integrates with existing homelab repository structure

terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66.0"
    }
  }
  required_version = ">= 1.5.0"
}

variable "existing_config" {
  description = "Path to existing homelab configuration"
  type        = string
  default     = "../../../../../kubernetes"
}

variable "proxmox_api_url" {
  description = "Proxmox API URL (used for cloud-init upload script)"
  type        = string
}

variable "target_node" {
  description = "Target Proxmox node name for VM deployment"
  type        = string
}

variable "vm_template_name" {
  description = "Name of the VM template to clone from (built with Packer). If null or template doesn't exist, VMs will be created from scratch"
  type        = string
  default     = "ubuntu-k3s-homelab-template"

  validation {
    condition     = var.vm_template_name == null || length(var.vm_template_name) > 0
    error_message = "Template name must be null or a non-empty string."
  }
}

variable "vm_template_id" {
  description = "ID of the VM template to clone from. If specified, takes precedence over vm_template_name. If null, will attempt to discover by name. Common template IDs: pve2=9000, pve-nas-01=9001"
  type        = number
  default     = null
}

# Legacy variables removed - authentication now handled via provider configuration

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "network_bridge" {
  description = "Network bridge name"
  type        = string
  default     = "vmbr0"
}

variable "vlan_tag" {
  description = "VLAN tag for cluster network"
  type        = number
  default     = 11
}

variable "ssh_public_keys" {
  description = "List of SSH public keys"
  type        = list(string)
}


variable "workers_per_node" {
  description = "Number of worker nodes per Proxmox node"
  type        = number
  default     = 2
}

variable "gpu_workers_per_node" {
  description = "Number of GPU worker nodes per Proxmox node (only for prod)"
  type        = number
  default     = 1
}

locals {
  # Parse existing configurations if available
  existing_apps = try(
    yamldecode(file("${var.existing_config}/apps/kustomization.yaml")),
    {}
  )

  # Single node deployment configuration
  single_node = var.target_node

  # Per-node VM configuration
  vm_configs_per_node = {
    masters = {
      count_per_node = 1 # Always 1 master per node
      memory         = 4096
      cores          = 4
      disk_size      = 50
      pool           = "k3s-control"
      vm_id_start    = 200
    }
    workers = {
      count_per_node = var.workers_per_node
      memory         = 8192
      cores          = 4
      disk_size      = 100
      pool           = "k3s-workers"
      vm_id_start    = 300
    }
    gpu-workers = {
      count_per_node = var.environment == "dev" ? 0 : var.gpu_workers_per_node
      memory         = 16384
      cores          = 8
      disk_size      = 200
      pool           = "k3s-gpu"
      vm_id_start    = 400
      gpu            = true
    }
  }

  # Create flattened list of VM configurations for single node
  vm_list = flatten([
    for vm_type, config in local.vm_configs_per_node : [
      for vm_idx in range(config.count_per_node) : {
        key          = "${vm_type}-${local.single_node}-${vm_idx + 1}"
        name         = "k3s-${vm_type}-${local.single_node}-${vm_idx + 1}"
        vm_id        = config.vm_id_start + vm_idx + (
          local.single_node == "pve" ? 0 : 
          local.single_node == "pve2" ? 100 : 
          local.single_node == "pve-nas-01" ? 200 :
          local.single_node == "pve4" ? 300 : 400
        )
        vm_type      = vm_type
        memory       = config.memory
        cores        = config.cores
        disk_size    = config.disk_size
        pool         = config.pool
        gpu          = try(config.gpu, false)
        proxmox_node = local.single_node
        is_primary   = vm_type == "masters" && local.single_node == "pve" && vm_idx == 0
        instance_id  = vm_idx + 1
      }
      if config.count_per_node > 0
    ]
  ])

  # Convert to map for resource iteration
  all_vms = {
    for vm in local.vm_list : vm.key => vm
  }

  # Tags for all resources (Proxmox format - no colons allowed)
  common_tags = [
    "Environment-${var.environment}",
    "Project-homelab",
    "ManagedBy-terraform",
    "Cluster-k3s-ha"
  ]

  # Template validation and configuration
  template_requested = var.vm_template_id != null || var.vm_template_name != null
  template_id_provided = var.vm_template_id != null
  
  # Template discovery by name (only if ID not provided)
  all_templates     = local.template_requested && !local.template_id_provided ? try(data.proxmox_virtual_environment_vms.all_templates[0].vms, []) : []
  matching_template = local.template_requested && !local.template_id_provided ? [
    for vm in local.all_templates : vm if vm.name == var.vm_template_name
  ] : []
  
  # Template resolution - use provided ID or discovered ID
  template_found_by_name = length(local.matching_template) > 0
  template_found = local.template_id_provided || local.template_found_by_name
  template_vm_id = local.template_id_provided ? var.vm_template_id : (local.template_found_by_name ? local.matching_template[0].vm_id : null)
  use_template   = local.template_found

  # Template status for outputs and debugging
  template_status = local.template_requested ? (
    local.template_found ? "found" : "not_found"
  ) : "not_requested"
}

# Template discovery and validation
# Only query templates if we need to discover by name (ID not provided)
data "proxmox_virtual_environment_vms" "all_templates" {
  count     = var.vm_template_id == null && var.vm_template_name != null ? 1 : 0
  node_name = var.target_node

  filter {
    name   = "template"
    values = ["1"]
  }
}

# Random token for K3s cluster
resource "random_password" "k3s_token" {
  length  = 32
  special = false
}

# Create VMs for K3s cluster
# Uses template cloning when template exists, falls back to fresh VM creation
resource "proxmox_virtual_environment_vm" "k3s_vms" {
  for_each = local.all_vms

  # Basic configuration
  name        = each.value.name
  vm_id       = each.value.vm_id
  description = "K3s ${each.value.vm_type} node - ${var.environment} environment"
  tags        = local.common_tags

  # VM placement on specific Proxmox node
  node_name = each.value.proxmox_node

  # Boot configuration
  started = true
  on_boot = true

  # BIOS and firmware - using seabios instead of UEFI to avoid EFI disk requirement
  bios = "seabios"

  # CPU configuration
  cpu {
    cores   = each.value.cores
    sockets = 1
    type    = "kvm64"
  }

  # Memory configuration
  memory {
    dedicated = each.value.memory
    floating  = each.value.memory
  }

  # Template cloning or fresh VM creation
  dynamic "clone" {
    for_each = local.use_template ? [1] : []
    content {
      vm_id = local.template_vm_id
      full  = true # Full clone for better performance and isolation
    }
  }

  # Disk configuration - only needed when not using template
  dynamic "disk" {
    for_each = local.use_template ? [] : [1]
    content {
      datastore_id = "local-lvm"
      interface    = "virtio0"
      size         = each.value.disk_size
      file_format  = "raw"
      cache        = "writeback"
      discard      = "on"
    }
  }

  # Network configuration
  network_device {
    bridge   = var.network_bridge
    model    = "virtio"
    vlan_id  = var.vlan_tag
    firewall = false
  }

  # Cloud-init configuration
  initialization {
    user_account {
      username = "ubuntu"
      keys     = var.ssh_public_keys
    }

    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    dns {
      domain  = "cluster.local"
      servers = ["8.8.8.8", "8.8.4.4"]
    }

    # user_data_file_id = "local:snippets/k3s-${each.key}-cloud-init.yaml"  # Disabled until cloud-init upload is working
  }

  # GPU passthrough for GPU workers (disabled until GPU mappings are configured)
  # Uncomment when GPU mappings "gpu-pve2" and "gpu-pve-nas-01" exist on nodes
  /*
  dynamic "hostpci" {
    for_each = each.value.gpu ? [1] : []
    content {
      device  = "hostpci0"
      mapping = "gpu-${each.value.proxmox_node}"
      pcie    = true
      rombar  = true
      xvga    = false
    }
  }
  */

  # Lifecycle management
  lifecycle {
    ignore_changes = [
      initialization[0].user_data_file_id,
      # Only ignore disk file_id when not using template (template VMs don't create new disks)
      disk[0].file_id
    ]

    # Prevent destruction and recreation when switching between template and non-template modes
    create_before_destroy = true
  }
}

# Generate cloud-init configurations
resource "local_file" "cloud_init_configs" {
  for_each = local.all_vms

  filename = "${path.module}/generated/cloud-init-${each.key}.yaml"
  content = templatefile("${path.module}/templates/cloud-init.yaml.tpl", {
    hostname        = each.value.name
    vm_type         = each.value.vm_type
    is_primary      = each.value.is_primary
    k3s_token       = random_password.k3s_token.result
    environment     = var.environment
    ssh_public_keys = var.ssh_public_keys
  })
}

# Upload cloud-init files to Proxmox (disabled for now to test VM creation)
# Uncomment after verifying SSH access to Proxmox nodes
/*
resource "null_resource" "upload_cloud_init" {
  for_each = local.all_vms
  
  triggers = {
    cloud_init_content = local_file.cloud_init_configs[each.key].content
  }
  
  provisioner "local-exec" {
    command = "bash -c \"PROXMOX_HOST=\\$(echo '${var.proxmox_api_url}' | sed 's|https\\\\?://||' | sed 's|:.*||'); echo 'Uploading cloud-init for ${each.key} to '\\$PROXMOX_HOST; ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o BatchMode=yes root@\\$PROXMOX_HOST 'mkdir -p /var/lib/vz/snippets' 2>/dev/null || true; scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o BatchMode=yes '${local_file.cloud_init_configs[each.key].filename}' root@\\$PROXMOX_HOST:/var/lib/vz/snippets/k3s-${each.key}-cloud-init.yaml && echo 'Successfully uploaded cloud-init for ${each.key}' || echo 'Warning: Failed to upload cloud-init file for ${each.key}'\""
  }
  
  depends_on = [local_file.cloud_init_configs]
}
*/

# Template information output
output "template_info" {
  description = "Template usage information"
  value = {
    template_name           = var.vm_template_name
    template_id_provided    = var.vm_template_id
    template_requested      = local.template_requested
    template_found          = local.template_found
    template_vm_id          = local.template_vm_id
    template_status         = local.template_status
    using_template          = local.use_template
    template_id_provided_flag = local.template_id_provided
    available_templates     = local.template_requested && !local.template_id_provided ? [for vm in local.all_templates : vm.name] : []
    template_search_node    = var.target_node
  }
}

# Output cluster information
output "cluster_nodes" {
  description = "Information about all cluster nodes"
  value = {
    for k, vm in local.all_vms : k => {
      name           = vm.name
      vm_id          = vm.vm_id
      vm_type        = vm.vm_type
      is_primary     = vm.is_primary
      node_name      = proxmox_virtual_environment_vm.k3s_vms[k].node_name
      using_template = local.use_template
    }
  }
}

output "k3s_token" {
  description = "K3s cluster token"
  value       = random_password.k3s_token.result
  sensitive   = true
}

output "master_nodes" {
  description = "Master node information"
  value = [
    for k, vm in local.all_vms : {
      name       = vm.name
      vm_id      = vm.vm_id
      is_primary = vm.is_primary
    } if vm.vm_type == "masters"
  ]
}

output "worker_nodes" {
  description = "Worker node information"
  value = [
    for k, vm in local.all_vms : {
      name  = vm.name
      vm_id = vm.vm_id
      gpu   = vm.gpu
    } if contains(["workers", "gpu-workers"], vm.vm_type)
  ]
}

output "node_cluster_size" {
  description = "Cluster size summary for this node"
  value = {
    total_vms_on_node   = length(local.all_vms)
    target_node         = var.target_node
    masters_on_node     = local.vm_configs_per_node.masters.count_per_node
    workers_on_node     = local.vm_configs_per_node.workers.count_per_node
    gpu_workers_on_node = local.vm_configs_per_node["gpu-workers"].count_per_node
    environment         = var.environment
  }
}

output "node_vm_distribution" {
  description = "VM distribution on this Proxmox node"
  value = {
    node = var.target_node
    masters = [
      for k, vm in local.all_vms : vm.name
      if vm.vm_type == "masters"
    ]
    workers = [
      for k, vm in local.all_vms : vm.name
      if vm.vm_type == "workers"
    ]
    gpu_workers = [
      for k, vm in local.all_vms : vm.name
      if vm.vm_type == "gpu-workers"
    ]
  }
}