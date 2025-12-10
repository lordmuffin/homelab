#!/bin/bash
# Comprehensive Cluster Health Monitor with Failover Automation
# Monitors all single-node clusters and triggers automated recovery

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/cluster-health-monitor.log"
HEALTH_DIR="/var/lib/homelab/health"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

# Node configuration
declare -A NODES=(
    ["node1-compute"]="10.0.1.101"
    ["node2-storage"]="10.0.1.102"
    ["node3-general"]="10.0.1.103"
)

# Load balancer configuration
LB_VIP="10.0.1.100"
LB_PRIMARY="10.0.1.10"
LB_BACKUP="10.0.1.11"

# Health check thresholds
CPU_THRESHOLD=85
MEMORY_THRESHOLD=85
DISK_THRESHOLD=85
API_TIMEOUT=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Initialize health directory
mkdir -p "${HEALTH_DIR}"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "${LOG_FILE}"
}

# Send alert notification
send_alert() {
    local severity="$1"
    local message="$2"
    local node="${3:-all}"
    
    # Write to health status file
    echo "{
        \"timestamp\": \"$(date -Iseconds)\",
        \"severity\": \"$severity\",
        \"node\": \"$node\",
        \"message\": \"$message\"
    }" > "${HEALTH_DIR}/last_alert.json"
    
    # Send webhook notification if configured
    if [[ -n "${ALERT_WEBHOOK}" ]]; then
        curl -X POST "${ALERT_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"🚨 HomeLab Alert [$severity]\",
                \"attachments\": [{
                    \"color\": \"$([ "$severity" = "critical" ] && echo "danger" || echo "warning")\",
                    \"fields\": [{
                        \"title\": \"Node\",
                        \"value\": \"$node\",
                        \"short\": true
                    }, {
                        \"title\": \"Message\",
                        \"value\": \"$message\",
                        \"short\": false
                    }]
                }]
            }" || true
    fi
    
    # Log alert
    log_error "ALERT [$severity] $node: $message"
}

# Check load balancer health
check_load_balancer() {
    local health_status="healthy"
    local details=""
    
    # Check VIP accessibility
    if ! curl -s --max-time 5 "http://${LB_VIP}:8404/stats" > /dev/null; then
        health_status="unhealthy"
        details="VIP not accessible"
        send_alert "critical" "Load balancer VIP ${LB_VIP} not responding" "load-balancer"
        return 1
    fi
    
    # Check backend servers
    local backend_status
    backend_status=$(curl -s --max-time 5 "http://${LB_VIP}:8404/stats" | grep -c "UP" || echo "0")
    
    if [[ "${backend_status}" -eq 0 ]]; then
        health_status="unhealthy"
        details="No backend servers available"
        send_alert "critical" "No backend servers available in load balancer" "load-balancer"
        return 1
    fi
    
    # Write health status
    echo "{
        \"component\": \"load_balancer\",
        \"status\": \"$health_status\",
        \"timestamp\": \"$(date -Iseconds)\",
        \"details\": \"$details\",
        \"backends_up\": $backend_status
    }" > "${HEALTH_DIR}/load_balancer.json"
    
    log_success "Load balancer health: $health_status ($backend_status backends up)"
    return 0
}

