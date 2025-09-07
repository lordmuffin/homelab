# K3s HA Cluster - VM Image Management Guide

## Overview

This guide covers the complete lifecycle management of VM templates used for the K3s HA cluster. The template-based approach ensures consistency, security, and rapid deployment of cluster nodes.

## Image Architecture

### Template Strategy

```
Base Image Lifecycle:
Ubuntu 22.04 LTS → K3s Optimizations → Security Hardening → Template Creation
      │                    │                    │                 │
      ▼                    ▼                    ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ OS Install  │    │ Kernel      │    │ Security    │    │ Template    │
│ & Updates   │ → │ Tuning &    │ → │ Hardening & │ → │ Ready for   │
│             │    │ K3s Prep    │    │ Final Setup │    │ Deployment  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Template Variants

| Template Type | Purpose | Special Configuration | Update Frequency |
|---------------|---------|----------------------|------------------|
| k3s-master | Control plane nodes | etcd optimizations, API server tuning | Monthly |
| k3s-worker | Standard workload nodes | Container runtime optimization | Monthly |
| k3s-gpu | GPU-accelerated nodes | NVIDIA drivers, CUDA toolkit | Quarterly |
| k3s-dev | Development/testing | Relaxed security, debug tools | As needed |

## Packer Configuration

### Base Configuration Structure

```hcl
# ubuntu-k3s-base.pkr.hcl
packer {
  required_plugins {
    proxmox = {
      version = "~> 1"
      source  = "github.com/hashicorp/proxmox"
    }
  }
}

# Variables for customization
variable "proxmox_url" {
  type        = string
  description = "Proxmox API URL"
}

variable "proxmox_username" {
  type        = string
  description = "Proxmox username"
}

variable "proxmox_password" {
  type        = string
  sensitive   = true
  description = "Proxmox password"
}

variable "proxmox_node" {
  type        = string
  description = "Proxmox node name"
}

variable "template_name" {
  type        = string
  default     = "ubuntu-k3s-template"
  description = "Template name"
}

variable "vm_id" {
  type        = number
  default     = 9000
  description = "VM ID for template"
}

source "proxmox-iso" "ubuntu-k3s" {
  # Proxmox connection
  proxmox_url              = var.proxmox_url
  username                 = var.proxmox_username
  password                 = var.proxmox_password
  node                     = var.proxmox_node
  insecure_skip_tls_verify = true

  # VM configuration
  vm_id                = var.vm_id
  vm_name              = var.template_name
  template_description = "Ubuntu 22.04 K3s Ready Template - Built $(timestamp)"

  # ISO configuration
  iso_file         = "local:iso/ubuntu-22.04.3-live-server-amd64.iso"
  iso_storage_pool = "local"
  unmount_iso      = true

  # System configuration
  qemu_agent    = true
  scsi_controller = "virtio-scsi-pci"
  disks {
    disk_size    = "32G"
    format       = "raw"
    storage_pool = "local-zfs"
    type         = "virtio"
  }

  # CPU and Memory
  cores   = 2
  sockets = 1
  memory  = 4096

  # Network
  network_adapters {
    model    = "virtio"
    bridge   = "vmbr0"
    vlan_tag = "10"
  }

  # Cloud-init
  cloud_init              = true
  cloud_init_storage_pool = "local-zfs"

  # Boot configuration
  boot_command = [
    "<esc><wait>",
    "autoinstall ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
    "<enter><wait>"
  ]

  boot_wait = "5s"
  boot_key_interval = "10ms"

  # SSH configuration
  ssh_username = "ubuntu"
  ssh_password = "ubuntu"
  ssh_timeout = "20m"

  # HTTP server for autoinstall
  http_directory = "http"
  http_bind_address = "0.0.0.0"
  http_port_min = 8000
  http_port_max = 9000
}

