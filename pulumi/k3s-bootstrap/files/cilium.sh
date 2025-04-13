#!/bin/sh

echo "cilium.sh script is running!!!"
exec sudo -u root /bin/sh - << eof

# Install k3sup
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

sudo mkdir /usr/local/bin
sudo kubectl create namespace cilium

CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
CLI_ARCH=amd64
if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /usr/local/bin
rm cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}


API_SERVER_IP="192.168.10.20"
API_SERVER_PORT="6443"
sudo cilium install --version 1.15.5 --namespace cilium --set=ipam.operator.clusterPoolIPv4PodCIDRList="10.42.0.0/16" --set kubeProxyReplacement=strict --set k8sServiceHost=${API_SERVER_IP} --set k8sServicePort=${API_SERVER_PORT}
sudo cilium hubble enable --namespace cilium
eof