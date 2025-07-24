#!/bin/bash
# Interactive .env file creation script

set -e

echo "=== OneNote to Tandoor Migration - Environment Setup ==="
echo ""
echo "This script will help you create the .env file with your Azure credentials."
echo ""

# Function to prompt for input with validation
prompt_for_value() {
    local var_name=$1
    local prompt_text=$2
    local is_secret=${3:-false}
    local value=""
    
    while [[ -z "$value" ]]; do
        if [[ "$is_secret" == "true" ]]; then
            read -s -p "$prompt_text: " value
            echo ""
        else
            read -p "$prompt_text: " value
        fi
        
        if [[ -z "$value" ]]; then
            echo "Error: $var_name cannot be empty. Please try again."
        fi
    done
    
    echo "$value"
}

echo "Please have your Azure app registration details ready from the Azure portal."
echo "If you haven't created the app registration yet, follow the MANUAL_SETUP.md guide first."
echo ""

# Get Azure credentials
CLIENT_ID=$(prompt_for_value "CLIENT_ID" "Enter your Application (client) ID")
CLIENT_SECRET=$(prompt_for_value "CLIENT_SECRET" "Enter your Client Secret" true)
TENANT_ID=$(prompt_for_value "TENANT_ID" "Enter your Directory (tenant) ID")

echo ""
echo "Now let's configure your Tandoor instance..."
echo ""

# Get Tandoor configuration
TANDOOR_URL=$(prompt_for_value "TANDOOR_URL" "Enter your Tandoor URL (e.g., https://recipes.yourdomain.com)")
TANDOOR_TOKEN=$(prompt_for_value "TANDOOR_TOKEN" "Enter your Tandoor API token" true)

echo ""
echo "Microsoft Authentication for Tandoor (if your Tandoor is protected by Microsoft SSO):"
read -p "Does your Tandoor use Microsoft authentication middleware? (y/N): " USE_MSFT_AUTH
USE_MSFT_AUTH=${USE_MSFT_AUTH:-N}

if [[ "$USE_MSFT_AUTH" =~ ^[Yy]$ ]]; then
    TANDOOR_MSFT_USERNAME=$(prompt_for_value "TANDOOR_MSFT_USERNAME" "Enter your Microsoft username for Tandoor access")
    TANDOOR_MSFT_PASSWORD=$(prompt_for_value "TANDOOR_MSFT_PASSWORD" "Enter your Microsoft password for Tandoor access" true)
    TANDOOR_SKIP_MSFT_AUTH=false
else
    TANDOOR_MSFT_USERNAME=""
    TANDOOR_MSFT_PASSWORD=""
    TANDOOR_SKIP_MSFT_AUTH=true
fi

echo ""
echo "Optional settings (press Enter for defaults)..."
echo ""

# Optional settings with defaults
read -p "OneNote notebook name [Recipes]: " NOTEBOOK_NAME
NOTEBOOK_NAME=${NOTEBOOK_NAME:-Recipes}

read -p "OneNote page name filter (e.g., 'recipes' to only process pages with 'recipes' in the title) [leave empty for auto-detection]: " PAGE_NAME_FILTER
PAGE_NAME_FILTER=${PAGE_NAME_FILTER:-}

read -p "Batch size [10]: " BATCH_SIZE
BATCH_SIZE=${BATCH_SIZE:-10}

read -p "Skip duplicates [true]: " SKIP_DUPLICATES
SKIP_DUPLICATES=${SKIP_DUPLICATES:-true}

read -p "Dry run mode [false]: " DRY_RUN
DRY_RUN=${DRY_RUN:-false}

read -p "Log level [INFO]: " LOG_LEVEL
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Create .env file
cat > .env << EOF
# Azure App Registration Credentials
MICROSOFT_CLIENT_ID=$CLIENT_ID
MICROSOFT_CLIENT_SECRET=$CLIENT_SECRET
MICROSOFT_TENANT_ID=$TENANT_ID

# Tandoor Configuration
TANDOOR_URL=$TANDOOR_URL
TANDOOR_API_TOKEN=$TANDOOR_TOKEN

# Microsoft Authentication for Tandoor (if protected by middleware)
TANDOOR_MSFT_USERNAME=$TANDOOR_MSFT_USERNAME
TANDOOR_MSFT_PASSWORD=$TANDOOR_MSFT_PASSWORD
TANDOOR_SKIP_MSFT_AUTH=$TANDOOR_SKIP_MSFT_AUTH

# Migration Settings
ONENOTE_NOTEBOOK_NAME=$NOTEBOOK_NAME
ONENOTE_PAGE_NAME_FILTER=$PAGE_NAME_FILTER
BATCH_SIZE=$BATCH_SIZE
SKIP_DUPLICATES=$SKIP_DUPLICATES
DRY_RUN=$DRY_RUN

# Logging
LOG_LEVEL=$LOG_LEVEL
LOG_CONSOLE=true
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "✅ .env file created successfully!"
echo ""
echo "Next steps:"
echo "1. Verify your .env file contains the correct values"
echo "2. Make sure you granted admin consent for the app permissions in Azure"
echo "3. Test the migration with: python migrate.py --dry-run"
echo ""
echo "Your .env file has been created with your credentials."
echo "Keep this file secure and do not commit it to version control!"