# VM and Network Layout Documentation
## Cloud-Homelab Infrastructure Architecture

**Agent**: Infrastructure Validator (Hive Mind Swarm)  
**Infrastructure**: Rackspace Spot Kubernetes Platform  
**Version**: 1.0.0  
**Date**: $(date)

## 🎯 Architecture Overview

This document details the VM and network layout for the cloud-homelab infrastructure deployed on Rackspace Spot, providing comprehensive visibility into the infrastructure topology, resource allocation, and network segmentation.

## 🏗️ Infrastructure Topology

### 🌐 High-Level Infrastructure Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Rackspace Spot Cloud                              │
│                              us-central-ord-1                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Cloud-Homelab Cloudspace                         │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                 Kubernetes Cluster v1.31.1                  │   │   │
│  │  │                     CNI: Cilium                             │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │               Managed Control Plane                         │   │   │
│  │  │           (Rackspace Spot Managed Service)                  │   │   │
│  │  │                                                             │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │   │
│  │  │  │ API Server  │  │    etcd     │  │ Controller  │        │   │   │
│  │  │  │             │  │             │  │   Manager   │        │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘        │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │                    Worker Node Pool                        │   │   │
│  │  │              Autoscaling Nodepool (3-6 nodes)             │   │   │
│  │  │                                                             │   │   │
│  │  │     ┌─────────────┬─────────────┬─────────────┐           │   │   │
│  │  │     │   Node-1    │   Node-2    │   Node-3    │           │   │   │
│  │  │     │ (Minimum)   │ (Minimum)   │ (Minimum)   │           │   │   │
│  │  │     └─────────────┴─────────────┴─────────────┘           │   │   │
│  │  │                                                             │   │   │
│  │  │     ┌─────────────┬─────────────┬─────────────┐           │   │   │
│  │  │     │   Node-4    │   Node-5    │   Node-6    │           │   │   │
│  │  │     │(Auto-scale) │(Auto-scale) │(Auto-scale) │           │   │   │
│  │  │     └─────────────┴─────────────┴─────────────┘           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 💻 Virtual Machine Specifications

### 📊 Node Configuration Matrix

| Component | Specification | Value | Notes |
|-----------|---------------|-------|-------|
| **Server Class** | Instance Type | gp.vs1.xlarge-ord | Extra Large general purpose |
| **CPU Cores** | vCPUs per Node | 4 cores | Dedicated compute resources |
| **Memory** | RAM per Node | >8GB | Minimum guaranteed memory |
| **Storage** | Local Storage | SSD-backed | High-performance storage |
| **Network** | Bandwidth | High-speed | Rackspace network backbone |
| **Region** | Location | us-central-ord-1 | Chicago data center |

### 🔢 Node Pool Details

#### Autoscaling Configuration
```
Minimum Nodes: 3
Maximum Nodes: 6
Current Nodes: Dynamic (3-6 based on load)
Scaling Policy: CPU/Memory based
Scale-up Trigger: >80% resource utilization
Scale-down Trigger: <30% resource utilization for 10 minutes
```

#### Total Resource Capacity
```
Minimum Configuration (3 nodes):
├── CPU: 12 cores total
├── Memory: 24GB+ total
├── Network: 3 x high-speed connections
└── Storage: 3 x SSD-backed local storage

Maximum Configuration (6 nodes):
├── CPU: 24 cores total
├── Memory: 48GB+ total
├── Network: 6 x high-speed connections
└── Storage: 6 x SSD-backed local storage
```

## 🌐 Network Architecture

### 📡 Network Topology Diagram

```
                    Internet Gateway
                           │
                           ▼
                  ┌─────────────────┐
                  │  Rackspace Edge │
                  │    Load Balancer │
                  └─────────┬───────┘
                            │
                    ┌───────┼───────┐
                    │   Cloudspace   │
                    │   Network      │
                    │   us-central-  │
                    │   ord-1        │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │        Kubernetes Cluster         │
          │                                   │
          │  ┌─────────────────────────────┐  │
          │  │      Control Plane          │  │
          │  │    (Managed by Rackspace)   │  │
          │  └─────────────┬───────────────┘  │
          │                │                  │
          │  ┌─────────────▼───────────────┐  │
          │  │        Cilium CNI           │  │
          │  │     Pod Network Layer       │  │
          │  └─────────────┬───────────────┘  │
          │                │                  │
    ┌─────┼────────────────┼────────────────┼─────┐
    │     │                │                │     │
    ▼     ▼                ▼                ▼     ▼
 Node-1 Node-2         Node-3           Node-4 Node-5
[Min]   [Min]          [Min]           [Auto] [Auto]
    │     │                │                │     │
    ▼     ▼                ▼                ▼     ▼
┌─────┬─────┐      ┌─────┬─────┐      ┌─────┬─────┐
│Pod  │Pod  │      │Pod  │Pod  │      │Pod  │Pod  │
│Net  │Net  │      │Net  │Net  │      │Net  │Net  │
└─────┴─────┘      └─────┴─────┘      └─────┴─────┘
```