build {
  name = "ubuntu-k3s-template"
  sources = ["source.proxmox-iso.ubuntu-k3s"]

  # Wait for cloud-init to complete
  provisioner "shell" {
    inline = [
      "while [ ! -f /var/lib/cloud/instance/boot-finished ]; do echo 'Waiting for cloud-init...'; sleep 1; done",
      "sudo cloud-init status --wait"
    ]
  }

  # System updates and base packages
  provisioner "shell" {
    script = "scripts/base.sh"
  }

  # Kernel tuning for K3s
  provisioner "shell" {
    script = "scripts/kernel-tuning.sh"
  }

  # K3s prerequisites
  provisioner "shell" {
    script = "scripts/k3s-prep.sh"
  }

  # Security hardening
  provisioner "shell" {
    script = "scripts/security-hardening.sh"
  }

  # Template cleanup and preparation
  provisioner "shell" {
    script = "scripts/cleanup.sh"
  }

  # Convert to template
  post-processor "manifest" {
    output = "manifest.json"
    strip_path = true
  }
}
```

## Provisioning Scripts

### Base System Setup (`scripts/base.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Base System Setup ==="

# Update system packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get upgrade -y

# Install essential packages
apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    htop \
    iotop \
    nmon \
    tree \
    jq \
    vim \
    nano \
    net-tools \
    dnsutils \
    iputils-ping \
    traceroute \
    tcpdump \
    nmap \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    build-essential \
    linux-headers-$(uname -r) \
    open-iscsi \
    nfs-common

# Configure timezone
timedatectl set-timezone UTC

# Enable and configure NTP
systemctl enable systemd-timesyncd
systemctl start systemd-timesyncd

# Configure SSH
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# Configure automatic security updates
apt-get install -y unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/51myunattended-upgrades

echo "Base system setup complete"
```

### Kernel Tuning (`scripts/kernel-tuning.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Kernel Tuning for K3s ==="

# Enable required kernel modules
cat <<EOF > /etc/modules-load.d/k3s.conf
# Kernel modules for K3s
overlay
br_netfilter
ip_tables
ip6_tables
netfilter_conntrack
nf_nat
xt_REDIRECT
xt_owner
iptable_nat
iptable_mangle
iptable_raw
EOF

# Load modules immediately
modprobe overlay
modprobe br_netfilter
modprobe ip_tables
modprobe ip6_tables

# Configure sysctl parameters
cat <<EOF > /etc/sysctl.d/99-k3s.conf
# Network settings for K3s
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Disable swap
vm.swappiness = 0

# Network performance tuning
net.core.somaxconn = 32768
net.core.netdev_max_backlog = 5000
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
net.ipv4.tcp_wmem = 4096 12582912 16777216
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.ip_local_port_range = 10000 65000

# File system performance
fs.file-max = 2097152
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 1048576

# Process limits
kernel.pid_max = 4194304
kernel.threads-max = 4194304

# Memory management
vm.max_map_count = 524288
EOF

# Apply sysctl settings
sysctl --system

# Disable swap permanently
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# Configure systemd limits
mkdir -p /etc/systemd/system.conf.d
cat <<EOF > /etc/systemd/system.conf.d/k3s.conf
[Manager]
DefaultLimitNOFILE=1048576
DefaultLimitNPROC=1048576
EOF

# Configure user limits
cat <<EOF > /etc/security/limits.d/99-k3s.conf
# Limits for K3s
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
root soft nofile 1048576
root hard nofile 1048576
root soft nproc 1048576
root hard nproc 1048576
EOF

echo "Kernel tuning complete"
```

### K3s Prerequisites (`scripts/k3s-prep.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== K3s Prerequisites Setup ==="

# Install Docker (for compatibility, though K3s uses containerd)
# curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
# echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
# apt-get update
# apt-get install -y docker-ce docker-ce-cli containerd.io

# Install containerd
apt-get install -y containerd

# Configure containerd
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml

# Enable SystemdCgroup
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Install CNI plugins
mkdir -p /opt/cni/bin
CNI_VERSION="v1.3.0"
curl -L "https://github.com/containernetworking/plugins/releases/download/${CNI_VERSION}/cni-plugins-linux-amd64-${CNI_VERSION}.tgz" | tar -C /opt/cni/bin -xz

# Install crictl (CRI debugging tool)
CRICTL_VERSION="v1.28.0"
curl -L "https://github.com/kubernetes-sigs/cri-tools/releases/download/${CRICTL_VERSION}/crictl-${CRICTL_VERSION}-linux-amd64.tar.gz" | tar -C /usr/local/bin -xz

