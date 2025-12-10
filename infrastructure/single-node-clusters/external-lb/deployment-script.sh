#!/bin/bash
# External Load Balancer Deployment Script
# Deploys HAProxy + Keepalived for Single-Node Kubernetes Clusters

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/lb-deployment.log"
VIP="10.0.1.100"
BACKUP_IP="10.0.1.11"
PRIMARY_IP="10.0.1.10"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    # Update package list
    apt-get update -qq
    
    # Install required packages
    apt-get install -y \
        docker.io \
        docker-compose \
        curl \
        wget \
        net-tools \
        iputils-ping \
        tcpdump \
        iptables-persistent \
        ufw \
        jq
    
    # Start and enable Docker
    systemctl enable --now docker
    
    # Add current user to docker group (if not root)
    if [[ "${SUDO_USER:-}" ]]; then
        usermod -aG docker "${SUDO_USER}"
        log_warning "Please logout and login again for docker group changes to take effect"
    fi
    
    log_success "Dependencies installed successfully"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful not to lock yourself out)
    ufw allow 22/tcp
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow Kubernetes API
    ufw allow 6443/tcp
    
    # Allow HAProxy stats
    ufw allow 8404/tcp
    
    # Allow Prometheus metrics
    ufw allow 9101/tcp
    
    # Allow VRRP (Keepalived)
    ufw allow in on eth0 to 224.0.0.0/8
    ufw allow in on eth0 from 10.0.1.0/24
    
    # Allow log aggregation
    ufw allow 24224
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured successfully"
}

# Create SSL certificate directory and self-signed certs
setup_ssl() {
    log "Setting up SSL certificates..."
    
    mkdir -p "${SCRIPT_DIR}/ssl-certs"
    
    # Create self-signed certificate for testing (replace with real certs in production)
    if [[ ! -f "${SCRIPT_DIR}/ssl-certs/homelab.pem" ]]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "${SCRIPT_DIR}/ssl-certs/homelab.key" \
            -out "${SCRIPT_DIR}/ssl-certs/homelab.crt" \
            -subj "/C=US/ST=Home/L=Lab/O=HomeLab/CN=*.homelab.local" \
            -addext "subjectAltName = DNS:*.homelab.local,DNS:homelab.local,IP:${VIP}"
        
        # Combine certificate and key for HAProxy
        cat "${SCRIPT_DIR}/ssl-certs/homelab.crt" "${SCRIPT_DIR}/ssl-certs/homelab.key" \
            > "${SCRIPT_DIR}/ssl-certs/homelab.pem"
        
        chmod 600 "${SCRIPT_DIR}/ssl-certs/"*
        log_success "Self-signed SSL certificate created"
        log_warning "Replace with proper certificates in production"
    else
        log "SSL certificates already exist, skipping creation"
    fi
}

