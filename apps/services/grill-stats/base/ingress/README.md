# Grill Stats Traefik Ingress Configuration

This directory contains the complete Traefik ingress configuration for the Grill Stats platform, providing secure external access to all services with SSL/TLS termination, rate limiting, and comprehensive monitoring.

## 📁 File Structure

```
ingress/
├── README.md                      # This file
├── DEPLOYMENT-GUIDE.md           # Comprehensive deployment guide
├── validate-ingress.sh           # Validation and testing script
├── traefik-ingressroute.yaml     # Main ingress route configurations
├── traefik-middleware.yaml       # Security and routing middleware
├── cert-issuer.yaml              # SSL/TLS certificate issuers
├── traefik-monitoring.yaml       # Prometheus monitoring configuration
├── traefik-admin.yaml            # Administrative access configuration
├── traefik-tcp.yaml              # TCP routes for database access
└── kustomization.yaml            # Kustomize configuration
```

## 🚀 Quick Start

1. **Deploy the ingress configuration:**
   ```bash
   kubectl apply -k kustomize/base/ingress/
   ```

2. **Validate the deployment:**
   ```bash
   ./kustomize/base/ingress/validate-ingress.sh
   ```

3. **Access the application:**
   - Web UI: https://grill-stats.homelab.local
   - API: https://api.grill-stats.homelab.local
   - Admin: https://admin.grill-stats.homelab.local

## 🏗️ Architecture Overview

### Service Routing

| Service | Path | Port | Description |
|---------|------|------|-------------|
| Web UI | `/` | 80 | React frontend application |
| Authentication | `/api/auth` | 8082 | User authentication service |
| Device Management | `/api/devices` | 8080 | Device discovery and management |
| Temperature Data | `/api/temperature` | 8081 | Real-time temperature data |
| Historical Data | `/api/historical` | 8083 | Historical data analysis |
| Home Assistant | `/api/homeassistant` | 8080 | Home Assistant integration |
| Notifications | `/api/notifications` | 8080 | Alert and notification service |
| Data Processing | `/api/data` | 8080 | Data processing pipeline |

### Real-time Communication

| Protocol | Path | Description |
|----------|------|-------------|
| WebSocket | `/ws` | Real-time temperature streaming |
| Server-Sent Events | `/sse` | Event streaming for UI updates |

### Administrative Access

| Service | Path | Access | Description |
|---------|------|--------|-------------|
| Traefik Dashboard | `/dashboard` | IP-restricted + BasicAuth | Traefik configuration dashboard |
| Metrics | `/metrics` | IP-restricted + BasicAuth | Prometheus metrics endpoint |
| Debug API | `/api/debug` | IP-restricted + BasicAuth | Debug and diagnostic endpoints |

## 🔒 Security Features

### SSL/TLS Configuration

- **Production**: Let's Encrypt certificates with automatic renewal
- **Development**: Self-signed certificates for local development
- **Staging**: Let's Encrypt staging certificates for testing

### Security Headers

- **HSTS**: HTTP Strict Transport Security with 1-year max age
- **CSP**: Content Security Policy with strict directives
- **X-Frame-Options**: Clickjacking protection
- **X-Content-Type-Options**: MIME type sniffing protection
- **Referrer-Policy**: Referrer information control

### Rate Limiting

- **Web UI**: 100 requests/minute, burst 50
- **API Endpoints**: 1000 requests/minute, burst 200
- **WebSocket**: 500 requests/minute, burst 100
- **Admin Endpoints**: 10 requests/minute, burst 5

### Access Control

- **CORS**: Environment-specific origin policies
- **IP Whitelist**: Admin endpoints restricted to private networks
- **Authentication**: Forward auth integration with auth-service
- **Authorization**: Role-based access control headers

## 🌐 Environment Configuration

### Production (`grill-stats.homelab.local`)

- **Security**: Maximum security with strict CSP and HSTS
- **Certificates**: Let's Encrypt production certificates
- **Rate Limiting**: Standard production limits
- **Monitoring**: Full Prometheus metrics and alerting
- **Authentication**: Required for all protected endpoints

### Development (`grill-stats.dev.homelab.local`)

- **Security**: Relaxed CSP for development tools
- **Certificates**: Self-signed certificates
- **Rate Limiting**: Higher limits for development testing
- **Authentication**: Bypass mode for easier development
- **CORS**: Permissive policy for localhost development

### Staging (`grill-stats.staging.homelab.local`)

- **Security**: Production-like security with some relaxations
- **Certificates**: Let's Encrypt staging certificates
- **Rate Limiting**: Production-like limits
- **Authentication**: Full authentication required

## 📊 Monitoring and Observability

### Prometheus Metrics

- **Request Rate**: Requests per second by service
- **Response Time**: Latency percentiles (50th, 95th, 99th)
- **Error Rate**: 4xx/5xx errors by service and endpoint
- **Active Connections**: Current connection count
- **Certificate Expiry**: Days until certificate expiration

### Grafana Dashboard

- **Traffic Overview**: Real-time request rates and patterns
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Error rates and failure analysis
- **Security Events**: Authentication failures and rate limiting

### Alerting Rules

