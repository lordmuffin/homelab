#!/bin/bash
# K3s Single-Node Cluster Bootstrap Script
# Configures K3s for homelab single-node architecture with role-specific optimizations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/k3s-bootstrap.log"
K3S_VERSION="${K3S_VERSION:-v1.28.1+k3s1}"
CLUSTER_INIT="${CLUSTER_INIT:-true}"
FLUX_BRANCH="${FLUX_BRANCH:-single-node-cluster}"

# Node configuration detection
NODE_NAME="${NODE_NAME:-$(hostname)}"
NODE_IP="${NODE_IP:-$(ip route get 8.8.8.8 | awk 'NR==1 {print $7}')}"
CLUSTER_SECRET="${CLUSTER_SECRET:-homelab-k3s-$(openssl rand -hex 16)}"

# Load balancer configuration
LB_VIP="${LB_VIP:-10.0.1.100}"
LB_API_PORT="${LB_API_PORT:-6443}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Detect node role based on hostname or environment
detect_node_role() {
    if [[ "${NODE_NAME}" =~ compute|gpu|ai ]]; then
        echo "compute"
    elif [[ "${NODE_NAME}" =~ storage|media|nas ]]; then
        echo "storage"
    elif [[ "${NODE_NAME}" =~ general|utility|main ]]; then
        echo "general"
    else
        # Default to general if no pattern matches
        echo "general"
    fi
}

# Pre-installation checks
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Check system resources
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    TOTAL_CPU=$(nproc)
    
    if [[ "${TOTAL_RAM}" -lt 2048 ]]; then
        log_warning "System has less than 2GB RAM (${TOTAL_RAM}MB). K3s may not perform optimally."
    fi
    
    if [[ "${TOTAL_CPU}" -lt 2 ]]; then
        log_warning "System has less than 2 CPU cores (${TOTAL_CPU}). K3s may not perform optimally."
    fi
    
    # Check disk space
    AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
    if [[ "${AVAILABLE_SPACE}" -lt 10485760 ]]; then  # 10GB in KB
        log_error "Insufficient disk space. At least 10GB required."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Configure system for K3s
configure_system() {
    log "Configuring system for K3s..."
    
    # Update system packages
    apt-get update -qq
    apt-get install -y \
        curl \
        wget \
        unzip \
        jq \
        git \
        htop \
        iotop \
        net-tools \
        nfs-common \
        open-iscsi \
        cryptsetup \
        dmsetup
    
    # Configure kernel modules for K3s
    cat > /etc/modules-load.d/k3s.conf << 'EOF'
# Kernel modules for K3s
br_netfilter
overlay
ip_tables
ip6_tables
netfilter_xtables
xt_owner
xt_REDIRECT
xt_statistic
xt_TCPMSS
xt_tcpudp
xt_udp
xt_multiport
xt_set
ip_set
ip_set_hash_ip
ip_set_hash_net
xt_mark
xt_addrtype
xt_conntrack
xt_comment
xt_nat
ipt_MASQUERADE
nf_nat
nf_nat_redirect
nf_conntrack
nf_defrag_ipv4
nf_conntrack_netlink
xfrm_user
xfrm_algo
xt_addrtype
xt_conntrack
br_netfilter
EOF
    
    # Load kernel modules
    systemctl enable systemd-modules-load
    systemctl restart systemd-modules-load
    
    # Configure sysctl settings
    cat > /etc/sysctl.d/90-k3s.conf << 'EOF'
# K3s sysctl settings
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv6.conf.all.forwarding = 1
net.netfilter.nf_conntrack_max = 131072
vm.overcommit_memory = 1
kernel.panic = 10
kernel.panic_on_oops = 1
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 524288
fs.file-max = 2097152
net.core.somaxconn = 32768
net.ipv4.tcp_max_syn_backlog = 8192
net.core.netdev_max_backlog = 5000
EOF
    
    # Apply sysctl settings
    sysctl -p /etc/sysctl.d/90-k3s.conf
    
    log_success "System configuration completed"
}

