#!/bin/bash
# FluxCD Migration Validation Script
# Comprehensive validation of FluxCD deployment health and functionality

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
WARNINGS=0

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"
    ((WARNINGS++))
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"
}

test_start() {
    local test_name="$1"
    info "Testing: $test_name"
    ((TESTS_RUN++))
}

test_pass() {
    local test_name="$1"
    log "✓ PASS: $test_name"
    ((TESTS_PASSED++))
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    error "✗ FAIL: $test_name - $reason"
}

# Test FluxCD system components
test_flux_system() {
    test_start "FluxCD System Components"
    
    local required_controllers=("source-controller" "kustomize-controller" "helm-controller")
    local missing_controllers=()
    
    for controller in "${required_controllers[@]}"; do
        if ! kubectl get deployment "$controller" -n flux-system &>/dev/null; then
            missing_controllers+=("$controller")
        elif [[ $(kubectl get deployment "$controller" -n flux-system -o jsonpath='{.status.readyReplicas}') -eq 0 ]]; then
            missing_controllers+=("$controller (not ready)")
        fi
    done
    
    if [[ ${#missing_controllers[@]} -eq 0 ]]; then
        test_pass "All FluxCD controllers are running"
    else
        test_fail "FluxCD System Components" "Missing/unhealthy controllers: ${missing_controllers[*]}"
        return 1
    fi
}

# Test source repositories
test_sources() {
    test_start "Source Repositories"
    
    local git_sources
    git_sources=$(kubectl get gitrepositories -A --no-headers 2>/dev/null | wc -l)
    
    local helm_sources
    helm_sources=$(kubectl get helmrepositories -A --no-headers 2>/dev/null | wc -l)
    
    if [[ $git_sources -eq 0 && $helm_sources -eq 0 ]]; then
        test_fail "Source Repositories" "No sources configured"
        return 1
    fi
    
    # Check source health
    local unhealthy_git
    unhealthy_git=$(kubectl get gitrepositories -A --no-headers 2>/dev/null | grep -v "True" | wc -l)
    
    local unhealthy_helm
    unhealthy_helm=$(kubectl get helmrepositories -A --no-headers 2>/dev/null | grep -v "True" | wc -l)
    
    if [[ $unhealthy_git -gt 0 ]]; then
        warn "$unhealthy_git Git repositories are not healthy"
        kubectl get gitrepositories -A | grep -v "True" || true
    fi
    
    if [[ $unhealthy_helm -gt 0 ]]; then
        warn "$unhealthy_helm Helm repositories are not healthy"
        kubectl get helmrepositories -A | grep -v "True" || true
    fi
    
    test_pass "Found $git_sources Git sources and $helm_sources Helm sources"
}

# Test applications
test_applications() {
    test_start "FluxCD Applications"
    
    local kustomizations
    kustomizations=$(kubectl get kustomizations -A --no-headers 2>/dev/null | wc -l)
    
    local helmreleases
    helmreleases=$(kubectl get helmreleases -A --no-headers 2>/dev/null | wc -l)
    
    if [[ $kustomizations -eq 0 && $helmreleases -eq 0 ]]; then
        test_fail "FluxCD Applications" "No applications found"
        return 1
    fi
    
    # Check application health
    local unhealthy_kustomizations
    unhealthy_kustomizations=$(kubectl get kustomizations -A --no-headers 2>/dev/null | grep -v "True" | wc -l)
    
    local unhealthy_helmreleases  
    unhealthy_helmreleases=$(kubectl get helmreleases -A --no-headers 2>/dev/null | grep -v "True" | wc -l)
    
    local total_apps=$((kustomizations + helmreleases))
    local unhealthy_apps=$((unhealthy_kustomizations + unhealthy_helmreleases))
    local healthy_apps=$((total_apps - unhealthy_apps))
    
    if [[ $unhealthy_apps -gt 0 ]]; then
        warn "$unhealthy_apps/$total_apps applications are not healthy"
        
        if [[ $unhealthy_kustomizations -gt 0 ]]; then
            echo "Unhealthy Kustomizations:"
            kubectl get kustomizations -A | grep -v "True" || true
        fi
        
        if [[ $unhealthy_helmreleases -gt 0 ]]; then
            echo "Unhealthy HelmReleases:"
            kubectl get helmreleases -A | grep -v "True" || true
        fi
    fi
    
    test_pass "$healthy_apps/$total_apps applications are healthy"
}

# Test namespace creation
test_namespaces() {
    test_start "Required Namespaces"
    
    local required_namespaces=("flux-system" "traefik" "monitoring" "argocd")
    local missing_namespaces=()
    
    for ns in "${required_namespaces[@]}"; do
        if ! kubectl get namespace "$ns" &>/dev/null; then
            missing_namespaces+=("$ns")
        fi
    done
    
    if [[ ${#missing_namespaces[@]} -gt 0 ]]; then
        warn "Missing namespaces: ${missing_namespaces[*]}"
    fi
    
    test_pass "Namespace validation completed"
}

# Test RBAC configuration
test_rbac() {
    test_start "FluxCD RBAC"
    
    local flux_sa_count
    flux_sa_count=$(kubectl get serviceaccounts -A | grep -c "flux" || echo "0")
    
    local flux_role_count
    flux_role_count=$(kubectl get clusterroles | grep -c "flux" || echo "0")
    
    local flux_binding_count
    flux_binding_count=$(kubectl get clusterrolebindings | grep -c "flux" || echo "0")
    
    if [[ $flux_sa_count -eq 0 ]]; then
        warn "No FluxCD service accounts found"
    fi
    
    if [[ $flux_role_count -eq 0 ]]; then
        warn "No FluxCD cluster roles found"
    fi
    
    if [[ $flux_binding_count -eq 0 ]]; then
        warn "No FluxCD cluster role bindings found"
    fi
    
    test_pass "RBAC validation completed ($flux_sa_count SAs, $flux_role_count roles, $flux_binding_count bindings)"
}

# Test critical applications
test_critical_apps() {
    test_start "Critical Application Health"
    
    local critical_apps=("traefik" "cert-manager" "prometheus" "grafana")
    local failed_apps=()
    
    for app in "${critical_apps[@]}"; do
        # Check if deployment exists and is ready
        if kubectl get deployment "$app" -A &>/dev/null; then
            local ready_replicas
            ready_replicas=$(kubectl get deployment "$app" -A -o jsonpath='{.items[0].status.readyReplicas}' 2>/dev/null || echo "0")
            local desired_replicas
            desired_replicas=$(kubectl get deployment "$app" -A -o jsonpath='{.items[0].spec.replicas}' 2>/dev/null || echo "1")
            
            if [[ "$ready_replicas" != "$desired_replicas" ]]; then
                failed_apps+=("$app ($ready_replicas/$desired_replicas ready)")
            fi
        else
            # App might not be deployed yet - just note it
            info "$app deployment not found (may not be deployed yet)"
        fi
    done
    
    if [[ ${#failed_apps[@]} -gt 0 ]]; then
        warn "Critical apps with issues: ${failed_apps[*]}"
    fi
    
    test_pass "Critical application check completed"
}

# Test resource usage
test_resource_usage() {
    test_start "Resource Usage"
    
    # Check FluxCD controller resource usage
    info "FluxCD Controller Resource Usage:"
    kubectl top pods -n flux-system --no-headers 2>/dev/null | while read -r line; do
        echo "  $line"
    done || warn "Unable to get resource usage (metrics-server may not be available)"
    
    # Check for pods in bad states
    local bad_pods
    bad_pods=$(kubectl get pods -A --no-headers | grep -v "Running\|Completed" | wc -l)
    
    if [[ $bad_pods -gt 0 ]]; then
        warn "$bad_pods pods are not in Running/Completed state"
        kubectl get pods -A --no-headers | grep -v "Running\|Completed" | head -10
    fi
    
    test_pass "Resource usage check completed"
}

# Test connectivity and ingress
test_connectivity() {
    test_start "Network Connectivity"
    
    # Test if Traefik is accessible (if deployed)
    if kubectl get service traefik -A &>/dev/null; then
        local traefik_ip
        traefik_ip=$(kubectl get service traefik -A -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [[ -n "$traefik_ip" ]]; then
            info "Traefik LoadBalancer IP: $traefik_ip"
        else
            warn "Traefik service has no external IP assigned"
        fi
    fi
    
    # Check certificate status (if cert-manager is deployed)
    if kubectl get certificates -A &>/dev/null; then
        local cert_count
        cert_count=$(kubectl get certificates -A --no-headers | wc -l)
        local ready_certs
        ready_certs=$(kubectl get certificates -A --no-headers | grep "True" | wc -l)
        
        info "Certificates: $ready_certs/$cert_count ready"
        
        if [[ $ready_certs -lt $cert_count ]]; then
            warn "Some certificates are not ready"
            kubectl get certificates -A | grep -v "True" || true
        fi
    fi
    
    test_pass "Connectivity check completed"
}

# Test specific category
test_category() {
    local category="$1"
    
    test_start "Category: $category"
    
    case "$category" in
        "core")
            test_critical_apps
            ;;
        "networking")
            test_connectivity
            ;;
        "monitoring")  
            # Check if Prometheus is accessible
            if kubectl get service prometheus-kube-prometheus-prometheus -A &>/dev/null; then
                info "Prometheus service found"
            fi
            ;;
        *)
            info "No specific tests for category: $category"
            ;;
    esac
    
    # Check applications in the category
    local category_kustomizations
    category_kustomizations=$(kubectl get kustomizations -A --no-headers | grep "$category" | wc -l)
    
    local category_helmreleases
    category_helmreleases=$(kubectl get helmreleases -A --no-headers | grep "$category" | wc -l)
    
    test_pass "Category $category: $category_kustomizations kustomizations, $category_helmreleases helm releases"
}

# Generate report
generate_report() {
    echo
    echo "================================"
    echo "  FluxCD Validation Report"
    echo "================================"
    echo "Tests Run:    $TESTS_RUN"
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo "Warnings:     $WARNINGS"
    echo "================================"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        error "Validation completed with failures"
        return 1
    elif [[ $WARNINGS -gt 0 ]]; then
        warn "Validation completed with warnings"
        return 0
    else
        log "All tests passed successfully! ✓"
        return 0
    fi
}

main() {
    local scope="${1:-all}"
    
    log "Starting FluxCD validation (scope: $scope)"
    echo
    
    case "$scope" in
        "all")
            test_flux_system
            test_sources
            test_applications
            test_namespaces
            test_rbac
            test_critical_apps
            test_resource_usage
            test_connectivity
            ;;
        "system")
            test_flux_system
            test_sources
            test_rbac
            ;;
        "apps")
            test_applications
            test_critical_apps
            ;;
        "core"|"networking"|"monitoring"|"services"|"data"|"utilities"|"secrets")
            test_category "$scope"
            ;;
        "help"|*)
            cat << EOF
FluxCD Validation Script

Usage: $0 [scope]

Scopes:
  all         - Run all validation tests (default)
  system      - Test FluxCD system components only
  apps        - Test application deployment and health
  <category>  - Test specific category (core, networking, monitoring, etc.)
  help        - Show this help message

Examples:
  $0              # Run all tests
  $0 system       # Test FluxCD system health
  $0 apps         # Test application health
  $0 networking   # Test networking category
  $0 core         # Test core category

This script validates:
- FluxCD system component health
- Source repository connectivity
- Application deployment status  
- RBAC configuration
- Resource usage and connectivity
- Category-specific functionality
EOF
            exit 0
            ;;
    esac
    
    generate_report
}

# Run main function
main "$@"