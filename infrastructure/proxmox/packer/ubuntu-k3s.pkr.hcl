# Ubuntu 22.04 K3s Homelab Template
# Integrates with existing homelab SSH keys and configurations

variable "proxmox_api_url" {
  type        = string
  description = "Proxmox API URL"
  default     = env("PROXMOX_URL")
}

variable "proxmox_username" {
  type        = string
  description = "Proxmox username"
  default     = env("PROXMOX_USERNAME")
}

variable "proxmox_password" {
  type        = string
  description = "Proxmox password"
  sensitive   = true
  default     = env("PROXMOX_PASSWORD")
}

variable "proxmox_token" {
  type        = string
  description = "Proxmox API token"
  sensitive   = true
  default     = env("PROXMOX_TOKEN")
}

variable "proxmox_node" {
  type        = string
  description = "Proxmox node name"
  default     = env("PROXMOX_NODE")
}

variable "existing_ssh_keys" {
  type        = string
  description = "Existing SSH public keys"
  default     = ""
}

variable "homelab_scripts_path" {
  type        = string
  description = "Path to existing homelab scripts"
  default     = "../../../scripts/"
}

variable "template_vm_id" {
  type        = number
  description = "VM ID for the template (if not specified, Proxmox will auto-assign)"
  default     = null
}

# Get SSH keys from multiple sources
locals {
  ssh_keys = [
    # Try to read from common locations
    try(file("${path.root}/../../../.ssh/authorized_keys"), ""),
    try(file("~/.ssh/id_rsa.pub"), ""),
    var.existing_ssh_keys
  ]
  
  # Filter out empty keys
  valid_ssh_keys = [for key in local.ssh_keys : key if key != ""]
  
  # Join all valid keys
  all_ssh_keys = join("\n", local.valid_ssh_keys)
  
  # Template name with timestamp
  template_name = "ubuntu-k3s-homelab-${formatdate("YYYYMMDD-HHMM", timestamp())}"
}

source "proxmox-iso" "ubuntu-k3s-homelab" {
  # Proxmox connection - use token auth (preferred) or password
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_username
  token                    = var.proxmox_token
  # password                 = var.proxmox_password  # Comment out when using token
  node                     = var.proxmox_node
  insecure_skip_tls_verify = true
  
  # Connection timeout settings
  task_timeout    = "20m"
  iso_download_pve = false
  
  # Template configuration
  template_name        = local.template_name
  template_description = "Ubuntu 22.04 LTS optimized for K3s homelab cluster"
  vm_id                = var.template_vm_id
  
  # ISO configuration - use manually uploaded ISO
  iso_file             = "local:iso/ubuntu-22.04.5-live-server-amd64.iso"
  iso_checksum         = "9bc6028870aef3f74f4e16b900008179e78b130e6b0b9a140635434a46aa98b0"
  unmount_iso          = true
  
  # VM configuration
  qemu_agent    = true
  scsi_controller = "virtio-scsi-pci"
  
  cores   = 2
  memory  = 2048
  
  disks {
    disk_size    = "20G"
    format       = "raw"
    storage_pool = "local-lvm"
    type         = "virtio"
  }
  
  network_adapters {
    model    = "virtio"
    bridge   = "vmbr0"
    firewall = false
  }
  
  # Cloud-init configuration
  cloud_init              = true
  cloud_init_storage_pool = "local"
  
  # Boot configuration
  boot_command = [
    "<esc><wait>",
    "e<wait>",
    "<down><down><down><end>",
    "<bs><bs><bs><bs><wait>",
    "autoinstall ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ ---<wait>",
    "<f10><wait>"
  ]
  
  boot_wait = "5s"
  
  # HTTP server for autoinstall
  http_directory = "http"
  http_bind_address = "0.0.0.0"
  http_port_min = 8000
  http_port_max = 8999
  
  # SSH configuration
  ssh_username = "ubuntu"
  ssh_password = "ubuntu"
  ssh_timeout = "20m"
  
  # SSH public key authentication
  ssh_clear_authorized_keys = false
}

build {
  description = "Build Ubuntu 22.04 K3s homelab template"
  
  sources = ["source.proxmox-iso.ubuntu-k3s-homelab"]
  
  # Wait for system to be ready
  provisioner "shell" {
    inline = [
      "while [ ! -f /var/lib/cloud/instance/boot-finished ]; do echo 'Waiting for cloud-init...'; sleep 1; done"
    ]
  }
  
  # Copy existing homelab scripts if available (skip if directory doesn't exist)
  provisioner "shell" {
    inline = [
      "echo 'Checking for homelab scripts...'",
      "mkdir -p /tmp/homelab-scripts",
      "echo 'Homelab scripts directory created'"
    ]
  }
  
  # System preparation
  provisioner "shell" {
    scripts = [
      "scripts/base.sh",
      "scripts/kernel-tuning.sh",
      "scripts/k3s-prep.sh"
    ]
  }
  
  # Configure SSH keys
  provisioner "shell" {
    inline = [
      "mkdir -p /home/ubuntu/.ssh",
      "echo '${local.all_ssh_keys}' >> /home/ubuntu/.ssh/authorized_keys",
      "chown -R ubuntu:ubuntu /home/ubuntu/.ssh",
      "chmod 700 /home/ubuntu/.ssh",
      "chmod 600 /home/ubuntu/.ssh/authorized_keys"
    ]
  }
  
  # Install homelab-specific configurations
  provisioner "shell" {
    inline = [
      "set -e",
      "# Install additional tools for homelab integration",
      "echo 'Installing kubectl...'",
      "KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)",
      "curl -LO \"https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl\"",
      "sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl",
      "rm -f kubectl",
      "",
      "# Install Helm for package management",
      "echo 'Installing Helm...'",
      "curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3",
      "chmod 700 get_helm.sh",
      "sudo ./get_helm.sh",
      "rm -f get_helm.sh",
      "",
      "# Install k9s for cluster management",
      "echo 'Installing k9s...'",
      "K9S_VERSION=$(curl -s https://api.github.com/repos/derailed/k9s/releases/latest | grep -oP '\"tag_name\": \"\\K[^\"]*')",
      "curl -L \"https://github.com/derailed/k9s/releases/download/$K9S_VERSION/k9s_Linux_amd64.tar.gz\" | tar xz",
      "sudo mv k9s /usr/local/bin/",
      "sudo chmod +x /usr/local/bin/k9s"
    ]
  }
  
  # Final cleanup and preparation
  provisioner "shell" {
    scripts = ["scripts/cleanup.sh"]
  }
  
  # Template finalization
  provisioner "shell" {
    inline = [
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*",
      "cat /dev/null > ~/.bash_history || true",
      "sudo cloud-init clean",
      "sudo sync"
    ]
  }
}