# Generate K3s configuration based on node role
generate_k3s_config() {
    local node_role=$1
    log "Generating K3s configuration for ${node_role} node..."
    
    mkdir -p /etc/rancher/k3s
    
    # Base configuration
    cat > /etc/rancher/k3s/config.yaml << EOF
# K3s Configuration for ${node_role} node
cluster-init: ${CLUSTER_INIT}
token: "${CLUSTER_SECRET}"
node-name: "${NODE_NAME}"
node-ip: "${NODE_IP}"
bind-address: "${NODE_IP}"
advertise-address: "${NODE_IP}"
cluster-cidr: "10.42.0.0/16"
service-cidr: "10.43.0.0/16"
cluster-dns: "10.43.0.10"
cluster-domain: "cluster.local"
flannel-backend: "vxlan"
disable-cloud-controller: true
disable-network-policy: true
write-kubeconfig-mode: "0644"
kube-controller-manager-arg:
  - "bind-address=0.0.0.0"
  - "node-monitor-grace-period=40s"
  - "node-monitor-period=5s"
  - "cluster-signing-duration=87600h"
kube-proxy-arg:
  - "proxy-mode=iptables"
  - "metrics-bind-address=0.0.0.0"
kube-scheduler-arg:
  - "bind-address=0.0.0.0"
kubelet-arg:
  - "node-status-update-frequency=5s"
  - "image-gc-high-threshold=85"
  - "image-gc-low-threshold=80"
  - "eviction-hard=imagefs.available<15%,memory.available<750Mi,nodefs.available<10%"
  - "eviction-soft=imagefs.available<20%,memory.available<1Gi,nodefs.available<15%"
  - "eviction-soft-grace-period=imagefs.available=2m,memory.available=1m,nodefs.available=2m"
  - "eviction-max-pod-grace-period=120"
  - "max-pods=250"
EOF

    # Role-specific configurations
    case "${node_role}" in
        "compute")
            cat >> /etc/rancher/k3s/config.yaml << 'EOF'
# Compute-specific configuration
disable:
  - traefik
  - servicelb
  - local-storage
node-label:
  - "homelab.io/node-type=compute"
  - "homelab.io/gpu-enabled=true"
  - "homelab.io/workload-class=ai-ml"
node-taint:
  - "homelab.io/compute=true:NoSchedule"
kubelet-arg:
  - "feature-gates=DevicePlugins=true,KubeletPodResources=true"
  - "cpu-manager-policy=static"
  - "cpu-manager-reconcile-period=5s"
  - "topology-manager-policy=single-numa-node"
  - "reserved-cpus=0,1"
kube-apiserver-arg:
  - "feature-gates=DevicePlugins=true"
EOF
            ;;
        "storage")
            cat >> /etc/rancher/k3s/config.yaml << 'EOF'
# Storage-specific configuration  
disable:
  - traefik
  - servicelb
node-label:
  - "homelab.io/node-type=storage"
  - "homelab.io/storage-primary=true"
  - "homelab.io/workload-class=media"
node-taint:
  - "homelab.io/storage=true:NoSchedule"
kubelet-arg:
  - "feature-gates=CSIDriverRegistry=true,CSINodeInfo=true,VolumeSnapshotDataSource=true"
  - "volume-plugin-dir=/var/lib/kubelet/volumeplugins"
EOF
            ;;
        "general")
            cat >> /etc/rancher/k3s/config.yaml << 'EOF'
# General-purpose configuration
disable:
  - traefik
  - servicelb
node-label:
  - "homelab.io/node-type=general"
  - "homelab.io/monitoring-primary=true"
  - "homelab.io/workload-class=utility"
EOF
            ;;
    esac
    
    # External load balancer configuration
    cat >> /etc/rancher/k3s/config.yaml << EOF
# External load balancer integration
tls-san:
  - "${LB_VIP}"
  - "${NODE_IP}"
  - "localhost"
  - "127.0.0.1"
  - "kubernetes.default.svc.cluster.local"
  - "*.homelab.local"
  - "homelab.local"
EOF
    
    log_success "K3s configuration generated for ${node_role} node"
}

