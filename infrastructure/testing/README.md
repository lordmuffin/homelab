# K3s Testing Framework v1.1.0

A comprehensive automated testing framework for K3s cluster deployments with advanced validation, reporting, and orchestration capabilities.

## 🚀 Features

### Core Capabilities
- **🔧 Complete Deployment Testing**: Full infrastructure → K3s → Applications testing pipeline
- **⚡ Parallel Execution**: Multi-threaded test execution with configurable parallelism
- **📊 Comprehensive Validation**: Storage and network validation with performance metrics
- **🎯 Smart Resource Management**: Priority-based cleanup with automated resource tracking
- **📈 Advanced Reporting**: Interactive HTML dashboards and detailed JSON reports
- **⚙️ Flexible Configuration**: Profile-based configuration system with inheritance
- **🔄 Iterative Testing**: Support for repeated test campaigns (3, 5, 100+ iterations)

### Testing Components
- **Storage Validation**: PVC creation, I/O performance, data persistence testing
- **Network Validation**: DNS resolution, pod connectivity, ingress testing, service discovery
- **Performance Monitoring**: Real-time metrics collection and trend analysis
- **Resource Tracking**: Automated resource registration and intelligent cleanup
- **Failure Analysis**: Detailed error tracking and pattern recognition

## 📁 Directory Structure

```
infrastructure/testing/
├── README.md                      # This file - framework overview
├── apps/                          # Test applications
│   ├── storage-test/              # Storage validation application
│   │   └── chart/                 # Helm chart for storage testing
│   │       ├── Chart.yaml
│   │       ├── values.yaml
│   │       └── templates/         # Kubernetes manifests
│   └── network-test/              # Network validation application
│       └── chart/                 # Helm chart for network testing
│           ├── Chart.yaml
│           ├── values.yaml
│           └── templates/         # Kubernetes manifests
├── config/                        # Configuration profiles
│   ├── README.md                  # Configuration system guide
│   ├── loader.py                  # Configuration loader utility
│   ├── default.yaml               # Default testing configuration
│   ├── quick.yaml                 # Fast testing profile
│   ├── performance.yaml           # Performance testing profile
│   └── comprehensive.yaml         # Complete testing profile
└── docs/                          # Documentation
    ├── user-guide.md              # User guide and tutorials
    ├── api-reference.md           # API documentation
    └── troubleshooting.md         # Troubleshooting guide
```

## 🚦 Quick Start

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install pyyaml  # For configuration loading
   ```

2. **Required Tools**:
   - `kubectl` - Kubernetes CLI
   - `helm` - Helm package manager
   - `terraform` - Infrastructure provisioning
   - `ansible` - Configuration management

3. **Environment Setup**:
   ```bash
   # Ensure kubectl is configured for your cluster
   kubectl cluster-info
   
   # Verify Helm is installed and working
   helm version
   ```

### Basic Usage

1. **Run Default Test Campaign**:
   ```bash
   python3 k3s-deploy-v1.1.0.py test --environment dev --iterations 3
   ```

2. **Quick Development Testing**:
   ```bash
   python3 k3s-deploy-v1.1.0.py test --environment dev --test-focus storage,network --iterations 2
   ```

3. **Performance Benchmarking**:
   ```bash
   python3 k3s-deploy-v1.1.0.py test --environment dev --test-focus storage,network --iterations 5 --parallel-tests 2
   ```

4. **Comprehensive Validation**:
   ```bash
   python3 k3s-deploy-v1.1.0.py test --environment dev --test-focus storage,network --iterations 10
   ```

## ⚙️ Configuration Profiles

### Available Profiles

| Profile | Iterations | Parallel | Timeouts | Use Case |
|---------|------------|----------|----------|----------|
| `default` | 3 | 2 | 1.0x | Standard CI/CD validation |
| `quick` | 2 | 3 | 0.7x | Development and debugging |
| `performance` | 5 | 4 | 1.5x | Performance benchmarking |
| `comprehensive` | 10 | 1 | 2.0x | Production validation |

### Configuration Examples

**Custom Configuration**:
```yaml
# my-config.yaml
profile_name: "my-config"
extends: "default"

execution:
  default_iterations: 7
  max_parallel_tests: 3
  test_focus: ["storage", "network"]

