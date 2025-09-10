# Single-Node Cluster Architecture Overview

## 🏗️ Architecture Philosophy

The Single-Node Cluster architecture represents a paradigm shift from traditional multi-node Kubernetes deployments to a distributed yet simplified approach. This design eliminates the complexity of Proxmox virtualization while maintaining service resilience through external load balancing and intelligent workload distribution.

## 🎯 Core Design Principles

### 1. Simplicity Over Complexity
- **Direct Hardware Access**: No virtualization layer overhead
- **Single Responsibility**: Each node optimized for specific workload types
- **Minimal Dependencies**: Reduced failure points and troubleshooting complexity

### 2. Resilience Through Distribution
- **External Load Balancing**: HAProxy + Keepalived for service availability
- **Workload Isolation**: Failures contained to specific service domains
- **Cross-Cluster Backup**: Multiple deployment targets for critical services

### 3. Resource Optimization
- **Role-Based Allocation**: Resources tailored to workload requirements
- **Hardware Utilization**: Direct access to GPU, storage, and compute resources
- **Efficiency Focus**: 15-20% performance improvement over virtualized deployments

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Load Balancer                       │
│                      HAProxy + Keepalived                          │
│                     VIP: 10.0.1.100                                │
└─────────────────┬───────────────┬───────────────┬───────────────────┘
                  │               │               │
         ┌────────▼────────┐ ┌────▼────────┐ ┌────▼────────────┐
         │  Node1-Compute  │ │ Node2-Storage│ │  Node3-General  │
         │  10.0.1.101     │ │  10.0.1.102  │ │   10.0.1.103    │
         │                 │ │              │ │                 │
         │  🧠 AI/ML Stack │ │  📀 Media    │ │  🏠 Home Auto   │
         │  • LocalAI      │ │  • Jellyfin  │ │  • HomeAssist   │
         │  • Qdrant       │ │  • Sonarr    │ │  • AdGuard      │
         │  • Milvus       │ │  • Radarr    │ │  • UniFi        │
         │  • TurboPilot   │ │  • Prowlarr  │ │  📊 Monitoring  │
         │                 │ │  • Lidarr    │ │  • Prometheus   │
         │  🔧 Resources:  │ │              │ │  • Grafana      │
         │  CPU: 16 cores  │ │  🔧 Resources│ │                 │
         │  RAM: 64GB      │ │  CPU: 8 cores│ │  🔧 Resources:  │
         │  GPU: 1x NVIDIA │ │  RAM: 32GB   │ │  CPU: 6 cores   │
         │  Storage: NVMe  │ │  Storage: 4TB│ │  RAM: 16GB      │
         └─────────────────┘ └──────────────┘ └─────────────────┘
                  │               │               │
         ┌────────▼───────────────▼───────────────▼─────────────────┐
         │                  NFS Storage Backend                    │
         │                 Synology NAS                           │
         │               10.0.1.200                               │
         │  📁 /volume1/k8s-storage   📁 /volume1/media          │
         │  📁 /volume1/k8s-apps      📁 /volume1/backups        │
         └─────────────────────────────────────────────────────────┘
```

## 🔧 Component Architecture

### External Load Balancer Layer

**HAProxy Configuration:**
- **Service Discovery**: Hostname-based routing to appropriate clusters
- **Health Checking**: Intelligent failover based on backend availability
- **SSL Termination**: Centralized certificate management
- **Performance**: Connection pooling and keep-alive optimization

**Keepalived Integration:**
- **Virtual IP Management**: Seamless failover between LB instances
- **Priority-Based Election**: Master/backup configuration with health-based priority
- **VRRP Protocol**: Industry-standard redundancy protocol
- **Network Integration**: Unicast mode for complex network topologies

### Kubernetes Cluster Layer

**K3s Configuration:**
- **Lightweight Runtime**: Reduced memory footprint and faster startup
- **External Datastore**: etcd embedded for single-node simplicity
- **CNI Integration**: Flannel with VXLAN backend for network isolation
- **Container Runtime**: containerd with built-in image management

**Node Specialization:**

| Node Type | Primary Function | Resource Profile | Workload Examples |
|-----------|-----------------|------------------|-------------------|
| **Compute** | AI/ML Processing | High CPU/GPU, Fast Storage | LocalAI, Qdrant, Milvus |
| **Storage** | Media & File Services | High Storage, Moderate CPU | Jellyfin, *arr Stack |
| **General** | Utility & Monitoring | Balanced Resources | Home Assistant, Monitoring |

### Storage Architecture

**Democratic CSI with NFS Backend:**
- **Storage Classes**: Performance-optimized classes for different workloads
- **Volume Provisioning**: Dynamic PV creation with appropriate performance profiles
- **Data Persistence**: Cross-cluster data availability and backup integration
- **Performance Tuning**: NFS mount options optimized for each workload type

**Storage Class Strategy:**
```yaml
nfs-media:    # Large files, high throughput
  mountOptions: [nfsvers=4.2, nconnect=16, rsize=1048576, wsize=1048576]
  
