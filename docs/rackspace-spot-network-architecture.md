# Rackspace Spot Network Architecture Design

**Document Version**: 1.0  
**Created**: 2025-07-27  
**Author**: Hive Mind Network Architect  
**Environment**: Rackspace Spot Kubernetes with Cilium CNI  

## 🎯 Executive Summary

This document defines the network architecture for Rackspace Spot infrastructure, leveraging Kubernetes-native segmentation instead of traditional VLANs. The design utilizes Cilium CNI's advanced networking capabilities for environment isolation, namespace segmentation, and integration with existing homelab infrastructure.

## 🏗️ Architecture Overview

### Core Design Principles

1. **Kubernetes-Native Segmentation**: Use namespaces and Cilium NetworkPolicies instead of traditional VLAN-based segmentation
2. **Environment Isolation**: Separate cloudspaces for production and lab environments
3. **Zero Trust Networking**: Default-deny policies with explicit allow rules
4. **Cilium Integration**: Leverage existing homelab Cilium deployment for hybrid connectivity

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Rackspace Spot Cloud                        │
├─────────────────────┬───────────────────────────────────────────┤
│   prod-homelab      │            lab-homelab                    │
│   Cloudspace        │            Cloudspace                     │
│                     │                                           │
│ ┌─────────────────┐ │ ┌─────────────────────────────────────────┐ │
│ │ Kubernetes      │ │ │ Kubernetes Cluster                      │ │
│ │ Cluster v1.31.1 │ │ │ v1.31.1                                 │ │
│ │ CNI: Cilium     │ │ │ CNI: Cilium                             │ │
│ └─────────────────┘ │ └─────────────────────────────────────────┘ │
└─────────────────────┼───────────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │  Integration Hub  │
            │ (Cilium Mesh)     │
            └─────────┬─────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                 Existing Homelab                                │
│              K3s + Cilium CNI                                   │
│         ArgoCD + Monitoring Stack                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🔒 Environment Isolation Strategy

### 1. Cloudspace-Level Separation

**Production Environment** (`prod-homelab`)
- **Purpose**: Mission-critical workloads and services
- **Network Policy**: Default-deny with strict allow rules
- **HA Configuration**: 3 control plane nodes
- **Worker Pools**: General (4 vCPU), Memory-optimized (8 vCPU), GPU (variable)
- **Security**: Maximum isolation and monitoring

**Lab Environment** (`lab-homelab`)
- **Purpose**: Development, testing, and experimentation
- **Network Policy**: Configurable (permissive/restrictive modes)
- **HA Configuration**: Configurable (cost-optimized)
- **Worker Pools**: General (2 vCPU), Experimental (1 vCPU)
- **Security**: Flexible policies for development needs

### 2. Namespace-Based Segmentation

#### Production Environment Namespaces

```yaml
Namespaces:
  ├── kube-system          # System components (Cilium, CoreDNS)
  ├── monitoring           # Prometheus, Grafana, AlertManager
  ├── ingress-system       # Traefik, Cert-Manager
  ├── storage              # CSI drivers, storage operators
  ├── database             # PostgreSQL, Redis clusters
  ├── applications         # Business applications
  ├── batch-jobs           # Scheduled tasks and ETL
  └── utilities            # Support tools and operators
```

#### Lab Environment Namespaces

```yaml
Namespaces:
  ├── kube-system          # System components
  ├── development          # Active development workloads
  ├── testing              # Test environments and CI/CD
  ├── experimental         # Research and proof-of-concepts
  ├── staging              # Pre-production validation
  └── playground           # Learning and experimentation
```

## 🌐 Network Policy Framework

### 1. Production Environment Policies

#### Default Deny Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

#### System Services Allow Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: system-services-allow
  namespace: kube-system
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - {}  # Allow all ingress for system services
  egress:
  - {}  # Allow all egress for system services
```

#### Inter-Namespace Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring-access
  namespace: applications
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8080  # Metrics endpoint
```

### 2. Lab Environment Policies

#### Permissive Mode (Default)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-intra-namespace
  namespace: development
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: lab
```

#### Restrictive Mode (Security Testing)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: security-test-deny
  namespace: testing
spec:
  podSelector:
    matchLabels:
      security-test: "true"
  policyTypes:
  - Ingress
  - Egress
  # No ingress/egress rules = deny all
```

## 🔧 Cilium Advanced Features

### 1. CiliumNetworkPolicy for L7 Security

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-l7-security
  namespace: applications
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/.*"
        - method: "POST"
          path: "/api/v1/users"
