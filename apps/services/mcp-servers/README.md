# MCP Servers Deployment

This directory contains a comprehensive Model Context Protocol (MCP) server deployment system for your Kubernetes homelab, following established GitOps patterns and Kustomize configurations.

## Architecture Overview

The MCP servers deployment follows your established homelab patterns:

- **GitOps Deployment**: Managed via ArgoCD with automatic sync and self-healing
- **Kustomize Configuration**: Base/overlay structure for environment-specific configurations
- **Security Integration**: 1Password Connect for secret management, proper RBAC, and security contexts
- **Service Discovery**: Internal cluster DNS and external ingress with Traefik
- **Monitoring**: Prometheus ServiceMonitor integration for observability
- **Networking**: Following your established ClusterIP and IngressRoute patterns

## Directory Structure

```
apps/services/mcp-servers/
├── kustomization.yaml                    # Root aggregation
├── base/                                 # Core infrastructure
│   ├── kustomization.yaml
│   ├── namespace.yaml                    # mcp-servers namespace
│   ├── rbac.yaml                        # Service accounts and permissions
│   ├── shared-config.yaml               # Common configuration
│   └── monitoring.yaml                  # Prometheus integration
├── gitea-mcp/                           # Gitea MCP server
│   ├── kustomization.yaml
│   └── base/
│       ├── kustomization.yaml
│       ├── deployment.yaml
│       ├── svc.yaml
│       ├── configmap.yaml
│       └── ingress.yaml
├── kubernetes-mcp/                      # Kubernetes MCP server
├── postgresql-mcp/                      # PostgreSQL MCP server
├── redis-mcp/                          # Redis MCP server
├── sequential-thinking-mcp/             # Sequential Thinking MCP server
└── claude-code-config/                 # Claude Code integration
    └── config-generator.yaml
```

## Deployed MCP Servers

### 1. Gitea MCP Server
- **Purpose**: Integration with your Gitea instance for repository management
- **Service**: `gitea-mcp.mcp-servers.svc.cluster.local:3000`
- **External**: `https://gitea-mcp.home.andrewpjackson.com`
- **Features**:
  - Repository CRUD operations
  - Issue and Pull Request management
  - Branch and commit operations
  - File content management
  - Organization and user operations
  - Webhook management

### 2. Kubernetes MCP Server
- **Purpose**: Direct Kubernetes cluster management and operations
- **Service**: `kubernetes-mcp.mcp-servers.svc.cluster.local:3000`
- **External**: `https://k8s-mcp.home.andrewpjackson.com`
- **Features**:
  - Cluster information and node management
  - Pod, deployment, and service operations
  - ConfigMap and secret management
  - Ingress and networking operations
  - Job and CronJob management
  - RBAC operations
  - Resource metrics and monitoring

### 3. PostgreSQL MCP Server
- **Purpose**: Database operations and management
- **Service**: `postgresql-mcp.mcp-servers.svc.cluster.local:3000`
- **External**: `https://postgres-mcp.home.andrewpjackson.com`
- **Features**:
  - SQL query execution
  - Database schema management
  - Table operations
  - Data import/export
  - Performance monitoring
  - Backup and restore operations

### 4. Redis MCP Server
- **Purpose**: Cache and session management
- **Service**: `redis-mcp.mcp-servers.svc.cluster.local:3000`
- **External**: `https://redis-mcp.home.andrewpjackson.com`
- **Features**:
  - Key-value operations
  - Cache management
  - Session handling
  - Pub/Sub operations
  - Performance monitoring

### 5. Sequential Thinking MCP Server
- **Purpose**: Enhanced reasoning and problem-solving capabilities
- **Service**: `sequential-thinking-mcp.mcp-servers.svc.cluster.local:3000`
- **External**: `https://sequential-mcp.home.andrewpjackson.com`
- **Features**:
  - Step-by-step reasoning
  - Problem decomposition
  - Chain-of-thought processing
  - Decision tree analysis

## Deployment Instructions

### Prerequisites

1. **1Password Items**: Create the following items in your HomeLab vault:
   ```
   - gitea-mcp-token-1password      # Gitea API token
   - redis-mcp-creds-1password      # Redis credentials
   ```

2. **Namespace**: The `mcp-servers` namespace will be created automatically

3. **Dependencies**: Ensure the following services are running:
   - ArgoCD
   - 1Password Connect Operator
   - Traefik
   - cert-manager
   - external-dns

### Step 1: Deploy Secrets

