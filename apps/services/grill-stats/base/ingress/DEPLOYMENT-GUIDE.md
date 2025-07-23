# Grill Stats Traefik Ingress Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Traefik ingress configuration for the Grill Stats platform across different environments (dev-lab, prod-lab, staging).

## Architecture

The ingress configuration provides:

- **Web UI Access**: Main React application served at `https://grill-stats.homelab.local`
- **API Gateway**: Microservices accessible via `/api/*` paths
- **Real-time Data**: WebSocket and SSE endpoints for temperature streaming
- **SSL/TLS**: Automatic certificate management with Let's Encrypt and self-signed certificates
- **Security**: Rate limiting, CORS, security headers, and authentication middleware
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Admin Access**: Protected administrative endpoints

## Prerequisites

1. **Traefik**: Deployed and running in the cluster
2. **cert-manager**: For SSL/TLS certificate management
3. **Prometheus**: For metrics collection (optional)
4. **Grafana**: For monitoring dashboards (optional)

## Deployment Steps

### 1. Install Required Dependencies

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Verify cert-manager is running
kubectl get pods -n cert-manager

# Install Traefik (if not already installed)
helm repo add traefik https://helm.traefik.io/traefik
helm install traefik traefik/traefik -n kube-system
```

### 2. Configure DNS

Add the following DNS entries to your homelab DNS server or `/etc/hosts`:

```
# Production Environment
192.168.1.100 grill-stats.homelab.local
192.168.1.100 api.grill-stats.homelab.local
192.168.1.100 admin.grill-stats.homelab.local

# Development Environment
192.168.1.100 grill-stats.dev.homelab.local
192.168.1.100 api.grill-stats.dev.homelab.local

# Database Access
192.168.1.100 db.grill-stats.homelab.local
192.168.1.100 influx.grill-stats.homelab.local
192.168.1.100 redis.grill-stats.homelab.local
```

### 3. Deploy Base Configuration

```bash
# Create namespace
kubectl create namespace grill-stats

# Deploy the base ingress configuration
kubectl apply -k kustomize/base/ingress/

# Verify deployment
kubectl get ingressroute -n grill-stats
kubectl get middleware -n grill-stats
kubectl get certificate -n grill-stats
```

### 4. Environment-Specific Deployments

#### Development Environment

```bash
# Create development namespace
kubectl create namespace grill-stats-dev

# Deploy development configuration
kubectl apply -k kustomize/overlays/dev-lab/

# Verify development deployment
kubectl get ingressroute -n grill-stats-dev
kubectl get certificate -n grill-stats-dev
```

#### Production Environment

```bash
# Deploy production configuration
kubectl apply -k kustomize/overlays/prod-lab/

# Verify production deployment
kubectl get ingressroute -n grill-stats
kubectl get certificate -n grill-stats
```

### 5. Configure Cloudflare (Optional)

For external access with Cloudflare DNS:

```bash
# Create Cloudflare API token secret
kubectl create secret generic cloudflare-api-token-secret \
  --from-literal=api-token=your-cloudflare-api-token \
  -n cert-manager

# Update certificate issuer to use DNS challenge
kubectl patch clusterissuer letsencrypt-prod \
  --type='merge' \
  -p='{"spec":{"acme":{"solvers":[{"dns01":{"cloudflare":{"email":"your@email.com","apiTokenSecretRef":{"name":"cloudflare-api-token-secret","key":"api-token"}}}}]}}}'