- **High Error Rate**: Alert when error rate exceeds 5%
- **High Latency**: Alert when 95th percentile exceeds 2 seconds
- **Service Down**: Alert when service becomes unavailable
- **Certificate Expiry**: Alert when certificates expire within 30 days

## 🗄️ Database Access

TCP routes provide secure access to database services:

- **PostgreSQL**: `db.grill-stats.homelab.local:5432`
- **InfluxDB**: `influx.grill-stats.homelab.local:8086`
- **Redis**: `redis.grill-stats.homelab.local:6379`

All database access is TLS-encrypted and IP-restricted.

## 🔧 Configuration Files

### `traefik-ingressroute.yaml`

Main ingress route definitions:
- Web UI ingress for React frontend
- API Gateway for microservices
- WebSocket ingress for real-time data
- SSE ingress for event streaming
- Health check endpoints

### `traefik-middleware.yaml`

Security and routing middleware:
- Security headers with CSP and HSTS
- CORS configuration for cross-origin requests
- Rate limiting for DDoS protection
- Authentication middleware for protected endpoints
- Compression for performance optimization

### `cert-issuer.yaml`

SSL/TLS certificate management:
- Let's Encrypt production issuer
- Let's Encrypt staging issuer
- Self-signed issuer for development
- Certificate definitions for all domains

### `traefik-monitoring.yaml`

Monitoring and observability:
- Prometheus ServiceMonitor for metrics
- PrometheusRule for alerting
- Grafana dashboard configuration

### `traefik-admin.yaml`

Administrative access configuration:
- Protected dashboard access
- Metrics endpoint security
- Debug API restrictions
- BasicAuth configuration

### `traefik-tcp.yaml`

TCP routing for database access:
- PostgreSQL TCP route
- InfluxDB TCP route
- Redis TCP route
- Database-specific certificates

## 🚨 Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check service availability: `kubectl get pods -n grill-stats`
   - Verify service endpoints: `kubectl get endpoints -n grill-stats`

2. **Certificate Issues**
   - Check certificate status: `kubectl get certificate -n grill-stats`
   - View cert-manager logs: `kubectl logs -n cert-manager deployment/cert-manager`

3. **CORS Errors**
   - Verify middleware configuration: `kubectl get middleware grill-stats-cors -o yaml`
   - Check browser developer tools for CORS headers

4. **Rate Limiting**
   - Check middleware configuration: `kubectl get middleware grill-stats-api-rate-limit -o yaml`
   - Monitor rate limit headers in responses

### Debugging Commands

```bash
# Check Traefik logs
kubectl logs -n kube-system deployment/traefik

# Test connectivity
curl -I https://grill-stats.homelab.local

# Verify certificate
openssl s_client -connect grill-stats.homelab.local:443 -servername grill-stats.homelab.local

# Check middleware application
kubectl describe ingressroute grill-stats-web-ui -n grill-stats
```

## 📋 Maintenance Tasks

### Regular Maintenance

1. **Certificate Monitoring**: Check certificate expiry monthly
2. **Rate Limit Review**: Adjust rate limits based on traffic patterns
3. **Security Updates**: Update middleware configurations quarterly
4. **Performance Monitoring**: Review metrics and optimize as needed

### Scaling Considerations

- Monitor request rates and adjust rate limits
- Consider implementing circuit breakers for high traffic
- Scale web UI replicas based on load
- Implement caching strategies for frequently accessed endpoints

## 🔄 Integration Points

### Homelab Infrastructure

- Integrates with existing Traefik deployment
- Uses homelab DNS naming conventions
- Supports GitOps deployment patterns
- Compatible with ArgoCD and Flux

### Monitoring Stack

- Prometheus metrics collection
- Grafana dashboard visualization
- AlertManager notification routing
- Jaeger distributed tracing support

### Security Integration

- 1Password Connect for secret management
- Vault integration for certificate storage
- LDAP/Active Directory authentication
- RBAC with Kubernetes service accounts

## 📈 Performance Optimizations

### Caching Strategy

- Static asset caching in nginx (web-ui)
- API response caching with Redis
- Browser caching with appropriate headers
- CDN integration for external access

### Compression

- Gzip compression for text-based responses
- Brotli compression for modern browsers
- Exclusion of streaming content from compression
- Optimized compression levels for performance

### Load Balancing

- Round-robin for stateless services
- Sticky sessions for WebSocket connections
- Health checks for automatic failover
- Circuit breaker patterns for resilience

## 🛡️ Security Best Practices

1. **Network Segmentation**: Use Kubernetes NetworkPolicies
2. **Secret Management**: Never commit secrets to Git
3. **Regular Audits**: Review access logs and security events
4. **Least Privilege**: Restrict admin access to specific IPs
5. **TLS Everywhere**: Enforce HTTPS for all communications
6. **Regular Updates**: Keep middleware and certificates updated

## 📚 Additional Resources

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Kubernetes Ingress Documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

## 🤝 Contributing

When modifying the ingress configuration:

1. Test changes in development environment first
2. Run validation script before deploying
3. Update documentation for any new features
4. Follow security best practices
5. Monitor metrics after deployment

## 📞 Support

For issues with the ingress configuration:

1. Check the troubleshooting section
2. Run the validation script for diagnostics
3. Review Traefik and cert-manager logs
4. Consult the deployment guide for detailed instructions
