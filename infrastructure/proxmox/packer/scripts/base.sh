#!/bin/bash
# Base system configuration for Ubuntu K3s template

set -euo pipefail

echo "=== Base System Configuration ==="

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  software-properties-common \
  wget \
  git \
  htop \
  iotop \
  iftop \
  ncdu \
  net-tools \
  unzip \
  jq \
  tree \
  vim \
  tmux \
  build-essential

# Install container runtime dependencies
sudo apt-get install -y \
  containerd \
  runc \
  nfs-common \
  open-iscsi \
  util-linux \
  cryptsetup \
  lvm2 \
  sg3-utils \
  multipath-tools

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo systemctl enable containerd
sudo systemctl start containerd

# Enable and start iSCSI
sudo systemctl enable iscsid
sudo systemctl start iscsid

# Install cloud-init and qemu-guest-agent
sudo apt-get install -y cloud-init qemu-guest-agent

# Configure qemu-guest-agent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Configure SSH
sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Configure automatic updates
sudo apt-get install -y unattended-upgrades apt-listchanges
echo 'APT::Periodic::Update-Package-Lists "1";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
echo 'APT::Periodic::Unattended-Upgrade "1";' | sudo tee -a /etc/apt/apt.conf.d/20auto-upgrades

# Install monitoring tools
sudo apt-get install -y \
  prometheus-node-exporter \
  collectd \
  sysstat

# Enable and start node exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter

# Clean up
sudo apt-get autoremove -y
sudo apt-get autoclean

echo "=== Base system configuration completed ==="