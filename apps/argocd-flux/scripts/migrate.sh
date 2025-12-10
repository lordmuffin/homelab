#!/bin/bash
# ArgoCD to FluxCD Migration Script
# This script automates the installation and application of FluxCD resources

set -euo pipefail

# Configuration
GITHUB_USER="${GITHUB_USER:-lordmuffin}"
GITHUB_REPO="${GITHUB_REPO:-homelab}"  
BRANCH="${BRANCH:-main}"
FLUX_PATH="${FLUX_PATH:-apps/argocd-flux}"
NAMESPACE="${NAMESPACE:-flux-system}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
    fi
    
    # Check flux CLI
    if ! command -v flux &> /dev/null; then
        error "flux CLI is not installed. Install with: curl -s https://fluxcd.io/install.sh | sudo bash"
    fi
    
    # Check kubectl context
    if ! kubectl cluster-info &> /dev/null; then
        error "kubectl is not configured or cluster is not accessible"
    fi
    
    # Check GitHub token
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        error "GITHUB_TOKEN environment variable is not set"
    fi
    
    # Verify flux prerequisites
    if ! flux check --pre; then
        error "FluxCD prerequisites not met"
    fi
    
    log "Prerequisites check passed ✓"
}

backup_argocd() {
    log "Creating backup of existing ArgoCD configuration..."
    
    mkdir -p backup
    
    # Backup applications
    if kubectl get applications -n argocd &> /dev/null; then
        kubectl get applications -n argocd -o yaml > backup/argocd-applications-$(date +%Y%m%d-%H%M%S).yaml
        log "ArgoCD applications backed up"
    else
        warn "No ArgoCD applications found to backup"
    fi
    
    # Backup projects
    if kubectl get appprojects -n argocd &> /dev/null; then
        kubectl get appprojects -n argocd -o yaml > backup/argocd-projects-$(date +%Y%m%d-%H%M%S).yaml
        log "ArgoCD projects backed up"
    else
        warn "No ArgoCD projects found to backup"
    fi
    
    # Backup cluster state
    kubectl get pods -A -o yaml > backup/cluster-pods-$(date +%Y%m%d-%H%M%S).yaml
    kubectl get services -A -o yaml > backup/cluster-services-$(date +%Y%m%d-%H%M%S).yaml
    
    log "Backup completed ✓"
}

install_fluxcd() {
    log "Installing FluxCD..."
    
    # Bootstrap FluxCD
    flux bootstrap github \
        --owner="$GITHUB_USER" \
        --repository="$GITHUB_REPO" \
        --branch="$BRANCH" \
        --path="$FLUX_PATH" \
        --personal \
        --components-extra=image-reflector-controller,image-automation-controller
    
    # Wait for FluxCD to be ready
    log "Waiting for FluxCD components to be ready..."
    kubectl wait --for=condition=ready pod -l app=source-controller -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=kustomize-controller -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=helm-controller -n "$NAMESPACE" --timeout=300s
    
    log "FluxCD installation completed ✓"
}

deploy_applications() {
    local category="$1"
    log "Deploying $category applications..."
    
    case "$category" in
        "all")
            categories=("core" "networking" "monitoring" "services" "utilities" "secrets")
            ;;
        *)
            categories=("$category")
            ;;
    esac
    
    for cat in "${categories[@]}"; do
        log "Deploying $cat category..."
        
        # Check if category exists
        if [[ ! -d "apps/$cat" ]]; then
            warn "Category $cat not found, skipping"
            continue
        fi
        
        # Apply the category
        kubectl apply -f "apps/$cat/"
        
        # Wait for reconciliation
        log "Waiting for $cat applications to reconcile..."
        sleep 30
        
        # Check status
        if ! flux get kustomizations -n "$NAMESPACE" | grep -q "$cat"; then
            warn "No kustomizations found for $cat category"
        fi
    done
    
    log "Application deployment completed ✓"
}

