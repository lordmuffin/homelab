#!/bin/bash
# Grill Stats Kustomize Upgrade Script
# Syncs comprehensive kustomize configuration from source to homelab

set -euo pipefail

# Configuration
SOURCE_DIR="/home/lordmuffin/Claude/Git/grill-stats/kustomize"
TARGET_DIR="/home/lordmuffin/Claude/Git/homelab/apps/services/grill-stats"
BACKUP_DIR="${TARGET_DIR}.backup.$(date +%Y%m%d-%H%M%S)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-flight checks
preflight_checks() {
    log "Running pre-flight checks..."
    
    if [[ ! -d "$SOURCE_DIR" ]]; then
        error "Source directory not found: $SOURCE_DIR"
        exit 1
    fi
    
    if [[ ! -d "$TARGET_DIR" ]]; then
        error "Target directory not found: $TARGET_DIR"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git -C "$TARGET_DIR" status &> /dev/null; then
        error "Target directory is not in a git repository"
        exit 1
    fi
    
    log "Pre-flight checks passed"
}

# Create backup
create_backup() {
    log "Creating backup at $BACKUP_DIR..."
    cp -r "$TARGET_DIR" "$BACKUP_DIR"
    log "Backup created successfully"
}

# Sync base components
sync_base_components() {
    log "Syncing base components..."
    
    # Create missing base directories
    for dir in "monitoring" "vault" "external-services" "operators"; do
        mkdir -p "${TARGET_DIR}/base/${dir}"
    done
    
    # Copy missing base components
    rsync -av --exclude='*.example' "${SOURCE_DIR}/base/monitoring/" "${TARGET_DIR}/base/monitoring/"
    rsync -av --exclude='*.example' "${SOURCE_DIR}/base/vault/" "${TARGET_DIR}/base/vault/"
    rsync -av --exclude='*.example' "${SOURCE_DIR}/base/external-services/" "${TARGET_DIR}/base/external-services/"
    
    # Update operators with enhanced configuration
    rsync -av "${SOURCE_DIR}/base/operators/" "${TARGET_DIR}/base/operators/"
    
    # Enhanced database configurations
    rsync -av --exclude='*.example' "${SOURCE_DIR}/base/databases/" "${TARGET_DIR}/base/databases/"
    
    # Enhanced core services with monitoring
    rsync -av "${SOURCE_DIR}/base/core-services/" "${TARGET_DIR}/base/core-services/"
    
    # Enhanced ingress configuration
    rsync -av "${SOURCE_DIR}/base/ingress/" "${TARGET_DIR}/base/ingress/"
    
    log "Base components synced"
}

