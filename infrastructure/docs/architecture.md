# K3s HA Cluster - Technical Architecture

## Executive Summary

This document describes the technical architecture of a production-ready, highly available K3s Kubernetes cluster designed for homelab and enterprise use. The implementation provides 99.9% uptime SLA with automated failover, distributed storage, GPU acceleration, and comprehensive monitoring.

## Architecture Principles

### Design Philosophy
- **High Availability First**: Multi-master design with no single points of failure
- **Cloud-Native Standards**: Kubernetes-native solutions with industry best practices
- **Operational Excellence**: Automated deployment, monitoring, and recovery procedures
- **Security by Design**: Zero-trust architecture with defense-in-depth
- **Scalability**: Horizontal scaling capabilities for workloads and infrastructure

### Architectural Decisions

| Decision | Rationale | Trade-offs | Alternatives Considered |
|----------|-----------|------------|----------------------|
| K3s vs K8s | Simpler management, lower resource overhead | Some enterprise features missing | kubeadm, managed services |
| Embedded etcd | Reduced complexity, built-in HA | Less flexibility than external etcd | External etcd cluster |
| Longhorn storage | K8s-native, multi-replica, backup support | Performance overhead vs local storage | Ceph, GlusterFS, NFS |
| MetalLB | Standard LB for bare metal | L2 mode limitations | HAProxy, nginx, cloud LBs |
| Flannel CNI | K3s default, simple configuration | Basic feature set | Cilium, Calico, Weave |

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Homelab Network                          │
│                      10.10.0.0/16                              │
├─────────────────────────────────────────────────────────────────┤
│                    Load Balancer Pool                           │
│                 10.10.200.100-200/24                           │
├─────────────────────────────────────────────────────────────────┤
│  Control Plane (HA Masters)     │  Data Plane (Workers)         │
│  ┌─────────────────────────────┐│  ┌───────────────────────────┐ │
│  │ k3s-master-01 (10.10.10.10)││  │ k3s-worker-01-05          │ │
│  │ k3s-master-02 (10.10.10.11)││  │ (10.10.10.20-24)          │ │
│  │ k3s-master-03 (10.10.10.12)││  │                           │ │
│  │                             ││  │ k3s-gpu-01-02             │ │
│  │ • API Server                ││  │ (10.10.10.30-31)          │ │
│  │ • etcd Cluster              ││  │                           │ │
│  │ • Controller Manager        ││  │ • kubelet                 │ │
│  │ • Scheduler                 ││  │ • Container Runtime       │ │
│  │ • Cloud Controller          ││  │ • CNI Plugin              │ │
│  └─────────────────────────────┘│  │ • Storage Drivers         │ │
│                                 │  └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### Control Plane (Masters)
- **Count**: 3 nodes for HA quorum
- **Resources**: 4 vCPU, 8GB RAM, 60GB storage each
- **Role**: Cluster management, API serving, scheduling decisions
- **Redundancy**: Active-active with leader election
- **Failure Tolerance**: Can lose 1 node without service interruption

#### Data Plane (Workers)
- **Standard Workers**: 5 nodes (4 vCPU, 16GB RAM, 100-200GB storage)
- **GPU Workers**: 2 nodes (8 vCPU, 32GB RAM, 200GB storage + NVIDIA GPU)
- **Role**: Workload execution, storage provision, network handling
- **Scaling**: Horizontal scaling based on demand

### Network Architecture

