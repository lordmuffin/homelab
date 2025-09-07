#!/bin/bash
#
# K3s Deploy + Test Integration Example
# ====================================
#
# This script demonstrates how to use the original k3s-deploy.py
# for deployment and the new k3s-testing.py for comprehensive testing.
#

set -e

ENVIRONMENT="${1:-production}"
KUBECONFIG_PATH="$HOME/.kube/k3s-cluster-config"

echo "🚀 K3s Deploy + Test Integration"
echo "================================="
echo "Environment: $ENVIRONMENT"
echo "Kubeconfig: $KUBECONFIG_PATH"
echo ""

# Step 1: Deploy K3s cluster using original script
echo "📦 Step 1: Deploying K3s cluster..."
echo "-----------------------------------"
cd /home/lordmuffin/Claude/Git/homelab/infrastructure

python3 k3s-deploy.py deploy \
    --environment "$ENVIRONMENT" \
    --auto-approve \
    --verbose

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed!"
    exit 1
fi

echo "✅ K3s deployment completed successfully"
echo ""

# Step 2: Wait for cluster to stabilize
echo "⏳ Step 2: Waiting for cluster to stabilize..."
echo "----------------------------------------------"
sleep 30

# Check if kubeconfig exists
if [ -f "$KUBECONFIG_PATH" ]; then
    export KUBECONFIG="$KUBECONFIG_PATH"
    echo "✅ Found kubeconfig: $KUBECONFIG_PATH"
else
    echo "⚠️ Kubeconfig not found at expected location, using default"
fi

# Step 3: Run comprehensive tests
echo "🧪 Step 3: Running comprehensive tests..."
echo "----------------------------------------"

python3 k3s-testing.py \
    --test-focus "storage,network" \
    --iterations 3 \
    --kubeconfig "$KUBECONFIG_PATH" \
    --output-file "/tmp/k3s-test-results-$(date +%Y%m%d-%H%M%S).json" \
    --verbose

TEST_EXIT_CODE=$?

echo ""
echo "📊 Integration Results:"
echo "======================"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed! Cluster is ready for production."
    echo ""
    echo "🎯 Next steps:"
    echo "  • Deploy your applications"
    echo "  • Set up monitoring and alerting"
    echo "  • Configure backups"
    echo ""
    echo "🔧 Useful commands:"
    echo "  export KUBECONFIG=$KUBECONFIG_PATH"
    echo "  kubectl get nodes"
    echo "  kubectl get pods --all-namespaces"
else
    echo "❌ Some tests failed. Please review the test results."
    echo ""
    echo "🔍 Troubleshooting:"
    echo "  • Check cluster health: kubectl get nodes"
    echo "  • Review test logs: /tmp/k3s-testing.log"
    echo "  • Re-run specific tests: python3 k3s-testing.py --test-focus <focus>"
    exit $TEST_EXIT_CODE
fi