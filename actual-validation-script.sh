#!/bin/bash

# Actual Budget Migration Validation Script
# This script validates the migration and tests the new PostgreSQL setup

set -euo pipefail

# Configuration
NAMESPACE="services"
APP_NAME="actual"
DB_NAME="actual-database"

# Logging functions
log_info() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO: $*" >&2
}

log_error() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2
}

log_success() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ✅ SUCCESS: $*" >&2
}

log_warning() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ⚠️  WARNING: $*" >&2
}

# Check database cluster health
check_database_health() {
    log_info "Checking PostgreSQL database health..."
    
    # Check cluster status
    if kubectl get cluster $DB_NAME -n $NAMESPACE >/dev/null 2>&1; then
        local status=$(kubectl get cluster $DB_NAME -n $NAMESPACE -o jsonpath='{.status.phase}')
        if [ "$status" = "Cluster in healthy state" ] || [ "$status" = "Ready" ]; then
            log_success "Database cluster is healthy (status: $status)"
        else
            log_warning "Database cluster status: $status"
        fi
    else
        log_error "Database cluster not found"
        return 1
    fi
    
    # Check pods
    local db_pods=$(kubectl get pods -n $NAMESPACE -l cnpg.io/cluster=$DB_NAME --no-headers | wc -l)
    local ready_pods=$(kubectl get pods -n $NAMESPACE -l cnpg.io/cluster=$DB_NAME --no-headers | grep -c "Running" || echo "0")
    
    log_info "Database pods: $ready_pods/$db_pods ready"
    
    if [ "$ready_pods" -eq "$db_pods" ] && [ "$db_pods" -gt "0" ]; then
        log_success "All database pods are running"
    else
        log_error "Database pods are not ready"
        kubectl get pods -n $NAMESPACE -l cnpg.io/cluster=$DB_NAME
        return 1
    fi
}

# Test database connectivity
test_database_connectivity() {
    log_info "Testing database connectivity..."
    
    # Get primary database pod
    local db_pod=$(kubectl get pods -n $NAMESPACE --selector=cnpg.io/instanceRole=primary -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -z "$db_pod" ]; then
        log_error "Could not find primary database pod"
        return 1
    fi
    
    log_info "Using database pod: $db_pod"
    
    # Test connection
    if kubectl exec -n $NAMESPACE $db_pod -- psql -U postgres -d actual -c "SELECT version();" >/dev/null 2>&1; then
        log_success "Database connection test passed"
    else
        log_error "Database connection test failed"
        return 1
    fi
    
    # Check database tables
    local table_count=$(kubectl exec -n $NAMESPACE $db_pod -- psql -U postgres -d actual -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
    log_info "Database contains $table_count tables"
    
    if [ "$table_count" -gt "0" ]; then
        log_info "Listing database tables:"
        kubectl exec -n $NAMESPACE $db_pod -- psql -U postgres -d actual -c "\dt"
    fi
}

# Check application deployment
check_application_deployment() {
    log_info "Checking Actual Budget application deployment..."
    
    # Check deployment status
    if kubectl get deployment $APP_NAME -n $NAMESPACE >/dev/null 2>&1; then
        local ready_replicas=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' || echo "0")
        local desired_replicas=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.replicas}' || echo "0")
        
        log_info "Application pods: $ready_replicas/$desired_replicas ready"
        
        if [ "$ready_replicas" = "$desired_replicas" ] && [ "$ready_replicas" -gt "0" ]; then
            log_success "Application deployment is ready"
        else
            log_warning "Application deployment is not fully ready"
            kubectl get pods -n $NAMESPACE -l app=$APP_NAME
        fi
    else
        log_warning "Application deployment not found - may not be deployed yet"
    fi
}

# Test backup system
test_backup_system() {
    log_info "Testing backup system..."
    
    # Check if backup CronJob exists
    if kubectl get cronjob actual-postgres-backup -n $NAMESPACE >/dev/null 2>&1; then
        log_success "Backup CronJob is configured"
        
        # Show backup schedule
        local schedule=$(kubectl get cronjob actual-postgres-backup -n $NAMESPACE -o jsonpath='{.spec.schedule}')
        log_info "Backup schedule: $schedule"
        
        # Create a test backup job
        log_info "Creating test backup job..."
        if kubectl create job --from=cronjob/actual-postgres-backup actual-backup-test-$(date +%s) -n $NAMESPACE >/dev/null 2>&1; then
            log_success "Test backup job created successfully"
            log_info "Monitor with: kubectl logs -f job/actual-backup-test-$(date +%s) -n $NAMESPACE"
        else
            log_warning "Could not create test backup job"
        fi
    else
        log_error "Backup CronJob not found"
        return 1
    fi
}

# Test restoration system
test_restoration_system() {
    log_info "Testing restoration system capabilities..."
    
    # Check init containers in deployment
    if kubectl get deployment $APP_NAME -n $NAMESPACE >/dev/null 2>&1; then
        local init_containers=$(kubectl get deployment $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.template.spec.initContainers[*].name}' || echo "")
        
        if echo "$init_containers" | grep -q "restore-db-backup"; then
            log_success "Restoration init container is configured"
        else
            log_warning "Restoration init container not found in deployment"
        fi
        
        if echo "$init_containers" | grep -q "wait-for-db"; then
            log_success "Database wait init container is configured"
        else
            log_warning "Database wait init container not found"
        fi
    fi
}