#### Network Topology
```
Internet
    │
    ▼
┌─────────────────────────┐
│    Router/Firewall      │
│    10.10.0.1/16        │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│   Proxmox Bridge       │
│     vmbr0              │
│   VLAN 10 (K8s)        │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    K3s Cluster Network                          │
│                                                                 │
│  Pod Network (Flannel VXLAN)    │  Service Network             │
│  10.42.0.0/16                   │  10.43.0.0/16               │
│                                 │                              │
│  ┌─────────────────────────────┐│  ┌─────────────────────────┐ │
│  │        CNI Plugin           ││  │     CoreDNS             │ │
│  │      (Flannel)              ││  │   Service Discovery     │ │
│  │                             ││  │                         │ │
│  │ • VXLAN Tunneling           ││  │ • DNS Resolution        │ │
│  │ • Cross-node Routing        ││  │ • Service Endpoints     │ │
│  │ • Network Policies          ││  │ • Cluster DNS           │ │
│  └─────────────────────────────┘│  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Network Configuration

| Component | Network | Purpose | Configuration |
|-----------|---------|---------|---------------|
| Host Network | 10.10.10.0/24 | Node management | Static IPs, VLAN 10 |
| Pod Network | 10.42.0.0/16 | Inter-pod communication | Flannel VXLAN |
| Service Network | 10.43.0.0/16 | Service discovery | ClusterIP, NodePort |
| LoadBalancer Pool | 10.10.200.100-200/24 | External access | MetalLB L2 mode |

### Storage Architecture

#### Longhorn Distributed Storage

```
┌─────────────────────────────────────────────────────────────────┐
│                    Longhorn Storage System                      │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   NVMe Tier     │  │    SSD Tier     │  │   Bulk Tier     │ │
│  │                 │  │                 │  │                 │ │
│  │ • 3 Replicas    │  │ • 2 Replicas    │  │ • 2 Replicas    │ │
│  │ • High IOPS     │  │ • Balanced      │  │ • High Capacity │ │
│  │ • Low Latency   │  │ • Performance   │  │ • Cost Effective│ │
│  │ • Critical Apps │  │ • Standard Apps │  │ • Bulk Storage  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │        │
│           ▼                     ▼                     ▼        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Longhorn Manager & Controller                  │ │
│  │                                                             │ │
│  │ • Volume Management      • Replica Placement               │ │
│  │ • Backup Orchestration   • Health Monitoring               │ │
│  │ • Disaster Recovery      • Performance Optimization        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Storage Classes

| Storage Class | Replicas | Node Selector | Use Case | Performance |
|---------------|----------|---------------|----------|-------------|
| longhorn-nvme-critical | 3 | storage.type=nvme | Databases, critical apps | 10K+ IOPS |
| longhorn-ssd-standard | 2 | storage.type=ssd | Web apps, caches | 5K+ IOPS |
| longhorn-bulk | 2 | none | Logs, backups, media | 1K+ IOPS |

#### Backup Strategy
- **Frequency**: Daily automated backups at 2 AM
- **Retention**: 30 days local, 90 days remote
- **Destination**: Backblaze B2 with encryption
- **Recovery**: Point-in-time recovery with <2 hour RTO

### Security Architecture

#### Defense in Depth Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        Security Layers                          │
│                                                                 │
│  Layer 7: Application Security                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • Pod Security Standards    • Admission Controllers         │ │
│  │ • Security Contexts         • Resource Quotas               │ │
│  │ • Runtime Security          • Image Scanning                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 4: Network Security                                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • Network Policies          • Service Mesh (Optional)       │ │
│  │ • Firewall Rules            • Traffic Encryption            │ │
│  │ • Ingress Controllers       • DDoS Protection               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 3: Authentication & Authorization                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • RBAC Policies             • Service Accounts              │ │
│  │ • Certificate Management    • Token Authentication          │ │
│  │ • Audit Logging             • Identity Integration          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 2: Cluster Security                                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • etcd Encryption           • API Server Security           │ │
│  │ • Secrets Management        • Certificate Rotation          │ │
│  │ • Node Security             • Container Runtime Security    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 1: Infrastructure Security                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • Host Hardening            • Network Segmentation          │ │
│  │ • Hypervisor Security       • Physical Security             │ │
│  │ • Secure Boot               • Hardware Security             │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Security Controls

| Control Type | Implementation | Coverage |
|--------------|----------------|----------|
| Authentication | X.509 certificates, service account tokens | 100% |
| Authorization | RBAC with least privilege | All API access |
| Encryption | TLS 1.3 for all communication | In transit + at rest |
| Audit Logging | Complete API audit trail | All operations |
| Network Security | Network policies, firewall rules | Pod-to-pod + ingress |
| Runtime Security | Pod security standards, admission controllers | All workloads |

### Monitoring Architecture

#### Observability Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring & Observability                   │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Prometheus    │  │     Grafana     │  │  Alertmanager   │ │
│  │                 │  │                 │  │                 │ │
│  │ • Metrics       │  │ • Dashboards    │  │ • Alert Routing │ │
│  │ • Storage       │  │ • Visualization │  │ • Notifications │ │
│  │ • Querying      │  │ • Analytics     │  │ • Escalation    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           ▲                     ▲                     ▲        │
│           │                     │                     │        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Metrics Collection                          │ │
│  │                                                             │ │
│  │ • Node Exporter         • kube-state-metrics                │ │
│  │ • cAdvisor              • Custom Application Metrics        │ │
│  │ • Longhorn Metrics      • GPU Metrics                       │ │
│  │ • Network Metrics       • Service Mesh Metrics (Optional)   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Monitoring Metrics

