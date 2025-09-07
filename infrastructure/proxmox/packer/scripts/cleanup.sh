#!/bin/bash
# Final cleanup for VM template

set -euo pipefail

echo "=== Final Template Cleanup ==="

# Clean apt cache
sudo apt-get autoremove -y
sudo apt-get autoclean
sudo apt-get clean

# Clean logs
sudo find /var/log -type f -name "*.log" -exec truncate -s 0 {} \;
sudo find /var/log -type f -name "*.log.*" -delete
sudo journalctl --vacuum-time=1s

# Clean temporary files
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*
sudo rm -rf /var/cache/apt/archives/*.deb
sudo rm -rf /var/cache/apt/archives/partial/*
sudo rm -rf /var/lib/apt/lists/*

# Clean user history and cache
history -c
cat /dev/null > ~/.bash_history
sudo rm -rf ~/.cache/*

# Clean SSH host keys (will be regenerated on first boot)
sudo rm -f /etc/ssh/ssh_host_*

# Clean machine ID (will be regenerated on first boot)
sudo truncate -s 0 /etc/machine-id
sudo rm -f /var/lib/dbus/machine-id

# Clean cloud-init state
sudo cloud-init clean --logs

# Clean network configuration (cloud-init will handle this)
sudo rm -f /etc/udev/rules.d/70-persistent-net.rules

# Remove DHCP leases
sudo rm -f /var/lib/dhcp/*

# Zero out free space (optional, but helps with template compression)
echo "Zeroing free space..."
sudo dd if=/dev/zero of=/EMPTY bs=1M || true
sudo rm -f /EMPTY

# Sync filesystem
sudo sync

echo "=== Template cleanup completed ==="