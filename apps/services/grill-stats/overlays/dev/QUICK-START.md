# 🚀 Grill-Stats Development Environment - Quick Start

## One-Command Deployment

```bash
# Deploy the complete development environment
cd /mnt/c/Users/lordmuffin/Git/homelab/apps/services/grill-stats/overlays/dev
./deploy-dev.sh
```

## Instant Access

After deployment completes:

```bash
# Check application health
curl http://localhost:30500/health

# Verify mock mode is active
curl http://localhost:30500/api/config

# View mock devices
curl http://localhost:30500/devices
```

## Key Features

### 🧪 **Mock Data Enabled**
- **4 realistic devices** with live temperature simulation
- **No API keys required** - works offline
- **Historical data** included for testing

### 🔧 **Development Optimized**
- **Single replicas** to save resources
- **Debug mode** enabled with detailed logging
- **Fast sync intervals** (60s) for quick testing
- **NodePort access** on port 30500

### 🔐 **Development Credentials**
- **Admin**: `dev@localhost` / `dev123`
- **Database**: `dev_grill_user` / `dev-password-123`
- **Safe defaults** for development use

## Namespace Configuration

- **Namespace**: `grill-stats-dev`
- **Resource Limits**: 4 CPU cores, 8Gi RAM
- **Network Policy**: Open (all traffic allowed)
- **Prefix**: All resources prefixed with `dev-`

## Directory Structure

```
overlays/dev/
├── kustomization.yaml           # Main kustomization config
├── deploy-dev.sh               # One-command deployment script
├── README.md                   # Comprehensive documentation
├── QUICK-START.md             # This file
├── patches/
│   ├── dev-env-patch.yaml     # Environment variables (MOCK_MODE=true)
│   ├── dev-ingress-patch.yaml # HTTP ingress + NodePort
│   ├── dev-namespace-patch.yaml # Namespace and quotas
│   ├── dev-replicas-patch.yaml # Single replicas, no HPA/PDB
│   ├── dev-resources-patch.yaml # Reduced resource requests
│   └── dev-service-patch.yaml  # Service with NodePort
└── secrets/
    ├── grill-stats-dev-creds-1password.yaml # 1Password integration
    └── dev.env.example        # Environment variable template
```

## Common Commands

### Deployment
```bash
# Deploy
kubectl apply -k .

# Check status
kubectl get pods -n grill-stats-dev

# View logs
kubectl logs -f deployment/dev-grill-stats -n grill-stats-dev
```

### Testing
```bash
# Health check
curl http://localhost:30500/health

# Mock devices
curl http://localhost:30500/devices

# Temperature data
curl http://localhost:30500/devices/mock-bluedot-002/temperature

# Session history
curl http://localhost:30500/api/sessions/history

# Device registration test
curl -X POST http://localhost:30500/api/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_id": "TW-TEST-999", "nickname": "Test Device"}'
```

### Development
```bash
# Port forward for debugging
kubectl port-forward deployment/dev-grill-stats 5678:5678 -n grill-stats-dev

# Shell access
kubectl exec -it deployment/dev-grill-stats -n grill-stats-dev -- /bin/bash

# Scale to zero (pause)
kubectl scale deployment dev-grill-stats --replicas=0 -n grill-stats-dev

# Scale back up
kubectl scale deployment dev-grill-stats --replicas=1 -n grill-stats-dev
```

### Cleanup
```bash
# Remove development environment
kubectl delete namespace grill-stats-dev
```

## Environment Variables

| Variable | Value | Purpose |
|----------|--------|---------|
| `MOCK_MODE` | `true` | Enable mock ThermoWorks data |
| `FLASK_ENV` | `development` | Flask development mode |
| `DEBUG` | `true` | Enable debug logging |
| `SYNC_INTERVAL` | `60` | Fast sync for testing |
| `ADMIN_EMAIL` | `dev@localhost` | Development admin |
| `ADMIN_PASSWORD` | `dev123` | Development password |

## Differences from Production

| Feature | Development | Production |
|---------|------------|------------|
| **Mock Mode** | ✅ Enabled | ❌ Disabled |
| **Replicas** | 1 | 2-5 (with HPA) |
| **Resources** | 128Mi-512Mi | 256Mi-1Gi |
| **TLS** | ❌ HTTP only | ✅ HTTPS |
| **Credentials** | Hardcoded dev values | 1Password secrets |
| **Sync Interval** | 60s (fast) | 300s (production) |
| **Debug Mode** | ✅ Enabled | ❌ Disabled |
| **CORS** | ✅ Enabled | ❌ Disabled |

## Next Steps

1. **Deploy**: Run `./deploy-dev.sh`
2. **Test**: Access http://localhost:30500
3. **Develop**: Use mock data for UI development
4. **Debug**: Port forward to 5678 for debugging
5. **Customize**: Edit patches for your needs

For detailed documentation, see [README.md](README.md).