```bash
# Deploy secrets first
kubectl apply -k apps/secrets/mcp-servers
```

### Step 2: Deploy MCP Servers

```bash
# Deploy all MCP servers
kubectl apply -k apps/services/mcp-servers
```

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -n mcp-servers

# Check services
kubectl get svc -n mcp-servers

# Check ingress routes
kubectl get ingressroute -n mcp-servers

# Run health checks
kubectl exec -n mcp-servers deployment/gitea-mcp -- curl -f http://localhost:3000/health
```

## Claude Code Integration

Three configuration modes are provided:

### Production Mode (Cluster Services)
```bash
# Extract configuration
kubectl get configmap claude-code-mcp-config -n mcp-servers -o jsonpath='{.data.claude-code-production\.json}' > ~/.config/claude-code/config.json
```

### Development Mode (Port-Forward)
```bash
# Setup port-forwarding
kubectl get configmap claude-code-mcp-config -n mcp-servers -o jsonpath='{.data.setup-port-forward\.sh}' | bash

# Use development config
kubectl get configmap claude-code-mcp-config -n mcp-servers -o jsonpath='{.data.claude-code-development\.json}' > ~/.config/claude-code/config.json
```

### External Mode (Ingress)
```bash
# Use external configuration
kubectl get configmap claude-code-mcp-config -n mcp-servers -o jsonpath='{.data.claude-code-external\.json}' > ~/.config/claude-code/config.json
```

## Monitoring and Health Checks

### Prometheus Integration
- ServiceMonitor is automatically configured
- Metrics available at `/metrics` endpoint on port 9090
- Dashboards can be imported in Grafana

### Health Check Script
```bash
# Run comprehensive health check
kubectl get configmap claude-code-mcp-config -n mcp-servers -o jsonpath='{.data.health-check\.sh}' | bash
```

### Individual Service Health
```bash
# Check specific service
kubectl exec -n mcp-servers deployment/gitea-mcp -- curl -f http://localhost:3000/health
kubectl exec -n mcp-servers deployment/kubernetes-mcp -- kubectl cluster-info
```

## Troubleshooting

### Common Issues

1. **Pod Startup Issues**
   ```bash
   kubectl describe pod -n mcp-servers -l app.kubernetes.io/part-of=mcp-servers
   kubectl logs -n mcp-servers deployment/gitea-mcp
   ```

2. **Secret Access Issues**
   ```bash
   kubectl get onepassworditem -n mcp-servers
   kubectl describe secret gitea-mcp-token-1password -n mcp-servers
   ```

3. **Service Connectivity Issues**
   ```bash
   kubectl get endpoints -n mcp-servers
   kubectl exec -n mcp-servers deployment/gitea-mcp -- nslookup gitea-internal.gitea.svc.cluster.local
   ```

4. **Ingress Issues**
   ```bash
   kubectl get ingressroute -n mcp-servers
   kubectl describe ingressroute gitea-mcp -n mcp-servers
   ```

### Resource Management

Check resource usage:
```bash
kubectl top pods -n mcp-servers
kubectl describe quota -n mcp-servers
```

### Logs and Debugging

```bash
# View logs for all MCP servers
kubectl logs -n mcp-servers -l app.kubernetes.io/part-of=mcp-servers

# Follow logs for specific server
kubectl logs -n mcp-servers -f deployment/gitea-mcp
```

## Security Considerations

- All containers run with non-root security contexts
- Secrets are managed via 1Password Connect
- RBAC follows principle of least privilege
- Network policies can be added for additional isolation
- TLS termination at ingress level
- Regular security scanning recommended

## Scaling and Performance

### Resource Limits
Current resource allocation per server:
- **Requests**: 100m CPU, 128Mi memory
- **Limits**: 200m CPU, 256Mi memory

### Horizontal Scaling
To scale individual servers:
```bash
kubectl scale deployment gitea-mcp -n mcp-servers --replicas=2
```

### Performance Monitoring
- Prometheus metrics collection enabled
- Health checks with configurable timeouts
- Resource usage monitoring via kubectl top

## Maintenance

### Updates
MCP servers will auto-update via ArgoCD when changes are committed to the repository.

### Backup
- ConfigMaps and secrets are stored in git
- Persistent data should be backed up according to your backup strategy
- Database and Redis data is handled by their respective operators

### Certificate Renewal
- Handled automatically by cert-manager
- Let's Encrypt certificates auto-renew

This deployment provides a robust, secure, and scalable MCP server infrastructure that integrates seamlessly with your existing homelab patterns and tooling.