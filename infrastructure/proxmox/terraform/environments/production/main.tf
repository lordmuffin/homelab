# Production Environment for K3s Homelab Cluster
# This configuration deploys a production-ready K3s cluster on Proxmox

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
  }
}

# Proxmox Provider Configurations - Using API Token Authentication (SSH disabled)
provider "proxmox" {
  alias     = "pve2"
  endpoint  = var.proxmox_nodes_config["pve2"].api_url
  api_token = "${var.proxmox_nodes_config["pve2"].token_id}=${var.proxmox_nodes_config["pve2"].token_secret}"
  insecure  = var.proxmox_tls_insecure
}

provider "proxmox" {
  alias     = "pve-nas-01"
  endpoint  = var.proxmox_nodes_config["pve-nas-01"].api_url
  api_token = "${var.proxmox_nodes_config["pve-nas-01"].token_id}=${var.proxmox_nodes_config["pve-nas-01"].token_secret}"
  insecure  = var.proxmox_tls_insecure
}

provider "proxmox" {
  alias     = "pve4"
  endpoint  = var.proxmox_nodes_config["pve4"].api_url
  api_token = "${var.proxmox_nodes_config["pve4"].token_id}=${var.proxmox_nodes_config["pve4"].token_secret}"
  insecure  = var.proxmox_tls_insecure
}

# Local variables for resource naming and configuration
locals {
  environment = "production"
  cluster_name = "${var.cluster_name}-${local.environment}"
  
  # Common tags for all resources
  common_tags = {
    Environment = local.environment
    Cluster     = local.cluster_name
    ManagedBy   = "Terraform"
    Purpose     = "K3s-Homelab"
  }
}

# K3s Cluster Modules - Only for available nodes (pve is commented out)

module "k3s_cluster_pve2" {
  source = "../../modules/vm-template"
  providers = {
    proxmox = proxmox.pve2
  }
  
  # Proxmox node configuration
  proxmox_api_url = var.proxmox_nodes_config["pve2"].api_url
  target_node = "pve2"
  
  # Template configuration - use template ID if available, fallback to name
  vm_template_id   = lookup(var.vm_template_ids, "pve2", null)
  vm_template_name = var.vm_template_name
  
  # Environment configuration
  environment = "prod"
  
  # Network configuration
  network_bridge = var.network_bridge
  vlan_tag      = 11
  
  # Per-node VM configuration
  workers_per_node = 2
  gpu_workers_per_node = 1
  
  # SSH configuration
  ssh_public_keys = var.ssh_public_keys
}

module "k3s_cluster_pve_nas_01" {
  source = "../../modules/vm-template"
  providers = {
    proxmox = proxmox.pve-nas-01
  }
  
  # Proxmox node configuration
  proxmox_api_url = var.proxmox_nodes_config["pve-nas-01"].api_url
  target_node = "pve-nas-01"
  
  # Template configuration - use template ID if available, fallback to name
  vm_template_id   = lookup(var.vm_template_ids, "pve-nas-01", null)
  vm_template_name = var.vm_template_name
  
  # Environment configuration
  environment = "prod"
  
  # Network configuration
  network_bridge = var.network_bridge
  vlan_tag      = 11
  
  # Per-node VM configuration
  workers_per_node = 2
  gpu_workers_per_node = 1
  
  # SSH configuration
  ssh_public_keys = var.ssh_public_keys
}

module "k3s_cluster_pve4" {
  source = "../../modules/vm-template"
  providers = {
    proxmox = proxmox.pve4
  }
  
  # Proxmox node configuration
  proxmox_api_url = var.proxmox_nodes_config["pve4"].api_url
  target_node = "pve4"
  
  # Template configuration - use template ID if available, fallback to name
  vm_template_id   = lookup(var.vm_template_ids, "pve4", null)
  vm_template_name = var.vm_template_name
  
  # Environment configuration
  environment = "prod"
  
  # Network configuration
  network_bridge = var.network_bridge
  vlan_tag      = 11
  
  # Per-node VM configuration
  workers_per_node = 2
  gpu_workers_per_node = 1
  
  # SSH configuration
  ssh_public_keys = var.ssh_public_keys
}