```

### 2. Cluster Mesh Integration

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterMesh
metadata:
  name: homelab-mesh
spec:
  clusters:
  - name: rackspace-prod
    address: prod-cluster.rackspace.endpoint
  - name: rackspace-lab
    address: lab-cluster.rackspace.endpoint
  - name: homelab-k3s
    address: homelab.local.endpoint
  enabledServices:
  - global-load-balancing
  - cross-cluster-discovery
  - network-policy-enforcement
```

### 3. Service Mesh Integration

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: api-gateway
  namespace: applications
spec:
  services:
  - name: api-server
    namespace: applications
  backendServices:
  - name: backend-v1
    namespace: applications
    weight: 90
  - name: backend-v2
    namespace: applications
    weight: 10
  routingRules:
  - match:
      headers:
      - name: "x-canary"
        value: "true"
    route:
      service: backend-v2
```

## 🔗 Integration with Existing Homelab

### 1. Cilium Mesh Connectivity

```yaml
# Homelab K3s Cilium Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  cluster-name: homelab-k3s
  cluster-id: "1"
  enable-cluster-mesh: "true"
  cluster-mesh-config: |
    clusters:
    - name: rackspace-prod
      id: 2
      address: prod.mesh.rackspace.endpoint:2379
    - name: rackspace-lab
      id: 3
      address: lab.mesh.rackspace.endpoint:2379
```

### 2. Cross-Cluster Service Discovery

```yaml
apiVersion: v1
kind: Service
metadata:
  name: homelab-monitoring
  namespace: monitoring
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/shared: "true"
spec:
  type: ClusterIP
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
```

### 3. GitOps Integration with ArgoCD

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rackspace-network-policies
  namespace: argocd
spec:
  project: networking
  source:
    repoURL: https://github.com/homelab/infrastructure
    path: rackspace/network-policies
    targetRevision: main
  destination:
    server: https://rackspace-prod-api.endpoint
    namespace: networking
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## 🛡️ Security Implementation

### 1. Zero Trust Network Model

**Principles:**
- Default deny all traffic
- Explicit allow rules only
- Least privilege access
- Continuous monitoring and logging

**Implementation:**
```yaml
# Global default deny (applied to all namespaces)
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: global-default-deny
spec:
  endpointSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 2. Workload Identity and mTLS

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: mtls-enforcement
  namespace: applications
spec:
  endpointSelector:
    matchLabels:
      security: high
  ingress:
  - fromEndpoints:
    - matchLabels:
        identity: verified-client
    authentication:
      mode: required
  egress:
  - toEndpoints:
    - matchLabels:
        identity: verified-server
    authentication:
      mode: required
```

### 3. Network Encryption

```yaml
# Enable Cilium WireGuard encryption
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-wireguard: "true"
  wireguard-userspace-fallback: "true"
```

## 📊 Monitoring and Observability

### 1. Network Policy Monitoring

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cilium-network-policies
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: cilium
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### 2. Flow Visibility with Hubble

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-hubble: "true"
  hubble-flow-buffer-size: "65535"
  hubble-metrics: >
    dns,drop,tcp,flow,icmp,http:sourceContext=workload-name|reserved-identity;destinationContext=workload-name|reserved-identity
```

### 3. Policy Violation Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-network-policy-alerts
  namespace: monitoring
spec:
  groups:
  - name: cilium.network.policy
    rules:
    - alert: NetworkPolicyViolation
      expr: increase(cilium_policy_verdict_total{verdict="denied"}[5m]) > 10
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "High number of network policy violations detected"
        description: "{{ $value }} network policy violations in the last 5 minutes"
