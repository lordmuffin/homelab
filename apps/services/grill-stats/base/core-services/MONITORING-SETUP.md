# Grill Stats Monitoring Setup

This document describes the comprehensive monitoring setup for the Grill Stats platform, including Prometheus metrics collection, Grafana dashboards, AlertManager notifications, and SLO monitoring.

## Overview

The monitoring setup provides:
- **Service Monitoring**: Health checks and performance metrics for all microservices
- **Business Metrics**: Temperature data, user activity, and cooking sessions
- **Database Monitoring**: PostgreSQL, InfluxDB, and Redis metrics
- **SLO/SLI Tracking**: Service level objectives and error budget monitoring
- **Alerting**: Multi-channel notifications for critical and warning conditions
- **Dashboards**: Comprehensive visualization of all metrics

## Architecture

### Components

1. **Prometheus**: Metrics collection and storage
2. **Grafana**: Visualization and dashboards
3. **AlertManager**: Alert routing and notifications
4. **Sloth**: SLO/SLI monitoring and error budget tracking
5. **Custom Metrics Exporters**: Business-specific metrics

### Service Monitors

The following ServiceMonitors are configured:

- `grill-stats-auth-service`: Authentication service metrics
- `grill-stats-device-service`: Device management metrics
- `grill-stats-temperature-service`: Temperature data metrics (15s interval)
- `grill-stats-historical-service`: Historical data analytics metrics
- `grill-stats-encryption-service`: Encryption and key management metrics
- `grill-stats-web-ui`: Web UI and static asset metrics

### Key Metrics

#### Business Metrics
- `grill_stats_temperature_celsius`: Current temperature readings
- `grill_stats_device_online_status`: Device connectivity status
- `grill_stats_user_login_total`: User authentication metrics
- `grill_stats_cook_duration_seconds`: Cooking session duration
- `grill_stats_temperature_alerts_total`: Temperature alert counts

#### Performance Metrics
- `http_requests_total`: HTTP request counts by service
- `http_request_duration_seconds`: Request latency histograms
- `container_memory_usage_bytes`: Memory utilization
- `container_cpu_usage_seconds_total`: CPU utilization

#### Database Metrics
- `pg_up`: PostgreSQL availability
- `redis_memory_used_bytes`: Redis memory usage
- `influxdb_system_memory_usage_percent`: InfluxDB system resources

## Dashboards

### Platform Overview Dashboard
- **File**: `grill-stats-overview.json`
- **UID**: `grill-stats-overview`
- **Features**:
  - Service health status
  - Active device count
  - Request rates and error rates
  - Current temperature readings
  - Response time P95
  - Memory usage by service
  - SLO compliance indicators

### Business Metrics Dashboard
- **File**: `grill-stats-business.json`
- **UID**: `grill-stats-business`
- **Features**:
  - Active users (24h)
  - Temperature readings count
  - Average cook time
  - Device battery levels
  - Cook session duration distribution
  - Temperature alerts summary

### SLO/SLI Dashboard
- **File**: `grill-stats-slo.json`
- **UID**: `grill-stats-slo`
- **Features**:
  - Availability SLO (99.9%)
  - Data freshness SLO (99.5%)
  - Response time SLO (P95 < 500ms)
  - Error budget burn rate
  - Service level indicators table

### Application-Specific Dashboards
- **Authentication Service**: Login metrics, session tracking
- **Device Service**: Device management, ThermoWorks API calls
- **Temperature Service**: Real-time data processing, cache performance
- **Historical Service**: Query performance, data retention
- **Encryption Service**: Key rotation, vault health
- **Web UI**: Page load times, WebSocket connections

## Alerting

### Alert Categories

1. **Critical Alerts** (Immediate response required)
   - Service down
   - High temperature alerts
   - Database failures
   - SLO violations

2. **Warning Alerts** (Investigation required)
   - High resource usage
   - Performance degradation
   - Authentication failures
   - Device connectivity issues

3. **Business Alerts** (Operational awareness)
   - Temperature data missing
   - Device battery low
   - Unusual temperature spikes

### Alert Routing

Alerts are routed based on:
- **Severity**: Critical, Warning, Info
- **Category**: Business, SLO, Database, Security
- **Service**: Specific microservice alerts

### Notification Channels

1. **Email**: Different recipients based on alert type
2. **Slack**: Critical alerts to `#grill-stats-alerts`
3. **Webhook**: Integration with external notification services
4. **PagerDuty**: Critical alerts with escalation

## SLO Monitoring

### Service Level Objectives

1. **Request Availability**: 99.9% uptime
2. **Response Time**: P95 < 500ms
3. **Temperature Data Freshness**: 99.5% within 60 seconds
4. **Device Connectivity**: 99% devices online
5. **Authentication Success**: 99.5% success rate

### Error Budget Tracking

- **Fast Burn**: 2% error budget in 1 hour → Critical alert
- **Slow Burn**: 10% error budget in 6 hours → Warning alert
- **Exhaustion**: Monthly budget near depletion → Warning alert

### SLI Definitions

