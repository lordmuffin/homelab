#!/bin/bash
set -e

echo "Creating 1Password item for KASM All-in-one Secrets..."

# Generate secure random passwords
ADMIN_PASSWORD=$(openssl rand -base64 16)
DB_PASSWORD=$(openssl rand -base64 16)
REDIS_PASSWORD=$(openssl rand -base64 16)
ENCRYPTION_SECRET=$(openssl rand -base64 32)
MANAGER_TOKEN=$(openssl rand -base64 16)
SERVICE_TOKEN=$(openssl rand -base64 16)
USER_PASSWORD=$(openssl rand -base64 16)

# Create the 1Password item with all required fields
op item create --vault HomeLab \
  --category "LOGIN" \
  --title "KASM All-in-one Secrets" \
  --url "https://kasm.lab.apj.dev" \
  "admin-password=${ADMIN_PASSWORD}" \
  "db-password=${DB_PASSWORD}" \
  "redis-password=${REDIS_PASSWORD}" \
  "encryption-secret=${ENCRYPTION_SECRET}" \
  "manager-token=${MANAGER_TOKEN}" \
  "service-token=${SERVICE_TOKEN}" \
  "user-password=${USER_PASSWORD}"

echo "✓ Created 1Password item 'KASM All-in-one Secrets' in HomeLab vault"
echo ""
echo "Admin credentials:"
echo "Username: admin"
echo "Password: ${ADMIN_PASSWORD}"
echo ""
echo "To access KASM, visit: https://kasm.lab.apj.dev"