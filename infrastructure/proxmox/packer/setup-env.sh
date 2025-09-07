#!/bin/bash
# Proxmox Packer Environment Setup Script

echo "🔧 Setting up Proxmox Packer Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file with your Proxmox credentials"
    echo ""
    echo "Required steps:"
    echo "1. Edit .env file with your Proxmox server details"
    echo "2. Create API token in Proxmox (Datacenter -> Permissions -> API Tokens)"
    echo "3. Run: source .env"
    echo "4. Run: packer build ubuntu-k3s.pkr.hcl"
    exit 1
fi

# Load environment variables
source .env

# Validate required variables
missing_vars=()
[ -z "$PROXMOX_URL" ] && missing_vars+=("PROXMOX_URL")
[ -z "$PROXMOX_USERNAME" ] && missing_vars+=("PROXMOX_USERNAME")

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '%s\n' "${missing_vars[@]}"
    echo "Please edit your .env file and set these variables"
    exit 1
fi

# Test connection
echo "🔍 Testing Proxmox connection..."
if curl -k -s -f "$PROXMOX_URL" > /dev/null; then
    echo "✅ Proxmox server is reachable"
else
    echo "❌ Cannot connect to Proxmox server at $PROXMOX_URL"
    exit 1
fi

echo "🚀 Environment setup complete!"
echo "You can now run: packer build ubuntu-k3s.pkr.hcl"