- **Availability SLI**: Ratio of successful requests to total requests
- **Latency SLI**: Ratio of requests completing within SLO target
- **Data Freshness SLI**: Ratio of fresh data points to total expected
- **Connectivity SLI**: Ratio of online devices to total devices

## Custom Metrics

### Business Metrics Exporter

A custom metrics exporter collects business-specific metrics:

- Temperature and device data
- User activity and session metrics
- Cooking session analytics
- API performance metrics
- Data processing efficiency

### Recording Rules

Pre-computed metrics for dashboards:

- `grill_stats:active_users_24h`: Daily active users
- `grill_stats:temperature_data_freshness_ratio`: Data freshness percentage
- `grill_stats:api_success_rate_5m`: API success rate
- `grill_stats:average_cook_time_hours`: Average cooking duration

## Deployment

### Prerequisites

- Prometheus Operator installed
- Grafana instance available
- AlertManager configured
- Sloth operator for SLO monitoring

### Installation

1. **Deploy ServiceMonitors**:
   ```bash
   kubectl apply -f monitoring.yaml
   ```

2. **Deploy Dashboards**:
   ```bash
   kubectl apply -f additional-dashboards.yaml
   kubectl apply -f application-dashboards.yaml
   ```

3. **Configure AlertManager**:
   ```bash
   kubectl apply -f alertmanager-config.yaml
   ```

4. **Deploy SLO Monitoring**:
   ```bash
   kubectl apply -f slo-monitoring.yaml
   ```

5. **Deploy Custom Metrics**:
   ```bash
   kubectl apply -f custom-metrics.yaml
   ```

### Validation

1. **Check ServiceMonitor Discovery**:
   ```bash
   kubectl get servicemonitors -n grill-stats
   ```

2. **Verify Prometheus Targets**:
   ```bash
   kubectl port-forward svc/prometheus 9090:9090
   # Visit http://localhost:9090/targets
   ```

3. **Check Grafana Dashboards**:
   ```bash
   kubectl port-forward svc/grafana 3000:3000
   # Visit http://localhost:3000
   ```

4. **Test AlertManager**:
   ```bash
   kubectl port-forward svc/alertmanager 9093:9093
   # Visit http://localhost:9093
   ```

## Troubleshooting

### Common Issues

1. **ServiceMonitor Not Discovered**:
   - Check label selectors match service labels
   - Verify namespace selector configuration
   - Ensure Prometheus has RBAC permissions

2. **Missing Metrics**:
   - Verify service `/metrics` endpoint
   - Check metric relabeling configuration
   - Confirm scrape interval settings

3. **Dashboard Loading Issues**:
   - Validate JSON syntax in ConfigMaps
   - Check Grafana data source configuration
   - Verify metric queries are correct

4. **Alert Not Firing**:
   - Test PromQL expressions in Prometheus
   - Check alert rule syntax
   - Verify AlertManager routing configuration

### Monitoring Health

Monitor the monitoring stack itself:

1. **Prometheus Health**:
   ```promql
   up{job="prometheus"}
   ```

2. **Grafana Health**:
   ```promql
   up{job="grafana"}
   ```

3. **AlertManager Health**:
   ```promql
   up{job="alertmanager"}
   ```

## Maintenance

### Regular Tasks

1. **Review SLO Compliance**: Weekly review of SLO adherence
2. **Update Dashboards**: Monthly dashboard improvements
3. **Alert Tuning**: Quarterly alert threshold reviews
4. **Capacity Planning**: Monitor resource usage trends

### Backup and Recovery

1. **Prometheus Data**: Configure persistent storage
2. **Grafana Dashboards**: Export configurations regularly
3. **AlertManager Config**: Version control configuration

## Integration Points

### Home Assistant
- Temperature sensor creation
- Device state synchronization
- Alert forwarding to Home Assistant

### External Services
- ThermoWorks API monitoring
- SMTP server for email alerts
- Slack webhook integration

### Security
- Network policies for monitoring traffic
- RBAC for monitoring components
- Secret management for credentials

## Performance Considerations

### Resource Requirements

- **Prometheus**: 2 CPU, 4GB RAM, 100GB storage
- **Grafana**: 1 CPU, 2GB RAM
- **AlertManager**: 0.5 CPU, 1GB RAM
- **Custom Exporters**: 0.2 CPU, 256MB RAM

### Optimization

1. **Metric Retention**: Configure appropriate retention periods
2. **Scrape Intervals**: Balance frequency with resource usage
3. **Recording Rules**: Pre-compute expensive queries
4. **Dashboard Optimization**: Limit query complexity

## Future Enhancements

1. **Distributed Tracing**: Integrate with Jaeger or Tempo
2. **Log Aggregation**: Centralized logging with Loki
3. **Anomaly Detection**: Machine learning-based alerting
4. **Mobile Alerts**: Push notifications for critical issues
5. **Capacity Forecasting**: Predictive scaling alerts

## Contact Information

- **Team**: Platform/SRE Team
- **On-Call**: operations@homelab.local
- **Documentation**: https://homelab.local/docs/monitoring
- **Runbooks**: https://homelab.local/runbooks/grill-stats/
