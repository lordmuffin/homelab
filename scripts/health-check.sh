#!/bin/bash
# Homelab Infrastructure Health Check Script - Enhanced Version
# Monitors cluster health, applications, security posture, performance, and GitHub Actions
# Integrates with inventory-check.py for comprehensive reporting

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${HOMELAB_ROOT}/logs/health-check-${TIMESTAMP}.log"
REPORT_FILE="${HOMELAB_ROOT}/logs/health-report-$(date +%Y%m%d).md"
JSON_REPORT_FILE="${HOMELAB_ROOT}/logs/health-report-${TIMESTAMP}.json"
ALERT_WEBHOOK="${DISCORD_WEBHOOK_URL:-}"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"

# Enhanced reporting options
FORMAT="summary"  # summary, json, markdown
OUTPUT_FILE=""
COMPONENT_FILTER=""
ENABLE_GITHUB_ACTIONS_CHECK=true
ENABLE_INVENTORY_CHECK=true

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Component health tracking
declare -A COMPONENT_STATUS
declare -A COMPONENT_DETAILS
declare -A HEALTH_SCORES

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Enhanced health check result tracking
check_result() {
    local status="$1"
    local component="${2:-general}"
    local message="$3"
    local details="${4:-}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    # Update component status (worst status wins)
    local current_status="${COMPONENT_STATUS[$component]:-PASS}"
    case "$status" in
        "FAIL")
            COMPONENT_STATUS[$component]="FAIL"
            ;;
        "WARN")
            if [[ "$current_status" != "FAIL" ]]; then
                COMPONENT_STATUS[$component]="WARN"
            fi
            ;;
        "PASS")
            if [[ "$current_status" == "" ]]; then
                COMPONENT_STATUS[$component]="PASS"
            fi
            ;;
    esac
    
    # Store details
    if [[ -n "$details" ]]; then
        COMPONENT_DETAILS[$component]="${COMPONENT_DETAILS[$component]}$message: $details; "
    else
        COMPONENT_DETAILS[$component]="${COMPONENT_DETAILS[$component]}$message; "
    fi
    
    case "$status" in
        "PASS")
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            log "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            log "${RED}❌ FAIL${NC}: $message"
            [ -n "$details" ] && log "   Details: $details"
            ;;
        "WARN")
            WARNING_CHECKS=$((WARNING_CHECKS + 1))
            log "${YELLOW}⚠️  WARN${NC}: $message"
            [ -n "$details" ] && log "   Details: $details"
            ;;
    esac
}

# Cluster Health Checks
check_cluster_health() {
    log "\n${BLUE}🏥 Cluster Health Checks${NC}"
    
    # Node status
    if kubectl get nodes --no-headers | grep -q "Ready"; then
        ready_nodes=$(kubectl get nodes --no-headers | grep -c "Ready" || echo 0)
        total_nodes=$(kubectl get nodes --no-headers | wc -l)
        check_result "PASS" "cluster" "Cluster nodes status" "$ready_nodes/$total_nodes nodes ready"
    else
        check_result "FAIL" "cluster" "No ready nodes found"
    fi
    
    # Node resource utilization
    kubectl top nodes 2>/dev/null | tail -n +2 | while read -r line; do
        node=$(echo "$line" | awk '{print $1}')
        cpu_usage=$(echo "$line" | awk '{print $3}' | tr -d '%')
        memory_usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
        
        if [ "$cpu_usage" -gt 80 ]; then
            check_result "WARN" "cluster" "High CPU usage on node $node" "${cpu_usage}%"
        elif [ "$memory_usage" -gt 80 ]; then
            check_result "WARN" "cluster" "High memory usage on node $node" "${memory_usage}%"
        else
            check_result "PASS" "cluster" "Node $node resource usage normal" "CPU: ${cpu_usage}%, Memory: ${memory_usage}%"
        fi
    done || check_result "WARN" "cluster" "Unable to get node metrics (metrics-server may not be available)"
    
    # Storage capacity
    kubectl get pv --no-headers 2>/dev/null | while read -r line; do
        pv_name=$(echo "$line" | awk '{print $1}')
        capacity=$(echo "$line" | awk '{print $2}')
        status=$(echo "$line" | awk '{print $5}')
        
        if [ "$status" = "Available" ] || [ "$status" = "Bound" ]; then
            check_result "PASS" "storage" "Persistent Volume $pv_name" "Status: $status, Capacity: $capacity"
        else
            check_result "FAIL" "storage" "Persistent Volume $pv_name" "Status: $status"
        fi
    done || check_result "WARN" "storage" "No persistent volumes found or unable to query"
    
    # Network connectivity (DNS)
    if kubectl run dns-test --image=busybox --rm -it --restart=Never -- nslookup kubernetes.default.svc.cluster.local >/dev/null 2>&1; then
        check_result "PASS" "networking" "DNS resolution working"
    else
        check_result "FAIL" "networking" "DNS resolution failed"
    fi
}