| Category | Metrics | Alerting Thresholds |
|----------|---------|-------------------|
| Infrastructure | CPU, Memory, Disk, Network | >80% utilization |
| Kubernetes | Pod status, Node status, API latency | Pod failures, Node down |
| Application | Response time, Error rate, Throughput | >5% error rate, >500ms response |
| Storage | IOPS, Latency, Capacity | >90% full, >100ms latency |
| Network | Bandwidth, Packet loss, DNS failures | >1% packet loss |
| Security | Failed auth, Policy violations | Any security event |

### GPU Architecture

#### NVIDIA GPU Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                      GPU Worker Nodes                           │
│                                                                 │
│  ┌─────────────────┐                    ┌─────────────────┐    │
│  │   k3s-gpu-01    │                    │   k3s-gpu-02    │    │
│  │                 │                    │                 │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │   NVIDIA    │ │                    │ │   NVIDIA    │ │    │
│  │ │     GPU     │ │                    │ │     GPU     │ │    │
│  │ │   Hardware  │ │                    │ │   Hardware  │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  │       │         │                    │       │         │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │   Driver    │ │                    │ │   Driver    │ │    │
│  │ │   535.xxx   │ │                    │ │   535.xxx   │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  │       │         │                    │       │         │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │  Container  │ │                    │ │  Container  │ │    │
│  │ │   Toolkit   │ │                    │ │   Toolkit   │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  │       │         │                    │       │         │    │
│  │ ┌─────────────┐ │                    │ ┌─────────────┐ │    │
│  │ │  containerd │ │                    │ │  containerd │ │    │
│  │ │   Runtime   │ │                    │ │   Runtime   │ │    │
│  │ └─────────────┘ │                    │ └─────────────┘ │    │
│  └─────────────────┘                    └─────────────────┘    │
│           │                                       │             │
│           └───────────────┬───────────────────────┘             │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            NVIDIA Device Plugin DaemonSet                   │ │
│  │                                                             │ │
│  │ • GPU Discovery          • Resource Allocation              │ │
│  │ • Device Advertising     • Health Monitoring                │ │
│  │ • Runtime Class Setup    • Scheduling Support               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### GPU Resource Management

| Resource | Configuration | Purpose |
|----------|---------------|---------|
| Node Labels | `nvidia.com/gpu=true` | GPU node identification |
| Node Taints | `nvidia.com/gpu=true:NoSchedule` | Dedicated GPU scheduling |
| Runtime Class | `nvidia` | Container runtime selection |
| Device Plugin | `nvidia-device-plugin-daemonset` | GPU resource advertising |
| Resource Limits | `nvidia.com/gpu: 1` | GPU allocation per pod |

## Infrastructure as Code

### Terraform Architecture

```
terraform/
├── modules/
│   └── vm-template/
│       ├── main.tf              # VM provisioning logic
│       ├── variables.tf         # Input parameters
│       ├── outputs.tf           # Resource outputs
│       └── templates/
│           └── cloud-init.yaml  # VM initialization
├── terraform.tfvars            # Environment configuration
├── main.tf                     # Root module
├── variables.tf                # Global variables
└── outputs.tf                  # Cluster outputs
```

#### Resource Provisioning Flow

```
Terraform Plan → Resource Creation → Cloud-Init → VM Ready
     │                    │              │           │
     ▼                    ▼              ▼           ▼
┌─────────┐    ┌─────────────────┐    ┌─────────┐  ┌─────────┐
│Variable │    │   Proxmox API   │    │OS Setup │  │SSH Keys │
│Validation│    │   VM Creation   │    │Network  │  │Ready    │
└─────────┘    └─────────────────┘    │Config   │  └─────────┘
                                     └─────────┘
```

### Ansible Architecture

```
ansible/
├── playbooks/
│   ├── configure-k3s.yml       # Main orchestration
│   ├── install-k3s.yml         # K3s installation
│   └── validate-cluster.yml    # Health verification
├── tasks/
│   ├── configure-master.yml    # Master node setup
│   ├── configure-worker.yml    # Worker node setup
│   ├── configure-gpu-worker.yml# GPU node setup
│   ├── kubectl-access.yml      # Access configuration
│   ├── install-helm.yml        # Package manager
│   ├── configure-networking.yml# Network setup
│   └── install-core-services.yml# Essential services
├── inventory/
│   └── hosts.yml               # Dynamic inventory
├── group_vars/
│   ├── all.yml                 # Global configuration
│   └── secrets.yml             # Encrypted secrets
└── configs/
    ├── master-config.yaml      # K3s master config
    └── worker-config.yaml      # K3s worker config
```

## Deployment Architecture

