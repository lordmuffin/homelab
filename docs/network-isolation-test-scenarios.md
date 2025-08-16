# Network Isolation Test Scenarios
## Comprehensive Network Segmentation Validation

**Agent**: Infrastructure Validator (Hive Mind Swarm)  
**Target Infrastructure**: Rackspace Spot Cloud-Homelab  
**Version**: 1.0.0  
**Date**: $(date)

## 🎯 Test Overview

This document defines comprehensive test scenarios to verify network isolation and segmentation in the Rackspace Spot Kubernetes infrastructure. Tests validate Cilium CNI network policies, namespace isolation, and security boundaries.

## 🧪 Test Categories

### 1. Infrastructure Layer Tests
### 2. Kubernetes Network Policy Tests  
### 3. Namespace Isolation Tests
### 4. Service Mesh Security Tests
### 5. External Connectivity Tests
### 6. Security Boundary Tests

---

## 🔧 Test Environment Setup

### Prerequisites
```bash
# Ensure cluster access
kubectl cluster-info

# Verify Cilium CNI
kubectl get pods -n kube-system -l k8s-app=cilium

# Check node status
kubectl get nodes -o wide
```

### Test Namespaces
```bash
# Create test namespaces
kubectl create namespace test-frontend
kubectl create namespace test-backend
kubectl create namespace test-database
kubectl create namespace test-isolated
kubectl create namespace test-public
```

### Test Applications
```yaml
# frontend-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-app
  namespace: test-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
        tier: frontend
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: test-frontend
spec:
  selector:
    app: frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
```

```yaml
# backend-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-app
  namespace: test-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
        tier: backend
    spec:
      containers:
      - name: httpd
        image: httpd:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: test-backend
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
```

---

## 🧪 Test Scenario 1: Infrastructure Layer Network Isolation

### Test 1.1: Node-to-Node Communication
**Objective**: Verify inter-node communication within cluster
**Expected Result**: All nodes can communicate on cluster network

```bash
# Test node connectivity
kubectl get nodes -o wide

# Create test pod on each node
kubectl run node-test-1 --image=alpine --rm -it --restart=Never --overrides='{"spec":{"nodeName":"<node1-name>"}}' -- ping -c 3 <node2-ip>

kubectl run node-test-2 --image=alpine --rm -it --restart=Never --overrides='{"spec":{"nodeName":"<node2-name>"}}' -- ping -c 3 <node3-ip>
```

**Validation Criteria**:
- ✅ Ping successful between all nodes
- ✅ Network latency < 10ms
- ✅ No packet loss

### Test 1.2: Pod Network Isolation by Node
**Objective**: Verify pods on different nodes can communicate
**Expected Result**: Cross-node pod communication works

```bash
# Deploy test pods on specific nodes
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-pod-node1
  namespace: default
spec:
  nodeName: <node1-name>
  containers:
  - name: alpine
    image: alpine
    command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod-node2
  namespace: default
spec:
  nodeName: <node2-name>
  containers:
  - name: alpine
    image: alpine
    command: ["sleep", "3600"]
EOF

# Test cross-node pod communication
kubectl exec test-pod-node1 -- ping -c 3 $(kubectl get pod test-pod-node2 -o jsonpath='{.status.podIP}')
```

**Validation Criteria**:
- ✅ Cross-node pod communication successful
- ✅ Cilium routing working correctly
- ✅ Network policies not blocking legitimate traffic

---

## 🔒 Test Scenario 2: Kubernetes Network Policy Enforcement

### Test 2.1: Default Deny All Policy
**Objective**: Verify default deny policy blocks all traffic
**Expected Result**: All inter-pod communication blocked by default

```yaml
# Apply default deny policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: test-frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

```bash
# Apply policy
kubectl apply -f default-deny-policy.yaml