# Application Health Checks
check_application_health() {
    log "\n${BLUE}🚀 Application Health Checks${NC}"
    
    # ArgoCD health
    if kubectl get pods -n argocd --no-headers | grep -q "Running"; then
        running_pods=$(kubectl get pods -n argocd --no-headers | grep -c "Running" || echo 0)
        total_pods=$(kubectl get pods -n argocd --no-headers | wc -l)
        
        if [ "$running_pods" -eq "$total_pods" ]; then
            check_result "PASS" "argocd" "ArgoCD pods healthy" "$running_pods/$total_pods pods running"
        else
            check_result "WARN" "argocd" "Some ArgoCD pods not running" "$running_pods/$total_pods pods running"
        fi
        
        # ArgoCD sync status
        if command -v argocd >/dev/null 2>&1; then
            out_of_sync=$(argocd app list -o json 2>/dev/null | jq -r '.[] | select(.status.sync.status != "Synced") | .metadata.name' | wc -l || echo "unknown")
            if [ "$out_of_sync" = "0" ]; then
                check_result "PASS" "argocd" "All ArgoCD applications synced"
            elif [ "$out_of_sync" = "unknown" ]; then
                check_result "WARN" "argocd" "Unable to check ArgoCD sync status"
            else
                check_result "WARN" "argocd" "Applications out of sync" "$out_of_sync applications need attention"
            fi
        else
            check_result "WARN" "argocd" "ArgoCD CLI not available"
        fi
    else
        check_result "FAIL" "argocd" "ArgoCD pods not running"
    fi
    
    # cert-manager health
    if kubectl get pods -n cert-manager --no-headers | grep -q "Running"; then
        running_pods=$(kubectl get pods -n cert-manager --no-headers | grep -c "Running" || echo 0)
        total_pods=$(kubectl get pods -n cert-manager --no-headers | wc -l)
        
        if [ "$running_pods" -eq "$total_pods" ]; then
            check_result "PASS" "certificates" "cert-manager pods healthy" "$running_pods/$total_pods pods running"
        else
            check_result "FAIL" "certificates" "cert-manager pods not healthy" "$running_pods/$total_pods pods running"
        fi
        
        # Certificate status
        failed_certs=$(kubectl get certificates --all-namespaces --no-headers | grep -v "True" | wc -l || echo 0)
        if [ "$failed_certs" -eq 0 ]; then
            check_result "PASS" "certificates" "All certificates valid"
        else
            check_result "WARN" "certificates" "Some certificates not ready" "$failed_certs certificates need attention"
        fi
    else
        check_result "FAIL" "certificates" "cert-manager not running"
    fi
    
    # Monitoring stack health
    if kubectl get pods -n monitoring --no-headers | grep -q "Running"; then
        running_pods=$(kubectl get pods -n monitoring --no-headers | grep -c "Running" || echo 0)
        total_pods=$(kubectl get pods -n monitoring --no-headers | wc -l)
        
        if [ "$running_pods" -eq "$total_pods" ]; then
            check_result "PASS" "monitoring" "Monitoring stack healthy" "$running_pods/$total_pods pods running"
        else
            check_result "WARN" "monitoring" "Some monitoring pods not running" "$running_pods/$total_pods pods running"
        fi
        
        # Prometheus targets
        if command -v curl >/dev/null 2>&1; then
            kubectl port-forward -n monitoring svc/kube-prometheus-kube-prome-prometheus 9090:9090 >/dev/null 2>&1 &
            PORT_FORWARD_PID=$!
            sleep 5
            
            if targets=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | jq -r '.data.activeTargets[] | select(.health != "up") | .labels.job' | wc -l); then
                if [ "$targets" -eq 0 ]; then
                    check_result "PASS" "monitoring" "All Prometheus targets healthy"
                else
                    check_result "WARN" "monitoring" "Some Prometheus targets down" "$targets targets unhealthy"
                fi
            else
                check_result "WARN" "monitoring" "Unable to check Prometheus targets"
            fi
            
            kill $PORT_FORWARD_PID 2>/dev/null || true
        else
            check_result "WARN" "monitoring" "curl not available for Prometheus target check"
        fi
    else
        check_result "FAIL" "monitoring" "Monitoring stack not running"
    fi
}