storage_tests:
  scenarios:
    - name: "high_performance"
      storage_class: "fast-ssd"
      size: "5Gi"
      
validation:
  success_rate:
    minimum: 90.0
    target: 98.0
```

**Environment Variable Support**:
```yaml
storage_tests:
  scenarios:
    - name: "dynamic_test"
      storage_class: "${STORAGE_CLASS:default}"
      size: "${TEST_SIZE:1Gi}"
```

## 🧪 Test Applications

### Storage Test Application

**Features**:
- PVC creation and binding validation
- I/O performance benchmarking (read/write IOPS, bandwidth)
- Data persistence testing across pod restarts
- Multiple storage class support
- Configurable test scenarios

**Deployment**:
```bash
helm install storage-test ./testing/apps/storage-test/chart \
  --namespace k3s-storage-test --create-namespace \
  --set storage.size=5Gi \
  --set test.iterations=5
```

### Network Test Application

**Features**:
- DNS resolution testing (internal and external)
- Pod-to-pod connectivity validation
- Service discovery testing
- Ingress controller validation
- Network performance benchmarking

**Deployment**:
```bash
helm install network-test ./testing/apps/network-test/chart \
  --namespace k3s-network-test --create-namespace \
  --set network.ingress.enabled=true \
  --set server.enabled=true
```

## 📊 Reporting and Analytics

### Report Formats

1. **Interactive HTML Dashboard**:
   - Real-time performance charts
   - Success rate trends
   - Detailed iteration breakdown
   - Storage and network metrics
   - Failure analysis

2. **Detailed JSON Reports**:
   - Complete test data
   - Performance metrics
   - Error details
   - Trend analysis
   - Machine-readable format

### Sample Report Structure

```json
{
  "metadata": {
    "report_version": "1.1.0",
    "generated_at": "2025-01-15T10:30:00Z",
    "run_id": "test-run-20250115-103000"
  },
  "summary": {
    "overall_success_rate": 98.5,
    "completed_iterations": 5,
    "average_iteration_time": 145.2
  },
  "performance_metrics": {
    "storage": {
      "averages": {
        "read_iops": 850,
        "write_iops": 620,
        "pvc_creation_time": 5.2
      }
    },
    "network": {
      "averages": {
        "dns_resolution_time": 0.8,
        "pod_to_pod_latency": 2.1,
        "ingress_response_time": 120
      }
    }
  }
}
```

## 🔧 Advanced Usage

### Custom Test Scenarios

**Adding Storage Scenarios**:
```yaml
storage_tests:
  scenarios:
    - name: "custom_performance"
      description: "Custom high-performance storage test"
      storage_class: "nvme-ssd"
      size: "20Gi"
      test_duration: "300s"
      io_patterns: ["sequential", "random"]
      block_sizes: ["4k", "64k", "1M"]
```

**Adding Network Tests**:
```yaml
network_tests:
  connectivity:
    external_hosts:
      - "custom-api.example.com"
      - "internal-service.local"
  performance:
    bandwidth_test: "2G"
    latency_threshold_ms: 10
```

### Parallel Execution Strategies

1. **Test-Level Parallelism**:
   ```bash
   # Run storage and network tests in parallel
   python3 k3s-deploy-v1.1.0.py test --environment dev --parallel-tests 2
   ```

2. **Iteration-Level Parallelism**:
   ```bash
   # Run multiple iterations concurrently
   python3 k3s-deploy-v1.1.0.py test --environment dev --parallel-tests 3
   ```

### Resource Management

**Automatic Cleanup**:
```yaml
resource_management:
  auto_cleanup_success: true      # Clean successful test resources
  ask_cleanup_failed: true        # Prompt for failed resource cleanup
  max_resource_age_hours: 24      # Maximum resource age
  cleanup_batch_size: 5           # Resources per cleanup batch
```

**Priority-Based Cleanup**:
```yaml
priorities:
  critical: ["vm", "k3s_cluster"]
  high: ["helm_release", "namespace"]  
  normal: ["configmap", "secret"]
  low: ["test_data"]