```

## 🚀 Deployment Strategy

### 1. Phase 1: Infrastructure Setup
1. Deploy Rackspace Spot clusters with Cilium CNI
2. Configure basic network policies (default deny)
3. Set up monitoring and logging infrastructure
4. Establish cluster mesh connectivity

### 2. Phase 2: Namespace Segmentation
1. Create namespace hierarchy
2. Implement namespace-specific network policies
3. Deploy workloads with proper labels
4. Test isolation and connectivity

### 3. Phase 3: Advanced Features
1. Enable L7 policies and service mesh
2. Implement workload identity and mTLS
3. Configure cross-cluster services
4. Optimize performance and security

### 4. Phase 4: Integration and Validation
1. Connect to existing homelab infrastructure
2. Validate security boundaries
3. Performance testing and optimization
4. Documentation and runbooks

## 🔧 Terraform Implementation

### Network Policy Resources

```hcl
# Production environment network policies
resource "kubernetes_network_policy" "prod_default_deny" {
  count = var.enable_network_policies ? 1 : 0
  
  metadata {
    name      = "default-deny-all"
    namespace = "default"
    labels = {
      "environment" = "production"
      "policy-type" = "security"
    }
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
  
  depends_on = [module.prod_cluster]
}

# Cilium-specific network policies
resource "kubectl_manifest" "cilium_l7_policy" {
  count = var.enable_cilium_l7_policies ? 1 : 0
  
  yaml_body = yamlencode({
    apiVersion = "cilium.io/v2"
    kind       = "CiliumNetworkPolicy"
    metadata = {
      name      = "api-l7-security"
      namespace = "applications"
    }
    spec = {
      endpointSelector = {
        matchLabels = {
          app = "api-server"
        }
      }
      ingress = [
        {
          fromEndpoints = [
            {
              matchLabels = {
                app = "frontend"
              }
            }
          ]
          toPorts = [
            {
              ports = [
                {
                  port     = "8080"
                  protocol = "TCP"
                }
              ]
              rules = {
                http = [
                  {
                    method = "GET"
                    path   = "/api/v1/.*"
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  })
}
```

### Namespace Creation with Labels

```hcl
# Production namespaces with proper labels
resource "kubernetes_namespace" "prod_namespaces" {
  for_each = var.prod_namespaces
  
  metadata {
    name = each.key
    labels = merge(
      {
        "environment"    = "production"
        "network-policy" = each.value.network_policy
        "monitoring"     = each.value.monitoring
      },
      each.value.additional_labels
    )
  }
  
  depends_on = [module.prod_cluster]
}

# Lab namespaces with flexible configuration
resource "kubernetes_namespace" "lab_namespaces" {
  for_each = var.lab_namespaces
  
  metadata {
    name = each.key
    labels = merge(
      {
        "environment"    = "lab"
        "network-policy" = each.value.network_policy
        "cost-tier"      = "optimized"
      },
      each.value.additional_labels
    )
  }
  
  depends_on = [module.lab_cluster]
}
```

## 📋 Validation and Testing

### 1. Network Isolation Tests

```bash
# Test namespace isolation
kubectl run test-pod-1 --image=busybox --namespace=development
kubectl run test-pod-2 --image=busybox --namespace=testing

# Verify isolation (should fail)
kubectl exec -n development test-pod-1 -- ping test-pod-2.testing.svc.cluster.local

# Test allowed communication
kubectl exec -n monitoring prometheus-pod -- curl api-server.applications:8080/metrics
```

### 2. Policy Validation

```bash
# Check Cilium policy status
kubectl get cnp,ccnp --all-namespaces

# Verify policy enforcement
cilium policy get --all-namespaces

# Test L7 policy enforcement
curl -H "X-Test: blocked" http://api-server.applications:8080/api/v1/unauthorized
```

### 3. Cluster Mesh Connectivity

```bash
# Verify cluster mesh status
cilium clustermesh status

# Test cross-cluster service discovery
kubectl get services --context=rackspace-prod
kubectl get services --context=homelab-k3s

# Test cross-cluster connectivity
kubectl exec -n applications test-pod -- curl homelab-monitoring.monitoring.svc.cluster.local:9090
```

## 🔄 Maintenance and Operations

### 1. Policy Updates

- Use GitOps approach with ArgoCD for policy management
- Version control all network policies
- Implement canary deployments for policy changes
- Monitor policy violations and adjust as needed

### 2. Performance Monitoring

- Regular Cilium performance metrics review
- Network latency and throughput monitoring
- Policy enforcement overhead analysis
- Capacity planning for cluster mesh

### 3. Security Auditing

- Quarterly network policy reviews
- Penetration testing of isolation boundaries
- Compliance validation (if applicable)
- Incident response procedures for policy violations

## 🎯 Future Enhancements

### 1. Advanced Security Features

- **Cilium Tetragon**: Runtime security observability
- **Network Segmentation**: Micro-segmentation with Cilium
- **Threat Detection**: Integration with security tools
- **Compliance**: Automated compliance checking

### 2. Performance Optimizations

- **eBPF Optimization**: Custom eBPF programs for specific workloads
- **Network Acceleration**: DPDK integration where applicable
- **Load Balancing**: Advanced load balancing algorithms
- **Traffic Engineering**: QoS and traffic shaping

### 3. Multi-Cloud Integration

- **Cloud Interconnect**: Direct connections to other cloud providers
- **Hybrid Networking**: Seamless on-premises integration
- **Disaster Recovery**: Cross-cloud backup and failover
- **Cost Optimization**: Multi-cloud workload placement

## 📚 References and Documentation

- [Cilium Documentation](https://docs.cilium.io/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Rackspace Spot Documentation](https://docs.rackspace.com/spot/)
- [Cluster Mesh Configuration](https://docs.cilium.io/en/stable/gettingstarted/clustermesh/)
- [Hubble Observability](https://docs.cilium.io/en/stable/intro/#hubble)

---

**Document Classification**: Technical Architecture  
**Review Cycle**: Quarterly  
**Next Review**: 2025-10-27  
**Approved By**: Hive Mind Architect Agent  