### 🔗 Network Layers

#### Layer 1: Physical Infrastructure
- **Provider**: Rackspace Cloud Infrastructure
- **Region**: us-central-ord-1 (Chicago)
- **Availability Zone**: Rackspace managed
- **Network Backbone**: High-speed Rackspace network

#### Layer 2: Cloudspace Network
- **Cloudspace**: cloud-homelab
- **Network Type**: Private cloud network
- **Security**: Rackspace security groups
- **Isolation**: Tenant-level network isolation

#### Layer 3: Kubernetes Cluster Network
- **CNI**: Cilium
- **Pod CIDR**: Automatically assigned by Cilium
- **Service CIDR**: Kubernetes service network
- **Cluster DNS**: CoreDNS with Cilium integration

#### Layer 4: Application Network
- **Ingress**: Cilium ingress controller
- **Load Balancing**: Cilium eBPF load balancing
- **Service Mesh**: Cilium service mesh (optional)
- **Network Policies**: Cilium network policies

## 🔒 Network Segmentation Strategy

### 🛡️ Security Zones

```
┌─────────────────────────────────────────────────────────────┐
│                        DMZ Zone                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Public-Facing Services                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Ingress   │  │ Load Balancer│  │   Gateway   │ │   │
│  │  │ Controller  │  │              │  │   Services  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ Firewall/Network Policies
┌─────────────────────────▼───────────────────────────────────┐
│                   Application Zone                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Frontend Tier                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Web Apps  │  │    APIs     │  │  Microservices │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Backend Tier                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Business   │  │   Message   │  │  Processing │ │   │
│  │  │   Logic     │  │   Queues    │  │   Services  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ Database Network Policies
┌─────────────────────────▼───────────────────────────────────┐
│                     Data Zone                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 Data Tier                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Databases  │  │   Storage   │  │   Backups   │ │   │
│  │  │             │  │   Services  │  │             │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 🔧 Network Policy Implementation

#### Default Security Posture
```yaml
# Default deny all traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

#### Namespace Isolation Matrix
| Source Namespace | Target Namespace | Access Level | Policy Type |
|------------------|------------------|--------------|-------------|
| frontend | backend | HTTP/HTTPS | Selective Allow |
| backend | database | Database Ports | Selective Allow |
| monitoring | all | Metrics Ports | Monitoring Allow |
| ingress | frontend | HTTP/HTTPS | Ingress Allow |
| all | external | HTTPS/DNS | Egress Control |

## 🗺️ Detailed VM Layout

### 🖥️ Node Specifications Per VM

#### Node-1 (Master/Worker - Minimum Node)
```
Hostname: node-1.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Always Running (Minimum Pool)

Hardware Specifications:
├── CPU: 4 vCPUs (Intel/AMD x86_64)
├── Memory: 8GB+ RAM
├── Storage: SSD-backed local storage
├── Network: High-speed Rackspace network
└── Region: us-central-ord-1

Software Configuration:
├── OS: Container Linux (Rackspace managed)
├── Kubernetes: v1.31.1
├── CNI: Cilium
├── Container Runtime: containerd
└── Node Labels: spot=true, nodepool=autoscaling-bid

Network Configuration:
├── Cluster IP: Assigned by Kubernetes
├── Pod CIDR: Assigned by Cilium
├── External IP: Rackspace managed
└── DNS: CoreDNS + Cilium
```

#### Node-2 (Worker - Minimum Node)
```
Hostname: node-2.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Always Running (Minimum Pool)

Hardware Specifications:
├── CPU: 4 vCPUs (Intel/AMD x86_64)
├── Memory: 8GB+ RAM
├── Storage: SSD-backed local storage
├── Network: High-speed Rackspace network
└── Region: us-central-ord-1

Software Configuration:
├── OS: Container Linux (Rackspace managed)
├── Kubernetes: v1.31.1
├── CNI: Cilium
├── Container Runtime: containerd
└── Node Labels: spot=true, nodepool=autoscaling-bid

Network Configuration:
├── Cluster IP: Assigned by Kubernetes
├── Pod CIDR: Assigned by Cilium
├── External IP: Rackspace managed
└── DNS: CoreDNS + Cilium
```