# Sync overlay environments
sync_overlays() {
    log "Syncing overlay environments..."
    
    # Create missing overlay directories
    for env in "dev-lab" "prod-lab" "staging"; do
        mkdir -p "${TARGET_DIR}/overlays/${env}"
    done
    
    # Copy enhanced overlays
    rsync -av --exclude='*.env' --exclude='secrets' "${SOURCE_DIR}/overlays/" "${TARGET_DIR}/overlays/"
    
    # Create example secret files (don't overwrite existing)
    for env in "dev" "prod" "staging" "dev-lab" "prod-lab"; do
        if [[ -d "${SOURCE_DIR}/overlays/${env}/secrets" ]]; then
            mkdir -p "${TARGET_DIR}/overlays/${env}/secrets"
            for example in "${SOURCE_DIR}/overlays/${env}/secrets"/*.example; do
                if [[ -f "$example" ]]; then
                    filename=$(basename "$example")
                    target="${TARGET_DIR}/overlays/${env}/secrets/${filename}"
                    if [[ ! -f "$target" ]]; then
                        cp "$example" "$target"
                        warn "Created example secret file: $target"
                    fi
                fi
            done
        fi
    done
    
    log "Overlay environments synced"
}

# Update main kustomization
update_main_kustomization() {
    log "Updating main kustomization.yaml..."
    
    # Update base kustomization.yaml to include new components
    cp "${SOURCE_DIR}/base/kustomization.yaml" "${TARGET_DIR}/base/kustomization.yaml"
    
    log "Main kustomization updated"
}

# Copy documentation
sync_documentation() {
    log "Syncing documentation..."
    
    # Copy enhanced documentation
    rsync -av "${SOURCE_DIR}/*.md" "${TARGET_DIR}/"
    
    log "Documentation synced"
}

# Validate configuration
validate_config() {
    log "Validating kustomize configuration..."
    
    # Validate base configuration
    if ! kubectl kustomize "${TARGET_DIR}/base" > /dev/null; then
        error "Base kustomization validation failed"
        return 1
    fi
    
    # Validate overlay configurations
    for overlay in "${TARGET_DIR}/overlays"/*; do
        if [[ -d "$overlay" && -f "$overlay/kustomization.yaml" ]]; then
            overlay_name=$(basename "$overlay")
            if ! kubectl kustomize "$overlay" > /dev/null; then
                warn "Overlay $overlay_name validation failed - may need secret configuration"
            else
                log "Overlay $overlay_name validated successfully"
            fi
        fi
    done
    
    log "Configuration validation completed"
}

# Display upgrade summary
upgrade_summary() {
    echo
    log "=== UPGRADE SUMMARY ==="
    
    # Count files before and after
    BEFORE_COUNT=$(find "$BACKUP_DIR" -name "*.yaml" | wc -l)
    AFTER_COUNT=$(find "$TARGET_DIR" -name "*.yaml" | wc -l)
    
    log "Files before upgrade: $BEFORE_COUNT"
    log "Files after upgrade: $AFTER_COUNT"
    log "New files added: $((AFTER_COUNT - BEFORE_COUNT))"
    
    echo
    log "New components added:"
    log "  - Enhanced monitoring stack"
    log "  - Vault integration for secrets"
    log "  - External services configuration"
    log "  - Enhanced operator configurations"
    log "  - Dev-lab and prod-lab overlays"
    
    echo
    log "Next steps:"
    log "  1. Review new secret templates in overlays/*/secrets/"
    log "  2. Configure environment-specific values"
    log "  3. Test deployment with: kubectl apply -k overlays/dev"
    log "  4. Update ArgoCD applications if needed"
    
    echo
    log "Backup location: $BACKUP_DIR"
}

# Deploy to development environment
deploy_dev() {
    if [[ "${1:-}" == "--deploy-dev" ]]; then
        log "Deploying to development environment..."
        
        # Check if secrets are configured
        if [[ ! -f "${TARGET_DIR}/overlays/dev/secrets/dev.env" ]]; then
            warn "Development secrets not configured. Creating from example..."
            if [[ -f "${TARGET_DIR}/overlays/dev/secrets/dev.env.example" ]]; then
                cp "${TARGET_DIR}/overlays/dev/secrets/dev.env.example" "${TARGET_DIR}/overlays/dev/secrets/dev.env"
                warn "Please configure ${TARGET_DIR}/overlays/dev/secrets/dev.env before deployment"
            fi
        fi
        
        # Apply the configuration
        kubectl apply -k "${TARGET_DIR}/overlays/dev"
        log "Development deployment completed"
    fi
}

# Main execution
main() {
    log "Starting Grill Stats kustomize upgrade..."
    
    preflight_checks
    create_backup
    sync_base_components
    sync_overlays
    update_main_kustomization
    sync_documentation
    validate_config
    upgrade_summary
    deploy_dev "$@"
    
    log "Upgrade completed successfully!"
}

# Help text
show_help() {
    cat << EOF
Grill Stats Kustomize Upgrade Script

Usage: $0 [OPTIONS]

Options:
    --deploy-dev    Deploy to development environment after upgrade
    --help         Show this help message

Examples:
    $0                    # Upgrade configuration only
    $0 --deploy-dev      # Upgrade and deploy to dev environment

This script will:
1. Create a backup of current configuration
2. Sync enhanced kustomize files from source repository
3. Add new components (monitoring, vault, operators, etc.)
4. Validate the updated configuration
5. Provide deployment instructions

EOF
}

# Check for help flag
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"