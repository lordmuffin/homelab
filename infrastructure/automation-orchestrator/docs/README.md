# Automation Orchestrator

> 🚀 **Infrastructure Discovery and Management System**  
> Automatically discover, catalog, and generate Ansible inventories for your infrastructure

## Overview

The Automation Orchestrator is a comprehensive system that implements the four core user stories:

1. **📋 Seed Inventory Ingestion** - Start discovery with a simple YAML file
2. **🔍 Automated Asset Discovery** - Scan networks and detect hardware automatically  
3. **💾 Centralized Source of Truth** - Store all data in version-controlled database
4. **⚡ Dynamic Ansible Inventory** - Generate inventories with intelligent grouping

## Features

### 🎯 Core Capabilities
- **Multi-method Discovery**: Network scanning, hardware detection, service discovery
- **GPU Detection**: Automatic NVIDIA/AMD GPU identification for AI workloads
- **Smart Classification**: Automatic host grouping (ai_nodes, compute_nodes, storage_nodes)
- **Version Control**: Git-based change tracking with automatic commits
- **Multiple Formats**: YAML, JSON, and INI inventory output
- **Rich CLI**: User-friendly command interface with progress indicators

### 🏗️ Architecture
- **Modular Design**: Pluggable discovery methods and classifiers
- **Async Operations**: Non-blocking network operations for performance
- **Extensible Rules**: Configurable classification and grouping rules
- **Error Resilience**: Graceful handling of network failures and timeouts
- **Comprehensive Logging**: Detailed operation tracking and debugging

## Quick Start

### 1. Installation

```bash
# Clone repository
cd /home/lordmuffin/Claude/Git/homelab/infrastructure/automation-orchestrator

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x cli/orchestrate.py
```

### 2. Create Seed Inventory

```bash
# Generate sample seed file
python cli/orchestrate.py create-seed my_infrastructure.yml

# Edit the file to match your infrastructure
vim my_infrastructure.yml
```

### 3. Run Discovery

```bash
# Validate seed file first
python cli/orchestrate.py validate my_infrastructure.yml

# Run full discovery pipeline
python cli/orchestrate.py discover my_infrastructure.yml
```

### 4. Use Generated Inventory

```bash
# View discovered assets
python cli/orchestrate.py list-assets

# Your Ansible inventory is ready!
ansible-playbook -i hosts.yml site.yml
```

## Configuration

### Main Configuration (`config/orchestrator.yml`)

```yaml
discovery:
  network_timeout: 30
  enable_gpu_detection: true
  default_ports: [22, 80, 443, 3389, 5900]

storage:
  enable_git_versioning: true
  backup_retention_days: 30

ansible:
  output_format: "yaml"
  group_by_hardware: true
```

### Discovery Rules (`config/discovery_rules.yml`)

Customize service detection, hardware patterns, and security assessment rules.

### Group Rules (`config/group_rules.yml`) 

Define custom Ansible grouping logic and variable assignments.

## CLI Commands

### Discovery Operations

```bash
# Full discovery pipeline
python cli/orchestrate.py discover seed_inventory.yml

# Validate seed file only
python cli/orchestrate.py validate seed_inventory.yml --show-suggestions

# Generate inventory from existing assets
python cli/orchestrate.py generate-inventory --format yaml
```

### Asset Management

```bash
# List all discovered assets
python cli/orchestrate.py list-assets --format table

# Filter assets by type or location
python cli/orchestrate.py list-assets --filter-type server --filter-location "Home Lab"

# Export assets to external format
python cli/orchestrate.py export assets_backup.json --format json
```

### System Information

```bash
# Show orchestrator status
python cli/orchestrate.py status

# Create sample seed file
python cli/orchestrate.py create-seed example_seed.yml
```

## Seed Inventory Format

### Basic Structure

```yaml
version: "1.0"
name: "My Infrastructure"

# Network ranges to scan
networks:
  - network: "192.168.1.0/24"
    name: "Main Network"
    scan_ports: [22, 80, 443]
    
# Pre-known hosts with metadata  
known_hosts:
  - ip: "192.168.1.10"
    hostname: "proxmox-host"
    type: "hypervisor"
    role: "compute"
    
# Discovery preferences
discovery_hints:
  enable_gpu_detection: true
  network_timeout: 30
```

### Advanced Features

- **Network Exclusions**: Skip IP ranges or specific hosts
- **Custom Credentials**: SSH keys and authentication methods
- **Priority Scanning**: Scan critical networks first
- **Service Hints**: Pre-define expected services

## Ansible Integration

### Generated Inventory Structure

