#!/bin/bash
set -e

# Get 1Password values
ADMIN_PASSWORD=$(op item get "kasm-admin-creds-1password" --vault "HomeLab" --fields password)
DB_PASSWORD=$(op item get "kasm-db-postgres-creds-1password" --vault "HomeLab" --fields password)
ENCRYPTION_KEY=$(op item get "kasm-encryption-key-1password" --vault "HomeLab" --fields password)

# Create the secret with both kebab-case and camelCase keys
kubectl create secret generic kasm-secrets -n kasm \
  --from-literal=admin-password="$ADMIN_PASSWORD" \
  --from-literal=adminPassword="$ADMIN_PASSWORD" \
  --from-literal=db-password="$DB_PASSWORD" \
  --from-literal=dbPassword="$DB_PASSWORD" \
  --from-literal=redis-password="$DB_PASSWORD" \
  --from-literal=redisPassword="$DB_PASSWORD" \
  --from-literal=encryption-secret="$ENCRYPTION_KEY" \
  --from-literal=encryptionSecret="$ENCRYPTION_KEY" \
  --from-literal=manager-token="$DB_PASSWORD" \
  --from-literal=managerToken="$DB_PASSWORD" \
  --from-literal=service-token="$DB_PASSWORD" \
  --from-literal=serviceToken="$DB_PASSWORD" \
  --from-literal=user-password="$DB_PASSWORD" \
  --from-literal=userPassword="$DB_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "KASM secrets created successfully!"