# Check individual node health
check_node_health() {
    local node_name="$1"
    local node_ip="$2"
    local health_status="healthy"
    local issues=()
    
    # Check network connectivity
    if ! ping -c 1 -W 3 "${node_ip}" > /dev/null 2>&1; then
        health_status="unhealthy"
        issues+=("Network unreachable")
        send_alert "critical" "Node network unreachable" "$node_name"
    else
        # Check SSH connectivity
        if ! ssh -o ConnectTimeout=5 root@"${node_ip}" "echo test" > /dev/null 2>&1; then
            health_status="degraded"
            issues+=("SSH unreachable")
            send_alert "warning" "SSH connectivity failed" "$node_name"
        else
            # Check Kubernetes API
            if ! ssh root@"${node_ip}" "timeout ${API_TIMEOUT} kubectl get nodes" > /dev/null 2>&1; then
                health_status="unhealthy"
                issues+=("Kubernetes API failed")
                send_alert "critical" "Kubernetes API not responding" "$node_name"
            else
                # Check resource utilization
                local cpu_usage memory_usage disk_usage
                
                # Get CPU usage
                cpu_usage=$(ssh root@"${node_ip}" "top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | cut -d'%' -f1" 2>/dev/null || echo "0")
                cpu_usage=${cpu_usage%.*}  # Remove decimal part
                
                if [[ "${cpu_usage}" -gt "${CPU_THRESHOLD}" ]]; then
                    health_status="degraded"
                    issues+=("High CPU usage: ${cpu_usage}%")
                    send_alert "warning" "High CPU usage: ${cpu_usage}%" "$node_name"
                fi
                
                # Get memory usage
                memory_usage=$(ssh root@"${node_ip}" "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2 * 100}'" 2>/dev/null || echo "0")
                
                if [[ "${memory_usage}" -gt "${MEMORY_THRESHOLD}" ]]; then
                    health_status="degraded"
                    issues+=("High memory usage: ${memory_usage}%")
                    send_alert "warning" "High memory usage: ${memory_usage}%" "$node_name"
                fi
                
                # Get disk usage
                disk_usage=$(ssh root@"${node_ip}" "df / | tail -1 | awk '{print \$5}' | cut -d'%' -f1" 2>/dev/null || echo "0")
                
                if [[ "${disk_usage}" -gt "${DISK_THRESHOLD}" ]]; then
                    health_status="degraded"
                    issues+=("High disk usage: ${disk_usage}%")
                    send_alert "warning" "High disk usage: ${disk_usage}%" "$node_name"
                fi
                
                # Check critical pods
                local critical_pods
                critical_pods=$(ssh root@"${node_ip}" "kubectl get pods -A | grep -E '(traefik|democratic-csi|flux-system)' | grep -v Running | wc -l" 2>/dev/null || echo "1")
                
                if [[ "${critical_pods}" -gt 0 ]]; then
                    health_status="degraded"
                    issues+=("${critical_pods} critical pods not running")
                    send_alert "warning" "${critical_pods} critical pods not running" "$node_name"
                fi
                
                # Write detailed health status
                echo "{
                    \"component\": \"$node_name\",
                    \"status\": \"$health_status\",
                    \"timestamp\": \"$(date -Iseconds)\",
                    \"ip_address\": \"$node_ip\",
                    \"issues\": [$(printf '\"%s\",' "${issues[@]}" | sed 's/,$//')]",
                    \"metrics\": {
                        \"cpu_usage\": $cpu_usage,
                        \"memory_usage\": $memory_usage,
                        \"disk_usage\": $disk_usage,
                        \"critical_pods_down\": $critical_pods
                    }
                }" > "${HEALTH_DIR}/${node_name}.json"
            fi
        fi
    fi
    
    if [[ "$health_status" == "healthy" ]]; then
        log_success "Node $node_name health: $health_status"
    else
        log_warning "Node $node_name health: $health_status (${issues[*]})"
    fi
    
    return 0
}

