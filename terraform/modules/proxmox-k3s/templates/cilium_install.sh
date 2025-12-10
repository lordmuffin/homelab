#!/bin/bash

SERVER_IP=$1
echo "cilium_install.sh script is running for server: $SERVER_IP"

# Wait for K3s to be ready
echo "Waiting for K3s to be ready..."
timeout=300
counter=0
while [ $counter -lt $timeout ]; do
    if sudo kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get nodes > /dev/null 2>&1; then
        echo "K3s is ready"
        break
    fi
    echo "Waiting for K3s... ($counter/$timeout)"
    sleep 5
    counter=$((counter + 5))
done

if [ $counter -ge $timeout ]; then
    echo "Timeout waiting for K3s to be ready"
    exit 1
fi

# Install Cilium CLI
echo "Installing Cilium CLI..."
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
CLI_ARCH=amd64
if [ "$(uname -m)" = "aarch64" ]; then 
    CLI_ARCH=arm64
fi

# Download and install Cilium CLI
curl -L --fail --remote-name-all "https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}"

if sha256sum --check "cilium-linux-${CLI_ARCH}.tar.gz.sha256sum"; then
    sudo tar xzvfC "cilium-linux-${CLI_ARCH}.tar.gz" /usr/local/bin
    rm "cilium-linux-${CLI_ARCH}.tar.gz"{,.sha256sum}
    echo "Cilium CLI installed successfully"
else
    echo "Cilium CLI checksum verification failed"
    exit 1
fi

# Install Cilium CNI
echo "Installing Cilium CNI..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml cilium install \
    --version 1.15.4 \
    --namespace kube-system \
    --set k8sServiceHost="$SERVER_IP" \
    --set k8sServicePort=6443 \
    --set=ipam.operator.clusterPoolIPv4PodCIDRList="10.42.0.0/16" \
    --set=kubeProxyReplacement=true \
    --set=operator.replicas=1

if [ $? -eq 0 ]; then
    echo "Cilium installed successfully"
else
    echo "Cilium installation failed"
    exit 1
fi

# Wait for Cilium to be ready
echo "Waiting for Cilium to be ready..."
timeout=300
counter=0
while [ $counter -lt $timeout ]; do
    if sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml cilium status --wait > /dev/null 2>&1; then
        echo "Cilium is ready"
        break
    fi
    echo "Waiting for Cilium... ($counter/$timeout)"
    sleep 10
    counter=$((counter + 10))
done

if [ $counter -ge $timeout ]; then
    echo "Timeout waiting for Cilium to be ready"
    exit 1
fi

# Verify installation
echo "Verifying Cilium installation..."
sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml cilium status

echo "Cilium installation completed successfully!"