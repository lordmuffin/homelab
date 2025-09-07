#!/bin/bash
# K3s preparation and prerequisites installation

set -euo pipefail

echo "=== K3s Preparation ==="

# Create k3s user
sudo useradd --system --create-home --shell /bin/bash k3s || true

# Create necessary directories
sudo mkdir -p /etc/rancher/k3s
sudo mkdir -p /var/lib/rancher/k3s
sudo mkdir -p /var/log/k3s

# Set permissions
sudo chown -R k3s:k3s /var/lib/rancher/k3s
sudo chown -R k3s:k3s /var/log/k3s

# Install additional networking tools
sudo apt-get update
sudo apt-get install -y \
  bridge-utils \
  vlan \
  iptables \
  ipset \
  conntrack \
  socat \
  ethtool

# Configure iptables to use legacy mode for better compatibility
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Install crictl for container debugging
CRICTL_VERSION="v1.28.0"
curl -L "https://github.com/kubernetes-sigs/cri-tools/releases/download/${CRICTL_VERSION}/crictl-${CRICTL_VERSION}-linux-amd64.tar.gz" | sudo tar -C /usr/local/bin -xz

# Configure crictl
sudo tee /etc/crictl.yaml > /dev/null <<EOF
runtime-endpoint: unix:///run/containerd/containerd.sock
image-endpoint: unix:///run/containerd/containerd.sock
timeout: 2
debug: false
pull-image-on-create: false
EOF

# Install CNI plugins
CNI_VERSION="v1.3.0"
sudo mkdir -p /opt/cni/bin
curl -L "https://github.com/containernetworking/plugins/releases/download/${CNI_VERSION}/cni-plugins-linux-amd64-${CNI_VERSION}.tgz" | sudo tar -C /opt/cni/bin -xz

# Configure containerd for K3s
sudo tee /etc/containerd/config.toml > /dev/null <<EOF
version = 2
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
  runtime_type = "io.containerd.runc.v2"
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true
[plugins."io.containerd.grpc.v1.cri"]
  systemd_cgroup = true
[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
    endpoint = ["https://registry-1.docker.io"]
EOF

# Restart containerd with new configuration
sudo systemctl restart containerd

# Create systemd drop-in directory for k3s service customization
sudo mkdir -p /etc/systemd/system/k3s.service.d

# Create a helper script for K3s management
sudo tee /usr/local/bin/k3s-helper > /dev/null <<'EOF'
#!/bin/bash
# K3s helper script for common operations

case "$1" in
    status)
        systemctl status k3s
        ;;
    logs)
        journalctl -u k3s -f
        ;;
    restart)
        systemctl restart k3s
        ;;
    reset)
        echo "WARNING: This will reset the K3s cluster!"
        read -p "Are you sure? (yes/no): " confirm
        if [[ $confirm == "yes" ]]; then
            /usr/local/bin/k3s-uninstall.sh || true
            rm -rf /var/lib/rancher/k3s/*
            rm -rf /etc/rancher/k3s/*
            echo "K3s reset completed"
        fi
        ;;
    kubectl)
        shift
        kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml "$@"
        ;;
    *)
        echo "Usage: k3s-helper {status|logs|restart|reset|kubectl}"
        echo "  status  - Show K3s service status"
        echo "  logs    - Follow K3s logs"
        echo "  restart - Restart K3s service"
        echo "  reset   - Reset K3s cluster (destructive)"
        echo "  kubectl - Run kubectl with K3s config"
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/k3s-helper

# Create logrotate configuration for K3s
sudo tee /etc/logrotate.d/k3s > /dev/null <<EOF
/var/log/k3s/*.log {
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
EOF

# Install k9s for cluster management
K9S_VERSION="v0.27.4"
curl -sL "https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_Linux_amd64.tar.gz" | sudo tar xz -C /usr/local/bin k9s

# Install Longhorn prerequisites
sudo apt-get install -y \
  jq \
  util-linux \
  cryptsetup \
  lvm2 \
  nfs-common \
  open-iscsi

# Configure iSCSI
sudo systemctl enable --now iscsid
sudo systemctl enable --now multipathd

# Install GPU support for GPU nodes (will be configured later via cloud-init)
if lspci | grep -i nvidia > /dev/null; then
    echo "NVIDIA GPU detected, preparing for GPU support"
    # Basic preparation - full GPU setup happens in cloud-init
    sudo apt-get install -y \
        software-properties-common
    
    # Add NVIDIA repository
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
fi

# Create kubectl alias
echo 'alias k="kubectl"' | sudo tee -a /etc/bash.bashrc
echo 'alias kgp="kubectl get pods"' | sudo tee -a /etc/bash.bashrc
echo 'alias kgs="kubectl get services"' | sudo tee -a /etc/bash.bashrc
echo 'alias kgn="kubectl get nodes"' | sudo tee -a /etc/bash.bashrc

# Enable bash completion
sudo apt-get install -y bash-completion
echo 'source <(kubectl completion bash)' | sudo tee -a /etc/bash.bashrc
echo 'complete -F __start_kubectl k' | sudo tee -a /etc/bash.bashrc

echo "=== K3s preparation completed ==="