# Check service-specific health
check_service_health() {
    local service_name="$1"
    local namespace="$2"
    local target_node="${3:-any}"
    
    # Determine which node to check
    local check_node
    if [[ "$target_node" == "any" ]]; then
        # Find a healthy node
        for node in "${!NODES[@]}"; do
            if [[ -f "${HEALTH_DIR}/${node}.json" ]]; then
                local node_status
                node_status=$(jq -r '.status' "${HEALTH_DIR}/${node}.json")
                if [[ "$node_status" == "healthy" ]]; then
                    check_node="${NODES[$node]}"
                    break
                fi
            fi
        done
    else
        check_node="${NODES[$target_node]}"
    fi
    
    if [[ -z "$check_node" ]]; then
        send_alert "critical" "No healthy nodes available to check service $service_name" "cluster"
        return 1
    fi
    
    # Check service status
    local service_health="healthy"
    local pod_count ready_pods
    
    pod_count=$(ssh root@"${check_node}" "kubectl get pods -n $namespace -l app.kubernetes.io/name=$service_name --no-headers 2>/dev/null | wc -l" || echo "0")
    ready_pods=$(ssh root@"${check_node}" "kubectl get pods -n $namespace -l app.kubernetes.io/name=$service_name --no-headers 2>/dev/null | grep Running | wc -l" || echo "0")
    
    if [[ "$pod_count" -eq 0 ]]; then
        service_health="missing"
        send_alert "critical" "Service $service_name not found in namespace $namespace" "$target_node"
    elif [[ "$ready_pods" -eq 0 ]]; then
        service_health="unhealthy"
        send_alert "critical" "Service $service_name has no running pods" "$target_node"
    elif [[ "$ready_pods" -lt "$pod_count" ]]; then
        service_health="degraded"
        send_alert "warning" "Service $service_name has $ready_pods/$pod_count pods ready" "$target_node"
    fi
    
    # Write service health status
    echo "{
        \"service\": \"$service_name\",
        \"namespace\": \"$namespace\",
        \"status\": \"$service_health\",
        \"timestamp\": \"$(date -Iseconds)\",
        \"checked_node\": \"$check_node\",
        \"pods_total\": $pod_count,
        \"pods_ready\": $ready_pods
    }" > "${HEALTH_DIR}/service_${service_name}.json"
    
    if [[ "$service_health" == "healthy" ]]; then
        log_success "Service $service_name health: $service_health ($ready_pods/$pod_count pods ready)"
    else
        log_warning "Service $service_name health: $service_health ($ready_pods/$pod_count pods ready)"
    fi
    
    return 0
}

# Automated recovery actions
attempt_recovery() {
    local component="$1"
    local issue="$2"
    
    log "Attempting automated recovery for $component: $issue"
    
    case "$component" in
        "load-balancer")
            # Restart HAProxy service
            log "Restarting HAProxy on primary LB..."
            ssh root@"${LB_PRIMARY}" "systemctl restart haproxy" || true
            ssh root@"${LB_PRIMARY}" "systemctl restart keepalived" || true
            sleep 30
            check_load_balancer
            ;;
            
        node*)
            local node_ip="${NODES[$component]}"
            
            if [[ "$issue" =~ "Kubernetes API" ]]; then
                log "Restarting K3s on $component..."
                ssh root@"${node_ip}" "systemctl restart k3s" || true
                sleep 60
                check_node_health "$component" "$node_ip"
                
            elif [[ "$issue" =~ "High disk usage" ]]; then
                log "Cleaning up disk space on $component..."
                ssh root@"${node_ip}" "
                    docker system prune -f
                    kubectl delete pods --field-selector=status.phase=Succeeded -A
                    journalctl --vacuum-time=7d
                " || true
                sleep 30
                check_node_health "$component" "$node_ip"
                
            elif [[ "$issue" =~ "critical pods" ]]; then
                log "Restarting critical pods on $component..."
                ssh root@"${node_ip}" "
                    kubectl rollout restart deployment -n traefik-system
                    kubectl rollout restart deployment -n democratic-csi
                    kubectl rollout restart deployment -n flux-system
                " || true
                sleep 60
                check_node_health "$component" "$node_ip"
            fi
            ;;
            
        service*)
            local service_name="${component#service_}"
            log "Attempting service recovery for $service_name..."
            
            # Find healthy node to execute recovery
            for node in "${!NODES[@]}"; do
                local node_status
                node_status=$(jq -r '.status' "${HEALTH_DIR}/${node}.json" 2>/dev/null || echo "unknown")
                if [[ "$node_status" == "healthy" ]]; then
                    ssh root@"${NODES[$node]}" "
                        kubectl rollout restart deployment -l app.kubernetes.io/name=$service_name -A
                        kubectl delete pods -l app.kubernetes.io/name=$service_name -A --grace-period=0 --force
                    " || true
                    break
                fi
            done
            ;;
    esac
    
    log "Recovery attempt completed for $component"
}