# Security Posture Checks
check_security_posture() {
    log "\n${BLUE}🔒 Security Posture Checks${NC}"
    
    # Certificate expiration
    kubectl get certificates --all-namespaces -o json | jq -r '.items[] | select(.status.notAfter) | "\(.metadata.namespace)/\(.metadata.name) \(.status.notAfter)"' | while read -r cert_info; do
        cert_name=$(echo "$cert_info" | cut -d' ' -f1)
        expiry_date=$(echo "$cert_info" | cut -d' ' -f2)
        
        if [ -n "$expiry_date" ]; then
            expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || echo 0)
            current_timestamp=$(date +%s)
            days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [ "$days_until_expiry" -lt 7 ]; then
                check_result "FAIL" "security" "Certificate expiring soon" "$cert_name expires in $days_until_expiry days"
            elif [ "$days_until_expiry" -lt 30 ]; then
                check_result "WARN" "security" "Certificate expiring within 30 days" "$cert_name expires in $days_until_expiry days"
            else
                check_result "PASS" "security" "Certificate validity" "$cert_name expires in $days_until_expiry days"
            fi
        fi
    done
    
    # 1Password Connect status  
    if kubectl get pods -n secrets --no-headers 2>/dev/null | grep -q "Running"; then
        check_result "PASS" "security" "1Password Connect operational"
    else
        check_result "WARN" "security" "1Password Connect not running or namespace not found"
    fi
    
    # Secret audit (check for default service account tokens)
    default_secrets=$(kubectl get secrets --all-namespaces --no-headers | grep "default-token" | wc -l || echo 0)
    if [ "$default_secrets" -gt 0 ]; then
        check_result "WARN" "security" "Default service account tokens present" "$default_secrets found"
    else
        check_result "PASS" "security" "No default service account tokens"
    fi
    
    # RBAC validation
    cluster_admin_bindings=$(kubectl get clusterrolebindings -o json | jq -r '.items[] | select(.roleRef.name=="cluster-admin") | .metadata.name' | wc -l || echo 0)
    if [ "$cluster_admin_bindings" -gt 3 ]; then
        check_result "WARN" "security" "Many cluster-admin bindings" "$cluster_admin_bindings bindings found"
    else
        check_result "PASS" "security" "Cluster-admin bindings reasonable" "$cluster_admin_bindings bindings found"
    fi
}

