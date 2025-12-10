#!/bin/bash

# Actual Budget File-Based Data Backup Script
# This script creates a comprehensive backup of file-based Actual Budget data

set -euo pipefail

# Configuration
NAMESPACE="services"
POD_NAME="actual-migration-backup"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="actual-data-backup-${BACKUP_DATE}.tar.gz"
LOCAL_BACKUP_DIR="./actual-backups"

# Logging functions
log_info() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO: $*" >&2
}

log_error() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2
}

# Create local backup directory
log_info "Creating local backup directory: $LOCAL_BACKUP_DIR"
mkdir -p "$LOCAL_BACKUP_DIR"

# Deploy backup pod
log_info "Deploying backup pod..."
kubectl apply -f migration-backup-pod.yaml

# Wait for pod to be ready
log_info "Waiting for backup pod to be ready..."
kubectl wait --for=condition=Ready pod/$POD_NAME -n $NAMESPACE --timeout=300s

if ! kubectl get pod $POD_NAME -n $NAMESPACE >/dev/null 2>&1; then
    log_error "Backup pod failed to start"
    exit 1
fi

# Install required tools in the pod
log_info "Installing backup tools in pod..."
kubectl exec -n $NAMESPACE $POD_NAME -- sh -c "
    apk add --no-cache tar gzip findutils file
"

# Examine the data structure
log_info "Examining current data structure..."
kubectl exec -n $NAMESPACE $POD_NAME -- sh -c "
    echo '=== Data Directory Structure ==='
    find /data -type f -name '*.sqlite*' -o -name '*.db' -o -name '*.json' | head -20
    echo ''
    echo '=== Directory Sizes ==='
    du -sh /data/* 2>/dev/null || echo 'No subdirectories found'
    echo ''
    echo '=== File Types ==='
    find /data -type f | head -20 | xargs file 2>/dev/null || echo 'Could not determine file types'
"

# Create the backup archive
log_info "Creating backup archive..."
kubectl exec -n $NAMESPACE $POD_NAME -- sh -c "
    cd /backup
    echo 'Creating backup of Actual Budget data...'
    tar -czf $BACKUP_FILE /data/ --exclude='lost+found' 2>/dev/null || true
    
    # Verify the backup
    if [ -f $BACKUP_FILE ]; then
        echo 'Backup created successfully:'
        ls -lh $BACKUP_FILE
        tar -tzf $BACKUP_FILE | head -10
    else
        echo 'ERROR: Backup file not created'
        exit 1
    fi
"

# Copy backup to local machine
log_info "Copying backup to local machine..."
kubectl cp $NAMESPACE/$POD_NAME:/backup/$BACKUP_FILE "$LOCAL_BACKUP_DIR/$BACKUP_FILE"

# Verify local backup
if [ -f "$LOCAL_BACKUP_DIR/$BACKUP_FILE" ]; then
    log_info "✅ Backup completed successfully!"
    log_info "Backup file: $LOCAL_BACKUP_DIR/$BACKUP_FILE"
    log_info "Backup size: $(du -sh "$LOCAL_BACKUP_DIR/$BACKUP_FILE" | cut -f1)"
    
    # Extract a listing for verification
    log_info "Backup contents (first 20 files):"
    tar -tzf "$LOCAL_BACKUP_DIR/$BACKUP_FILE" | head -20
else
    log_error "Failed to copy backup file to local machine"
    exit 1
fi

# Create a detailed inventory
log_info "Creating detailed inventory..."
kubectl exec -n $NAMESPACE $POD_NAME -- sh -c "
    find /data -type f -exec ls -lah {} \; > /backup/file-inventory.txt
    find /data -name '*.sqlite*' -o -name '*.db' -exec sqlite3 {} '.tables' \; > /backup/database-tables.txt 2>/dev/null || echo 'No SQLite databases found' > /backup/database-tables.txt
"

# Copy inventory files
kubectl cp $NAMESPACE/$POD_NAME:/backup/file-inventory.txt "$LOCAL_BACKUP_DIR/file-inventory-${BACKUP_DATE}.txt"
kubectl cp $NAMESPACE/$POD_NAME:/backup/database-tables.txt "$LOCAL_BACKUP_DIR/database-tables-${BACKUP_DATE}.txt"

# Cleanup
log_info "Cleaning up backup pod..."
kubectl delete pod $POD_NAME -n $NAMESPACE --ignore-not-found=true

log_info "🎉 Backup process completed!"
log_info "Files created:"
log_info "  - Main backup: $LOCAL_BACKUP_DIR/$BACKUP_FILE"
log_info "  - File inventory: $LOCAL_BACKUP_DIR/file-inventory-${BACKUP_DATE}.txt"
log_info "  - Database info: $LOCAL_BACKUP_DIR/database-tables-${BACKUP_DATE}.txt"

echo ""
echo "Next steps:"
echo "1. Review the backup contents and inventory files"
echo "2. Deploy the PostgreSQL database: kubectl apply -f apps/services/finances/actual/base/"
echo "3. Run the migration script: ./actual-migration-script.sh"