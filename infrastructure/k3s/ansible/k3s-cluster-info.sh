#!/bin/bash
# K3s Cluster Information and Access Guide

echo "🚀 K3s Homelab Cluster - Ready for Use!"
echo "=========================================="
echo

echo "📋 Cluster Details:"
echo "- API Server: https://192.168.11.71:6443"
echo "- Version: K3s v1.28.5+k3s1"
echo "- Kubeconfig: $HOME/.kube/k3s-cluster-config"
echo

echo "🔧 Connection Methods:"
echo

echo "Method 1 - Export kubeconfig (recommended):"
echo "  export KUBECONFIG=\$HOME/.kube/k3s-cluster-config"
echo "  kubectl get nodes"
echo

echo "Method 2 - Per-command kubeconfig:"
echo "  kubectl --kubeconfig=\$HOME/.kube/k3s-cluster-config get nodes"
echo

echo "Method 3 - Helper script:"
echo "  \$HOME/k3s-kubectl get nodes"
echo

echo "📊 Quick Status Check:"
export KUBECONFIG=$HOME/.kube/k3s-cluster-config
if kubectl get nodes >/dev/null 2>&1; then
    echo "✅ Cluster is accessible"
    echo "✅ $(kubectl get nodes --no-headers | wc -l) nodes ready"
    echo "✅ $(kubectl get pods -A --no-headers | grep Running | wc -l) pods running"
else
    echo "❌ Cannot connect to cluster"
fi
echo

echo "🏗️ Next Steps:"
echo "1. Deploy your applications: kubectl create deployment ..."
echo "2. Install additional services: helm install ..."
echo "3. Configure ingress controllers"
echo "4. Set up persistent storage"
echo

echo "📝 Useful Commands:"
echo "  kubectl get nodes -o wide"
echo "  kubectl get pods -A"
echo "  kubectl cluster-info"
echo "  kubectl top nodes"
echo

echo "🔗 Resources:"
echo "- Kubeconfig: $HOME/.kube/k3s-cluster-config"
echo "- Helper script: $HOME/k3s-kubectl"
echo "- Updated playbook: $(dirname $0)/playbooks/configure-k3s-fixed.yml"
echo