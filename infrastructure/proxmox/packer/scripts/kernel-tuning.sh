#!/bin/bash
# Kernel tuning optimizations for K3s

set -euo pipefail

echo "=== Kernel Tuning for K3s ==="

# Create sysctl configuration for K3s
sudo tee /etc/sysctl.d/99-k3s.conf > /dev/null <<EOF
# Network optimizations
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv6.conf.all.forwarding = 1
net.netfilter.nf_conntrack_max = 131072

# Memory management
vm.swappiness = 1
vm.overcommit_memory = 1
vm.panic_on_oom = 0
vm.vfs_cache_pressure = 50

# Kernel parameters
kernel.panic = 10
kernel.panic_on_oops = 1
kernel.keys.root_maxkeys = 1000000
kernel.keys.root_maxbytes = 25000000

# File descriptor limits
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 524288
fs.file-max = 2097152

# Network tuning
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
net.ipv4.tcp_wmem = 4096 12582912 16777216
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_window_scaling = 1

# Security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
EOF

# Load bridge module
echo "br_netfilter" | sudo tee /etc/modules-load.d/k3s.conf
sudo modprobe br_netfilter

# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Configure systemd limits
sudo mkdir -p /etc/systemd/system.conf.d
sudo tee /etc/systemd/system.conf.d/kubernetes.conf > /dev/null <<EOF
[Manager]
DefaultLimitNOFILE=1048576
DefaultLimitNPROC=1048576
DefaultLimitCORE=infinity
DefaultLimitMEMLOCK=infinity
EOF

# Configure systemd user limits
sudo mkdir -p /etc/systemd/user.conf.d
sudo tee /etc/systemd/user.conf.d/kubernetes.conf > /dev/null <<EOF
[Manager]
DefaultLimitNOFILE=1048576
DefaultLimitNPROC=1048576
DefaultLimitCORE=infinity
DefaultLimitMEMLOCK=infinity
EOF

# Configure limits.conf
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
* soft memlock unlimited
* hard memlock unlimited
EOF

# Configure logrotate for container logs
sudo tee /etc/logrotate.d/k3s > /dev/null <<EOF
/var/log/pods/*/*/*.log
/var/log/containers/*.log {
    rotate 5
    daily
    compress
    missingok
    notifempty
    maxage 30
    copytruncate
}
EOF

# Apply sysctl settings
sudo sysctl --system

echo "=== Kernel tuning completed ==="