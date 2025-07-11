# Grill-Stats Development Environment

This overlay provides a complete development environment for the grill-stats temperature monitoring platform, optimized for local development and testing.

## Features

### 🧪 **Mock Data Mode**
- **MOCK_MODE=true** - Uses fake ThermoWorks device data for development
- Pre-configured with 4 realistic devices (Test Signals, Mock BlueDOT, Fake NODE, Test DOT)
- Dynamic temperature simulation with realistic cooking patterns
- No live API dependencies required

### 🔧 **Development Configuration**
- **Single replica** deployments to save resources
- **Reduced resource requirements** (128Mi-512Mi RAM, 100m-500m CPU)
- **Fast sync intervals** (60s sync, 30s polling) for quick testing
- **Debug mode enabled** with detailed logging
- **CORS enabled** for frontend development

### 🌐 **Access Methods**
- **Ingress**: `grill-stats-dev.lab.apj.dev` (HTTP only)
- **NodePort**: `localhost:30500` for direct access
- **Debug port**: `5678` for Python debugging

### 🔐 **Development Credentials**
- **Admin User**: `dev@localhost` / `dev123`
- **Database**: `dev_grill_user` / `dev-password-123`
- **All credentials** are development-safe defaults

## Quick Start

### 1. Deploy Development Environment

```bash
# Deploy to Kubernetes
kubectl apply -k overlays/dev

# Verify deployment
kubectl get pods -n grill-stats-dev
kubectl get services -n grill-stats-dev
```

### 2. Access the Application

```bash
# Via ingress (if configured)
curl http://grill-stats-dev.lab.apj.dev/health

# Via NodePort
curl http://localhost:30500/health

# Check mock mode status
curl http://localhost:30500/api/config
```

### 3. View Mock Devices

```bash
# List mock devices
curl http://localhost:30500/devices

# Get temperature data
curl http://localhost:30500/devices/mock-bluedot-002/temperature

# View historical data
curl "http://localhost:30500/devices/mock-bluedot-002/history?start=2025-01-11T06:00:00&end=2025-01-11T10:00:00"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_MODE` | `true` | Enable mock data mode |
| `FLASK_ENV` | `development` | Flask environment |
| `DEBUG` | `true` | Enable debug mode |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity |
| `SYNC_INTERVAL` | `60` | Data sync interval (seconds) |
| `THERMOWORKS_POLLING_INTERVAL` | `30` | API polling interval (seconds) |
| `ADMIN_EMAIL` | `dev@localhost` | Admin user email |
| `ADMIN_PASSWORD` | `dev123` | Admin user password |

### Database Configuration

The development environment uses:
- **Database Name**: `grill-stats-dev`
- **Username**: `dev_grill_user`
- **Password**: `dev-password-123`
- **Host**: `dev-grill-stats-db-rw.grill-stats-dev.svc.cluster.local`

### Mock Data Configuration

Mock data includes:
- **4 Devices**: Various ThermoWorks models with different probe configurations
- **Temperature Simulation**: Realistic cooking patterns (brisket, ribs, chicken)
- **Historical Data**: 4-hour pre-generated cooking curves
- **Device Status**: Battery levels, signal strength, online/offline simulation

## Development Workflows

### Frontend Development

```bash
# Start backend in development mode
kubectl apply -k overlays/dev

# Access backend API
export BACKEND_URL=http://localhost:30500

# Start frontend development
cd services/web-ui
npm install
npm start

# Frontend available at http://localhost:3000
```

### API Testing

```bash
# Health check
curl http://localhost:30500/health

# Device management
curl -X POST http://localhost:30500/api/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_id": "TW-TEST-999", "nickname": "Test Device"}'

# Session history
curl http://localhost:30500/api/sessions/history

# Temperature alerts
curl -X POST http://localhost:30500/api/alerts \
  -H "Content-Type: application/json" \
  -d '{"device_id": "mock-bluedot-002", "probe_id": "probe_1", "target_temperature": 165}'
```

### Database Access

```bash
# Connect to development database
kubectl port-forward svc/dev-grill-stats-db-rw 5432:5432 -n grill-stats-dev

# Connect with psql
psql -h localhost -p 5432 -U dev_grill_user -d grill-stats-dev
```

### Debugging

```bash
# View application logs
kubectl logs -f deployment/dev-grill-stats -n grill-stats-dev

# Port forward for debugging
kubectl port-forward deployment/dev-grill-stats 5678:5678 -n grill-stats-dev

# Attach debugger to port 5678
```

## Resource Usage

### Pod Resources
- **CPU Request**: 100m per pod
- **Memory Request**: 128Mi per pod
- **CPU Limit**: 500m per pod
- **Memory Limit**: 512Mi per pod

### Namespace Quotas
- **Total CPU Requests**: 2 cores
- **Total Memory Requests**: 4Gi
- **Maximum Pods**: 15
- **Maximum Services**: 10

## Customization

### Custom Environment Variables

Edit `patches/dev-env-patch.yaml` to add custom environment variables:

```yaml
- name: CUSTOM_SETTING
  value: "custom-value"
```

### Custom Resource Limits

Edit `patches/dev-resources-patch.yaml` to adjust resource requirements:

```yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Custom Ingress

Edit `patches/dev-ingress-patch.yaml` to change ingress configuration:

```yaml
rules:
- host: my-custom-dev-domain.local
  http:
    paths:
    - path: /
      pathType: Prefix
      backend:
        service:
          name: grill-stats
          port:
            number: 5000
```

## Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -n grill-stats-dev

# View pod logs
kubectl logs deployment/dev-grill-stats -n grill-stats-dev

# Describe pod for events
kubectl describe pod -l app.kubernetes.io/name=grill-stats -n grill-stats-dev
```

#### Mock Data Not Working
```bash
# Verify mock mode is enabled
kubectl exec -it deployment/dev-grill-stats -n grill-stats-dev -- \
  python -c "import os; print(f'MOCK_MODE: {os.getenv(\"MOCK_MODE\")}')"

# Check mock data files
kubectl exec -it deployment/dev-grill-stats -n grill-stats-dev -- \
  ls -la services/mock_data/
```

#### Database Connection Issues
```bash
# Check database pod
kubectl get pods -n grill-stats-dev | grep postgres

# Test database connection
kubectl exec -it deployment/dev-grill-stats -n grill-stats-dev -- \
  python -c "
import psycopg2
conn = psycopg2.connect(
  host='dev-grill-stats-db-rw.grill-stats-dev.svc.cluster.local',
  database='grill-stats-dev',
  user='dev_grill_user',
  password='dev-password-123'
)
print('Database connection successful')
"
```

#### Ingress Not Working
```bash
# Check ingress status
kubectl get ingress -n grill-stats-dev

# Test with NodePort instead
curl http://localhost:30500/health
```

### Reset Development Environment

```bash
# Delete and recreate
kubectl delete namespace grill-stats-dev
kubectl apply -k overlays/dev

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grill-stats -n grill-stats-dev --timeout=300s
```

## Production Migration

When ready to deploy to production:

1. **Update Configuration**: Copy environment variables to production overlay
2. **Real Credentials**: Replace development credentials with production secrets
3. **Disable Mock Mode**: Set `MOCK_MODE=false`
4. **Real API Keys**: Configure actual ThermoWorks API credentials
5. **Database Migration**: Run production database migrations
6. **TLS Configuration**: Enable HTTPS with proper certificates

## Related Documentation

- [Mock Data Documentation](../../MOCK.md)
- [Production Deployment](../prod/README.md)
- [Base Configuration](../../base/README.md)
- [API Documentation](../../docs/api.md)