#!/bin/bash
# Test script for OneNote to Tandoor migration

set -e

echo "=== OneNote to Tandoor Migration Test ==="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it first."
    echo "You can copy from .env.example and update the values."
    exit 1
fi

# Source environment variables
source .env

# Check required environment variables
required_vars=(
    "MICROSOFT_CLIENT_ID"
    "MICROSOFT_CLIENT_SECRET" 
    "MICROSOFT_TENANT_ID"
    "TANDOOR_URL"
    "TANDOOR_API_TOKEN"
)

echo "Checking required environment variables..."
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env file"
        exit 1
    else
        echo "✓ $var is set"
    fi
done

echo ""
echo "Running migration test (dry run mode)..."

# Run dry run first
python migrate.py --dry-run --verbose

echo ""
echo "Dry run completed successfully!"
echo ""

# Ask user if they want to run actual migration
read -p "Do you want to run the actual migration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running actual migration..."
    python migrate.py --verbose
    echo ""
    echo "Migration completed!"
    echo ""
    echo "Check the following files for results:"
    echo "  - migration.log (detailed logs)"
    echo "  - migration_success.json (successful uploads)"
    echo "  - migration_errors.json (any errors)"
else
    echo "Actual migration skipped."
fi

echo ""
echo "Test completed!"