# Generate health report
generate_health_report() {
    local report_file="${HEALTH_DIR}/health_report_$(date +%Y%m%d_%H%M%S).json"
    
    # Collect all health data
    local health_data="{
        \"timestamp\": \"$(date -Iseconds)\",
        \"cluster_status\": \"healthy\",
        \"components\": {"
    
    # Load balancer status
    if [[ -f "${HEALTH_DIR}/load_balancer.json" ]]; then
        health_data+='"load_balancer": '$(cat "${HEALTH_DIR}/load_balancer.json")','
    fi
    
    # Node statuses
    for node in "${!NODES[@]}"; do
        if [[ -f "${HEALTH_DIR}/${node}.json" ]]; then
            health_data+='"'${node}'": '$(cat "${HEALTH_DIR}/${node}.json")','
        fi
    done
    
    # Service statuses
    for service_file in "${HEALTH_DIR}"/service_*.json; do
        if [[ -f "$service_file" ]]; then
            local service_name
            service_name=$(basename "$service_file" .json)
            health_data+='"'${service_name}'": '$(cat "$service_file")','
        fi
    done
    
    # Remove trailing comma and close JSON
    health_data="${health_data%,}"
    health_data+="}}"
    
    # Determine overall cluster status
    local overall_status="healthy"
    if grep -q '"status": "unhealthy"' "${HEALTH_DIR}"/*.json 2>/dev/null; then
        overall_status="unhealthy"
    elif grep -q '"status": "degraded"' "${HEALTH_DIR}"/*.json 2>/dev/null; then
        overall_status="degraded"
    fi
    
    # Update cluster status
    health_data=$(echo "$health_data" | jq --arg status "$overall_status" '.cluster_status = $status')
    
    # Write report
    echo "$health_data" > "$report_file"
    ln -sf "$report_file" "${HEALTH_DIR}/latest_health_report.json"
    
    log "Health report generated: $report_file"
    echo "Overall cluster status: $overall_status"
}

# Main health check function
main_health_check() {
    log "Starting comprehensive cluster health check..."
    
    # Check load balancer
    check_load_balancer
    
    # Check all nodes
    for node in "${!NODES[@]}"; do
        check_node_health "$node" "${NODES[$node]}" &
    done
    
    # Wait for node checks to complete
    wait
    
    # Check critical services
    check_service_health "traefik" "traefik-system" &
    check_service_health "democratic-csi" "democratic-csi" &
    check_service_health "prometheus" "monitoring" &
    check_service_health "grafana" "monitoring" &
    
    # Wait for service checks to complete
    wait
    
    # Generate health report
    generate_health_report
    
    log "Health check cycle completed"
}

# Continuous monitoring mode
continuous_monitor() {
    local interval="${1:-300}"  # Default 5 minutes
    
    log "Starting continuous monitoring (interval: ${interval}s)"
    
    while true; do
        main_health_check
        
        # Check if automated recovery is enabled
        if [[ "${AUTO_RECOVERY:-false}" == "true" ]]; then
            # Look for unhealthy components and attempt recovery
            for health_file in "${HEALTH_DIR}"/*.json; do
                if [[ -f "$health_file" ]]; then
                    local status
                    status=$(jq -r '.status' "$health_file" 2>/dev/null || echo "unknown")
                    
                    if [[ "$status" == "unhealthy" ]]; then
                        local component
                        component=$(basename "$health_file" .json)
                        local last_issue
                        last_issue=$(jq -r '.issues[0] // .details // "unknown issue"' "$health_file" 2>/dev/null)
                        
                        attempt_recovery "$component" "$last_issue"
                    fi
                fi
            done
        fi
        
        sleep "$interval"
    done
}

# Handle script arguments
case "${1:-}" in
    "check")
        main_health_check
        ;;
    "monitor")
        continuous_monitor "${2:-300}"
        ;;
    "report")
        generate_health_report
        cat "${HEALTH_DIR}/latest_health_report.json"
        ;;
    "recover")
        attempt_recovery "${2:-}" "${3:-manual recovery}"
        ;;
    *)
        echo "Usage: $0 {check|monitor [interval]|report|recover <component> [issue]}"
        echo ""
        echo "Commands:"
        echo "  check                    - Single health check cycle"
        echo "  monitor [interval]       - Continuous monitoring (default 300s)"
        echo "  report                   - Generate and display health report"
        echo "  recover <component>      - Attempt recovery for specific component"
        echo ""
        echo "Environment Variables:"
        echo "  AUTO_RECOVERY=true       - Enable automated recovery"
        echo "  ALERT_WEBHOOK=<url>      - Send alerts to webhook"
        exit 1
        ;;
esac