```

## 📋 Testing Modes

### Full Stack Testing
```bash
# Complete infrastructure deployment + K3s + Applications
python3 k3s-deploy-v1.1.0.py test --environment dev --mode full --iterations 3
```

### K3s Only Testing
```bash
# Redeploy K3s on existing infrastructure + Applications  
python3 k3s-deploy-v1.1.0.py test --environment dev --mode k3s_only --iterations 5
```

### Applications Only Testing
```bash
# Redeploy test applications on existing K3s cluster
python3 k3s-deploy-v1.1.0.py test --environment dev --mode apps_only --iterations 10
```

## 🎯 Performance Thresholds

### Default Thresholds

**Storage Performance**:
- Minimum Read IOPS: 100
- Minimum Write IOPS: 80
- Maximum PVC Creation Time: 30 seconds

**Network Performance**:
- Maximum DNS Resolution Time: 2.0 seconds
- Maximum Pod-to-Pod Latency: 5.0 seconds
- Maximum Ingress Response Time: 200 milliseconds

**Success Rates**:
- Minimum: 80%
- Target: 95%
- Excellent: 99%

### Custom Thresholds

```yaml
validation:
  performance:
    storage:
      min_read_iops: 500
      min_write_iops: 400
      max_pvc_creation_time: 15
    network:
      max_dns_resolution_time: 1.0
      max_pod_to_pod_latency: 2.0
  success_rate:
    minimum: 95.0
    target: 99.0
    excellent: 99.9
```

## 🐛 Troubleshooting

### Common Issues

1. **Configuration Errors**:
   ```bash
   # Validate configuration
   python3 testing/config/loader.py validate --profile my-config
   ```

2. **Test Application Failures**:
   ```bash
   # Check application logs
   kubectl logs -n k3s-storage-test -l app.kubernetes.io/name=k3s-storage-test
   kubectl logs -n k3s-network-test -l app.kubernetes.io/name=k3s-network-test
   ```

3. **Resource Cleanup Issues**:
   ```bash
   # Manual cleanup
   helm uninstall storage-test --namespace k3s-storage-test
   helm uninstall network-test --namespace k3s-network-test
   kubectl delete namespace k3s-storage-test k3s-network-test
   ```

### Debug Mode

```bash
# Enable debug logging
python3 k3s-deploy-v1.1.0.py test --environment dev --debug --iterations 1
```

### Log Analysis

```bash
# Check test execution logs
tail -f test-execution.log

# Analyze performance metrics
jq '.performance_metrics' test-report-*.json
```

## 🔄 Integration

### CI/CD Pipeline Integration

**GitHub Actions Example**:
```yaml
name: K3s Testing
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run K3s Tests
        run: |
          python3 k3s-deploy-v1.1.0.py test --environment dev --test-focus storage,network --iterations 2
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test-reports/
```

**GitLab CI Example**:
```yaml
k3s-test:
  stage: test
  script:
    - python3 k3s-deploy-v1.1.0.py test --environment dev --test-focus storage,network --iterations 3
  artifacts:
    reports:
      junit: test-reports/*.xml
    paths:
      - test-reports/
  when: always
```

### Monitoring Integration

**Prometheus Metrics**:
```yaml
# Add to monitoring configuration
monitoring:
  enabled: true
  metrics_endpoint: "http://prometheus:9090"
  custom_metrics:
    - storage_iops_total
    - network_latency_seconds
    - test_success_rate
```

## 🚀 Advanced Features

### Trend Analysis
- Historical performance tracking
- Regression detection
- Performance baseline comparison
- Automated alerting on degradation

### Failure Pattern Analysis
- Error categorization and trending
- Root cause analysis assistance
- Automatic retry strategies
- Smart cleanup based on failure types

### Custom Validators
```python
# Add custom validation logic
class CustomValidator(TestValidator):
    def validate(self, context):
        # Custom validation implementation
        pass
```

## 🤝 Contributing

1. **Adding Test Scenarios**: Extend configuration profiles
2. **Creating Validators**: Implement custom validation logic
3. **Improving Reports**: Enhance HTML templates and JSON structure
4. **Documentation**: Update guides and examples

## 📚 Additional Resources

- [Configuration System Guide](config/README.md)
- [User Guide](docs/user-guide.md)
- [API Reference](docs/api-reference.md)  
- [Troubleshooting Guide](docs/troubleshooting.md)

## 📄 License

This testing framework is part of the K3s deployment project and follows the same licensing terms.

---

**K3s Testing Framework v1.1.0** - Comprehensive automated testing for reliable K3s deployments 🚀