# Test that communication is blocked
kubectl run test-client --image=alpine --rm -it --restart=Never -n test-frontend -- wget --timeout=5 -qO- http://frontend-service.test-frontend.svc.cluster.local
```

**Validation Criteria**:
- ❌ Connection should timeout/fail
- ✅ Network policy blocking traffic
- ✅ Policy correctly applied

### Test 2.2: Selective Allow Policy
**Objective**: Verify selective allow policies permit specific traffic
**Expected Result**: Only explicitly allowed traffic passes

```yaml
# Allow frontend to backend communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: test-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: test-frontend
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
```

```bash
# Apply selective allow policy
kubectl apply -f selective-allow-policy.yaml

# Test allowed communication
kubectl run test-client --image=alpine --rm -it --restart=Never -n test-frontend -- wget --timeout=5 -qO- http://backend-service.test-backend.svc.cluster.local

# Test blocked communication (different namespace)
kubectl run test-client --image=alpine --rm -it --restart=Never -n test-isolated -- wget --timeout=5 -qO- http://backend-service.test-backend.svc.cluster.local
```

**Validation Criteria**:
- ✅ Frontend to backend communication successful
- ❌ Other namespaces blocked from backend
- ✅ Policy granularly controlling access

---

## 🏗️ Test Scenario 3: Namespace Isolation Validation

### Test 3.1: Cross-Namespace Communication Block
**Objective**: Verify namespaces are isolated by default
**Expected Result**: Pods in different namespaces cannot communicate without explicit policy

```bash
# Deploy test applications in different namespaces
kubectl apply -f frontend-app.yaml
kubectl apply -f backend-app.yaml

# Apply default deny policies to all test namespaces
for ns in test-frontend test-backend test-database test-isolated; do
  kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: $ns
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF
done

# Test cross-namespace communication (should fail)
kubectl run test-client --image=alpine --rm -it --restart=Never -n test-frontend -- wget --timeout=5 -qO- http://backend-service.test-backend.svc.cluster.local
```

**Validation Criteria**:
- ❌ Cross-namespace communication blocked
- ✅ Namespace isolation enforced
- ✅ Default security posture maintained

### Test 3.2: Intra-Namespace Communication Allow
**Objective**: Verify pods within same namespace can communicate when allowed
**Expected Result**: Same-namespace communication works with appropriate policies

```yaml
# Allow intra-namespace communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
  namespace: test-frontend
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: test-frontend
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: test-frontend
  - to: {} # Allow egress for DNS, etc.
    ports:
    - protocol: UDP
      port: 53
```

```bash
# Apply intra-namespace policy
kubectl apply -f intra-namespace-allow.yaml

# Label namespace
kubectl label namespace test-frontend name=test-frontend

# Test same-namespace communication
kubectl run test-client --image=alpine --rm -it --restart=Never -n test-frontend -- wget --timeout=5 -qO- http://frontend-service.test-frontend.svc.cluster.local
```

**Validation Criteria**:
- ✅ Same-namespace communication successful
- ✅ Service discovery working
- ✅ DNS resolution functional

---

## 🌐 Test Scenario 4: Service Mesh Security (Cilium)

### Test 4.1: Service-to-Service Encryption
**Objective**: Verify Cilium provides transparent encryption
**Expected Result**: Service communication is encrypted

```bash
# Enable Cilium encryption
kubectl patch configmap cilium-config -n kube-system --type merge -p '{"data":{"enable-wireguard":"true"}}'

# Restart Cilium pods
kubectl rollout restart daemonset cilium -n kube-system

# Verify encryption is enabled
kubectl exec -n kube-system ds/cilium -- cilium status | grep Encryption
```

**Validation Criteria**:
- ✅ Cilium encryption enabled
- ✅ WireGuard tunnels established
- ✅ Traffic encrypted between nodes

### Test 4.2: Identity-Based Security
**Objective**: Verify Cilium enforces identity-based policies
**Expected Result**: Policies based on pod identity, not IP addresses

```yaml
# Cilium Network Policy with identities
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-to-backend-identity
  namespace: test-backend
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
```

```bash
# Apply Cilium policy
kubectl apply -f cilium-identity-policy.yaml

