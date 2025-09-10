"""
K3s Intelligent Installer - Modules Package

This package contains all the modular components for the K3s installer:
- gpu_config: GPU detection and configuration
- storage_setup: Storage provider setup (OpenEBS, local-path)
- networking: MetalLB and Wireguard configuration
- tls_certs: TLS certificate management
- backup_restore: Backup and restore capabilities
- system_utils: Common system utilities
"""

from .gpu_config import GPUConfigurator
from .storage_setup import StorageSetup
from .networking import NetworkingSetup
from .tls_certs import TLSManager
from .backup_restore import BackupManager
from .system_utils import SystemUtils

__all__ = [
    'GPUConfigurator',
    'StorageSetup', 
    'NetworkingSetup',
    'TLSManager',
    'BackupManager',
    'SystemUtils'
]

__version__ = "1.0.0"