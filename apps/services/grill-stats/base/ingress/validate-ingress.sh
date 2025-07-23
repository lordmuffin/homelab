#!/bin/bash

# Grill Stats Traefik Ingress Validation Script
# This script validates the ingress configuration and tests connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="grill-stats"
DEV_NAMESPACE="grill-stats-dev"
PROD_DOMAIN="grill-stats.homelab.local"
API_DOMAIN="api.grill-stats.homelab.local"
ADMIN_DOMAIN="admin.grill-stats.homelab.local"
DEV_DOMAIN="grill-stats.dev.homelab.local"

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisite() {
    local cmd=$1
    local name=$2

    if ! command -v $cmd &> /dev/null; then
        error "$name is not installed"
        return 1
    fi
    info "$name is available"
    return 0
}

check_namespace() {
    local ns=$1

    if ! kubectl get namespace $ns &> /dev/null; then
        error "Namespace $ns does not exist"
        return 1
    fi
    info "Namespace $ns exists"
    return 0
}

check_certificate() {
    local name=$1
    local namespace=$2

    if ! kubectl get certificate $name -n $namespace &> /dev/null; then
        error "Certificate $name not found in namespace $namespace"
        return 1
    fi

    local status=$(kubectl get certificate $name -n $namespace -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    if [[ "$status" != "True" ]]; then
        error "Certificate $name is not ready (status: $status)"
        return 1
    fi

    info "Certificate $name is ready"
    return 0
}

check_ingressroute() {
    local name=$1
    local namespace=$2

    if ! kubectl get ingressroute $name -n $namespace &> /dev/null; then
        error "IngressRoute $name not found in namespace $namespace"
        return 1
    fi

    info "IngressRoute $name exists"
    return 0
}

check_middleware() {
    local name=$1
    local namespace=$2

    if ! kubectl get middleware $name -n $namespace &> /dev/null; then
        error "Middleware $name not found in namespace $namespace"
        return 1
    fi

    info "Middleware $name exists"
    return 0
}

test_http_endpoint() {
    local url=$1
    local expected_status=$2
    local description=$3

    info "Testing $description: $url"

    local status=$(curl -s -o /dev/null -w "%{http_code}" -k "$url" || echo "000")

    if [[ "$status" == "$expected_status" ]]; then
        info "$description: HTTP $status (expected $expected_status) ✓"
        return 0
    else
        error "$description: HTTP $status (expected $expected_status) ✗"
        return 1
    fi
}

test_ssl_certificate() {
    local domain=$1
    local port=${2:-443}

    info "Testing SSL certificate for $domain:$port"

    if openssl s_client -connect "$domain:$port" -servername "$domain" </dev/null 2>/dev/null | openssl x509 -noout -dates; then
        info "SSL certificate for $domain is valid ✓"
        return 0
    else
        error "SSL certificate for $domain is invalid ✗"
        return 1
    fi
}

test_cors() {
    local url=$1
    local origin=$2

    info "Testing CORS for $url with origin $origin"

    local cors_header=$(curl -s -H "Origin: $origin" -I "$url" | grep -i "access-control-allow-origin" || echo "")

    if [[ -n "$cors_header" ]]; then
        info "CORS header found: $cors_header ✓"
        return 0
    else
        error "CORS header not found ✗"
        return 1
    fi
}

# Main validation function
main() {
    info "Starting Grill Stats Traefik Ingress Validation"

    # Check prerequisites
    info "Checking prerequisites..."
    check_prerequisite "kubectl" "kubectl" || exit 1
    check_prerequisite "curl" "curl" || exit 1
    check_prerequisite "openssl" "openssl" || exit 1

    # Check cluster connectivity
    info "Checking cluster connectivity..."
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    info "Connected to Kubernetes cluster"

    # Check namespaces
    info "Checking namespaces..."
    check_namespace "$NAMESPACE" || exit 1
    check_namespace "$DEV_NAMESPACE" || warn "Development namespace not found"

    # Check certificates
    info "Checking certificates..."
    check_certificate "grill-stats-tls" "$NAMESPACE" || warn "Production certificate not ready"
    check_certificate "grill-stats-dev-tls" "$DEV_NAMESPACE" || warn "Development certificate not ready"
    check_certificate "grill-stats-admin-tls" "$NAMESPACE" || warn "Admin certificate not ready"

    # Check IngressRoutes
    info "Checking IngressRoutes..."
    check_ingressroute "grill-stats-web-ui" "$NAMESPACE" || error "Web UI IngressRoute missing"
    check_ingressroute "grill-stats-api-gateway" "$NAMESPACE" || error "API Gateway IngressRoute missing"
    check_ingressroute "grill-stats-websocket" "$NAMESPACE" || error "WebSocket IngressRoute missing"

    # Check Middleware
    info "Checking Middleware..."
    check_middleware "grill-stats-security-headers" "$NAMESPACE" || error "Security headers middleware missing"
    check_middleware "grill-stats-cors" "$NAMESPACE" || error "CORS middleware missing"
    check_middleware "grill-stats-api-rate-limit" "$NAMESPACE" || error "Rate limit middleware missing"

    # Test HTTP endpoints
    info "Testing HTTP endpoints..."
    test_http_endpoint "https://$PROD_DOMAIN" "200" "Production Web UI"
    test_http_endpoint "https://$API_DOMAIN/api/health" "200" "Production API Health"
    test_http_endpoint "https://$DEV_DOMAIN" "200" "Development Web UI"
    test_http_endpoint "https://$ADMIN_DOMAIN/dashboard/" "401" "Admin Dashboard (should require auth)"

    # Test SSL certificates
    info "Testing SSL certificates..."
    test_ssl_certificate "$PROD_DOMAIN"
    test_ssl_certificate "$API_DOMAIN"
    test_ssl_certificate "$DEV_DOMAIN"

    # Test CORS
    info "Testing CORS..."
    test_cors "https://$API_DOMAIN/api/health" "https://$PROD_DOMAIN"
    test_cors "https://$DEV_DOMAIN/api/health" "http://localhost:3000"

    # Test rate limiting
    info "Testing rate limiting..."
    for i in {1..5}; do
        curl -s -o /dev/null "https://$API_DOMAIN/api/health"
    done

    local rate_limit_status=$(curl -s -o /dev/null -w "%{http_code}" "https://$API_DOMAIN/api/health")
    if [[ "$rate_limit_status" == "200" ]]; then
        info "Rate limiting test passed (requests under limit) ✓"
    else
        warn "Rate limiting may be too strict (status: $rate_limit_status)"
    fi

    # Check service discovery
    info "Checking service discovery..."
    local services=("web-ui-service" "auth-service" "device-service" "temperature-service" "historical-data-service")

    for service in "${services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
            info "Service $service is available ✓"
        else
            error "Service $service is not available ✗"
        fi
    done

    # Check monitoring
    info "Checking monitoring configuration..."
    if kubectl get servicemonitor "grill-stats-ingress-metrics" -n "$NAMESPACE" &> /dev/null; then
        info "ServiceMonitor is configured ✓"
    else
        warn "ServiceMonitor is not configured"
    fi

    if kubectl get prometheusrule "grill-stats-ingress-rules" -n "$NAMESPACE" &> /dev/null; then
        info "PrometheusRule is configured ✓"
    else
        warn "PrometheusRule is not configured"
    fi

    info "Validation complete!"

    # Summary
    echo
    info "=== VALIDATION SUMMARY ==="
    echo "Web UI: https://$PROD_DOMAIN"
    echo "API Gateway: https://$API_DOMAIN"
    echo "Admin Dashboard: https://$ADMIN_DOMAIN/dashboard/"
    echo "Development: https://$DEV_DOMAIN"
    echo "WebSocket: wss://$PROD_DOMAIN/ws"
    echo "Metrics: https://$ADMIN_DOMAIN/metrics"
    echo
    info "If any errors were reported, check the deployment guide for troubleshooting steps."
}

# Run validation
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
