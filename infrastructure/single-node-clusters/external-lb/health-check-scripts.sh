#!/bin/bash
# Health Check Scripts for HAProxy + Keepalived
# Creates monitoring scripts for high availability

set -euo pipefail

SCRIPT_DIR="/usr/local/bin"
LOG_DIR="/var/log/keepalived"

# Create log directory
mkdir -p "${LOG_DIR}"

# ======================================================================
# HAProxy Health Check Script
# ======================================================================
cat > "${SCRIPT_DIR}/check_haproxy.sh" << 'EOF'
#!/bin/bash
# HAProxy health check for Keepalived
# Returns 0 if HAProxy is healthy, 1 if unhealthy

set -euo pipefail

HAPROXY_STATS_URL="http://localhost:8404/stats"
LOG_FILE="/var/log/keepalived/haproxy_check.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_FILE}"
}

# Check if HAProxy process is running
if ! pgrep haproxy >/dev/null 2>&1; then
    log_message "ERROR: HAProxy process not running"
    exit 1
fi

# Check if HAProxy stats endpoint is responding
if ! curl -s --max-time 3 "${HAPROXY_STATS_URL}" >/dev/null; then
    log_message "ERROR: HAProxy stats endpoint not responding"
    exit 1
fi

# Check if any backend servers are available
backend_status=$(curl -s --max-time 3 "${HAPROXY_STATS_URL};csv" | grep -E "ai_cluster|media_cluster|general_cluster" | grep -c "UP" || echo "0")

if [[ "${backend_status}" -eq 0 ]]; then
    log_message "ERROR: No backend servers available"
    exit 1
fi

# Check HAProxy configuration syntax
if ! haproxy -c -f /etc/haproxy/haproxy.cfg >/dev/null 2>&1; then
    log_message "ERROR: HAProxy configuration syntax error"
    exit 1
fi

log_message "INFO: HAProxy health check passed (${backend_status} backends UP)"
exit 0
EOF

# ======================================================================
# Network Connectivity Health Check Script
# ======================================================================
cat > "${SCRIPT_DIR}/check_network.sh" << 'EOF'
#!/bin/bash
# Network connectivity health check for Keepalived
# Returns 0 if network connectivity is healthy, 1 if unhealthy

set -euo pipefail

LOG_FILE="/var/log/keepalived/network_check.log"
GATEWAY="10.0.1.1"
DNS_SERVER="1.1.1.1"
KUBERNETES_NODES=("10.0.1.101" "10.0.1.102" "10.0.1.103")

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "${LOG_FILE}"
}

# Check gateway connectivity
if ! ping -c 1 -W 3 "${GATEWAY}" >/dev/null 2>&1; then
    log_message "ERROR: Gateway ${GATEWAY} unreachable"
    exit 1
fi

# Check DNS connectivity
if ! ping -c 1 -W 3 "${DNS_SERVER}" >/dev/null 2>&1; then
    log_message "ERROR: DNS server ${DNS_SERVER} unreachable"
    exit 1
fi

# Check connectivity to at least one Kubernetes node
reachable_nodes=0
for node in "${KUBERNETES_NODES[@]}"; do
    if ping -c 1 -W 2 "${node}" >/dev/null 2>&1; then
        ((reachable_nodes++))
    fi
done

if [[ "${reachable_nodes}" -eq 0 ]]; then
    log_message "ERROR: No Kubernetes nodes reachable"
    exit 1
fi

log_message "INFO: Network health check passed (${reachable_nodes}/${#KUBERNETES_NODES[@]} nodes reachable)"
exit 0
EOF

# ======================================================================
# Master Notification Script
# ======================================================================
cat > "${SCRIPT_DIR}/notify_master.sh" << 'EOF'
#!/bin/bash
# Keepalived master state notification script

set -euo pipefail

LOG_FILE="/var/log/keepalived/state_changes.log"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the state change
echo "${TIMESTAMP} - ${HOSTNAME} - MASTER state activated" >> "${LOG_FILE}"

# Update DNS records (if using external DNS)
# /usr/local/bin/update_dns.sh master

# Send notification (optional - uncomment if needed)
# curl -X POST "https://discord.com/api/webhooks/YOUR_WEBHOOK" \
#      -H "Content-Type: application/json" \
#      -d "{\"content\": \"🟢 Load Balancer MASTER: ${HOSTNAME} is now active\"}"

# Start or restart services that should only run on master
systemctl enable --now haproxy
systemctl restart haproxy

# Update local routing if needed
ip route add default via 10.0.1.1 dev eth0 metric 1 2>/dev/null || true

exit 0
EOF

