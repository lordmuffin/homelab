# Claude Code Monitoring

This directory contains Kubernetes manifests for monitoring Claude Code usage through Prometheus and Grafana.

## Components

- **Deployment**: Simple metrics exporter (currently mock data)
- **Service**: Exposes metrics endpoint on port 9464
- **ServiceMonitor**: Configures Prometheus scraping
- **ConfigMap**: Grafana dashboard for visualizing Claude Code metrics

## Setup Real Monitoring

To connect to real Claude Code metrics, you need to:

### 1. Enable Claude Code Telemetry

```bash
# Set environment variables for Claude Code
export ANTHROPIC_TELEMETRY_ENABLED=true
export ANTHROPIC_TELEMETRY_EXPORTER=prometheus
export OTEL_EXPORTER_PROMETHEUS_PORT=9464

# Optional: Add custom attributes
export OTEL_RESOURCE_ATTRIBUTES="service.name=claude-code,team=homelab,user=$(whoami)"
```

### 2. Run Prometheus Exporter Locally

```bash
# Create a script to run locally and expose metrics
cat > claude-code-exporter.sh << 'EOF'
#!/bin/bash
export ANTHROPIC_TELEMETRY_ENABLED=true
export ANTHROPIC_TELEMETRY_EXPORTER=prometheus
export OTEL_EXPORTER_PROMETHEUS_PORT=9464

# Start prometheus metrics server
echo "Starting Claude Code metrics exporter on port 9464"
while true; do
  # This will be handled by Claude Code's built-in telemetry
  sleep 60
done
EOF

chmod +x claude-code-exporter.sh
```

### 3. Forward Metrics to Kubernetes

```bash
# Port forward to make local metrics available to Kubernetes
kubectl port-forward -n monitoring service/claude-code-exporter 9464:9464 &

# Or use a DaemonSet to collect from each node
```

## Accessing the Dashboard

Once deployed via ArgoCD, the Claude Code dashboard will be available in Grafana at:
- URL: `https://grafana.lab.apj.dev`
- Dashboard: "Claude Code Usage Analytics"

## Metrics Available

- `claude_code_session_count_total`: Total number of sessions
- `claude_code_token_usage_total`: Token usage by type (input/output/cache)
- `claude_code_cost_usage_total`: Total cost in USD
- `claude_code_lines_of_code_count_total`: Lines of code modified
- `claude_code_commit_count_total`: Git commits created
- `claude_code_pull_request_count_total`: Pull requests created
- `claude_code_tool_decision_total`: Tool usage decisions

## Development

The current deployment uses mock data for demonstration. To use real data:

1. Replace the deployment with a proper metrics exporter
2. Configure Claude Code telemetry on your development machines
3. Set up metric collection and forwarding to Kubernetes