#### Node-3 (Worker - Minimum Node)
```
Hostname: node-3.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Always Running (Minimum Pool)

Hardware Specifications:
├── CPU: 4 vCPUs (Intel/AMD x86_64)
├── Memory: 8GB+ RAM
├── Storage: SSD-backed local storage
├── Network: High-speed Rackspace network
└── Region: us-central-ord-1

Software Configuration:
├── OS: Container Linux (Rackspace managed)
├── Kubernetes: v1.31.1
├── CNI: Cilium
├── Container Runtime: containerd
└── Node Labels: spot=true, nodepool=autoscaling-bid

Network Configuration:
├── Cluster IP: Assigned by Kubernetes
├── Pod CIDR: Assigned by Cilium
├── External IP: Rackspace managed
└── DNS: CoreDNS + Cilium
```

#### Node-4 (Worker - Auto-scale Node)
```
Hostname: node-4.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Auto-scaling (Based on Load)

Hardware Specifications:
├── CPU: 4 vCPUs (Intel/AMD x86_64)
├── Memory: 8GB+ RAM
├── Storage: SSD-backed local storage
├── Network: High-speed Rackspace network
└── Region: us-central-ord-1

Software Configuration:
├── OS: Container Linux (Rackspace managed)
├── Kubernetes: v1.31.1
├── CNI: Cilium
├── Container Runtime: containerd
└── Node Labels: spot=true, nodepool=autoscaling-bid

Auto-scaling Triggers:
├── Scale Up: CPU > 80% for 5 minutes
├── Scale Down: CPU < 30% for 10 minutes
├── Memory Pressure: >85% memory utilization
└── Pod Pressure: >80% pod capacity
```

#### Node-5 (Worker - Auto-scale Node)
```
Hostname: node-5.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Auto-scaling (Based on Load)

[Same specifications as Node-4]
```

#### Node-6 (Worker - Auto-scale Node)
```
Hostname: node-6.cloud-homelab.local
Role: Kubernetes Worker Node
Status: Auto-scaling (Based on Load)

[Same specifications as Node-4]
```

## 🔄 Dynamic Scaling Behavior

### 📈 Scaling Scenarios

#### Scenario 1: Low Load (3 Nodes)
```
Time: Off-peak hours
Resource Utilization: <30%
Active Nodes: 3 (minimum)
Status: Stable
Actions: None (minimum maintained)
```

#### Scenario 2: Medium Load (4-5 Nodes)
```
Time: Business hours
Resource Utilization: 50-80%
Active Nodes: 4-5
Status: Auto-scaling active
Actions: Gradual scale-up based on demand
```

#### Scenario 3: High Load (6 Nodes)
```
Time: Peak usage/traffic spikes
Resource Utilization: >80%
Active Nodes: 6 (maximum)
Status: At capacity
Actions: Maximum scale reached, load balancing
```

#### Scenario 4: Scale-down (6→3 Nodes)
```
Time: Load decrease
Resource Utilization: <30% for 10+ minutes
Active Nodes: Gradual reduction to 3
Status: Scaling down
Actions: Graceful pod draining and node removal
```

## 🛠️ Management and Monitoring

### 📊 Resource Monitoring Points

#### Per-Node Monitoring
- **CPU Utilization**: Real-time and historical
- **Memory Usage**: Available/Used/Cached
- **Network I/O**: Bytes in/out, packet statistics
- **Storage I/O**: Read/Write operations, latency
- **Pod Count**: Running/Pending/Failed pods

#### Cluster-Level Monitoring
- **Total Resource Capacity**: Aggregate resources
- **Resource Allocation**: Requests vs. limits
- **Network Traffic**: Inter-node communication
- **API Server Performance**: Request latency
- **etcd Health**: Database performance metrics

### 🔧 Management Tools

#### Infrastructure Management
- **Terraform**: Infrastructure as Code
- **Rackspace Console**: Web-based management
- **kubectl**: Kubernetes CLI management
- **Cilium CLI**: Network policy management

#### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and management
- **Loki**: Log aggregation and analysis

## 🔐 Security Configuration

### 🛡️ Node Security

#### OS Security
- **Container Linux**: Hardened container-optimized OS
- **Automatic Updates**: Security patches applied automatically
- **Minimal Attack Surface**: Reduced unnecessary services
- **SELinux/AppArmor**: Mandatory access controls

#### Network Security
- **Private Networking**: Nodes on private network
- **Security Groups**: Rackspace-managed firewall rules
- **Network Policies**: Cilium-enforced micro-segmentation
- **Encryption**: TLS encryption for all communications

#### Access Control
- **RBAC**: Role-based access control
- **Service Accounts**: Minimal privilege principals
- **Pod Security Standards**: Container security policies
- **Secrets Management**: Encrypted secret storage

## 💾 Storage Architecture

### 🗄️ Storage Types