# ======================================================================
# Backup Notification Script
# ======================================================================
cat > "${SCRIPT_DIR}/notify_backup.sh" << 'EOF'
#!/bin/bash
# Keepalived backup state notification script

set -euo pipefail

LOG_FILE="/var/log/keepalived/state_changes.log"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the state change
echo "${TIMESTAMP} - ${HOSTNAME} - BACKUP state activated" >> "${LOG_FILE}"

# Send notification (optional)
# curl -X POST "https://discord.com/api/webhooks/YOUR_WEBHOOK" \
#      -H "Content-Type: application/json" \
#      -d "{\"content\": \"🟡 Load Balancer BACKUP: ${HOSTNAME} is now standby\"}"

# Keep HAProxy running but in backup mode
systemctl enable haproxy
# Don't restart HAProxy in backup mode to avoid service interruption

exit 0
EOF

# ======================================================================
# Fault Notification Script
# ======================================================================
cat > "${SCRIPT_DIR}/notify_fault.sh" << 'EOF'
#!/bin/bash
# Keepalived fault state notification script

set -euo pipefail

LOG_FILE="/var/log/keepalived/state_changes.log"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the state change
echo "${TIMESTAMP} - ${HOSTNAME} - FAULT state detected" >> "${LOG_FILE}"

# Send urgent notification
# curl -X POST "https://discord.com/api/webhooks/YOUR_WEBHOOK" \
#      -H "Content-Type: application/json" \
#      -d "{\"content\": \"🔴 URGENT: Load Balancer FAULT on ${HOSTNAME} - Manual intervention required\"}"

# Attempt basic recovery
systemctl restart keepalived
systemctl restart haproxy

# Log system status for debugging
{
    echo "=== System Status at Fault ==="
    echo "Date: ${TIMESTAMP}"
    echo "Hostname: ${HOSTNAME}"
    echo ""
    echo "Network interfaces:"
    ip addr show
    echo ""
    echo "Routing table:"
    ip route show
    echo ""
    echo "HAProxy status:"
    systemctl status haproxy --no-pager
    echo ""
    echo "Keepalived status:"
    systemctl status keepalived --no-pager
} >> "${LOG_FILE}"

exit 0
EOF

# ======================================================================
# Log Rotation Script
# ======================================================================
cat > "${SCRIPT_DIR}/rotate_keepalived_logs.sh" << 'EOF'
#!/bin/bash
# Log rotation for Keepalived health check logs

set -euo pipefail

LOG_DIR="/var/log/keepalived"
MAX_LOG_SIZE=10485760  # 10MB in bytes
MAX_LOG_FILES=5

for log_file in "${LOG_DIR}"/*.log; do
    if [[ -f "${log_file}" ]]; then
        log_size=$(stat -f%z "${log_file}" 2>/dev/null || stat -c%s "${log_file}" 2>/dev/null || echo 0)
        
        if [[ "${log_size}" -gt "${MAX_LOG_SIZE}" ]]; then
            # Rotate logs
            for i in $(seq $((MAX_LOG_FILES-1)) -1 1); do
                if [[ -f "${log_file}.${i}" ]]; then
                    mv "${log_file}.${i}" "${log_file}.$((i+1))"
                fi
            done
            
            mv "${log_file}" "${log_file}.1"
            touch "${log_file}"
            
            # Remove oldest logs
            if [[ -f "${log_file}.${MAX_LOG_FILES}" ]]; then
                rm -f "${log_file}.${MAX_LOG_FILES}"
            fi
        fi
    fi
done
EOF

# ======================================================================
# Make all scripts executable
# ======================================================================
chmod +x "${SCRIPT_DIR}"/check_*.sh
chmod +x "${SCRIPT_DIR}"/notify_*.sh
chmod +x "${SCRIPT_DIR}"/rotate_keepalived_logs.sh

# ======================================================================
# Create systemd service for log rotation
# ======================================================================
cat > /etc/systemd/system/keepalived-log-rotation.service << 'EOF'
[Unit]
Description=Keepalived Log Rotation
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/rotate_keepalived_logs.sh
User=root
Group=root
EOF

cat > /etc/systemd/system/keepalived-log-rotation.timer << 'EOF'
[Unit]
Description=Keepalived Log Rotation Timer
Requires=keepalived-log-rotation.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable log rotation timer
systemctl daemon-reload
systemctl enable --now keepalived-log-rotation.timer

echo "✅ Health check scripts created and configured successfully!"
echo "📍 Scripts location: ${SCRIPT_DIR}"
echo "📍 Logs location: ${LOG_DIR}"
echo "📍 Log rotation: Enabled (daily)"