# Performance Metrics
check_performance_metrics() {
    log "\n${BLUE}⚡ Performance Metrics${NC}"
    
    # API server response time
    start_time=$(date +%s%N)
    kubectl get nodes >/dev/null 2>&1
    end_time=$(date +%s%N)
    response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
    
    if [ "$response_time" -lt 1000 ]; then
        check_result "PASS" "performance" "API server response time" "${response_time}ms"
    elif [ "$response_time" -lt 3000 ]; then
        check_result "WARN" "performance" "API server response time" "${response_time}ms"
    else
        check_result "FAIL" "performance" "API server response time" "${response_time}ms"
    fi
    
    # Pod restart counts
    high_restart_pods=$(kubectl get pods --all-namespaces --no-headers | awk '$4 > 5 {print $1"/"$2": "$4}' | wc -l || echo 0)
    if [ "$high_restart_pods" -eq 0 ]; then
        check_result "PASS" "performance" "Pod restart counts normal"
    else
        check_result "WARN" "performance" "Pods with high restart counts" "$high_restart_pods pods restarted >5 times"
    fi
    
    # Persistent Volume usage
    kubectl get pvc --all-namespaces -o json | jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name) \(.status.capacity.storage // "unknown")"' | while read -r pvc_info; do
        pvc_name=$(echo "$pvc_info" | cut -d' ' -f1)
        capacity=$(echo "$pvc_info" | cut -d' ' -f2)
        
        if [ "$capacity" != "unknown" ]; then
            check_result "PASS" "performance" "PVC capacity" "$pvc_name: $capacity"
        else
            check_result "WARN" "performance" "PVC capacity unknown" "$pvc_name"
        fi
    done
}

# Backup Verification
check_backup_status() {
    log "\n${BLUE}💾 Backup Status Checks${NC}"
    
    # Check for backup jobs/cronjobs
    backup_jobs=$(kubectl get cronjobs --all-namespaces --no-headers | grep -i backup | wc -l || echo 0)
    if [ "$backup_jobs" -gt 0 ]; then
        check_result "PASS" "backup" "Backup jobs configured" "$backup_jobs backup jobs found"
        
        # Check last backup job runs
        kubectl get jobs --all-namespaces --no-headers | grep -i backup | while read -r job_line; do
            namespace=$(echo "$job_line" | awk '{print $1}')
            job_name=$(echo "$job_line" | awk '{print $2}')
            completions=$(echo "$job_line" | awk '{print $3}')
            
            if echo "$completions" | grep -q "1/1"; then
                check_result "PASS" "backup" "Backup job success" "$namespace/$job_name completed"
            else
                check_result "WARN" "backup" "Backup job status" "$namespace/$job_name status: $completions"
            fi
        done
    else
        check_result "WARN" "backup" "No backup jobs configured"
    fi
    
    # Check for Velero (if installed)
    if kubectl get ns velero >/dev/null 2>&1; then
        velero_backups=$(kubectl get backups -n velero --no-headers | wc -l || echo 0)
        if [ "$velero_backups" -gt 0 ]; then
            recent_backups=$(kubectl get backups -n velero --no-headers --sort-by='.metadata.creationTimestamp' | tail -5 | awk '{print $1": "$2}')
            check_result "PASS" "backup" "Velero backups present" "$velero_backups total backups"
        else
            check_result "WARN" "backup" "No Velero backups found"
        fi
    fi
}

