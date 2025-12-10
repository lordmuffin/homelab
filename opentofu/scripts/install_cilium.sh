#!/bin/bash
set -e

# Helper script to install Cilium on the Talos cluster
# Usage: ./install_cilium.sh [KUBECONFIG_PATH]

KUBECONFIG_PATH=${1:-"./kubeconfig"}

if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "Error: Kubeconfig file not found at $KUBECONFIG_PATH"
    echo "Usage: $0 [path_to_kubeconfig]"
    exit 1
fi

echo "Installing Cilium CLI if not present..."
if ! command -v cilium &> /dev/null; then
    CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/master/stable.txt)
    CLI_ARCH=amd64
    if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
    curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
    sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
    tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /tmp
    rm cilium-linux-${CLI_ARCH}.tar.gz cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
    # Depending on permissions, might need sudo, or just use locally
    chmod +x /tmp/cilium
    sudo mv /tmp/cilium /usr/local/bin/cilium || echo "Please move /tmp/cilium to your PATH"
fi

echo "Installing Cilium into the cluster..."
# Using 'cilium install' is the easiest way.
# It detects the environment and configures defaults.
# For Talos, we might need specific flags if strict mode is on,
# but generally standard install works if CNI is 'none'.

export KUBECONFIG=$KUBECONFIG_PATH

/usr/local/bin/cilium install \
    --version v1.16.1 \
    --set ipam.mode=kubernetes \
    --set kubeProxyReplacement=true \
    --set securityContext.capabilities.ciliumAgent="{CHOWN,KILL,NET_ADMIN,NET_RAW,IPC_LOCK,SYS_ADMIN,SYS_RESOURCE,DAC_OVERRIDE,FOWNER,SETGID,SETUID}" \
    --set securityContext.capabilities.cleanCiliumState="{NET_ADMIN,SYS_ADMIN,SYS_RESOURCE}" \
    --set cgroup.autoMount.enabled=false \
    --set cgroup.hostRoot=/sys/fs/cgroup

echo "Cilium installation triggered. Check status with 'cilium status --wait'."