# Configure crictl
cat <<EOF > /etc/crictl.yaml
runtime-endpoint: unix:///run/containerd/containerd.sock
image-endpoint: unix:///run/containerd/containerd.sock
timeout: 2
debug: false
pull-image-on-create: false
EOF

# Install helm
HELM_VERSION="3.13.3"
curl -L "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" | tar -xz
mv linux-amd64/helm /usr/local/bin/
rm -rf linux-amd64

# Install kubectl
KUBECTL_VERSION="v1.28.4"
curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl

# Create kubectl completion
kubectl completion bash > /etc/bash_completion.d/kubectl

# Create directories for K3s
mkdir -p /var/lib/rancher/k3s
mkdir -p /etc/rancher/k3s

# Create longhorn storage directory
mkdir -p /var/lib/longhorn

# Create K3s preparation marker
mkdir -p /opt/k3s-prep
cat <<EOF > /opt/k3s-prep/info.txt
K3s preparation completed at: $(date)
Template build: $(date +%Y%m%d-%H%M)
Ubuntu version: $(lsb_release -d)
Kernel version: $(uname -r)
Containerd version: $(containerd --version)
CNI plugins version: ${CNI_VERSION}
EOF

# Enable and start containerd
systemctl enable containerd
systemctl start containerd

echo "K3s prerequisites setup complete"
```

### Security Hardening (`scripts/security-hardening.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Security Hardening ==="

# Install security packages
apt-get install -y \
    fail2ban \
    ufw \
    aide \
    rkhunter \
    chkrootkit \
    auditd \
    audispd-plugins

# Configure UFW (Uncomplicated Firewall)
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22/tcp

# Allow K3s ports
ufw allow 6443/tcp    # K3s API server
ufw allow 10250/tcp   # Kubelet
ufw allow 2379/tcp    # etcd client
ufw allow 2380/tcp    # etcd peer
ufw allow 8472/udp    # Flannel VXLAN
ufw allow 51820/udp   # Flannel WireGuard IPv4
ufw allow 51821/udp   # Flannel WireGuard IPv6

# NodePort range
ufw allow 30000:32767/tcp
ufw allow 30000:32767/udp

# Enable UFW
echo "y" | ufw enable

# Configure fail2ban
systemctl enable fail2ban

# Configure auditd
cat <<EOF > /etc/audit/rules.d/k3s.rules
# K3s audit rules
-w /var/lib/rancher/k3s -p wa -k k3s
-w /etc/rancher/k3s -p wa -k k3s-config
-w /usr/local/bin/k3s -p x -k k3s-exec
EOF

systemctl enable auditd

# Configure AIDE (Advanced Intrusion Detection Environment)
aideinit --yes --force
systemctl enable aide.timer

# Secure shared memory
echo "tmpfs /run/shm tmpfs defaults,noexec,nosuid,nodev 0 0" >> /etc/fstab

# Kernel security settings
cat <<EOF >> /etc/sysctl.d/99-security.conf
# Security settings
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
EOF

# Apply security settings
sysctl --system

# Set proper file permissions
chmod 640 /etc/shadow
chmod 644 /etc/passwd
chmod 644 /etc/group
chmod 600 /etc/gshadow

# Configure login security
sed -i 's/PASS_MAX_DAYS\t99999/PASS_MAX_DAYS\t90/' /etc/login.defs
sed -i 's/PASS_MIN_DAYS\t0/PASS_MIN_DAYS\t7/' /etc/login.defs
sed -i 's/PASS_WARN_AGE\t7/PASS_WARN_AGE\t14/' /etc/login.defs

# Disable unused filesystems
cat <<EOF > /etc/modprobe.d/blacklist-rare-filesystems.conf
install cramfs /bin/true
install freevxfs /bin/true
install jffs2 /bin/true
install hfs /bin/true
install hfsplus /bin/true
install squashfs /bin/true
install udf /bin/true
EOF

echo "Security hardening complete"
```

### Template Cleanup (`scripts/cleanup.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Template Cleanup ==="

# Clean package cache
apt-get autoremove -y
apt-get autoclean
apt-get clean