validate_deployment() {
    log "Validating FluxCD deployment..."
    
    # Check FluxCD system health
    if ! flux check; then
        error "FluxCD health check failed"
    fi
    
    # Check sources
    log "Checking sources..."
    flux get sources git -A
    flux get sources helm -A
    
    # Check applications
    log "Checking applications..."
    flux get kustomizations -A
    flux get helmreleases -A
    
    # Check for failing resources
    local failing_kustomizations
    failing_kustomizations=$(kubectl get kustomizations -A --no-headers | grep -v "True" | wc -l)
    
    if [[ $failing_kustomizations -gt 0 ]]; then
        warn "$failing_kustomizations kustomization(s) are not ready"
        kubectl get kustomizations -A | grep -v "True" || true
    fi
    
    local failing_helmreleases
    failing_helmreleases=$(kubectl get helmreleases -A --no-headers | grep -v "True" | wc -l)
    
    if [[ $failing_helmreleases -gt 0 ]]; then
        warn "$failing_helmreleases helmrelease(s) are not ready"
        kubectl get helmreleases -A | grep -v "True" || true
    fi
    
    log "Validation completed ✓"
}

show_status() {
    log "FluxCD Status Summary:"
    echo "=========================="
    
    echo "Sources:"
    flux get sources git -A --no-header | wc -l | xargs echo "  Git repositories:"
    flux get sources helm -A --no-header | wc -l | xargs echo "  Helm repositories:"
    
    echo "Applications:"
    flux get kustomizations -A --no-header | wc -l | xargs echo "  Kustomizations:"
    flux get helmreleases -A --no-header | wc -l | xargs echo "  Helm releases:"
    
    echo "Health:"
    local healthy_kustomizations
    healthy_kustomizations=$(kubectl get kustomizations -A --no-headers | grep "True" | wc -l)
    local total_kustomizations
    total_kustomizations=$(kubectl get kustomizations -A --no-headers | wc -l)
    echo "  Kustomizations: $healthy_kustomizations/$total_kustomizations ready"
    
    local healthy_helmreleases
    healthy_helmreleases=$(kubectl get helmreleases -A --no-headers | grep "True" | wc -l)
    local total_helmreleases
    total_helmreleases=$(kubectl get helmreleases -A --no-headers | wc -l)
    echo "  Helm releases: $healthy_helmreleases/$total_helmreleases ready"
    
    echo "=========================="
}

main() {
    local action="${1:-help}"
    
    case "$action" in
        "install")
            check_prerequisites
            backup_argocd
            install_fluxcd
            validate_deployment
            show_status
            ;;
        "deploy")
            local category="${2:-all}"
            deploy_applications "$category"
            validate_deployment
            show_status
            ;;
        "validate")
            validate_deployment
            show_status
            ;;
        "status")
            show_status
            ;;
        "backup")
            backup_argocd
            ;;
        "help"|*)
            cat << EOF
ArgoCD to FluxCD Migration Script

Usage: $0 <action> [options]

Actions:
  install           - Full FluxCD installation and bootstrap
  deploy <category> - Deploy specific category (core|networking|monitoring|services|all)
  validate          - Validate current FluxCD deployment
  status            - Show current status summary
  backup            - Backup existing ArgoCD configuration
  help              - Show this help message

Environment Variables:
  GITHUB_TOKEN     - GitHub personal access token (required)
  GITHUB_USER      - GitHub username (default: lordmuffin)
  GITHUB_REPO      - GitHub repository (default: homelab)
  BRANCH           - Git branch (default: main)
  FLUX_PATH        - Path in repo (default: apps/argocd-flux)

Examples:
  export GITHUB_TOKEN=ghp_xxxxx
  $0 install                    # Full installation
  $0 deploy core               # Deploy core apps only
  $0 deploy all                # Deploy all categories
  $0 validate                  # Check deployment health
  $0 status                    # Show status summary

For detailed migration guide, see docs/MIGRATION-GUIDE.md
EOF
            ;;
    esac
}

# Run main function with all arguments
main "$@"