# Network Health
check_network_health() {
    log "\n${BLUE}🌐 Network Health Checks${NC}"
    
    # Ingress controller status
    if kubectl get pods -n kube-system --no-headers | grep -q "traefik"; then
        traefik_pods=$(kubectl get pods -n kube-system --no-headers | grep traefik | grep -c "Running" || echo 0)
        if [ "$traefik_pods" -gt 0 ]; then
            check_result "PASS" "networking" "Traefik ingress controller running" "$traefik_pods pods"
        else
            check_result "FAIL" "networking" "Traefik ingress controller not running"
        fi
    else
        check_result "WARN" "networking" "Traefik ingress controller not found"
    fi
    
    # Service endpoints
    services_without_endpoints=$(kubectl get endpoints --all-namespaces --no-headers | awk '$3 == "<none>" {print $1"/"$2}' | wc -l || echo 0)
    if [ "$services_without_endpoints" -eq 0 ]; then
        check_result "PASS" "networking" "All services have endpoints"
    else
        check_result "WARN" "networking" "Services without endpoints" "$services_without_endpoints services affected"
    fi
    
    # CNI health (Cilium)
    if kubectl get pods -n kube-system --no-headers | grep -q "cilium"; then
        cilium_pods=$(kubectl get pods -n kube-system --no-headers | grep cilium | grep -c "Running" || echo 0)
        total_cilium=$(kubectl get pods -n kube-system --no-headers | grep cilium | wc -l || echo 0)
        
        if [ "$cilium_pods" -eq "$total_cilium" ] && [ "$total_cilium" -gt 0 ]; then
            check_result "PASS" "networking" "Cilium CNI healthy" "$cilium_pods/$total_cilium pods running"
        else
            check_result "FAIL" "networking" "Cilium CNI issues" "$cilium_pods/$total_cilium pods running"
        fi
    else
        check_result "WARN" "networking" "Cilium CNI not found"
    fi
}

# GitHub Actions health check
check_github_actions_health() {
    if [[ "$ENABLE_GITHUB_ACTIONS_CHECK" != "true" ]]; then
        return 0
    fi
    
    log "\n${BLUE}🔄 GitHub Actions Health Checks${NC}"
    
    if ! command -v gh >/dev/null 2>&1; then
        check_result "WARN" "github-actions" "GitHub CLI not available"
        return 0
    fi
    
    # Check recent workflow runs
    if workflow_runs=$(gh run list --limit 10 --json conclusion,name,createdAt 2>/dev/null); then
        total_runs=$(echo "$workflow_runs" | jq length)
        recent_failures=$(echo "$workflow_runs" | jq '[.[] | select(.conclusion == "failure")] | length')
        
        if [[ $recent_failures -gt 3 ]]; then
            check_result "WARN" "github-actions" "Multiple recent workflow failures" "$recent_failures failures in last 10 runs"
        else
            check_result "PASS" "github-actions" "Workflow failure rate acceptable" "$recent_failures failures in last 10 runs"
        fi
        
        # Check specific workflows
        validate_status=$(echo "$workflow_runs" | jq -r '.[] | select(.name == "🔍 Homelab Validation") | .conclusion' | head -1)
        security_status=$(echo "$workflow_runs" | jq -r '.[] | select(.name == "🔒 Security Scanning") | .conclusion' | head -1)
        
        if [[ "$validate_status" == "failure" ]]; then
            check_result "WARN" "github-actions" "Validation workflow failing"
        elif [[ "$validate_status" == "success" ]]; then
            check_result "PASS" "github-actions" "Validation workflow passing"
        fi
        
        if [[ "$security_status" == "failure" ]]; then
            check_result "WARN" "github-actions" "Security workflow failing"
        elif [[ "$security_status" == "success" ]]; then
            check_result "PASS" "github-actions" "Security workflow passing"
        fi
    else
        check_result "WARN" "github-actions" "Cannot access GitHub Actions (authentication or network issue)"
    fi
}