# Test with correct identity
kubectl run frontend-test --image=alpine --rm -it --restart=Never -n test-frontend --labels="app=frontend" -- wget -qO- http://backend-service.test-backend.svc.cluster.local

# Test with incorrect identity
kubectl run wrong-identity --image=alpine --rm -it --restart=Never -n test-frontend --labels="app=other" -- wget --timeout=5 -qO- http://backend-service.test-backend.svc.cluster.local
```

**Validation Criteria**:
- ✅ Correct identity allowed
- ❌ Incorrect identity blocked
- ✅ Identity enforcement working

---

## 🔗 Test Scenario 5: External Connectivity Validation

### Test 5.1: Egress Policy Enforcement
**Objective**: Verify egress policies control outbound traffic
**Expected Result**: Only explicitly allowed external traffic permitted

```yaml
# Restrict egress to specific external services
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-egress
  namespace: test-frontend
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53  # DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS to specific domains
```

```bash
# Apply egress policy
kubectl apply -f egress-policy.yaml

# Test allowed egress (HTTPS)
kubectl run egress-test --image=alpine --rm -it --restart=Never -n test-frontend --labels="app=frontend" -- wget --timeout=5 -qO- https://httpbin.org/ip

# Test blocked egress (HTTP)
kubectl run egress-test --image=alpine --rm -it --restart=Never -n test-frontend --labels="app=frontend" -- wget --timeout=5 -qO- http://httpbin.org/ip
```

**Validation Criteria**:
- ✅ Allowed egress (HTTPS) successful
- ❌ Blocked egress (HTTP) fails
- ✅ DNS resolution still works

### Test 5.2: Ingress from External Sources
**Objective**: Verify ingress policies control inbound traffic
**Expected Result**: External traffic subject to ingress controls

```yaml
# Ingress controller with network policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-controller
  namespace: test-frontend
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 80
```

**Validation Criteria**:
- ✅ Ingress controller can reach pods
- ❌ Direct external access blocked
- ✅ Load balancer integration working

---

## 🛡️ Test Scenario 6: Security Boundary Validation

### Test 6.1: Pod Security Context Isolation
**Objective**: Verify pod security contexts prevent privilege escalation
**Expected Result**: Security contexts enforced at runtime

```yaml
# Pod with restricted security context
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: test-isolated
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: alpine
    image: alpine
    command: ["sleep", "3600"]
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
        - ALL
```

```bash
# Apply secure pod
kubectl apply -f secure-pod.yaml

# Test security context enforcement
kubectl exec secure-pod -n test-isolated -- id
kubectl exec secure-pod -n test-isolated -- ps aux
```

**Validation Criteria**:
- ✅ Pod runs as non-root user
- ✅ Capabilities dropped
- ✅ Read-only root filesystem

### Test 6.2: Resource Quota Enforcement
**Objective**: Verify resource quotas prevent resource exhaustion
**Expected Result**: Resource limits enforced per namespace

```yaml
# Resource quota for test namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: test-quota
  namespace: test-isolated
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
    pods: "5"
```

```bash
# Apply resource quota
kubectl apply -f resource-quota.yaml

