#cloud-config
# K3s HA Cluster Cloud-Init Configuration
# Hostname: ${hostname}
# VM Type: ${vm_type}
# Environment: ${environment}

hostname: ${hostname}
manage_etc_hosts: true

# User configuration
users:
  - name: ubuntu
    groups: [adm, cdrom, dip, plugdev, lxd, sudo]
    lock_passwd: false
    shell: /bin/bash
    ssh_authorized_keys:
%{ for key in ssh_public_keys ~}
      - ${key}
%{ endfor ~}
    sudo: ALL=(ALL) NOPASSWD:ALL

# System packages
packages:
  - curl
  - wget
  - git
  - htop
  - iotop
  - iftop
  - ncdu
  - net-tools
  - unzip
  - jq
  - nfs-common
  - open-iscsi
  - util-linux
  - cryptsetup
  - lvm2
%{ if vm_type == "gpu_workers" }
  - nvidia-utils-535
  - nvidia-driver-535
%{ endif }

# System configuration
write_files:
  # K3s configuration
  - path: /etc/k3s-config.yaml
    content: |
      cluster-init: ${is_primary}
      server: ${is_primary ? "https://${hostname}:6443" : ""}
      token: ${k3s_token}
      disable:
        - servicelb  # Use MetalLB instead
        - traefik    # Use existing Traefik
      tls-san:
        - k3s-vip.cluster.local
        - 10.10.100.50
%{ if vm_type == "masters" }
      node-taint:
        - "node-role.kubernetes.io/master=true:NoSchedule"
%{ endif }
%{ if vm_type == "workers" || vm_type == "gpu_workers" }
      node-label:
        - "node-role.kubernetes.io/worker=true"
%{ endif }
%{ if vm_type == "gpu_workers" }
        - "accelerator=nvidia-gpu"
        - "gpu=true"
%{ endif }
    permissions: '0644'

  # K3s installation script
  - path: /usr/local/bin/install-k3s.sh
    content: |
      #!/bin/bash
      set -euo pipefail
      
      echo "Installing K3s on ${hostname}..."
      
      # Wait for system to be ready
      sleep 30
      
      # Install K3s
      curl -sfL https://get.k3s.io | sh -s - \
        --config /etc/k3s-config.yaml \
%{ if vm_type == "masters" && !is_primary }
        --server https://k3s-masters-1:6443 \
%{ endif }
%{ if vm_type == "workers" || vm_type == "gpu_workers" }
        --server https://k3s-masters-1:6443 \
        agent \
%{ endif }
        --write-kubeconfig-mode 644
      
      # Enable and start K3s
      systemctl enable k3s
      systemctl start k3s
      
      # Wait for K3s to be ready
      until kubectl get nodes; do
        echo "Waiting for K3s to be ready..."
        sleep 10
      done
      
      echo "K3s installation completed on ${hostname}"
    permissions: '0755'

  # System optimization for K3s
  - path: /etc/sysctl.d/99-k3s.conf
    content: |
      # K3s system optimizations
      net.bridge.bridge-nf-call-iptables = 1
      net.bridge.bridge-nf-call-ip6tables = 1
      net.ipv4.ip_forward = 1
      vm.swappiness = 1
      vm.overcommit_memory = 1
      kernel.panic = 10
      kernel.panic_on_oops = 1
    permissions: '0644'

  # Logrotate configuration for K3s
  - path: /etc/logrotate.d/k3s
    content: |
      /var/log/k3s.log {
        daily
        missingok
        rotate 7
        compress
        notifempty
        create 644 root root
        postrotate
          systemctl reload k3s || true
        endscript
      }
    permissions: '0644'

%{ if vm_type == "gpu_workers" }
  # NVIDIA container runtime configuration
  - path: /etc/docker/daemon.json
    content: |
      {
        "default-runtime": "nvidia",
        "runtimes": {
          "nvidia": {
            "path": "/usr/bin/nvidia-container-runtime",
            "runtimeArgs": []
          }
        }
      }
    permissions: '0644'
%{ endif }

# Boot commands
bootcmd:
  - echo 'APT::Periodic::Update-Package-Lists "1";' > /etc/apt/apt.conf.d/20auto-upgrades
  - echo 'APT::Periodic::Unattended-Upgrade "1";' >> /etc/apt/apt.conf.d/20auto-upgrades

# Run commands
runcmd:
  # Update system
  - apt-get update
  - apt-get upgrade -y
  
  # Apply sysctl settings
  - sysctl --system
  
  # Enable and configure services
  - systemctl enable iscsid
  - systemctl start iscsid
  
%{ if vm_type == "gpu_workers" }
  # GPU setup
  - modprobe nvidia
  - nvidia-smi
%{ endif }
  
  # Install K3s (delayed to ensure system is ready)
  - sleep 60
  - /usr/local/bin/install-k3s.sh
  
  # Log completion
  - echo "Cloud-init completed for ${hostname} at $(date)" >> /var/log/cloud-init-custom.log

# Final message
final_message: |
  K3s node ${hostname} (${vm_type}) is ready!
  Environment: ${environment}
  VM Type: ${vm_type}
  Primary: ${is_primary}
  
  System information:
  - OS: Ubuntu 22.04 LTS
  - K3s: Latest stable
  - Hostname: ${hostname}
  
  The system is ready for K3s cluster operations.

# Reboot after cloud-init completion
power_state:
  mode: reboot
  delay: now
  condition: true