#!/bin/bash
set -e

# Proxmox OpenTofu User Setup Script
# This script creates a user, API token, and assigns permissions for OpenTofu/Terraform

USERNAME="opentofu"
REALM="pam"
TOKEN_NAME="opentofu"
ROLE="PVEAdmin"
PATH="/"

echo "=== Proxmox OpenTofu User Setup ==="
echo ""

# Check if user exists
if pveum user list | grep -q "${USERNAME}@${REALM}"; then
    echo "✓ User ${USERNAME}@${REALM} already exists"
else
    echo "Creating user ${USERNAME}@${REALM}..."
    pveum user add ${USERNAME}@${REALM} --comment "OpenTofu automation user"
    echo "✓ User created"
fi

# Create API token (this will regenerate if it exists)
echo ""
echo "Creating API token ${TOKEN_NAME}..."
TOKEN_OUTPUT=$(pveum user token add ${USERNAME}@${REALM} ${TOKEN_NAME} --privsep 0 --output-format=json 2>/dev/null || echo "")

if [ -z "$TOKEN_OUTPUT" ]; then
    echo "⚠ Token may already exist. To regenerate, run:"
    echo "  pveum user token remove ${USERNAME}@${REALM} ${TOKEN_NAME}"
    echo "  Then run this script again."
    echo ""
    echo "If the token exists, retrieve it from: /etc/pve/priv/token.cfg"
else
    FULL_TOKEN_ID="${USERNAME}@${REALM}!${TOKEN_NAME}"
    TOKEN_VALUE=$(echo $TOKEN_OUTPUT | grep -oP '"value"\s*:\s*"\K[^"]+')
    
    echo "✓ Token created successfully"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Add this to your terraform.tfvars:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "proxmox_api_token = \"${FULL_TOKEN_ID}=${TOKEN_VALUE}\""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Assign permissions
echo ""
echo "Assigning ${ROLE} role to ${USERNAME}@${REALM} on path ${PATH}..."
pveum acl modify ${PATH} --users ${USERNAME}@${REALM} --roles ${ROLE}
echo "✓ Permissions assigned"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The user ${USERNAME}@${REALM} now has ${ROLE} permissions on ${PATH}"
echo "You can now use OpenTofu/Terraform with this token."