### CI/CD Pipeline (Planned)

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions Workflow                     │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   Build     │    │   Test      │    │   Deploy    │          │
│  │             │    │             │    │             │          │
│  │ • Packer    │ → │ • Terraform │ → │ • Ansible   │          │
│  │   Validate  │    │   Plan      │    │   Deploy    │          │
│  │ • Template  │    │ • Ansible   │    │ • Health    │          │
│  │   Build     │    │   Syntax    │    │   Check     │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│                                                                 │
│  Triggers: Push to main, PR merge, Manual dispatch             │
│  Approval: Required for production deployments                 │
└─────────────────────────────────────────────────────────────────┘
```

### GitOps Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                         ArgoCD GitOps                           │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │    Git      │    │   ArgoCD    │    │   Cluster   │          │
│  │ Repository  │    │  Controller │    │Applications │          │
│  │             │    │             │    │             │          │
│  │ • App       │ → │ • Sync      │ → │ • Manifests │          │
│  │   Manifests │    │   Status    │    │   Applied   │          │
│  │ • Config    │    │ • Health    │    │ • Health    │          │
│  │   Maps      │    │   Monitor   │    │   Monitor   │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│                                                                 │
│  Sync Policy: Automatic with manual approval for production    │
│  Health Checks: Integrated with monitoring and alerting        │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Architecture

### Resource Allocation Strategy

#### Master Nodes
- **CPU**: 4 vCPU (3 reserved for K8s control plane, 1 for system)
- **Memory**: 8GB (6GB for K8s, 2GB for system + buffer)
- **Storage**: 60GB (etcd data, logs, container images)
- **Network**: 1Gbps (API server, etcd replication)

#### Worker Nodes
- **Standard Workers**: 4 vCPU, 16GB RAM (workload density: 20-30 pods)
- **High-Memory Workers**: 8 vCPU, 32GB RAM (memory-intensive workloads)
- **GPU Workers**: 8 vCPU, 32GB RAM + NVIDIA GPU (AI/ML workloads)

### Performance Optimizations

| Component | Optimization | Benefit |
|-----------|--------------|---------|
| etcd | SSD storage, regular compaction | <10ms write latency |
| API Server | Connection pooling, request limits | 100+ req/sec capacity |
| kubelet | Efficient garbage collection | Reduced memory pressure |
| CNI | VXLAN offloading, optimized routing | Gbps pod networking |
| Storage | NVMe for critical, balanced for standard | Tier-appropriate performance |
| Container Runtime | containerd with optimal settings | Fast pod startup |

## Scalability Architecture

### Horizontal Scaling

#### Cluster Scaling Limits
- **Maximum Nodes**: 100 (K3s supported limit)
- **Maximum Pods**: 5,000 (50 pods per node average)
- **etcd Cluster**: 3-node fixed (optimal for small-medium clusters)
- **Storage**: Unlimited with additional nodes

#### Application Scaling
- **Horizontal Pod Autoscaler**: CPU/Memory based scaling
- **Vertical Pod Autoscaler**: Resource request optimization
- **Cluster Autoscaler**: Node provisioning based on demand
- **Custom Metrics**: Application-specific scaling triggers

### Growth Strategy

```
Phase 1: Initial Deployment (Current)
├── 3 Masters, 7 Workers
├── Basic monitoring and alerting
├── Core services (storage, networking)
└── Foundation applications

Phase 2: Production Workloads (6 months)
├── Add 5-10 worker nodes
├── Implement service mesh
├── Advanced monitoring and tracing
└── Production application deployment

Phase 3: Enterprise Scale (12 months)
├── Multi-cluster federation
├── Advanced security policies
├── Disaster recovery automation
└── Performance optimization
```

## Disaster Recovery Architecture

### Backup Strategy

#### Data Protection Tiers

| Tier | Data Type | Backup Frequency | Retention | Recovery Time |
|------|-----------|------------------|-----------|---------------|
| Tier 0 | etcd state | Every 6 hours | 30 days | <15 minutes |
| Tier 1 | Persistent volumes | Daily | 90 days | <2 hours |
| Tier 2 | Configuration | Daily | 365 days | <30 minutes |
| Tier 3 | Application data | Application-specific | Variable | Application-specific |

#### Recovery Procedures

```
Disaster Scenario → Assessment → Recovery Plan → Execution → Validation
        │               │            │              │           │
        ▼               ▼            ▼              ▼           ▼
   ┌─────────┐    ┌─────────┐   ┌─────────┐   ┌─────────┐  ┌─────────┐
   │Impact   │    │Resource │   │Priority │   │Parallel │  │Health   │
   │Analysis │    │Inventory│   │Matrix   │   │Recovery │  │Check    │
   └─────────┘    └─────────┘   └─────────┘   └─────────┘  └─────────┘