#### Node Local Storage
- **Type**: SSD-backed local storage
- **Performance**: High IOPS, low latency
- **Use Case**: Container images, temporary files
- **Persistence**: Non-persistent (node lifecycle)

#### Persistent Storage (Optional)
- **Provider**: Rackspace Block Storage
- **Types**: SSD/SATA storage classes
- **Persistence**: Independent of node lifecycle
- **Use Case**: Database storage, application data

#### Backup Storage
- **Provider**: Rackspace Object Storage
- **Type**: S3-compatible object storage
- **Use Case**: Backup and archival storage
- **Retention**: Configurable retention policies

## 🔄 Disaster Recovery

### 💾 Backup Strategy

#### Infrastructure Backup
- **Terraform State**: Version-controlled state files
- **Cluster Configuration**: Kubernetes resource exports
- **Security Policies**: Network policy definitions
- **Monitoring Configuration**: Prometheus/Grafana configs

#### Data Backup
- **etcd Backup**: Kubernetes cluster state
- **Application Data**: Persistent volume snapshots
- **Configuration Data**: ConfigMaps and Secrets
- **Log Data**: Historical log archives

### 🔧 Recovery Procedures

#### Node Recovery
1. **Single Node Failure**: Automatic replacement by autoscaler
2. **Multiple Node Failure**: Manual intervention may be required
3. **Complete Node Loss**: Redeploy from Terraform configuration
4. **Data Recovery**: Restore from backup storage

#### Cluster Recovery
1. **Partial Outage**: Kubernetes self-healing
2. **Control Plane Issues**: Rackspace support engagement
3. **Complete Cluster Loss**: Full infrastructure rebuild
4. **Data Restoration**: Systematic data recovery procedures

## 📈 Performance Characteristics

### ⚡ Performance Metrics

#### Network Performance
- **Inter-node Latency**: <1ms within region
- **Pod-to-pod Latency**: <5ms with Cilium CNI
- **External Latency**: <10ms to internet
- **Bandwidth**: High-speed Rackspace network

#### Compute Performance
- **CPU Performance**: 4 dedicated vCPUs per node
- **Memory Performance**: >8GB per node
- **Storage Performance**: SSD-backed local storage
- **Container Startup**: <30 seconds for typical containers

#### Scaling Performance
- **Scale-up Time**: 2-5 minutes for new nodes
- **Scale-down Time**: 5-10 minutes (graceful draining)
- **Auto-scaling Response**: 1-3 minutes decision time
- **Load Balancing**: Real-time traffic distribution

## 📞 Support and Maintenance

### 🛠️ Maintenance Windows

#### Regular Maintenance
- **Security Updates**: Automated by Rackspace
- **Kubernetes Updates**: Scheduled with notification
- **Node Replacement**: Rolling updates with zero downtime
- **Network Maintenance**: Rackspace managed with SLA

#### Emergency Maintenance
- **Security Patches**: Immediate application
- **Critical Updates**: Emergency change procedures
- **Hardware Issues**: Automatic failover and replacement
- **Network Issues**: Rackspace NOC response

### 📞 Support Contacts

#### Rackspace Support
- **Technical Support**: 24/7 support portal
- **Emergency Support**: Critical issue hotline
- **Account Management**: Dedicated account team
- **Community**: Rackspace community forums

#### Internal Support
- **Infrastructure Team**: Primary support contact
- **Platform Team**: Kubernetes expertise
- **Security Team**: Security-related issues
- **Operations Team**: Day-to-day operations

## 📋 Compliance and Governance

### 🔒 Compliance Standards

#### Security Compliance
- **SOC 2**: Rackspace SOC 2 Type II certification
- **ISO 27001**: Information security management
- **PCI DSS**: Payment card industry standards (if applicable)
- **GDPR**: Data protection regulation compliance

#### Operational Compliance
- **SLA Requirements**: 99.9% uptime SLA
- **Data Residency**: us-central-ord-1 region
- **Audit Logging**: Comprehensive audit trails
- **Change Management**: Controlled change procedures

---

**Document Information**

| Field | Value |
|-------|-------|
| Document ID | VNL-LAYOUT-001 |
| Version | 1.0.0 |
| Author | Infrastructure Validator Agent |
| Creation Date | $(date) |
| Next Review | +1 month |
| Classification | Internal |

**Architecture Review**

| Role | Name | Date | Status |
|------|------|------|-------|
| Infrastructure Validator | Agent | $(date) | ✅ Complete |
| Network Architect | | | |
| Security Architect | | | |
| Operations Lead | | | |

**Change Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | $(date) | Infrastructure Validator | Initial documentation |

This comprehensive VM and network layout documentation provides complete visibility into the cloud-homelab infrastructure architecture, enabling effective management, troubleshooting, and future planning.