```yaml
all:
  children:
    ai_nodes:
      hosts:
        gpu-server-1:
          ansible_host: 192.168.1.31
          has_gpu: true
          gpu_type: nvidia
      vars:
        cuda_enabled: true
        nvidia_docker_runtime: true
        
    k8s_masters:
      hosts:
        k3s-master:
          ansible_host: 192.168.1.30
      vars:
        k8s_role: master
```

### Automatic Groups

| Group Name | Description | Auto-assigned When |
|------------|-------------|-------------------|
| `ai_nodes` | GPU-enabled hosts | NVIDIA/AMD GPU detected |
| `compute_nodes` | High-performance compute | 16+ CPU cores or 32+ GB RAM |
| `storage_nodes` | Storage systems | NFS/SMB services detected |
| `k8s_masters` | Kubernetes masters | Port 6443 (API server) open |
| `k8s_workers` | Kubernetes workers | K8s services but not master |
| `hypervisor_nodes` | Virtualization hosts | Proxmox/ESXi detected |
| `monitoring_nodes` | Monitoring services | Prometheus/Grafana detected |
| `database_servers` | Database services | MySQL/PostgreSQL/MongoDB |
| `web_servers` | HTTP services | Apache/Nginx detected |

### Host Variables

Each host automatically gets relevant variables:

```yaml
gpu-server-1:
  ansible_host: 192.168.1.31
  has_gpu: true
  gpu_type: nvidia
  gpu_count: 2
  cpu_cores: 16
  memory_gb: 64
  services: ["ssh", "docker", "nvidia-smi"]
  location: "Home Lab"
  host_type: server
```

## Development & Customization

### Project Structure

```
automation-orchestrator/
├── src/
│   ├── core/           # Core orchestration logic
│   ├── seed/           # Seed inventory processing  
│   ├── discovery/      # Asset discovery engines
│   ├── storage/        # Centralized data storage
│   └── ansible/        # Inventory generation
├── config/             # Configuration files
├── templates/          # Seed and inventory templates
├── cli/                # Command-line interface
├── tests/              # Test suites
└── docs/               # Documentation
```

### Adding Custom Discovery Methods

1. Create new discovery class inheriting from base
2. Implement detection methods
3. Register in orchestrator configuration
4. Add classification rules

### Custom Grouping Rules

Add rules to `config/group_rules.yml`:

```yaml
custom_classification:
  media_servers:
    description: "Media streaming servers"
    conditions:
      hostname:
        pattern: "plex|jellyfin|emby"
      services:
        contains_any: ["http", "https"]
```

## Troubleshooting

### Common Issues

**Discovery finds no hosts:**
- Check network connectivity with `ping`
- Verify firewall allows scanning ports
- Try smaller network ranges first

**Missing GPU detection:**
- Ensure hosts have SSH access
- Check if nvidia-smi or rocm-smi are installed
- Enable hardware detection in config

**Inventory missing groups:**
- Review classification rules in `config/group_rules.yml`
- Check if services are properly detected
- Verify host metadata is complete

### Debug Mode

```bash
# Enable detailed logging
python cli/orchestrate.py --log-level DEBUG discover seed.yml

# Validate configuration
python cli/orchestrate.py status
```

### Log Files

Logs are written to console by default. Configure file logging:

```yaml
# config/orchestrator.yml
log_file: "/var/log/automation-orchestrator.log"
```

## Performance Tuning

### Large Networks

```yaml
discovery:
  max_parallel_scans: 100    # Increase for faster scanning
  network_timeout: 15        # Reduce for quicker timeouts
  port_scan_timeout: 5       # Faster port scanning
```

### Resource Usage

- **Memory**: ~100MB base + 1MB per discovered host
- **CPU**: Scales with parallel_scan_limit
- **Network**: Configurable scan intensity
- **Storage**: ~1KB per host in JSON format

## Security Considerations

### Network Scanning
- Uses TCP SYN scanning (requires privileges)
- Respects rate limits and timeouts
- No exploit attempts or vulnerability scanning

### Credentials
- SSH keys stored securely with proper permissions
- No passwords stored in plain text
- Credential references in seed files only

### Data Storage
- Local storage by default
- Git version control for change tracking
- Configurable backup retention

## Contributing

1. Follow existing code patterns and structure
2. Add tests for new functionality  
3. Update documentation for changes
4. Use type hints and docstrings
5. Test with multiple network environments

## License

This project is part of the homelab infrastructure automation suite.

## Support

- **Documentation**: See `docs/` directory for detailed guides
- **Configuration**: Review `config/` files for all options  
- **Examples**: Check `templates/` for sample configurations
- **Issues**: Use GitHub issues for bug reports and feature requests