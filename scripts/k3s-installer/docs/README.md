# K3s Intelligent Installer

A comprehensive, intelligent installer for single-node K3s environments with production-ready features including GPU support, distributed storage, load balancing, TLS certificate management, and automated backup systems.

## Features

### 🚀 Core K3s Installation
- **Automated K3s Setup**: Latest stable K3s installation with customizable configuration
- **System Optimization**: Kernel module loading, sysctl tuning, firewall configuration
- **Prerequisites Check**: Automated validation of system requirements and dependencies

### 🎮 GPU Support
- **Multi-Vendor Support**: NVIDIA, AMD, and Intel GPU detection and configuration
- **Driver Installation**: Automatic driver installation for NVIDIA and AMD GPUs
- **Container Runtime**: GPU-aware container runtime configuration
- **Device Plugins**: Kubernetes device plugin deployment for GPU resource management
- **Monitoring**: GPU metrics collection and monitoring setup

### 💾 Storage Solutions
- **OpenEBS**: Cloud-native storage with multiple engine options
- **Local Path**: K3s default local storage provisioner
- **Backup Integration**: S3-compatible backup destinations for persistent data

### 🌐 Networking
- **MetalLB**: Layer 2 load balancer for bare metal environments
- **Wireguard VPN**: Secure cross-cluster networking capabilities
- **Ingress**: Traefik ingress controller configuration
- **Network Policies**: Optional network segmentation and security

### 🔐 TLS Certificate Management
- **cert-manager**: Automated certificate management for Kubernetes
- **Let's Encrypt**: Automatic SSL certificate provisioning and renewal
- **DNS/HTTP Challenges**: Flexible certificate validation methods
- **Self-Signed Certificates**: Development-friendly certificate generation

### 💾 Backup and Restore
- **Automated Backups**: Scheduled cluster state and application data backups
- **Multiple Destinations**: Local, S3, and remote backup storage options
- **Encryption**: Backup encryption for sensitive data protection
- **Retention Policies**: Configurable backup retention and cleanup

## Installation

### Prerequisites

- **Operating System**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, or compatible
- **Architecture**: x86_64, ARM64
- **Resources**: Minimum 2 CPU cores, 4GB RAM, 20GB disk space
- **Root Access**: Installation requires root/sudo privileges
- **Network**: Internet connectivity for downloading components

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd homelab/scripts/k3s-installer
   ```

2. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure the installer**:
   ```bash
   cp config/config.yaml.template config/config.yaml
   # Edit config/config.yaml with your settings
   ```

4. **Run the installer**:
   ```bash
   sudo python3 k3s_installer.py --config config/config.yaml
   ```

### Configuration

The installer uses a comprehensive YAML configuration file. Key sections include:

#### K3s Configuration
```yaml
k3s:
  version: "v1.31.1+k3s1"
  server:
    cluster_init: true
    disable:
      - traefik      # Use MetalLB instead
      - servicelb    # Use custom ingress
```

#### GPU Support
```yaml
gpu:
  enabled: true
  auto_detect: true
  nvidia:
    install_driver: true
    driver_version: "latest"
  amd:
    install_driver: true
```

#### Storage Configuration
```yaml
storage:
  provider: "local-path"  # or "openebs"
  # Local path storage is used by default
```

#### Networking Setup
```yaml
networking:
  metallb:
    enabled: true
    address_pools:
      - name: "default"
        addresses:
          - "192.168.1.240-192.168.1.250"
  wireguard:
    enabled: true
    listen_port: 51820
```

## Usage Examples

### Basic Installation
```bash
# Minimal installation with default settings
sudo python3 k3s_installer.py --config config/config.yaml
```

### GPU-Only Configuration
```bash
# Configure only GPU support on existing cluster
sudo python3 k3s_installer.py --config config/config.yaml --gpu-only
```

### Backup Operations
```bash
# Create manual backup
sudo python3 k3s_installer.py --config config/config.yaml --backup-only

# Restore from backup (placeholder)
sudo python3 k3s_installer.py --config config/config.yaml --restore backup-20241208_143000
```

### Validation
```bash
# Validate existing installation
sudo python3 k3s_installer.py --config config/config.yaml --validate-only
```

## Architecture

The installer follows a modular architecture with separate components for each major functionality:

```
k3s-installer/
├── k3s_installer.py          # Main orchestrator script
├── modules/                  # Modular components
│   ├── __init__.py
│   ├── system_utils.py       # System detection and optimization
│   ├── gpu_config.py         # GPU detection and configuration
│   ├── storage_setup.py      # Storage provider setup
│   ├── networking.py         # Network configuration
│   ├── tls_certs.py         # Certificate management
│   └── backup_restore.py     # Backup and restore operations
├── config/
│   └── config.yaml.template  # Configuration template
├── tests/
│   └── test_installer.py     # Comprehensive test suite
└── docs/
    └── README.md             # This file
```

### Module Responsibilities

- **SystemUtils**: Hardware detection, OS compatibility, system optimization
- **GPUConfigurator**: Multi-vendor GPU support, driver installation, device plugins
- **StorageSetup**: Storage provider deployment, configuration, validation
- **NetworkingSetup**: Load balancer, VPN, ingress controller setup
- **TLSManager**: Certificate authority, automated certificate management
- **BackupManager**: Backup scheduling, multiple destinations, retention policies

## Testing

The project includes a comprehensive test suite covering:

- Unit tests for individual modules
- Integration tests for component interaction
- Mock testing for external dependencies
- Performance tests for large configurations

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_installer.py::TestSystemUtils -v

# Run with coverage
python -m pytest tests/ --cov=modules --cov-report=html
```

## Troubleshooting

### Common Issues

**Installation fails with "Permission denied"**
- Ensure you're running with sudo/root privileges
- Check file permissions on the installer directory

**GPU detection fails**
- Verify GPU drivers are properly installed
- Check if nvidia-smi (NVIDIA) or rocm-smi (AMD) commands work
- Review GPU vendor-specific logs in `/var/log/`

**Storage setup fails**
- Ensure sufficient disk space for storage provider
- Check if required kernel modules are loaded
- Verify network connectivity for downloading components

**MetalLB address allocation fails**
- Verify IP address ranges don't conflict with existing network
- Ensure the specified network interface is available
- Check firewall rules for required ports

**Certificate generation fails**
- Verify DNS configuration for domain validation
- Check internet connectivity for Let's Encrypt
- Review cert-manager logs: `kubectl logs -n cert-manager deployment/cert-manager`

### Log Files

- **Main installer**: `/var/log/k3s-installer.log`
- **K3s service**: `journalctl -u k3s`
- **GPU drivers**: `/var/log/nvidia-installer.log` (NVIDIA)
- **Backup operations**: `/var/log/k3s-backup.log`

### Support Commands

```bash
# Check cluster status
kubectl get nodes -o wide
kubectl get pods --all-namespaces

# Check storage
kubectl get storageclass
kubectl get pv,pvc

# Check networking
kubectl get svc --all-namespaces
kubectl get ingress --all-namespaces

# Check certificates
kubectl get certificates --all-namespaces
kubectl get clusterissuer
```

## Contributing

We welcome contributions to improve the K3s Intelligent Installer. Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with detailed description

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd homelab/scripts/k3s-installer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy

# Run linting
black modules/ tests/ k3s_installer.py
flake8 modules/ tests/ k3s_installer.py
mypy modules/ k3s_installer.py
```

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- **K3s Team**: For the lightweight Kubernetes distribution
- **cert-manager Team**: For automated certificate management
- **MetalLB Team**: For bare metal load balancing
- **NVIDIA, AMD, Intel**: For GPU computing support