# Install K3s
install_k3s() {
    log "Installing K3s ${K3S_VERSION}..."
    
    # Download and install K3s
    curl -sfL https://get.k3s.io | \
        INSTALL_K3S_VERSION="${K3S_VERSION}" \
        INSTALL_K3S_EXEC="server" \
        sh -s -
    
    # Enable and start K3s service
    systemctl enable k3s.service
    systemctl start k3s.service
    
    # Wait for K3s to be ready
    log "Waiting for K3s to be ready..."
    local retry_count=0
    while ! kubectl get nodes > /dev/null 2>&1; do
        sleep 5
        retry_count=$((retry_count + 1))
        if [[ ${retry_count} -gt 60 ]]; then
            log_error "K3s failed to start within 5 minutes"
            exit 1
        fi
        log "Waiting for K3s... (${retry_count}/60)"
    done
    
    # Configure kubectl for regular users
    mkdir -p /home/*/
    cp /etc/rancher/k3s/k3s.yaml /home/*/kubeconfig
    chown 1000:1000 /home/*/kubeconfig 2>/dev/null || true
    
    # Export KUBECONFIG for current session
    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
    
    log_success "K3s installed and started successfully"
}

# Install Flux CD
install_flux() {
    log "Installing Flux CD..."
    
    # Download Flux CLI
    curl -s https://fluxcd.io/install.sh | bash
    
    # Move flux to PATH
    mv /root/.local/bin/flux /usr/local/bin/flux
    
    # Verify Flux installation
    if ! flux version --client > /dev/null 2>&1; then
        log_error "Failed to install Flux CLI"
        exit 1
    fi
    
    log_success "Flux CD CLI installed successfully"
}

# Bootstrap Flux for the cluster
bootstrap_flux() {
    local node_role=$1
    log "Bootstrapping Flux for ${node_role} cluster..."
    
    # Wait for cluster to be ready
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
    
    # Get GitHub token from environment or prompt
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_warning "GITHUB_TOKEN not set. Flux bootstrap will need to be run manually."
        log "To bootstrap Flux manually, run:"
        log "export GITHUB_TOKEN=<your-token>"
        log "flux bootstrap github --owner=lordmuffin --repository=homelab --branch=${FLUX_BRANCH} --path=./infrastructure/single-node-clusters/clusters/${NODE_NAME} --personal"
        return 0
    fi
    
    # Bootstrap Flux with GitHub
    flux bootstrap github \
        --owner=lordmuffin \
        --repository=homelab \
        --branch="${FLUX_BRANCH}" \
        --path="./infrastructure/single-node-clusters/clusters/${node_role}" \
        --personal \
        --components-extra=image-reflector-controller,image-automation-controller \
        --read-write-key \
        --reconcile
    
    if [[ $? -eq 0 ]]; then
        log_success "Flux bootstrapped successfully for ${node_role} cluster"
    else
        log_error "Failed to bootstrap Flux. Please run manually."
    fi
}

# Configure monitoring and observability
setup_monitoring() {
    local node_role=$1
    log "Setting up monitoring for ${node_role} node..."
    
    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Label monitoring namespace
    kubectl label namespace monitoring homelab.io/monitoring=enabled --overwrite
    
    # Install node-exporter as DaemonSet
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
    homelab.service: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
        args:
        - '--path.procfs=/host/proc'
        - '--path.sysfs=/host/sys'
        - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
        - '--collector.textfile.directory=/host/var/lib/node_exporter/textfile_collector'
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /rootfs
          readOnly: true
        - name: textfile
          mountPath: /host/var/lib/node_exporter/textfile_collector
          readOnly: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
      - name: textfile
        hostPath:
          path: /var/lib/node_exporter/textfile_collector
      tolerations:
      - operator: "Exists"
      serviceAccountName: node-exporter
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: node-exporter
  namespace: monitoring
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  type: NodePort
  ports:
  - port: 9100
    targetPort: 9100
    nodePort: 30910
    name: metrics
  selector:
    app: node-exporter
EOF

    log_success "Monitoring setup completed"
}

# Create cluster health check script
create_health_check() {
    log "Creating cluster health check script..."
    
    cat > /usr/local/bin/k3s-health-check.sh << 'EOF'
#!/bin/bash
# K3s Single-Node Cluster Health Check

set -euo pipefail

# Configuration
HEALTH_FILE="/var/lib/rancher/k3s/health"
LOG_FILE="/var/log/k3s-health.log"

# Health checks
check_k3s_service() {
    if systemctl is-active --quiet k3s.service; then
        return 0
    else
        return 1
    fi
}

check_k3s_api() {
    if kubectl get --raw='/readyz' > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_node_ready() {
    if kubectl get nodes --no-headers | grep -q " Ready "; then
        return 0
    else
        return 1
    fi
}

# Main health check
main() {
    local status="healthy"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if ! check_k3s_service; then
        status="unhealthy"
        echo "${timestamp} - K3s service is not running" >> "${LOG_FILE}"
    fi
    
    if ! check_k3s_api; then
        status="unhealthy"
        echo "${timestamp} - K3s API is not responding" >> "${LOG_FILE}"
    fi
    
    if ! check_node_ready; then
        status="unhealthy"
        echo "${timestamp} - Node is not ready" >> "${LOG_FILE}"
    fi
    
    # Write health status
    echo "${status}" > "${HEALTH_FILE}"
    echo "${timestamp} - Cluster status: ${status}" >> "${LOG_FILE}"
    
    # Exit with appropriate code
    if [[ "${status}" == "healthy" ]]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
EOF
    
    chmod +x /usr/local/bin/k3s-health-check.sh
    
    # Create systemd service for health checks
    cat > /etc/systemd/system/k3s-health-check.service << 'EOF'
[Unit]
Description=K3s Health Check
After=k3s.service
Requires=k3s.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/k3s-health-check.sh
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF
    
    # Create systemd timer for regular health checks
    cat > /etc/systemd/system/k3s-health-check.timer << 'EOF'
[Unit]
Description=K3s Health Check Timer
Requires=k3s-health-check.service

[Timer]
OnCalendar=*:0/5  # Every 5 minutes
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Enable health check timer
    systemctl daemon-reload
    systemctl enable --now k3s-health-check.timer
    
    log_success "Health check configured"
}

# Display cluster information
show_cluster_info() {
    local node_role=$1
    log_success "K3s ${node_role} cluster bootstrap completed!"
    log ""
    log "🎯 Cluster Information:"
    log "   Node Name: ${NODE_NAME}"
    log "   Node IP: ${NODE_IP}"
    log "   Cluster Role: ${node_role}"
    log "   K3s Version: ${K3S_VERSION}"
    log ""
    log "🔧 Management Commands:"
    log "   Check status: systemctl status k3s"
    log "   View logs: journalctl -u k3s -f"
    log "   Kubectl config: export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
    log "   Health check: /usr/local/bin/k3s-health-check.sh"
    log ""
    log "🚀 Flux CD:"
    log "   Check Flux: flux get all"
    log "   Reconcile: flux reconcile source git homelab-gitops"
    log ""
    log "📊 Monitoring:"
    log "   Node metrics: http://${NODE_IP}:30910/metrics"
    log "   Health status: cat /var/lib/rancher/k3s/health"
    log ""
    log "🔗 External Access:"
    log "   API Server: https://${LB_VIP}:${LB_API_PORT}"
    log "   Services: https://${LB_VIP}"
}

# Main bootstrap function
main() {
    local node_role
    node_role=$(detect_node_role)
    
    log "Starting K3s bootstrap for ${node_role} node..."
    
    check_prerequisites
    configure_system
    generate_k3s_config "${node_role}"
    install_k3s
    install_flux
    setup_monitoring "${node_role}"
    create_health_check
    bootstrap_flux "${node_role}"
    show_cluster_info "${node_role}"
    
    log_success "Bootstrap process completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "install")
        main
        ;;
    "config-only")
        node_role=$(detect_node_role)
        generate_k3s_config "${node_role}"
        ;;
    "flux-bootstrap")
        node_role=$(detect_node_role)
        bootstrap_flux "${node_role}"
        ;;
    "health-check")
        /usr/local/bin/k3s-health-check.sh
        ;;
    *)
        echo "Usage: $0 {install|config-only|flux-bootstrap|health-check}"
        echo ""
        echo "Commands:"
        echo "  install        - Full K3s installation and configuration"
        echo "  config-only    - Generate K3s configuration only"
        echo "  flux-bootstrap - Bootstrap Flux CD only"
        echo "  health-check   - Run cluster health check"
        exit 1
        ;;
esac