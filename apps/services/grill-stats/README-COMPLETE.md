# Grill Stats Kustomize Configuration

This document provides a comprehensive overview of the Kustomize configuration structure for the ThermoWorks BBQ monitoring application, supporting both dev-lab and prod-lab environments.

## Architecture Overview

The Grill Stats application consists of 6 core microservices:

1. **Authentication Service** (Port 8082) - JWT authentication with ThermoWorks integration
2. **Device Service** (Port 8080) - Device management with PostgreSQL backend
3. **Temperature Service** (Port 8081) - Real-time data with InfluxDB and Redis
4. **Historical Data Service** (Port 8083) - Historical analysis with TimescaleDB
5. **Encryption Service** (Port 8082) - Secure credential storage with HashiCorp Vault
6. **Web UI Service** (Port 80) - React frontend with Nginx reverse proxy

## Directory Structure

```
kustomize/
├── base/
│   ├── core-services/           # Core microservices
│   │   ├── auth-service.yaml
│   │   ├── device-service.yaml
│   │   ├── temperature-service.yaml
│   │   ├── historical-data-service.yaml
│   │   ├── encryption-service.yaml
│   │   ├── web-ui-service.yaml
│   │   ├── monitoring.yaml
│   │   └── kustomization.yaml
│   ├── databases/               # Database services
│   │   ├── postgresql.yaml
│   │   ├── influxdb.yaml
│   │   ├── redis.yaml
│   │   └── kustomization.yaml
│   ├── namespace/               # Namespace resources
│   │   ├── namespace.yaml
│   │   ├── resourcequota.yaml
│   │   ├── networkpolicy.yaml
│   │   ├── 1password-secrets.yaml
│   │   └── kustomization.yaml
│   ├── ingress/                 # Ingress configuration
│   │   ├── traefik-ingressroute.yaml
│   │   ├── traefik-middleware.yaml
│   │   └── kustomization.yaml
│   └── kustomization.yaml       # Base kustomization
├── overlays/
│   ├── dev-lab/                 # Development environment
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   └── patches/
│   │       ├── replicas.yaml
│   │       ├── resources.yaml
│   │       ├── ingress.yaml
│   │       └── environment.yaml
│   └── prod-lab/                # Production environment
│       ├── kustomization.yaml
│       ├── namespace.yaml
│       ├── hpa.yaml
│       ├── pdb.yaml
│       └── patches/
│           ├── replicas.yaml
│           ├── resources.yaml
│           ├── ingress.yaml
│           └── environment.yaml
```

## Environment Configurations

### Dev-Lab Environment

**Namespace**: `grill-stats-dev`
**Resource Allocation**: Optimized for development workloads
**Scaling**: Single replica for all services
**Image Tags**: `dev-latest`

**Key Features**:
- Reduced resource requests and limits
- Debug logging enabled
- Faster sync intervals
- Relaxed rate limiting
- Development-specific ingress rules

**Resource Quotas**:
- CPU Requests: 2 cores
- Memory Requests: 4Gi
- CPU Limits: 4 cores
- Memory Limits: 8Gi
- Pods: 20

### Prod-Lab Environment

**Namespace**: `grill-stats`
**Resource Allocation**: Production-ready with high availability
**Scaling**: Multiple replicas with HPA
**Image Tags**: `v1.0.0`

**Key Features**:
- Production resource allocation
- Horizontal Pod Autoscaling (HPA)
- Pod Disruption Budgets (PDB)
- Enhanced security headers
- Comprehensive monitoring

**Resource Quotas**:
- CPU Requests: 8 cores
- Memory Requests: 16Gi
- CPU Limits: 16 cores
- Memory Limits: 32Gi
- Pods: 50

## Service Details

### Authentication Service
- **Purpose**: JWT authentication and ThermoWorks API integration
- **Database**: PostgreSQL for user management
- **External APIs**: ThermoWorks Cloud API
- **Security**: OAuth2 integration, rate limiting

### Device Service
- **Purpose**: Device discovery and management
- **Database**: PostgreSQL for device metadata
- **Integration**: Home Assistant, RFX Gateway
- **Features**: Device registration, health monitoring

### Temperature Service
- **Purpose**: Real-time temperature data processing
- **Database**: InfluxDB for time-series data, Redis for caching
- **Features**: WebSocket support, real-time streaming
- **Scaling**: Highest replica count (3 in prod)

### Historical Data Service
- **Purpose**: Historical data analysis and reporting
- **Database**: TimescaleDB for time-series analytics
- **Features**: Data aggregation, trend analysis
- **Caching**: Redis for query optimization