# Try to exceed quota
kubectl run quota-test --image=alpine --rm -it --restart=Never -n test-isolated --requests="cpu=2,memory=3Gi" -- echo "test"
```

**Validation Criteria**:
- ❌ Resource creation exceeding quota fails
- ✅ Resource quota enforced
- ✅ Namespace resource isolation

---

## 📊 Test Execution Plan

### Phase 1: Infrastructure Tests (30 minutes)
1. Execute Test 1.1: Node-to-Node Communication
2. Execute Test 1.2: Pod Network Isolation by Node
3. Validate basic network connectivity

### Phase 2: Network Policy Tests (45 minutes)
1. Execute Test 2.1: Default Deny All Policy
2. Execute Test 2.2: Selective Allow Policy
3. Validate policy enforcement

### Phase 3: Namespace Isolation Tests (30 minutes)
1. Execute Test 3.1: Cross-Namespace Communication Block
2. Execute Test 3.2: Intra-Namespace Communication Allow
3. Validate namespace boundaries

### Phase 4: Service Mesh Tests (60 minutes)
1. Execute Test 4.1: Service-to-Service Encryption
2. Execute Test 4.2: Identity-Based Security
3. Validate Cilium features

### Phase 5: External Connectivity Tests (45 minutes)
1. Execute Test 5.1: Egress Policy Enforcement
2. Execute Test 5.2: Ingress from External Sources
3. Validate external boundaries

### Phase 6: Security Boundary Tests (30 minutes)
1. Execute Test 6.1: Pod Security Context Isolation
2. Execute Test 6.2: Resource Quota Enforcement
3. Validate security controls

## ✅ Test Results Template

### Test Execution Record
```
Test ID: [Test Number]
Test Name: [Test Description]
Execution Date: [Date/Time]
Executor: [Name/Agent]
Environment: [Cluster/Namespace]

Pre-conditions:
- [ ] Cluster accessible
- [ ] Required namespaces created
- [ ] Test applications deployed

Execution Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Expected Results:
- [Expected outcome 1]
- [Expected outcome 2]

Actual Results:
- [Actual outcome 1]
- [Actual outcome 2]

Status: ✅ PASS / ❌ FAIL / ⚠️ WARNING

Notes:
[Additional observations]

Evidence:
[Commands run, outputs, screenshots]
```

## 🚨 Failure Response Procedures

### Immediate Actions
1. **Document Failure**: Capture exact error conditions
2. **Isolate Problem**: Determine scope of impact
3. **Notify Team**: Alert relevant stakeholders
4. **Preserve Evidence**: Save logs and configurations

### Investigation Steps
1. **Review Configurations**: Check network policies and settings
2. **Examine Logs**: Analyze Cilium and Kubernetes logs
3. **Test Connectivity**: Use diagnostic tools
4. **Compare Baselines**: Check against known good states

### Remediation Actions
1. **Policy Correction**: Fix incorrect network policies
2. **Configuration Update**: Adjust cluster settings
3. **Resource Adjustment**: Modify resource allocations
4. **Documentation Update**: Update procedures based on findings

## 📈 Success Criteria

### Overall Test Suite Success
- **Pass Rate**: >95% of tests must pass
- **Security Validation**: 100% of security tests must pass
- **Performance**: Network latency <10ms within cluster
- **Isolation**: Complete namespace isolation verified

### Individual Test Success
- **Connectivity Tests**: Expected connections work
- **Isolation Tests**: Blocked connections properly denied
- **Policy Tests**: Policies enforce intended behavior
- **Security Tests**: Security controls function correctly

## 🔄 Continuous Testing

### Automated Testing
- **CI/CD Integration**: Run tests on infrastructure changes
- **Scheduled Testing**: Daily connectivity validation
- **Monitoring Integration**: Alert on test failures
- **Regression Testing**: Validate after updates

### Test Maintenance
- **Regular Review**: Monthly test procedure review
- **Update Procedures**: Modify tests for new features
- **Tool Updates**: Keep testing tools current
- **Documentation**: Maintain accurate test documentation

---

**Test Suite Information**

| Field | Value |
|-------|-------|
| Test Suite ID | NITS-001 |
| Version | 1.0.0 |
| Author | Infrastructure Validator Agent |
| Review Date | $(date) |
| Next Review | +1 month |
| Classification | Internal |

**Approval**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Infrastructure Validator | Agent | $(date) | ✓ |
| Network Security Lead | | | |
| Platform Engineering | | | |
| Quality Assurance | | | |