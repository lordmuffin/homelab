#!/bin/bash
# Azure App Registration Setup Script for OneNote to Tandoor Migration

set -e

echo "=== Azure App Registration Setup for OneNote Migration ==="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed."
    echo "Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo "Please log in to Azure CLI first:"
    echo "az login"
    exit 1
fi

# App registration details
APP_NAME="OneNote-Tandoor-Migration"
APP_DESCRIPTION="Application for migrating recipes from OneNote to Tandoor"

echo "Creating Azure App Registration: $APP_NAME"

# Create the app registration
APP_INFO=$(az ad app create \
    --display-name "$APP_NAME" \
    --available-to-other-tenants false \
    --reply-urls "http://localhost:8400" \
    --query '{appId: appId, objectId: id}' \
    --output json)

APP_ID=$(echo $APP_INFO | jq -r '.appId')
OBJECT_ID=$(echo $APP_INFO | jq -r '.objectId')

echo "App created with Application ID: $APP_ID"

# Create a client secret
SECRET_INFO=$(az ad app credential reset \
    --id $APP_ID \
    --display-name "Migration Tool Secret" \
    --years 2 \
    --query '{password: password}' \
    --output json)

CLIENT_SECRET=$(echo $SECRET_INFO | jq -r '.password')

# Get tenant ID
TENANT_ID=$(az account show --query tenantId --output tsv)

# Add Microsoft Graph API permissions
echo "Adding Microsoft Graph API permissions..."

# Add required permissions for OneNote access (delegated permissions)
az ad app permission add \
    --id $APP_ID \
    --api 00000003-0000-0000-c000-000000000000 \
    --api-permissions \
        3aeca27b-ee3a-4c2b-8ded-80376e2134a4=Scope \
        dfabfbf4-a4e9-4c80-a20c-bc55b0c9a91a=Scope

echo "Permissions added. Please grant admin consent in the Azure portal."

# Create .env file
cat > .env << EOF
# Azure App Registration Credentials
MICROSOFT_CLIENT_ID=$APP_ID
MICROSOFT_CLIENT_SECRET=$CLIENT_SECRET
MICROSOFT_TENANT_ID=$TENANT_ID

# Tandoor Configuration (please update these)
TANDOOR_URL=https://your-tandoor-instance.com
TANDOOR_API_TOKEN=your_tandoor_api_token_here

# Migration Settings
ONENOTE_NOTEBOOK_NAME=Recipes
BATCH_SIZE=10
SKIP_DUPLICATES=true
DRY_RUN=false

# Logging
LOG_LEVEL=INFO
LOG_CONSOLE=true
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Azure App Registration Details:"
echo "  Application ID: $APP_ID"
echo "  Tenant ID: $TENANT_ID"
echo "  Client Secret: [HIDDEN - check .env file]"
echo ""
echo "Next steps:"
echo "1. Update TANDOOR_URL and TANDOOR_API_TOKEN in the .env file"
echo "2. Grant admin consent for the app permissions in Azure portal:"
echo "   https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/$APP_ID"
echo "3. Run the migration tool: python migrate.py"
echo ""
echo "Required Microsoft Graph permissions:"
echo "  - Notes.Read (Read user OneNote notebooks)"
echo "  - Notes.Read.All (Read all OneNote notebooks)"
echo ""
echo "For more information, visit:"
echo "https://docs.microsoft.com/en-us/graph/permissions-reference#notes-permissions"