# Enhanced inventory security check
check_inventory_security() {
    if [[ "$ENABLE_INVENTORY_CHECK" != "true" ]]; then
        return 0
    fi
    
    log "\n${BLUE}🔍 Enhanced Security Assessment${NC}"
    
    if [[ -f "$HOMELAB_ROOT/scripts/inventory-check.py" ]]; then
        if inventory_output=$(cd "$HOMELAB_ROOT" && python scripts/inventory-check.py --format json 2>/dev/null); then
            security_score=$(echo "$inventory_output" | jq -r '.security_assessment.security_score // 100')
            cve_count=$(echo "$inventory_output" | jq -r '.security_assessment.total_cves // 0')
            high_risk_apps=$(echo "$inventory_output" | jq -r '.security_assessment.high_risk_applications // 0')
            
            if [[ $security_score -ge 90 ]] && [[ $high_risk_apps -eq 0 ]]; then
                check_result "PASS" "security" "Excellent security posture" "Score: $security_score/100, CVEs: $cve_count"
            elif [[ $security_score -ge 70 ]]; then
                check_result "WARN" "security" "Good security with minor issues" "Score: $security_score/100, High-risk apps: $high_risk_apps"
            else
                check_result "FAIL" "security" "Poor security posture" "Score: $security_score/100, CVEs: $cve_count, High-risk: $high_risk_apps"
            fi
            
            # Store inventory data for reporting
            echo "$inventory_output" > "${HOMELAB_ROOT}/logs/inventory-$(date +%Y%m%d).json"
        else
            check_result "WARN" "security" "Failed to run inventory security assessment"
        fi
    else
        check_result "WARN" "security" "Inventory check script not available"
    fi
}

# Generate enhanced health report
generate_report() {
    log "\n${BLUE}📊 Generating Enhanced Health Report${NC}"
    
    cat > "$REPORT_FILE" << EOF
# Homelab Health Report

**Generated**: $(date)  
**Cluster**: $(kubectl config current-context 2>/dev/null || echo "unknown")

## Summary

- **Total Checks**: $TOTAL_CHECKS
- **Passed**: $PASSED_CHECKS ✅
- **Failed**: $FAILED_CHECKS ❌  
- **Warnings**: $WARNING_CHECKS ⚠️

**Overall Health**: $(
    if [ "$FAILED_CHECKS" -eq 0 ] && [ "$WARNING_CHECKS" -eq 0 ]; then
        echo "🟢 Excellent"
    elif [ "$FAILED_CHECKS" -eq 0 ]; then
        echo "🟡 Good (warnings present)"
    elif [ "$FAILED_CHECKS" -lt 3 ]; then
        echo "🟠 Fair (issues need attention)"
    else
        echo "🔴 Poor (immediate action required)"
    fi
)

## Quick Stats

| Component | Status | Notes |
|-----------|--------|-------|
| Cluster Nodes | $(kubectl get nodes --no-headers | grep -c "Ready" || echo 0)/$(kubectl get nodes --no-headers | wc -l) Ready | $(kubectl get nodes --no-headers | head -1 | awk '{print $5}' || echo "unknown") |
| ArgoCD | $(kubectl get pods -n argocd --no-headers 2>/dev/null | grep -c "Running" || echo 0) pods | $(argocd app list 2>/dev/null | grep -c "Synced" || echo "unknown") apps synced |
| cert-manager | $(kubectl get pods -n cert-manager --no-headers 2>/dev/null | grep -c "Running" || echo 0) pods | $(kubectl get certificates --all-namespaces --no-headers 2>/dev/null | grep -c "True" || echo 0) certs ready |
| Monitoring | $(kubectl get pods -n monitoring --no-headers 2>/dev/null | grep -c "Running" || echo 0) pods | Prometheus/Grafana |

## Actions Required

EOF

    if [ "$FAILED_CHECKS" -gt 0 ]; then
        echo "### 🚨 Critical Issues" >> "$REPORT_FILE"
        grep "❌ FAIL" "$LOG_FILE" | sed 's/.*FAIL: /- /' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
    
    if [ "$WARNING_CHECKS" -gt 0 ]; then
        echo "### ⚠️ Warnings" >> "$REPORT_FILE"
        grep "⚠️  WARN" "$LOG_FILE" | sed 's/.*WARN: /- /' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
    
    cat >> "$REPORT_FILE" << EOF

## Next Steps

1. Address critical issues immediately
2. Plan resolution for warnings during next maintenance window
3. Review trends in upcoming health checks
4. Update monitoring dashboards as needed

---
*Generated by homelab health check automation*
EOF

    log "📄 Health report saved to: $REPORT_FILE"
    
    # Generate JSON report
    generate_json_report
}