```

## Configuration Details

### Hostnames and Routing

| Environment | Web UI | API Gateway | Admin | WebSocket |
|-------------|--------|-------------|--------|-----------|
| Production  | grill-stats.homelab.local | api.grill-stats.homelab.local | admin.grill-stats.homelab.local | wss://grill-stats.homelab.local/ws |
| Development | grill-stats.dev.homelab.local | grill-stats.dev.homelab.local/api | - | wss://grill-stats.dev.homelab.local/ws |
| Staging     | grill-stats.staging.homelab.local | grill-stats.staging.homelab.local/api | - | wss://grill-stats.staging.homelab.local/ws |

### SSL/TLS Certificates

- **Production**: Let's Encrypt production certificates
- **Development**: Self-signed certificates
- **Staging**: Let's Encrypt staging certificates

### Security Features

#### Rate Limiting
- **Web UI**: 100 requests/minute, burst 50
- **API**: 1000 requests/minute, burst 200
- **WebSocket**: 500 requests/minute, burst 100
- **Admin**: 10 requests/minute, burst 5

#### CORS Configuration
- **Production**: Strict origin policy
- **Development**: Permissive for localhost development
- **Staging**: Staging-specific origins

#### Security Headers
- HSTS with 1-year max age
- Content Security Policy
- X-Frame-Options
- X-Content-Type-Options
- Referrer Policy

### Monitoring and Observability

#### Prometheus Metrics
- Request rate and latency
- Error rates by service
- Active connections
- Certificate expiry

#### Grafana Dashboard
- Real-time traffic visualization
- Service health status
- Performance metrics
- Alert status

## Troubleshooting

### Common Issues

1. **Certificate Not Issued**
   ```bash
   # Check certificate status
   kubectl describe certificate grill-stats-tls -n grill-stats

   # Check cert-manager logs
   kubectl logs -n cert-manager deployment/cert-manager
   ```

2. **Ingress Route Not Working**
   ```bash
   # Check Traefik logs
   kubectl logs -n kube-system deployment/traefik

   # Verify service endpoints
   kubectl get endpoints -n grill-stats
   ```

3. **CORS Issues**
   ```bash
   # Check middleware configuration
   kubectl get middleware grill-stats-cors -n grill-stats -o yaml

   # Test CORS headers
   curl -H "Origin: https://grill-stats.homelab.local" \
        -H "Access-Control-Request-Method: GET" \
        -X OPTIONS \
        https://api.grill-stats.homelab.local/api/health
   ```

4. **Rate Limiting Too Strict**
   ```bash
   # Update rate limit middleware
   kubectl patch middleware grill-stats-api-rate-limit -n grill-stats \
     --type='merge' \
     -p='{"spec":{"rateLimit":{"average":2000,"burst":400}}}'
   ```

### Verification Commands

```bash
# Test web UI access
curl -I https://grill-stats.homelab.local

# Test API endpoints
curl -I https://api.grill-stats.homelab.local/api/health

# Test WebSocket connection
wscat -c wss://grill-stats.homelab.local/ws

# Check certificate validity
openssl s_client -connect grill-stats.homelab.local:443 -servername grill-stats.homelab.local

# View Traefik dashboard
kubectl port-forward -n kube-system deployment/traefik 8080:8080
# Access: http://localhost:8080/dashboard/
```

## Maintenance

### Certificate Renewal
Certificates are automatically renewed by cert-manager. Monitor renewal status:

```bash
# Check certificate expiry
kubectl get certificate -n grill-stats -o wide

# Force certificate renewal
kubectl delete secret grill-stats-tls -n grill-stats
kubectl delete certificaterequest -n grill-stats --all
```

### Scaling Considerations
- Monitor rate limits and adjust based on traffic patterns
- Consider implementing circuit breakers for high-traffic scenarios
- Use HPA for scaling web UI replicas based on request volume

### Security Updates
- Regularly update middleware configurations
- Monitor security headers and CSP policies
- Review and update IP whitelists for admin access

## Integration with Existing Infrastructure

### Homelab Integration
- Integrates with existing Traefik deployment
- Uses homelab DNS conventions
- Supports multiple environment overlays

### Monitoring Integration
- Prometheus ServiceMonitor for metrics
- Grafana dashboard for visualization
- AlertManager rules for notifications

### Authentication Integration
- Forward auth to auth-service
- Support for session-based authentication
- Role-based access control headers

## Performance Optimization

### Caching
- Static asset caching via nginx in web-ui
- API response caching where appropriate
- CDN integration for external access

### Compression
- Gzip compression for all text-based responses
- Exclusion of streaming content from compression
- Brotli compression for modern browsers

### Load Balancing
- Round-robin for stateless services
- Sticky sessions for WebSocket connections
- Health checks for service availability

## Security Best Practices

1. **Network Policies**: Implement Kubernetes NetworkPolicies
2. **Secret Management**: Use 1Password Connect for secrets
3. **Regular Audits**: Monitor access logs and security events
4. **Least Privilege**: Restrict admin access to specific IP ranges
5. **TLS Everywhere**: Enforce HTTPS for all endpoints

## Next Steps

1. **Implement Monitoring**: Set up Prometheus and Grafana
2. **Configure Alerting**: Set up alerts for service health
3. **External Access**: Configure Cloudflare for external access
4. **Backup Strategy**: Implement configuration backups
5. **Disaster Recovery**: Document recovery procedures