```

### High Availability Design

#### Failure Modes and Responses

| Failure Type | Detection Time | Automatic Response | Manual Intervention |
|--------------|----------------|-------------------|-------------------|
| Single master failure | <30 seconds | Leader re-election | None required |
| Worker node failure | <60 seconds | Pod rescheduling | Node replacement |
| Network partition | <30 seconds | Graceful degradation | Network repair |
| Storage failure | <10 seconds | Replica promotion | Storage rebuild |
| Complete site failure | <5 minutes | Manual DR activation | Site restoration |

## Security Architecture Deep Dive

### Certificate Management

```
┌─────────────────────────────────────────────────────────────────┐
│                   Certificate Authority Tree                    │
│                                                                 │
│              ┌─────────────────────────────────┐                │
│              │        Root CA (K3s)            │                │
│              │      Self-Signed Root           │                │
│              └─────────────────────────────────┘                │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              │               │               │                  │
│    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐      │
│    │   Server Certs  │ │Client Certs │ │   Service Certs │      │
│    │                 │ │             │ │                 │      │
│    │ • API Server    │ │ • kubelet   │ │ • etcd          │      │
│    │ • etcd Server   │ │ • kubectl   │ │ • Controller    │      │
│    │ • Proxy         │ │ • Scheduler │ │ • Scheduler     │      │
│    └─────────────────┘ └─────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### RBAC Model

#### Role Hierarchy

```
ClusterAdmin (Emergency Only)
    │
    ├── Platform-Admin (Infrastructure Team)
    │   ├── Namespace-Admin (Application Teams)
    │   │   ├── Developer (Read/Write in assigned namespaces)
    │   │   └── Viewer (Read-only access)
    │   └── Monitoring-Admin (SRE Team)
    │       ├── Metrics-Reader
    │       └── Alert-Manager
    └── Security-Admin (Security Team)
        ├── Policy-Manager
        └── Audit-Reader
```

## Integration Architecture

### Homelab Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Existing Homelab Services                    │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   Traefik   │  │ Prometheus  │  │   ArgoCD    │  │ 1Password   ││
│  │   Proxy     │  │ Monitoring  │  │   GitOps    │  │  Secrets    ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│         │                │                │                │      │
│         ▼                ▼                ▼                ▼      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                K3s Integration Layer                        │  │
│  │                                                             │  │
│  │ • LoadBalancer Service Type  • ServiceMonitors             │  │
│  │ • Ingress Resources          • Application CRDs            │  │
│  │ • TLS Certificate Requests   • Secret Synchronization      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Service Mesh Integration (Optional Future Enhancement)

```
┌─────────────────────────────────────────────────────────────────┐
│                       Service Mesh Layer                        │
│                         (Istio/Linkerd)                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Traffic   │  │ Observability│  │  Security   │              │
│  │ Management  │  │   (mTLS)     │  │  Policies   │              │
│  │             │  │              │  │             │              │
│  │ • Routing   │  │ • Metrics    │  │ • AuthN/Z   │              │
│  │ • L/B       │  │ • Tracing    │  │ • Encryption│              │
│  │ • Retry     │  │ • Logging    │  │ • Policies  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  Implementation: Gradual rollout, namespace by namespace        │
│  Benefits: Enhanced security, observability, traffic control    │
└─────────────────────────────────────────────────────────────────┘
```

## Operational Architecture

### Day-2 Operations Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                     Operations Framework                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   Monitor   │  │   Maintain  │  │   Upgrade   │  │   Scale     ││
│  │             │  │             │  │             │  │             ││
│  │ • Health    │  │ • Patches   │  │ • K3s       │  │ • Nodes     ││
│  │ • Metrics   │  │ • Certs     │  │ • Apps      │  │ • Storage   ││
│  │ • Alerts    │  │ • Cleanup   │  │ • Security  │  │ • Workloads ││
│  │ • Logs      │  │ • Backup    │  │ • Platform  │  │ • Resources ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│                                                                 │
│  Automation Level: 80% automated, 20% manual approval required │
│  SLA Target: 99.9% uptime, <100ms API response time            │
└─────────────────────────────────────────────────────────────────┘
```

## Conclusion

This architecture provides a robust, scalable, and secure foundation for running production Kubernetes workloads. The design emphasizes:

- **Reliability**: Multi-master HA with automatic failover
- **Scalability**: Horizontal scaling capabilities
- **Security**: Defense-in-depth with comprehensive controls
- **Operability**: Automated deployment and maintenance
- **Integration**: Seamless homelab service integration

The architecture supports current needs while providing a clear path for future enhancements including service mesh, multi-cluster federation, and advanced security controls.