### Encryption Service
- **Purpose**: Secure credential storage and management
- **Backend**: HashiCorp Vault integration
- **Features**: Key rotation, audit logging
- **Security**: Transit encryption, secret management

### Web UI Service
- **Purpose**: React frontend with Nginx reverse proxy
- **Features**: API gateway, static asset serving
- **Routing**: Service mesh integration
- **Security**: CSP headers, HSTS

## Security Configuration

### Network Policies
- **Default Deny**: All traffic blocked by default
- **Service Mesh**: Inter-service communication allowed
- **Database Access**: Backend services can access databases
- **External Access**: Only auth service can access external APIs
- **Monitoring**: Prometheus scraping allowed

### Secret Management
- **1Password Connect**: Centralized secret management
- **HashiCorp Vault**: Encryption service backend
- **Environment Separation**: Separate secrets per environment

## Monitoring and Observability

### Prometheus Integration
- **ServiceMonitor**: Automatic service discovery
- **PrometheusRule**: Alerting rules for all services
- **Grafana Dashboard**: Comprehensive monitoring dashboard

### Key Metrics
- Service availability and health
- Request rate and latency
- Resource utilization (CPU, memory)
- Temperature data freshness
- Authentication success/failure rates

### Alerting Rules
- Service down alerts
- High resource usage warnings
- API error rate alerts
- Temperature data staleness alerts

## Deployment Instructions

### Development Environment
```bash
# Deploy to dev-lab
kubectl apply -k kustomize/overlays/dev-lab

# Verify deployment
kubectl get pods -n grill-stats-dev
kubectl get services -n grill-stats-dev
```

### Production Environment
```bash
# Deploy to prod-lab
kubectl apply -k kustomize/overlays/prod-lab

# Verify deployment
kubectl get pods -n grill-stats
kubectl get hpa -n grill-stats
kubectl get pdb -n grill-stats
```

## Validation and Testing

### Kustomize Validation
```bash
# Validate dev-lab configuration
kustomize build kustomize/overlays/dev-lab | kubectl apply --dry-run=client -f -

# Validate prod-lab configuration
kustomize build kustomize/overlays/prod-lab | kubectl apply --dry-run=client -f -
```

### Service Health Checks
```bash
# Check service health
kubectl get pods -n grill-stats -l app.kubernetes.io/part-of=grill-stats

# Check ingress configuration
kubectl get ingressroute -n grill-stats
```

## ArgoCD Integration

### Application Configuration
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grill-stats-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/grill-stats
    targetRevision: HEAD
    path: kustomize/overlays/dev-lab
  destination:
    server: https://kubernetes.default.svc
    namespace: grill-stats-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Environment Variables

### Common Configuration
```yaml
# Sync intervals
SYNC_INTERVAL: "30"    # Dev: 30s, Prod: 300s

# Logging
LOG_LEVEL: "DEBUG"     # Dev: DEBUG, Prod: INFO

# Caching
CACHE_TTL: "60"        # Dev: 60s, Prod: 600s
```

### Service-Specific Variables
```yaml
# Auth Service
RATE_LIMIT_ATTEMPTS: "10"      # Dev: 10, Prod: 5
SESSION_TIMEOUT: "43200"       # Dev: 12h, Prod: 24h

# Historical Data Service
MAX_QUERY_RANGE_DAYS: "7"     # Dev: 7, Prod: 30
AGGREGATION_WINDOW: "1m"      # Dev: 1m, Prod: 5m
```

## Troubleshooting

### Common Issues
1. **Service Not Starting**: Check resource limits and secret availability
2. **Database Connection**: Verify network policies and credentials
3. **Ingress Issues**: Check Traefik configuration and DNS resolution
4. **Scaling Problems**: Review HPA metrics and resource quotas

### Debugging Commands
```bash
# Check pod logs
kubectl logs -f deployment/auth-service -n grill-stats

# Check network policies
kubectl get networkpolicy -n grill-stats

# Check resource usage
kubectl top pods -n grill-stats
```

## Maintenance

### Regular Tasks
- Monitor resource usage and adjust quotas
- Review and update security policies
- Rotate secrets and credentials
- Update image tags for deployments
- Review and tune HPA metrics

### Backup and Recovery
- Database backups handled by persistent volume snapshots
- Configuration stored in Git repository
- Secrets managed through 1Password Connect

This comprehensive configuration provides a robust foundation for deploying the Grill Stats application in both development and production environments using GitOps principles with ArgoCD.