# Clean logs
find /var/log -type f -name "*.log" -exec truncate -s 0 {} \;
find /var/log -type f -name "*.gz" -delete
find /var/log -type f -name "*.1" -delete
journalctl --vacuum-time=1s

# Clean temporary files
rm -rf /tmp/*
rm -rf /var/tmp/*

# Clean bash history
history -c
history -w
rm -f /home/ubuntu/.bash_history
rm -f /root/.bash_history

# Clean SSH host keys (they will be regenerated on first boot)
rm -f /etc/ssh/ssh_host_*

# Clean cloud-init
cloud-init clean --logs --seed

# Clean machine-id (will be regenerated)
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id

# Clean network configuration (cloud-init will handle this)
rm -f /etc/netplan/50-cloud-init.yaml

# Generate new SSH host keys on first boot
cat <<EOF > /etc/systemd/system/regenerate-ssh-host-keys.service
[Unit]
Description=Regenerate SSH host keys
After=cloud-init.service
ConditionFileNotExists=/etc/ssh/ssh_host_rsa_key

[Service]
Type=oneshot
ExecStart=/usr/bin/ssh-keygen -A
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable regenerate-ssh-host-keys.service

# Create template completion marker
cat <<EOF > /opt/k3s-prep/template-ready.txt
Template preparation completed at: $(date)
Template is ready for deployment.

Next steps:
1. Clone this template to create VMs
2. Run Ansible playbooks to configure K3s cluster
3. Deploy applications using GitOps

Template ID: 9000
Template Name: ubuntu-k3s-template
EOF

# Sync filesystem
sync

echo "Template cleanup complete - Ready for conversion to template"
```

## Template Management Operations

### Building Templates

#### Manual Build Process

```bash
# Navigate to Packer directory
cd infrastructure/proxmox/packer

# Validate Packer configuration
packer validate ubuntu-k3s.pkr.hcl

# Build the template
packer build \
  -var 'proxmox_url=https://proxmox.homelab.local:8006/api2/json' \
  -var 'proxmox_username=root@pam' \
  -var 'proxmox_password=your-password' \
  -var 'proxmox_node=proxmox-node-1' \
  ubuntu-k3s.pkr.hcl

# Monitor build progress
tail -f packer.log
```

#### Automated Build with Make

```bash
# Create Makefile for automation
cat <<EOF > Makefile
.PHONY: build clean validate test

TEMPLATE_NAME := ubuntu-k3s-template
VM_ID := 9000
PROXMOX_NODE := proxmox-node-1

build:
	@echo "Building K3s template..."
	packer build \
		-var 'template_name=$(TEMPLATE_NAME)' \
		-var 'vm_id=$(VM_ID)' \
		-var 'proxmox_node=$(PROXMOX_NODE)' \
		ubuntu-k3s.pkr.hcl

validate:
	@echo "Validating Packer configuration..."
	packer validate ubuntu-k3s.pkr.hcl

clean:
	@echo "Cleaning up build artifacts..."
	rm -f manifest.json
	rm -f packer.log

test:
	@echo "Testing template..."
	./scripts/test-template.sh $(VM_ID)

deploy-test:
	@echo "Deploying test cluster..."
	cd ../terraform && terraform apply -var='template_name=$(TEMPLATE_NAME)'
EOF

# Use make to build
make validate
make build
```

### Template Versioning Strategy

#### Version Scheme

```
Template Version: YYYY.MM.DD-BUILD
├── 2024.01.15-001  # Initial release
├── 2024.02.01-001  # Monthly update
├── 2024.02.15-002  # Security patch
└── 2024.03.01-001  # Monthly update with new features
```

#### Version Management

```bash
#!/bin/bash
# scripts/version-template.sh

VERSION=$(date +%Y.%m.%d)
BUILD_NUMBER=001

TEMPLATE_NAME="ubuntu-k3s-${VERSION}-${BUILD_NUMBER}"
VM_ID=$((9000 + $(date +%m%d)))

# Build template with version
packer build \
  -var "template_name=${TEMPLATE_NAME}" \
  -var "vm_id=${VM_ID}" \
  ubuntu-k3s.pkr.hcl

# Tag template in Proxmox
qm set ${VM_ID} -description "K3s Template ${VERSION}-${BUILD_NUMBER} - Built $(date)"
```

### Template Testing and Validation

#### Automated Testing Script

```bash
#!/bin/bash
# scripts/test-template.sh

set -euo pipefail

TEMPLATE_ID=${1:-9000}
TEST_VM_ID=999
TEST_VM_NAME="test-k3s-template"

echo "=== Testing K3s Template ID: ${TEMPLATE_ID} ==="

# Clone template for testing
echo "Cloning template for testing..."
qm clone ${TEMPLATE_ID} ${TEST_VM_ID} --name ${TEST_VM_NAME}

# Configure test VM
qm set ${TEST_VM_ID} --sockets 2 --cores 2 --memory 4096
qm set ${TEST_VM_ID} --net0 virtio,bridge=vmbr0,tag=10
qm set ${TEST_VM_ID} --ipconfig0 ip=dhcp

# Start test VM
echo "Starting test VM..."
qm start ${TEST_VM_ID}

# Wait for VM to be ready
sleep 60

# Get VM IP address
VM_IP=$(qm guest cmd ${TEST_VM_ID} network-get-interfaces | jq -r '.[] | select(.name=="eth0") | .["ip-addresses"][] | select(.["ip-address-type"]=="ipv4") | .["ip-address"]')

echo "Test VM IP: ${VM_IP}"

# Test SSH connectivity
echo "Testing SSH connectivity..."
timeout 30 bash -c "until ssh -o StrictHostKeyChecking=no ubuntu@${VM_IP} 'echo SSH OK'; do sleep 5; done"

# Test K3s prerequisites
echo "Testing K3s prerequisites..."
ssh -o StrictHostKeyChecking=no ubuntu@${VM_IP} '
    # Check kernel modules
    if ! lsmod | grep -q overlay; then
        echo "FAIL: overlay module not loaded"
        exit 1
    fi
    
    # Check containerd
    if ! systemctl is-active --quiet containerd; then
        echo "FAIL: containerd not running"
        exit 1
    fi
    
    # Check directories
    if [ ! -d /var/lib/rancher/k3s ]; then
        echo "FAIL: K3s directory missing"
        exit 1
    fi
    
    # Check crictl
    if ! crictl version; then
        echo "FAIL: crictl not working"
        exit 1
    fi
    
    echo "All tests passed!"
'

# Cleanup test VM
echo "Cleaning up test VM..."
qm stop ${TEST_VM_ID}
qm destroy ${TEST_VM_ID}

echo "=== Template testing completed successfully ==="
```

### Template Update Procedures

#### Monthly Update Process

```bash
#!/bin/bash
# scripts/update-template.sh

set -euo pipefail

OLD_TEMPLATE_ID=9000
NEW_TEMPLATE_ID=9001
BACKUP_STORAGE="backup-nas"

echo "=== Monthly Template Update Process ==="

# 1. Backup existing template
echo "Backing up existing template..."
vzdump ${OLD_TEMPLATE_ID} --storage ${BACKUP_STORAGE} --compress gzip

# 2. Build new template
echo "Building new template..."
make build

# 3. Test new template
echo "Testing new template..."
./scripts/test-template.sh ${NEW_TEMPLATE_ID}

# 4. Update Terraform configuration
echo "Updating Terraform template reference..."
sed -i "s/template_name = \"ubuntu-k3s-template\"/template_name = \"ubuntu-k3s-$(date +%Y.%m.%d)-001\"/" \
    ../terraform/terraform.tfvars

# 5. Create deployment plan
echo "Creating deployment plan..."
cd ../terraform
terraform plan -out=template-update.plan

echo "Template update ready for deployment"
echo "Run: cd ../terraform && terraform apply template-update.plan"
```

#### Security Update Process

```bash
#!/bin/bash
# scripts/security-update.sh

set -euo pipefail

TEMPLATE_ID=9000
SECURITY_VM_ID=998

echo "=== Security Update Process ==="

# Clone existing template
qm clone ${TEMPLATE_ID} ${SECURITY_VM_ID} --name "security-update-$(date +%Y%m%d)"
qm set ${SECURITY_VM_ID} --sockets 2 --cores 2 --memory 4096

# Start VM for updates
qm start ${SECURITY_VM_ID}
sleep 60

# Get IP and apply updates
VM_IP=$(qm guest cmd ${SECURITY_VM_ID} network-get-interfaces | jq -r '.[] | select(.name=="eth0") | .["ip-addresses"][] | select(.["ip-address-type"]=="ipv4") | .["ip-address"]')

ssh -o StrictHostKeyChecking=no ubuntu@${VM_IP} '
    sudo apt-get update
    sudo apt-get upgrade -y
    sudo apt-get autoremove -y
    sudo apt-get autoclean
    
    # Clear logs and history
    sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} \;
    history -c && history -w
    sudo rm -f /root/.bash_history
    
    # Sync and shutdown
    sync
    sudo shutdown -h now
'

# Wait for shutdown
sleep 30

# Convert to template
qm template ${SECURITY_VM_ID}

# Update template ID
NEW_TEMPLATE_NAME="ubuntu-k3s-security-$(date +%Y%m%d)"
qm set ${SECURITY_VM_ID} -description "Security updated template - $(date)"

echo "Security update complete - Template ID: ${SECURITY_VM_ID}"
```

## GPU Template Management

### GPU-Specific Template Configuration

```bash
#!/bin/bash
# scripts/build-gpu-template.sh

echo "=== Building GPU K3s Template ==="

# Build base template first
make build

# Clone for GPU customization
BASE_TEMPLATE_ID=9000
GPU_TEMPLATE_ID=9010

qm clone ${BASE_TEMPLATE_ID} ${GPU_TEMPLATE_ID} --name "ubuntu-k3s-gpu-template"

# Configure VM for GPU passthrough
qm set ${GPU_TEMPLATE_ID} --sockets 1 --cores 8 --memory 32768
qm set ${GPU_TEMPLATE_ID} --hostpci0 01:00.0,pcie=1  # Adjust GPU PCI address

# Start and customize for GPU
qm start ${GPU_TEMPLATE_ID}
sleep 60

VM_IP=$(qm guest cmd ${GPU_TEMPLATE_ID} network-get-interfaces | jq -r '.[] | select(.name=="eth0") | .["ip-addresses"][] | select(.["ip-address-type"]=="ipv4") | .["ip-address"]')

ssh -o StrictHostKeyChecking=no ubuntu@${VM_IP} '
    # Install NVIDIA drivers
    sudo apt-get update
    sudo apt-get install -y ubuntu-drivers-common
    sudo ubuntu-drivers autoinstall
    
    # Install NVIDIA container toolkit
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit nvidia-container-runtime
    
    # Configure containerd for GPU
    sudo nvidia-ctk runtime configure --runtime=containerd
    sudo systemctl restart containerd
    
    # Cleanup and shutdown
    sudo apt-get autoremove -y
    sudo apt-get clean
    history -c && history -w
    sync
    sudo shutdown -h now
'

# Wait and convert to template
sleep 30
qm template ${GPU_TEMPLATE_ID}

echo "GPU template created with ID: ${GPU_TEMPLATE_ID}"
```

## Template Deployment Integration

### Terraform Integration

```hcl
# terraform/variables.tf
variable "template_variants" {
  description = "Available template variants"
  type = map(object({
    template_id   = number
    template_name = string
    description   = string
  }))
  default = {
    master = {
      template_id   = 9000
      template_name = "ubuntu-k3s-template"
      description   = "Standard K3s template for master nodes"
    }
    worker = {
      template_id   = 9000
      template_name = "ubuntu-k3s-template"
      description   = "Standard K3s template for worker nodes"
    }
    gpu = {
      template_id   = 9010
      template_name = "ubuntu-k3s-gpu-template"
      description   = "GPU-enabled K3s template"
    }
  }
}

# Use template based on node type
resource "proxmox_vm_qemu" "k3s_nodes" {
  for_each = var.cluster_nodes
  
  target_node = var.proxmox_node
  vmid        = each.value.vm_id
  name        = each.key
  desc        = "K3s ${each.value.role} node"
  
  # Select template based on node role
  clone = lookup(var.template_variants, each.value.role, var.template_variants.worker).template_name
  
  # Node-specific configuration
  cores   = each.value.cores
  sockets = 1
  memory  = each.value.memory
  
  disk {
    size    = each.value.disk_size
    type    = "virtio"
    storage = var.storage_pool
  }
  
  network {
    model  = "virtio"
    bridge = var.network_bridge
    tag    = var.network_vlan
  }
  
  # Cloud-init configuration
  ipconfig0 = "ip=${each.value.ip}/24,gw=${var.network_gateway}"
  nameserver = var.network_nameservers[0]
  
  sshkeys = file(var.ssh_public_key_file)
  
  # GPU passthrough for GPU workers
  dynamic "hostpci" {
    for_each = each.value.role == "gpu" ? [1] : []
    content {
      device = "hostpci0"
      host   = each.value.gpu_pci_address
      pcie   = 1
    }
  }
}
```

## Monitoring and Maintenance

### Template Health Monitoring

```bash
#!/bin/bash
# scripts/monitor-templates.sh

TEMPLATE_IDS=(9000 9010)
ALERT_EMAIL="admin@homelab.local"

for template_id in "${TEMPLATE_IDS[@]}"; do
    echo "Checking template ${template_id}..."
    
    # Check if template exists
    if ! qm status ${template_id} >/dev/null 2>&1; then
        echo "ERROR: Template ${template_id} not found"
        continue
    fi
    
    # Get template info
    template_info=$(qm config ${template_id})
    template_name=$(echo "$template_info" | grep "name:" | awk '{print $2}')
    
    # Check template age
    creation_date=$(echo "$template_info" | grep "description:" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' | head -1)
    
    if [ -n "$creation_date" ]; then
        creation_epoch=$(date -d "$creation_date" +%s)
        current_epoch=$(date +%s)
        age_days=$(( (current_epoch - creation_epoch) / 86400 ))
        
        if [ $age_days -gt 30 ]; then
            echo "WARNING: Template ${template_name} is ${age_days} days old"
            echo "Template ${template_name} needs update (${age_days} days old)" | \
                mail -s "Template Update Required" ${ALERT_EMAIL}
        fi
    fi
    
    echo "Template ${template_name}: OK"
done
```

### Automated Template Updates

```bash
#!/bin/bash
# scripts/scheduled-template-update.sh
# Run via cron: 0 2 1 * * /path/to/scheduled-template-update.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/template-updates.log"

exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "=== Scheduled Template Update: $(date) ==="

# Check if updates are available
if apt list --upgradable 2>/dev/null | grep -q upgradable; then
    echo "Security updates available, building new template..."
    
    # Build new template
    cd "$SCRIPT_DIR/../"
    make build
    
    # Test new template
    ./scripts/test-template.sh 9001
    
    # If tests pass, replace old template
    if [ $? -eq 0 ]; then
        echo "Template tests passed, updating production template..."
        qm destroy 9000
        qm set 9001 --name "ubuntu-k3s-template"
        echo "Template update completed successfully"
    else
        echo "Template tests failed, keeping old template"
        qm destroy 9001
        exit 1
    fi
else
    echo "No updates available"
fi

echo "=== Template update check completed: $(date) ==="
```

## Best Practices and Recommendations

### Template Security

1. **Regular Updates**: Update templates monthly or when security updates are available
2. **Minimal Surface**: Install only necessary packages in templates
3. **Audit Trail**: Maintain detailed logs of template builds and changes
4. **Access Control**: Restrict template access to authorized personnel
5. **Encryption**: Use encrypted storage for template backups

### Performance Optimization

1. **Resource Allocation**: Right-size template resources based on actual usage
2. **Storage Optimization**: Use thin provisioning and efficient storage formats
3. **Network Configuration**: Optimize network settings for container workloads
4. **Kernel Tuning**: Apply K3s-specific kernel optimizations

### Operational Excellence

1. **Version Control**: Maintain template configurations in Git
2. **Automated Testing**: Implement comprehensive template testing
3. **Documentation**: Keep detailed documentation of template changes
4. **Monitoring**: Monitor template usage and performance
5. **Disaster Recovery**: Maintain template backups and recovery procedures

This image management guide provides comprehensive procedures for maintaining VM templates throughout their lifecycle, ensuring consistent, secure, and optimized infrastructure for your K3s cluster deployment.