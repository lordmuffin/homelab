#!/bin/bash

# Setup script for K3s Ansible environment
# This script installs all required dependencies

set -e

echo "🔧 Setting up Ansible environment for K3s deployment..."

# Check if we're in the right directory
if [[ ! -f "ansible.cfg" ]]; then
    echo "❌ Error: ansible.cfg not found. Please run this script from the ansible directory."
    exit 1
fi

# Install Python requirements
if [[ -f "requirements.txt" ]]; then
    echo "📦 Installing Python requirements..."
    pip3 install -r requirements.txt --user
else
    echo "⚠️  Warning: requirements.txt not found"
fi

# Install Ansible collections
if [[ -f "requirements.yml" ]]; then
    echo "📚 Installing Ansible collections..."
    ansible-galaxy collection install -r requirements.yml
else
    echo "⚠️  Warning: requirements.yml not found"
fi

# Make scripts executable
echo "🔨 Making scripts executable..."
chmod +x *.sh 2>/dev/null || true

echo ""
echo "✅ Ansible environment setup complete!"
echo ""
echo "📋 Available commands:"
echo "   • Run playbook: ansible-playbook playbooks/configure-k3s.yml"
echo "   • Or use helper: ./run-ansible.sh playbooks/configure-k3s.yml"
echo "   • Test connection: ansible all -m ping"
echo ""
echo "🚀 You're ready to deploy K3s!"