# Create error pages
create_error_pages() {
    log "Creating custom error pages..."
    
    mkdir -p "${SCRIPT_DIR}/errors"
    
    # 503 Service Unavailable
    cat > "${SCRIPT_DIR}/errors/503.http" << 'EOF'
HTTP/1.0 503 Service Unavailable
Content-Type: text/html
Cache-Control: no-cache
Connection: close

<!DOCTYPE html>
<html>
<head>
    <title>Service Temporarily Unavailable</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .error-container { max-width: 600px; margin: 0 auto; }
        .error-code { font-size: 72px; color: #e74c3c; margin-bottom: 20px; }
        .error-message { font-size: 24px; color: #2c3e50; margin-bottom: 30px; }
        .error-details { color: #7f8c8d; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">503</div>
        <div class="error-message">Service Temporarily Unavailable</div>
        <div class="error-details">
            <p>The Kubernetes cluster is currently unavailable. This may be due to:</p>
            <ul>
                <li>Scheduled maintenance</li>
                <li>Node failure or restart</li>
                <li>Network connectivity issues</li>
            </ul>
            <p>Please try again in a few moments.</p>
        </div>
    </div>
</body>
</html>
EOF

    # 502 Bad Gateway
    cat > "${SCRIPT_DIR}/errors/502.http" << 'EOF'
HTTP/1.0 502 Bad Gateway
Content-Type: text/html
Cache-Control: no-cache
Connection: close

<!DOCTYPE html>
<html>
<head>
    <title>Bad Gateway</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .error-container { max-width: 600px; margin: 0 auto; }
        .error-code { font-size: 72px; color: #e67e22; margin-bottom: 20px; }
        .error-message { font-size: 24px; color: #2c3e50; margin-bottom: 30px; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">502</div>
        <div class="error-message">Bad Gateway</div>
        <p>Unable to connect to the Kubernetes cluster backend.</p>
    </div>
</body>
</html>
EOF

    log_success "Error pages created successfully"
}

# Create fluentd configuration
create_fluentd_config() {
    log "Creating fluentd configuration..."
    
    cat > "${SCRIPT_DIR}/fluentd.conf" << 'EOF'
<source>
  @type tail
  path /var/log/haproxy/*.log
  pos_file /var/log/fluentd/haproxy.log.pos
  tag haproxy.access
  format /^(?<time>[^\]]*)\] (?<process_name>[^\[]*)\[(?<pid>[^\]]*)\]: (?<message>.*)$/
  time_format %d/%b/%Y:%H:%M:%S.%L
</source>

<source>
  @type tail
  path /var/log/keepalived/*.log
  pos_file /var/log/fluentd/keepalived.log.pos
  tag keepalived.status
  format /^(?<time>[^ ]* [^ ]*) - (?<message>.*)$/
  time_format %Y-%m-%d %H:%M:%S
</source>

<match haproxy.**>
  @type file
  path /var/log/fluentd/haproxy
  append true
  time_slice_format %Y%m%d
  time_slice_wait 10m
  time_format %Y%m%dT%H%M%S%z
</match>

<match keepalived.**>
  @type file  
  path /var/log/fluentd/keepalived
  append true
  time_slice_format %Y%m%d
  time_slice_wait 10m
  time_format %Y%m%dT%H%M%S%z
</match>
EOF

    log_success "Fluentd configuration created successfully"
}

# Configure network settings
configure_network() {
    log "Configuring network settings..."
    
    # Enable IP forwarding
    echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip-forward.conf
    sysctl -p /etc/sysctl.d/99-ip-forward.conf
    
    # Configure keepalived for the current host
    CURRENT_IP=$(ip route get 8.8.8.8 | awk 'NR==1 {print $7}')
    log "Detected current IP: ${CURRENT_IP}"
    
    # Update keepalived config with correct unicast peer
    if [[ "${CURRENT_IP}" == "${PRIMARY_IP}" ]]; then
        sed -i "s/state BACKUP/state MASTER/" "${SCRIPT_DIR}/keepalived.conf"
        sed -i "s/priority 100/priority 110/" "${SCRIPT_DIR}/keepalived.conf"
        sed -i "s/unicast_src_ip.*/unicast_src_ip ${PRIMARY_IP}/" "${SCRIPT_DIR}/keepalived.conf"
        log "Configured as PRIMARY keepalived instance"
    else
        sed -i "s/state MASTER/state BACKUP/" "${SCRIPT_DIR}/keepalived.conf"
        sed -i "s/priority 110/priority 100/" "${SCRIPT_DIR}/keepalived.conf"
        sed -i "s/unicast_src_ip.*/unicast_src_ip ${CURRENT_IP}/" "${SCRIPT_DIR}/keepalived.conf"
        log "Configured as BACKUP keepalived instance"
    fi
    
    log_success "Network settings configured successfully"
}

# Create health check scripts directory
setup_health_scripts() {
    log "Setting up health check scripts..."
    
    mkdir -p "${SCRIPT_DIR}/health-scripts"
    
    # Run the health check script creation
    bash "${SCRIPT_DIR}/health-check-scripts.sh"
    
    # Copy scripts to health-scripts directory for Docker volume mounting
    cp /usr/local/bin/check_*.sh "${SCRIPT_DIR}/health-scripts/"
    cp /usr/local/bin/notify_*.sh "${SCRIPT_DIR}/health-scripts/"
    
    chmod +x "${SCRIPT_DIR}/health-scripts/"*.sh
    
    log_success "Health check scripts configured successfully"
}

# Deploy with Docker Compose
deploy_services() {
    log "Deploying external load balancer services..."
    
    cd "${SCRIPT_DIR}"
    
    # Pull images
    docker-compose pull
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 30
    
    # Check service health
    if docker-compose ps | grep -q "Up"; then
        log_success "Services started successfully"
    else
        log_error "Some services failed to start"
        docker-compose logs
        exit 1
    fi
}

# Validate deployment
validate_deployment() {
    log "Validating deployment..."
    
    # Check if VIP is active
    if ip addr show | grep -q "${VIP}"; then
        log_success "Virtual IP ${VIP} is active"
    else
        log_warning "Virtual IP ${VIP} not yet active (may take a moment)"
    fi
    
    # Check HAProxy stats
    if curl -s "http://localhost:8404/stats" > /dev/null; then
        log_success "HAProxy stats endpoint is accessible"
    else
        log_error "HAProxy stats endpoint is not accessible"
    fi
    
    # Check service connectivity
    for port in 80 443 6443; do
        if nc -z localhost "${port}"; then
            log_success "Port ${port} is listening"
        else
            log_error "Port ${port} is not listening"
        fi
    done
    
    # Show service status
    log "Service status:"
    docker-compose ps
}

# Create monitoring dashboard
create_monitoring() {
    log "Creating monitoring configuration..."
    
    mkdir -p "${SCRIPT_DIR}/monitoring"
    
    cat > "${SCRIPT_DIR}/monitoring/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'haproxy'
    static_configs:
      - targets: ['localhost:9101']
    scrape_interval: 5s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF

    log_success "Monitoring configuration created"
}

# Main deployment function
main() {
    log "Starting External Load Balancer deployment..."
    
    check_root
    install_dependencies
    configure_firewall
    setup_ssl
    create_error_pages
    create_fluentd_config
    configure_network
    setup_health_scripts
    create_monitoring
    deploy_services
    validate_deployment
    
    log_success "External Load Balancer deployment completed successfully!"
    log ""
    log "🔗 Access URLs:"
    log "   HAProxy Stats: http://${VIP}:8404/stats"
    log "   Service Endpoint: https://${VIP}"
    log "   Kubernetes API: https://${VIP}:6443"
    log ""
    log "📊 Monitoring:"
    log "   HAProxy Metrics: http://${VIP}:9101/metrics"
    log ""
    log "📝 Logs:"
    log "   Deployment: ${LOG_FILE}"
    log "   Container Logs: docker-compose logs"
    log ""
    log "🔧 Management:"
    log "   Restart Services: docker-compose restart"
    log "   Update Config: Edit configs and docker-compose up -d"
    log "   View Status: docker-compose ps"
}

# Handle script arguments
case "${1:-}" in
    "install")
        main
        ;;
    "validate")
        validate_deployment
        ;;
    "restart")
        cd "${SCRIPT_DIR}"
        docker-compose restart
        ;;
    "stop")
        cd "${SCRIPT_DIR}"
        docker-compose down
        ;;
    "logs")
        cd "${SCRIPT_DIR}"
        docker-compose logs -f
        ;;
    *)
        echo "Usage: $0 {install|validate|restart|stop|logs}"
        echo ""
        echo "Commands:"
        echo "  install   - Full deployment of external load balancer"
        echo "  validate  - Validate current deployment"
        echo "  restart   - Restart all services"
        echo "  stop      - Stop all services"
        echo "  logs      - View service logs"
        exit 1
        ;;
esac