# Check secrets and configuration
check_secrets_and_config() {
    log_info "Checking secrets and configuration..."
    
    # Check 1Password secrets
    if kubectl get onepassworditem actual-db-postgres-creds-1password -n $NAMESPACE >/dev/null 2>&1; then
        log_success "Database credentials secret is configured"
    else
        log_error "Database credentials secret not found"
        return 1
    fi
    
    if kubectl get onepassworditem backblaze-cloud-homelab-creds-1password -n $NAMESPACE >/dev/null 2>&1; then
        log_success "Backup credentials secret is configured"
    else
        log_warning "Backup credentials secret not found"
    fi
    
    # Check generated secrets
    if kubectl get secret actual-db-postgres-creds-1password -n $NAMESPACE >/dev/null 2>&1; then
        log_success "Database credentials secret is available"
    else
        log_warning "Database credentials secret not yet generated by 1Password"
    fi
}

# Test application connectivity
test_application_connectivity() {
    log_info "Testing application connectivity..."
    
    # Check service
    if kubectl get service $APP_NAME -n $NAMESPACE >/dev/null 2>&1; then
        local port=$(kubectl get service $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')
        log_success "Application service is available on port $port"
    else
        log_warning "Application service not found"
    fi
    
    # Check ingress (if exists)
    if kubectl get ingress $APP_NAME -n $NAMESPACE >/dev/null 2>&1; then
        local host=$(kubectl get ingress $APP_NAME -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}')
        log_info "Application ingress configured for: $host"
    else
        log_info "No ingress configuration found"
    fi
}

# Generate validation report
generate_validation_report() {
    log_info "Generating validation report..."
    
    local report_file="actual-validation-report-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=== Actual Budget Migration Validation Report ==="
        echo "Generated: $(date)"
        echo "Namespace: $NAMESPACE"
        echo ""
        
        echo "=== Database Status ==="
        kubectl get cluster $DB_NAME -n $NAMESPACE 2>/dev/null || echo "Database cluster not found"
        echo ""
        
        echo "=== Database Pods ==="
        kubectl get pods -n $NAMESPACE -l cnpg.io/cluster=$DB_NAME 2>/dev/null || echo "No database pods found"
        echo ""
        
        echo "=== Application Status ==="
        kubectl get deployment $APP_NAME -n $NAMESPACE 2>/dev/null || echo "Application deployment not found"
        echo ""
        
        echo "=== Application Pods ==="
        kubectl get pods -n $NAMESPACE -l app=$APP_NAME 2>/dev/null || echo "No application pods found"
        echo ""
        
        echo "=== Backup Jobs ==="
        kubectl get cronjob actual-postgres-backup -n $NAMESPACE 2>/dev/null || echo "Backup CronJob not found"
        kubectl get jobs -n $NAMESPACE | grep actual-backup 2>/dev/null || echo "No backup jobs found"
        echo ""
        
        echo "=== Secrets ==="
        kubectl get onepassworditem -n $NAMESPACE 2>/dev/null || echo "No 1Password items found"
        kubectl get secrets -n $NAMESPACE | grep actual 2>/dev/null || echo "No Actual secrets found"
        echo ""
        
        echo "=== Services ==="
        kubectl get service $APP_NAME -n $NAMESPACE 2>/dev/null || echo "Application service not found"
        echo ""
        
        echo "=== Storage ==="
        kubectl get pvc -n $NAMESPACE 2>/dev/null || echo "No PVCs found"
    } > "$report_file"
    
    log_success "Validation report saved to: $report_file"
}

# Main validation function
main() {
    log_info "🔍 Starting Actual Budget migration validation..."
    echo ""
    
    local validation_passed=true
    
    # Run all validation checks
    check_secrets_and_config || validation_passed=false
    echo ""
    
    check_database_health || validation_passed=false
    echo ""
    
    test_database_connectivity || validation_passed=false
    echo ""
    
    check_application_deployment
    echo ""
    
    test_backup_system || validation_passed=false
    echo ""
    
    test_restoration_system
    echo ""
    
    test_application_connectivity
    echo ""
    
    generate_validation_report
    echo ""
    
    if [ "$validation_passed" = true ]; then
        log_success "🎉 All critical validation checks passed!"
        log_info "Your Actual Budget PostgreSQL migration setup is ready."
    else
        log_warning "⚠️  Some validation checks failed. Please review the issues above."
        log_info "You may need to:"
        log_info "1. Ensure 1Password Connect is working"
        log_info "2. Check database deployment status"
        log_info "3. Verify network connectivity"
    fi
    
    echo ""
    log_info "Next steps:"
    log_info "1. If validation passed, deploy Actual Budget: kubectl apply -f apps/services/finances/actual/base/deployment.yaml"
    log_info "2. Access the application and verify functionality"
    log_info "3. Import your budget data using Actual Budget's import features"
    log_info "4. Test the backup system: kubectl logs -f job/<backup-job-name> -n services"
}

# Run main function
main "$@"