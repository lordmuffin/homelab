# Grill Stats Kustomize Configuration

This directory contains Kubernetes manifests organized with Kustomize for deploying the Grill Stats microservices platform.

## Directory Structure

```
kustomize/
├── base/                  # Base configuration shared across all environments
│   ├── namespace/         # Namespace and common resources
│   ├── databases/         # Database deployments (PostgreSQL, InfluxDB, Redis)
│   ├── core-services/     # Core service deployments
│   ├── supporting-services/ # Supporting service deployments
│   ├── ingress/           # Traefik ingress configuration
│   └── operators/         # Kafka and other operator configurations
│
└── overlays/              # Environment-specific configurations
    ├── dev/               # Development environment
    ├── staging/           # Staging environment
    └── prod/              # Production environment
```

## Components

### Base Components

1. **Namespace**: Kubernetes namespace, resource quotas, and network policies
2. **Databases**:
   - PostgreSQL for device management
   - InfluxDB for time-series temperature data
   - Redis for caching and real-time data streaming
3. **Core Services**:
   - Device Service: Device discovery and management
   - Temperature Service: Temperature data collection and analysis
4. **Supporting Services**:
   - Home Assistant Service: Integration with Home Assistant
   - Notification Service: Multi-channel alerting
   - Data Processing Service: Analytics and data transformation
5. **Ingress**: Traefik IngressRoutes with TLS and middleware
6. **Operators**: Strimzi Kafka operator with topic configuration

### Environment Overlays

1. **Development (dev)**:
   - Single replica deployments
   - Reduced resource requests and limits
   - Faster sync intervals (60 seconds)
   - Development-specific ingress hostname

2. **Staging (staging)**:
   - Moderate resource allocation
   - Intermediate sync intervals (3 minutes)
   - Staging-specific ingress hostname

3. **Production (prod)**:
   - Horizontal Pod Autoscalers (HPAs) for core services
   - Pod Disruption Budgets (PDBs) for high availability
   - Higher resource allocations
   - Standard sync intervals (5 minutes)

## Usage

### Prerequisites

- Kubernetes 1.24+
- kubectl with kustomize support
- Cert Manager for TLS certificates
- Traefik Ingress Controller
- Strimzi Operator for Kafka (via OperatorHub)

### Deployment

1. **Create environment-specific secrets**:

   ```bash
   # Development
   cp kustomize/overlays/dev/secrets/dev.env.example kustomize/overlays/dev/secrets/dev.env
   # Edit dev.env with your development secrets
   
   # Staging
   cp kustomize/overlays/staging/secrets/staging.env.example kustomize/overlays/staging/secrets/staging.env
   # Edit staging.env with your staging secrets
   
   # Production
   cp kustomize/overlays/prod/secrets/prod.env.example kustomize/overlays/prod/secrets/prod.env
   # Edit prod.env with your production secrets
   ```

2. **Deploy to development environment**:

   ```bash
   kubectl apply -k kustomize/overlays/dev
   ```

3. **Deploy to staging environment**:

   ```bash
   kubectl apply -k kustomize/overlays/staging
   ```

4. **Deploy to production environment**:

   ```bash
   kubectl apply -k kustomize/overlays/prod
   ```

### Updating Configurations

1. Modify base configurations to apply changes across all environments
2. Modify overlay-specific configurations to apply changes to a specific environment

## Scaling

- Development: All services deploy with a single replica
- Staging: Services deploy with 2 replicas
- Production: Core services use Horizontal Pod Autoscalers with min=2, max=5

## Networking

- Traefik IngressRoutes provide external access
- NetworkPolicies enforce zero-trust security
- Services communicate via internal Kubernetes DNS

## Monitoring

- All services expose Prometheus metrics endpoints
- OpenTelemetry instrumentation for distributed tracing
- Health check endpoints for readiness and liveness probes

## Kafka Topics

1. **temperature-data**: Real-time temperature readings with 7-day retention
2. **device-events**: Device connectivity and status events with 3-day retention
3. **temperature-alerts**: High/low temperature alerts with 7-day retention