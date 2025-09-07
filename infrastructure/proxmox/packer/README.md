# Ubuntu K3s Packer Templates - Multi-Node Configuration

This directory contains Packer configurations to build Ubuntu 22.04 templates optimized for K3s on multiple Proxmox nodes.

## 🏗️ Architecture

Each Proxmox node gets its own template to avoid cross-node dependencies and network issues:
- **PVE2** (192.168.1.14) → Template ID 9000
- **PVE-NAS-01** (192.168.1.15) → Template ID 9001

Template VM IDs are now configurable and can be specified during build time for consistent infrastructure.

## 📋 Prerequisites

1. **Proxmox API Tokens**: Create API tokens for each node
   - Go to Datacenter → Permissions → API Tokens
   - Create token: `root@pam!packer` with full privileges
   - Copy the token secret (shown only once!)

2. **Network Access**: Ensure your machine can reach all Proxmox nodes on port 8006

3. **Storage**: Ensure `local` storage has sufficient space for ISO and template

## ⚙️ Configuration

### Step 1: Create Environment Files

Copy the example files for each node you want to build templates on:

```bash
# For PVE node
cp .env.pve.example .env.pve

# For PVE2 node  
cp .env.pve2.example .env.pve2

# For PVE-NAS-01 node
cp .env.pve-nas-01.example .env.pve-nas-01
```

### Step 2: Configure Each Environment File

Edit each `.env.*` file with your specific details:

#### `.env.pve` Configuration:
```bash
# Proxmox API URL (include https:// and :8006)
PROXMOX_URL=https://192.168.1.12:8006/api2/json

# Proxmox Node Name
PROXMOX_NODE=pve

# Proxmox Authentication
PROXMOX_USERNAME=root@pam!packer
PROXMOX_TOKEN=YOUR_PVE_TOKEN_HERE

# Template Configuration
TEMPLATE_ID=9000
TEMPLATE_NAME=ubuntu-k3s-homelab-template-pve
```

#### `.env.pve2` Configuration:
```bash
# Proxmox API URL (include https:// and :8006)
PROXMOX_URL=https://192.168.1.14:8006/api2/json

# Proxmox Node Name
PROXMOX_NODE=pve2

# Proxmox Authentication
PROXMOX_USERNAME=root@pam!packer
PROXMOX_TOKEN=0dd55215-4ce9-41e6-8529-c181e17765bc

# Template Configuration
TEMPLATE_ID=9001
TEMPLATE_NAME=ubuntu-k3s-homelab-template-pve2
```

#### `.env.pve-nas-01` Configuration:
```bash
# Proxmox API URL (include https:// and :8006)
PROXMOX_URL=https://192.168.1.15:8006/api2/json

# Proxmox Node Name
PROXMOX_NODE=pve-nas-01

# Proxmox Authentication
PROXMOX_USERNAME=root@pam!packer
PROXMOX_TOKEN=cd19164c-10f4-4c57-9eed-8644181d09dc

# Template Configuration
TEMPLATE_ID=9002
TEMPLATE_NAME=ubuntu-k3s-homelab-template-nas
```

## 🚀 Building Templates

### Option 1: Build All Templates (Recommended)

Use the automated script to build templates on all configured nodes:

```bash
./build-all-templates.sh
```

This script will:
- Check each environment file
- Test connectivity to each Proxmox node
- Build templates in parallel where possible
- Provide detailed success/failure reporting

### Option 2: Build Individual Templates

Build templates one node at a time:

```bash
# Build on PVE node
source .env.pve && packer build ubuntu-k3s.pkr.hcl

# Build on PVE2 node
source .env.pve2 && packer build ubuntu-k3s.pkr.hcl

# Build on PVE-NAS-01 node
source .env.pve-nas-01 && packer build ubuntu-k3s.pkr.hcl
```

### Option 3: Build Specific Variables

Override environment variables for one-off builds:

```bash
packer build \
  -var "proxmox_api_url=https://192.168.1.14:8006/api2/json" \
  -var "proxmox_username=root@pam!packer" \
  -var "proxmox_token=0dd55215-4ce9-41e6-8529-c181e17765bc" \
  -var "proxmox_node=pve2" \
  -var "template_id=9001" \
  ubuntu-k3s.pkr.hcl
```

## 🔧 Template Features

The Ubuntu K3s template includes:
- **Ubuntu 22.04 LTS** (latest stable)
- **K3s Prerequisites**: containerd, runc, CNI plugins
- **Kubernetes Tools**: kubectl, helm, k9s, crictl
- **System Optimizations**: kernel parameters, swap disabled
- **Cloud-init Ready**: for dynamic configuration
- **Security**: minimal packages, security updates

## 📊 Template IDs

Template VM IDs are now configurable via the `template_vm_id` variable or the build script configuration:

| Node | Default Template ID | Template Name |
|------|---------------------|---------------|
| pve2 | 9000 | ubuntu-k3s-homelab-template-pve2 |
| pve-nas-01 | 9001 | ubuntu-k3s-homelab-template-nas |

### Custom Template IDs

You can specify custom template VM IDs in several ways:

1. **Via build script** (edit `build-all-templates.sh`):
   ```bash
   declare -A NODE_CONFIGS=(
       ["pve2"]="9000"
       ["pve-nas-01"]="9001"
   )
   ```

2. **Via Packer variable**:
   ```bash
   packer build -var template_vm_id=9050 ubuntu-k3s.pkr.hcl
   ```

3. **Via environment variable**:
   ```bash
   export PKR_VAR_template_vm_id=9050
   packer build ubuntu-k3s.pkr.hcl
   ```

## 🔍 Troubleshooting

### Connection Issues
```bash
# Test API connectivity
curl -k "https://192.168.1.14:8006/api2/json/version"

# Test with authentication
curl -k "https://192.168.1.14:8006/api2/json/version" \
  -H "Authorization: PVEAPIToken=root@pam!packer:YOUR_TOKEN"
```

### Common Issues

1. **"write tcp: use of closed network connection"**
   - Network timeout during ISO upload
   - Try building during off-peak hours
   - Check firewall settings

2. **"username must be specified"**
   - Environment variables not loaded
   - Run `source .env.nodeX` before packer build

3. **"template already exists"**
   - Template with same ID exists
   - Change TEMPLATE_ID in .env file
   - Or remove existing template in Proxmox

4. **"insufficient privileges"**
   - API token lacks permissions
   - Recreate token with full privileges
   - Or use root password authentication

## 🔗 Integration

After building templates, update your Terraform configuration to use the template IDs:

```hcl
# Option 1: Use template ID directly (recommended)
vm_template_id = 9000  # For pve2 node

# Option 2: Use template name (requires discovery)
vm_template_name = "ubuntu-k3s-homelab-template-pve2"

# Example terraform.tfvars for multiple node deployment:
# For pve2 node
vm_template_id = 9000

# For pve-nas-01 node  
vm_template_id = 9001
```

## 📁 File Structure

```
packer/
├── ubuntu-k3s.pkr.hcl           # Main Packer configuration
├── .env.pve.example             # PVE environment template
├── .env.pve2.example            # PVE2 environment template
├── .env.pve-nas-01.example      # NAS environment template
├── build-all-templates.sh       # Automated build script
├── README.md                    # This documentation
└── scripts/                     # Provisioning scripts
    └── install-k3s-deps.sh      # K3s dependencies installer
```

## 🛡️ Security Notes

- **Never commit `.env.*` files** - they contain sensitive tokens
- Use API tokens instead of passwords when possible
- Limit token permissions to necessary scopes
- Rotate tokens periodically
- Use HTTPS connections only (`insecure = true` is for self-signed certs)

## 💡 Tips

- Build templates during maintenance windows (lower network load)
- Monitor Proxmox logs during builds: `/var/log/pveproxy/access.log`
- Templates are reusable - build once, deploy many VMs
- Consider automating builds with CI/CD pipelines