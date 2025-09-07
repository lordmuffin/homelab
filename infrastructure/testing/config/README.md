# K3s Testing Framework Configuration System

This directory contains the configuration system for the K3s Testing Framework v1.1.0. The configuration system supports profile-based testing configurations with inheritance and environment variable substitution.

## Configuration Profiles

### Available Profiles

| Profile | Description | Use Case |
|---------|-------------|-----------|
| `default.yaml` | Standard testing configuration | General validation and CI/CD |
| `quick.yaml` | Fast testing with minimal overhead | Development and quick validation |
| `performance.yaml` | Performance-focused testing | Benchmarking and performance validation |
| `comprehensive.yaml` | Complete testing suite | Production validation and thorough testing |

### Profile Inheritance

Profiles can extend other profiles using the `extends` field:

```yaml
profile_name: "my-custom-profile"
extends: "default"  # Inherit from default profile

# Override specific settings
execution:
  default_iterations: 5
  max_parallel_tests: 4
```

## Configuration Structure

### Top-Level Sections

- **execution**: Test execution parameters
- **storage_tests**: Storage validation configuration
- **network_tests**: Network validation configuration
- **validation**: Success thresholds and criteria
- **resource_management**: Resource cleanup policies
- **reporting**: Report generation settings
- **logging**: Logging configuration
- **features**: Feature flags

### Execution Configuration

```yaml
execution:
  max_parallel_tests: 2      # Number of parallel test threads
  default_iterations: 3      # Default number of test iterations
  timeout_multiplier: 1.0    # Global timeout multiplier
  test_focus: ["storage", "network"]  # Tests to run
  test_mode: "full"          # full, k3s_only, apps_only
```

### Storage Test Configuration

```yaml
storage_tests:
  enabled: true
  timeout_seconds: 300
  
  scenarios:
    - name: "basic_pvc"
      description: "Basic PVC creation test"
      storage_class: "default"
      size: "1Gi"
      access_mode: "ReadWriteOnce"
  
  storage_classes:
    - name: "local-path"
      size: "1Gi"
```

### Network Test Configuration

```yaml
network_tests:
  enabled: true
  timeout_seconds: 300
  
  dns:
    external_servers: ["8.8.8.8", "1.1.1.1"]
    internal_services: ["kubernetes.default.svc.cluster.local"]
  
  connectivity:
    pod_to_pod: true
    external_connectivity: true
    external_hosts: ["google.com", "github.com"]
  
  performance:
    enabled: true
    bandwidth_test: "100M"
    duration: "30s"
```

## Environment Variable Substitution

Configuration values can reference environment variables:

```yaml
# Simple substitution
output_directory: "${TEST_OUTPUT_DIR}"

# With default value
storage_class: "${STORAGE_CLASS:default}"

# In nested structures
database:
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
```

## Validation Thresholds

Configure success criteria and performance thresholds:

```yaml
validation:
  success_rate:
    minimum: 80.0      # Minimum acceptable success rate
    target: 95.0       # Target success rate
    excellent: 99.0    # Excellence threshold
  
  performance:
    storage:
      min_read_iops: 100
      min_write_iops: 80
      max_pvc_creation_time: 30
    network:
      max_dns_resolution_time: 2.0
      max_pod_to_pod_latency: 5.0
```

## Resource Management

Control resource cleanup behavior:

```yaml
resource_management:
  auto_cleanup_success: true     # Auto-cleanup successful test resources
  ask_cleanup_failed: true       # Ask before cleaning failed resources
  max_resource_age_hours: 24     # Maximum resource age before cleanup
  cleanup_batch_size: 5          # Resources to cleanup per batch
```

## Usage Examples

### Using the Configuration Loader

```python
from testing.config.loader import load_test_configuration

# Load default configuration
config = load_test_configuration("default")

# Load performance configuration
config = load_test_configuration("performance")

# Load with custom directory
config = load_test_configuration("custom", config_dir=Path("/custom/path"))
```

### CLI Usage

```bash
# List available profiles
python3 testing/config/loader.py list

# Get profile information
python3 testing/config/loader.py info --profile performance

# Validate a configuration
python3 testing/config/loader.py validate --profile comprehensive

# Load and display configuration
python3 testing/config/loader.py load --profile quick
```

### Integration with k3s-deploy.py

```bash
# Use default configuration
python3 k3s-deploy-v1.1.0.py --test --config default

# Use performance configuration  
python3 k3s-deploy-v1.1.0.py --test --config performance --iterations 5

# Use quick configuration for development
python3 k3s-deploy-v1.1.0.py --test --config quick --parallel 3
```

## Creating Custom Profiles

### Step 1: Create Configuration File

Create a new YAML file in the `config` directory:

```bash
touch testing/config/my-profile.yaml
```

### Step 2: Define Profile Content

```yaml
---
profile_name: "my-profile"
profile_version: "1.0"  
description: "My custom testing profile"
extends: "default"  # Optional: extend existing profile

# Override specific settings
execution:
  default_iterations: 5
  max_parallel_tests: 4

storage_tests:
  timeout_seconds: 600
  scenarios:
    - name: "custom_scenario"
      description: "My custom test scenario"
      storage_class: "fast-ssd"
      size: "10Gi"
```

### Step 3: Validate Configuration

```bash
python3 testing/config/loader.py validate --profile my-profile
```

### Step 4: Use Custom Profile

```bash
python3 k3s-deploy-v1.1.0.py --test --config my-profile
```

## Best Practices

### Profile Design

1. **Start with Inheritance**: Use `extends` to build on existing profiles
2. **Clear Naming**: Use descriptive profile and scenario names
3. **Documentation**: Include detailed descriptions for scenarios
4. **Environment Specific**: Create profiles for different environments

### Configuration Management

1. **Version Control**: Keep configurations in version control
2. **Validation**: Always validate configurations before use  
3. **Testing**: Test custom profiles thoroughly
4. **Documentation**: Document custom profiles and their use cases

### Performance Considerations

1. **Timeout Settings**: Adjust timeouts based on environment
2. **Parallelism**: Balance parallel tests with resource availability
3. **Iteration Counts**: More iterations = better statistics but longer runtime
4. **Resource Cleanup**: Configure appropriate cleanup policies

## Troubleshooting

### Common Issues

1. **YAML Syntax Errors**: Validate YAML syntax using online validators
2. **Missing Dependencies**: Ensure PyYAML is installed (`pip install PyYAML`)
3. **Profile Not Found**: Check file exists and has .yaml extension
4. **Inheritance Loops**: Avoid circular extends relationships
5. **Environment Variables**: Ensure referenced env vars exist

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
python3 testing/config/loader.py --verbose validate --profile my-profile
```

### Configuration Validation

The loader validates:
- Required fields presence
- Data type correctness  
- Value range appropriateness
- Profile inheritance chains
- Environment variable syntax

## Migration Guide

### From v1.0 to v1.1

1. **New Fields**: Add `features` section to existing profiles
2. **Resource Management**: Update `resource_management` with new fields
3. **Validation**: Add `performance` thresholds to `validation` section
4. **Inheritance**: Consider using `extends` to reduce duplication

### Configuration Updates

When updating profiles, consider:
- Backward compatibility with existing tests
- Impact on CI/CD pipelines
- Documentation updates
- Team communication about changes