# Generate JSON health report
generate_json_report() {
    local json_output="{"
    json_output+='"timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",'
    json_output+='"cluster": "'$(kubectl config current-context 2>/dev/null || echo 'unknown')'",'
    json_output+='"summary": {'
    json_output+='"total_checks": '$TOTAL_CHECKS','
    json_output+='"passed_checks": '$PASSED_CHECKS','
    json_output+='"failed_checks": '$FAILED_CHECKS','
    json_output+='"warning_checks": '$WARNING_CHECKS','
    json_output+='"health_percentage": '$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))'
    json_output+='},'
    json_output+='"components": {'
    
    local first=true
    for component in "${!COMPONENT_STATUS[@]}"; do
        if [[ $first == false ]]; then
            json_output+=','
        fi
        json_output+='"'$component'": {'
        json_output+='"status": "'${COMPONENT_STATUS[$component]}'",'
        json_output+='"details": "'${COMPONENT_DETAILS[$component]}'"}'
        first=false
    done
    
    json_output+='}}'
    
    echo "$json_output" | jq . > "$JSON_REPORT_FILE" 2>/dev/null || echo "$json_output" > "$JSON_REPORT_FILE"
    log "📄 JSON report saved to: $JSON_REPORT_FILE"
}

# Send alerts if critical issues found
send_alerts() {
    if [ "$FAILED_CHECKS" -gt 0 ] && [ -n "$ALERT_WEBHOOK" ]; then
        log "\n${BLUE}🚨 Sending Critical Alert${NC}"
        
        alert_payload=$(cat << EOF
{
  "content": "🚨 **Homelab Critical Issues Detected**",
  "embeds": [{
    "title": "Health Check Alert",
    "description": "Critical issues found in homelab infrastructure",
    "color": 15158332,
    "fields": [
      {"name": "Failed Checks", "value": "$FAILED_CHECKS", "inline": true},
      {"name": "Warnings", "value": "$WARNING_CHECKS", "inline": true},
      {"name": "Cluster", "value": "$(kubectl config current-context 2>/dev/null || echo 'unknown')", "inline": true}
    ],
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"
  }]
}
EOF
        )
        
        if curl -X POST -H "Content-Type: application/json" -d "$alert_payload" "$ALERT_WEBHOOK" >/dev/null 2>&1; then
            check_result "PASS" "alerts" "Alert sent successfully"
        else
            check_result "WARN" "alerts" "Failed to send alert"
        fi
    elif [ "$FAILED_CHECKS" -eq 0 ] && [ "$WARNING_CHECKS" -eq 0 ]; then
        log "\n${GREEN}🎉 All systems healthy - no alerts needed${NC}"
    else
        log "\n${YELLOW}⚠️ Issues found but no critical alerts configured${NC}"
    fi
}

