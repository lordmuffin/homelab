# Packer Proxmox Setup Guide

## Authentication Error Fix

The error `501 no such file '/access/ticket'` indicates Proxmox API authentication issues. Here are the solutions:

## Option 1: API Token Authentication (Recommended)

### Step 1: Create API Token in Proxmox

1. **Log into Proxmox Web UI**
2. **Navigate to Datacenter → Permissions → API Tokens**
3. **Click "Add" and create a new token:**
   ```
   User: root@pam
   Token ID: packer
   Privilege Separation: Unchecked (to inherit user permissions)
   ```
4. **Copy the generated token** (you'll only see it once)

### Step 2: Set Environment Variables

```bash
# Create environment file for Packer
cat > ~/.packer_env <<'EOF'
export PROXMOX_URL="https://your-proxmox-ip:8006/api2/json"
export PROXMOX_USERNAME="root@pam!packer"
export PROXMOX_TOKEN="your-generated-token"
export PROXMOX_NODE="your-node-name"
EOF

# Load environment variables
source ~/.packer_env
```

### Step 3: Test Authentication

```bash
# Test API access with curl
curl -k -H "Authorization: PVEAPIToken=root@pam!packer=your-token" \
  https://your-proxmox-ip:8006/api2/json/version

# Should return Proxmox version information
```

## Option 2: Password Authentication (Alternative)

If you prefer password authentication, modify the Packer configuration:

```bash
# Edit the Packer file to use password instead of token
sed -i 's/token.*= var.proxmox_token/password = var.proxmox_password/' \
  infrastructure/proxmox/packer/ubuntu-k3s.pkr.hcl

# Set environment variables
export PROXMOX_URL="https://your-proxmox-ip:8006/api2/json"
export PROXMOX_USERNAME="root@pam"
export PROXMOX_PASSWORD="your-password"
export PROXMOX_NODE="your-node-name"
```

## Step 4: Verify Proxmox Settings

### Check Node Name
```bash
# List available nodes
curl -k -H "Authorization: PVEAPIToken=root@pam!packer=your-token" \
  https://your-proxmox-ip:8006/api2/json/nodes

# Update PROXMOX_NODE environment variable with correct node name
```

### Check Storage Pools
```bash
# List storage pools
curl -k -H "Authorization: PVEAPIToken=root@pam!packer=your-token" \
  https://your-proxmox-ip:8006/api2/json/nodes/your-node/storage
```

## Step 5: Update Packer Configuration

Create a `packer.vars.hcl` file with your specific settings:

```hcl
# infrastructure/proxmox/packer/packer.vars.hcl
proxmox_api_url = "https://your-proxmox-ip:8006/api2/json"
proxmox_username = "root@pam!packer"  # For token auth
proxmox_node = "your-actual-node-name"
```

## Step 6: Run Packer Build

```bash
# Navigate to Packer directory
cd infrastructure/proxmox/packer

# Load environment variables
source ~/.packer_env

# Validate configuration
packer validate -var-file="packer.vars.hcl" ubuntu-k3s.pkr.hcl

# Build template
packer build -var-file="packer.vars.hcl" ubuntu-k3s.pkr.hcl
```

## Common Issues and Solutions

### Issue: Certificate Verification
```bash
# If you get SSL certificate errors, ensure insecure_skip_tls_verify = true
# Or add your Proxmox certificate to system trust store
```

### Issue: Wrong Node Name
```bash
# Get correct node name
pvesh get /nodes --output-format json | jq '.[].node'
```

### Issue: Storage Pool Not Found
```bash
# Check available storage
pvesh get /nodes/your-node/storage --output-format json

# Update storage_pool variables in Packer file to match available storage
```

### Issue: Network Bridge Not Found
```bash
# Check available bridges
pvesh get /nodes/your-node/network --output-format json | jq '.[] | select(.type=="bridge") | .iface'
```

## Troubleshooting Commands

```bash
# Enable Packer debug logging
export PACKER_LOG=1
export PACKER_LOG_PATH="packer.log"

# Run build with debug
packer build -debug ubuntu-k3s.pkr.hcl

# Check Proxmox task log
tail -f /var/log/pve/tasks/active
```

## Quick Fix Summary

1. **Create API token** in Proxmox with proper permissions
2. **Set environment variables** with correct URL, token, and node name
3. **Update storage pools** and network bridge names in Packer config
4. **Run with proper authentication**

The key is ensuring your API authentication is correct and all referenced Proxmox resources (node, storage, network) actually exist with the exact names specified.