nfs-apps:     # Application data, balanced performance  
  mountOptions: [nfsvers=4.2, nconnect=8, rsize=262144, wsize=262144]
  
nfs-backup:   # Reliability over performance
  mountOptions: [nfsvers=4.2, sync, retrans=5]
```

### Monitoring & Observability

**Prometheus Federation Architecture:**
- **Central Collection**: Node3-General hosts federated Prometheus
- **Cross-Cluster Scraping**: Intelligent metric collection from all clusters
- **Service Discovery**: Automatic endpoint detection and configuration
- **Alert Routing**: Context-aware alerting based on cluster and service type

**Grafana Integration:**
- **Multi-Datasource**: Separate connections to each cluster's Prometheus
- **Custom Dashboards**: Workload-specific visualization and analysis
- **Alert Management**: Unified alerting with cluster context
- **Performance Tracking**: Cross-cluster performance comparison

## 🚀 GitOps Workflow

### Flux CD Multi-Cluster Management

**Repository Structure:**
```
infrastructure/single-node-clusters/
├── clusters/
│   ├── base/                    # Shared configurations
│   │   ├── flux-system/        # Core Flux components
│   │   └── infrastructure/     # Common infrastructure
│   ├── node1-compute/          # Compute-specific configs
│   ├── node2-storage/          # Storage-specific configs  
│   └── node3-general/          # General-purpose configs
├── external-lb/                # Load balancer configuration
├── monitoring/                 # Federation monitoring
└── storage/                    # Shared storage configuration
```

**Deployment Flow:**
1. **Git Commit**: Configuration changes pushed to repository
2. **Flux Detection**: Each cluster's Flux instance detects changes
3. **Validation**: Kustomize builds and validates configurations
4. **Deployment**: Rolling updates with health checks
5. **Reconciliation**: Continuous drift detection and correction

### Workload Distribution Strategy

**Automatic Scheduling:**
- **Node Affinity**: Workloads prefer their designated node types
- **Tolerations**: Specialized workloads can overcome node taints
- **Anti-Affinity**: Critical services distributed across available nodes
- **Resource Requests**: Guaranteed resources for reliable performance

**Failover Behavior:**
- **Primary Failure**: Workloads reschedule to backup nodes automatically
- **Resource Constraints**: Intelligent degradation with priority preservation
- **Network Partitions**: Independent operation with eventual consistency

## 🔒 Security Architecture

### Network Security
- **Segmentation**: Each cluster operates in isolated network segments
- **Firewall Rules**: Restrictive ingress policies with explicit allowlists
- **TLS Everywhere**: End-to-end encryption for all inter-cluster communication
- **VPN Integration**: Tailscale overlay for secure remote access

### Kubernetes Security
- **Pod Security Standards**: Enforced security contexts and privilege restrictions
- **Network Policies**: Microsegmentation within clusters
- **RBAC**: Role-based access control with minimal privilege principles
- **Secret Management**: 1Password integration for credential security

### Certificate Management
- **Cert-Manager**: Automated certificate lifecycle management
- **Let's Encrypt**: Public certificate authority integration
- **Internal CA**: Self-signed certificates for internal services
- **Rotation**: Automatic certificate renewal and distribution

## 📊 Performance Characteristics

### Resource Utilization
- **CPU Efficiency**: 15-20% improvement over virtualized deployment
- **Memory Overhead**: Reduced system overhead without hypervisor layer
- **Storage Performance**: Direct hardware access for optimal I/O performance
- **Network Latency**: Reduced network stack overhead

### Scalability Patterns
- **Horizontal Scaling**: Additional physical nodes for capacity expansion
- **Workload Migration**: Dynamic workload rebalancing during maintenance
- **Resource Elasticity**: Seasonal workload adaptation within node constraints
- **Performance Monitoring**: Continuous optimization based on usage patterns

### High Availability
- **Service Availability**: 99.5% target with planned maintenance windows
- **Recovery Time**: < 5 minute RTO for critical services
- **Data Consistency**: RPO < 15 minutes for application data
- **Failover Testing**: Monthly chaos engineering validation

## 🔄 Operational Procedures

### Deployment Lifecycle
1. **Pre-deployment**: Infrastructure validation and resource allocation
2. **Rolling Deployment**: Staged rollout with health validation
3. **Smoke Testing**: Automated validation of core functionality
4. **Traffic Migration**: Gradual traffic shifting through load balancer
5. **Post-deployment**: Performance monitoring and optimization

### Maintenance Windows
- **Scheduled Maintenance**: Monthly patching and updates during low-usage periods
- **Emergency Updates**: Automated security patching with rollback capability
- **Capacity Planning**: Quarterly resource utilization review and planning
- **Disaster Recovery**: Quarterly backup restoration and failover testing

### Monitoring & Alerting
- **Health Monitoring**: Continuous cluster and service health validation
- **Performance Tracking**: Resource utilization and performance trend analysis
- **Alert Escalation**: Tiered alerting based on severity and business impact
- **Incident Response**: Automated response procedures for common failure scenarios

This architecture provides a robust, scalable, and maintainable foundation for the homelab infrastructure while significantly reducing operational complexity compared to the previous Proxmox-based approach.