# Main execution
main() {
    log "🏠 Homelab Health Check Starting - $(date)"
    log "Cluster: $(kubectl config current-context 2>/dev/null || echo 'unknown')"
    
    # Verify kubectl access
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log "${RED}❌ Unable to connect to Kubernetes cluster${NC}"
        exit 1
    fi
    
    # Run all health checks
    check_cluster_health
    check_application_health
    check_security_posture
    check_performance_metrics
    check_backup_status
    check_network_health
    check_github_actions_health
    check_inventory_security
    
    # Generate outputs
    generate_report
    send_alerts
    
    # Summary
    log "\n${BLUE}📋 Health Check Summary${NC}"
    log "Total Checks: $TOTAL_CHECKS"
    log "${GREEN}Passed: $PASSED_CHECKS${NC}"
    log "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    log "${RED}Failed: $FAILED_CHECKS${NC}"
    
    # Component summary
    log "\n${BLUE}🔍 Component Status Overview:${NC}"
    for component in "${!COMPONENT_STATUS[@]}"; do
        local status="${COMPONENT_STATUS[$component]}"
        local icon
        case $status in
            "PASS") icon="✅" ;;
            "WARN") icon="⚠️ " ;;
            "FAIL") icon="❌" ;;
            *) icon="❓" ;;
        esac
        printf "   %-20s %s %s\n" "$component" "$icon" "$status"
    done
    
    # Output final report based on format
    case "$FORMAT" in
        "json")
            if [[ -n "$OUTPUT_FILE" ]]; then
                cp "$JSON_REPORT_FILE" "$OUTPUT_FILE"
                log "\n📄 JSON output written to: $OUTPUT_FILE"
            fi
            ;;
        "markdown")
            if [[ -n "$OUTPUT_FILE" ]]; then
                cp "$REPORT_FILE" "$OUTPUT_FILE"
                log "\n📄 Markdown output written to: $OUTPUT_FILE"
            fi
            ;;
    esac
    
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        log "\n${GREEN}🎉 Health check completed successfully!${NC}"
        exit 0
    else
        log "\n${RED}🚨 Health check found critical issues!${NC}"
        exit 1
    fi
}

# Enhanced argument parsing
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --component)
                COMPONENT_FILTER="$2"
                shift 2
                ;;
            --no-github-actions)
                ENABLE_GITHUB_ACTIONS_CHECK=false
                shift
                ;;
            --no-inventory)
                ENABLE_INVENTORY_CHECK=false
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            check|report|help)
                # Legacy command handling
                break
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Homelab Health Check Script - Enhanced Version

USAGE:
    $0 [OPTIONS] [COMMAND]

OPTIONS:
    --format FORMAT         Output format: summary, json, or markdown (default: summary)
    --output FILE           Write output to file instead of stdout
    --component COMP        Check specific component only
    --no-github-actions     Skip GitHub Actions health checks
    --no-inventory          Skip inventory security assessment
    --help, -h              Show this help message

COMPONENTS:
    cluster                 Kubernetes cluster health
    argocd                  ArgoCD applications and sync status
    certificates            cert-manager certificate status
    monitoring              Monitoring stack health
    networking              Network connectivity and ingress
    storage                 Persistent volume status
    security                Security posture assessment
    performance             Performance metrics
    backup                  Backup status and verification
    github-actions          GitHub Actions workflow status

LEGACY COMMANDS:
    check                   Run full health check (default)
    report                  Generate health report only
    help                    Show this help message

EXAMPLES:
    $0                                      # Quick health summary
    $0 --format json --output health.json  # JSON report to file
    $0 --component argocd                   # Check only ArgoCD
    $0 --format markdown                    # Detailed markdown report
    $0 --no-github-actions check           # Skip GitHub Actions checks

ENVIRONMENT VARIABLES:
    DISCORD_WEBHOOK_URL     Discord webhook for alerts

OUTPUT FILES:
    Log: ${LOG_FILE}
    Report: ${REPORT_FILE}
    JSON: ${JSON_REPORT_FILE}

EXIT CODES:
    0    All checks passed
    1    Some issues detected (warnings or failures)
EOF
}

# Handle script arguments with enhanced parsing
parse_args "$@"

# Main execution logic
case "${1:-check}" in
    "check")
        main
        ;;
    "report")
        case "$FORMAT" in
            "json")
                generate_json_report
                if [[ -n "$OUTPUT_FILE" ]]; then
                    cp "$JSON_REPORT_FILE" "$OUTPUT_FILE"
                else
                    cat "$JSON_REPORT_FILE"
                fi
                ;;
            *)
                generate_report
                if [[ -n "$OUTPUT_FILE" ]]; then
                    cp "$REPORT_FILE" "$OUTPUT_FILE"
                else
                    cat "$REPORT_FILE"
                fi
                ;;
        esac
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac