#!/usr/bin/env python3
"""
Test Suite for K3s Intelligent Installer

This test suite provides comprehensive testing for all installer modules:
- System compatibility checks
- Configuration validation
- Module functionality testing
- Integration testing
- Mock testing for external dependencies

Usage:
    python -m pytest tests/test_installer.py -v
    python -m pytest tests/test_installer.py::TestSystemUtils -v
"""

import os
import sys
import pytest
import tempfile
import yaml
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.system_utils import SystemUtils, SystemInfo
from modules.gpu_config import GPUConfigurator, GPUInfo
from modules.storage_setup import StorageSetup
from modules.networking import NetworkingSetup
from modules.tls_certs import TLSManager
from modules.backup_restore import BackupManager
from k3s_installer import K3sInstaller

class TestSystemUtils:
    """Test SystemUtils module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.system_utils = SystemUtils()
    
    def test_detect_system(self):
        """Test system detection"""
        with patch('distro.name', return_value='Ubuntu'):
            with patch('distro.version', return_value='22.04'):
                with patch('platform.machine', return_value='x86_64'):
                    with patch('psutil.cpu_count', return_value=4):
                        with patch('psutil.virtual_memory') as mock_memory:
                            mock_memory.return_value.total = 8 * 1024**3  # 8GB
                            
                            system_info = self.system_utils.detect_system()
                            
                            assert system_info.os_name == 'Ubuntu'
                            assert system_info.os_version == '22.04'
                            assert system_info.architecture == 'x86_64'
                            assert system_info.cpu_count == 4
                            assert system_info.memory_gb == 8.0
    
    def test_check_compatibility_supported_os(self):
        """Test compatibility check with supported OS"""
        self.system_utils.system_info = SystemInfo(
            os_name='Ubuntu',
            os_version='22.04',
            architecture='x86_64',
            kernel_version='5.15.0',
            cpu_count=4,
            memory_gb=8.0,
            disk_space_gb=50.0,
            hostname='test-host'
        )
        
        assert self.system_utils.check_compatibility() == True
    
    def test_check_compatibility_unsupported_os(self):
        """Test compatibility check with unsupported OS"""
        self.system_utils.system_info = SystemInfo(
            os_name='Windows',
            os_version='11',
            architecture='x86_64',
            kernel_version='10.0.22000',
            cpu_count=4,
            memory_gb=8.0,
            disk_space_gb=50.0,
            hostname='test-host'
        )
        
        assert self.system_utils.check_compatibility() == False
    
    def test_check_resources_sufficient(self):
        """Test resource check with sufficient resources"""
        self.system_utils.system_info = SystemInfo(
            os_name='Ubuntu',
            os_version='22.04',
            architecture='x86_64',
            kernel_version='5.15.0',
            cpu_count=4,
            memory_gb=8.0,
            disk_space_gb=50.0,
            hostname='test-host'
        )
        
        assert self.system_utils.check_resources() == True
    
    def test_check_resources_insufficient(self):
        """Test resource check with insufficient resources"""
        self.system_utils.system_info = SystemInfo(
            os_name='Ubuntu',
            os_version='22.04',
            architecture='x86_64',
            kernel_version='5.15.0',
            cpu_count=1,  # Below minimum
            memory_gb=2.0,  # Below minimum
            disk_space_gb=10.0,  # Below minimum
            hostname='test-host'
        )
        
        assert self.system_utils.check_resources() == False

class TestGPUConfigurator:
    """Test GPUConfigurator module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'gpu': {
                'enabled': True,
                'auto_detect': True,
                'nvidia': {'install_driver': True},
                'amd': {'install_driver': True},
                'intel': {'device_plugin': True}
            }
        }
        self.gpu_configurator = GPUConfigurator(self.config)
    
    @patch('subprocess.run')
    def test_detect_nvidia_gpus(self, mock_subprocess):
        """Test NVIDIA GPU detection"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "NVIDIA GeForce RTX 3080, 10240, 470.57.02, GPU-12345678, 00000000:01:00.0"
        mock_subprocess.return_value = mock_result
        
        gpus = self.gpu_configurator._detect_nvidia_gpus()
        
        assert len(gpus) == 1
        assert gpus[0].vendor == "NVIDIA"
        assert gpus[0].model == "NVIDIA GeForce RTX 3080"
        assert gpus[0].memory == 10240
    
    @patch('subprocess.run')
    def test_detect_nvidia_gpus_not_found(self, mock_subprocess):
        """Test NVIDIA GPU detection when no GPUs found"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "nvidia-smi: command not found"
        mock_subprocess.return_value = mock_result
        
        gpus = self.gpu_configurator._detect_nvidia_gpus()
        
        assert len(gpus) == 0
    
    def test_gpu_config_disabled(self):
        """Test GPU configuration when disabled"""
        config = {'gpu': {'enabled': False}}
        gpu_configurator = GPUConfigurator(config)
        
        result = gpu_configurator.configure_gpu_support()
        
        assert result == True  # Should succeed when disabled

class TestStorageSetup:
    """Test StorageSetup module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'storage': {
                'provider': 'local-path'
            }
        }
        self.storage_setup = StorageSetup(self.config)
    
    def test_local_path_setup(self):
        """Test local-path storage setup"""
        config = {'storage': {'provider': 'local-path'}}
        storage_setup = StorageSetup(config)
        
        result = storage_setup._setup_local_path()
        
        assert result == True
        assert storage_setup.storage_config.provider == 'local-path'
    
    @patch('subprocess.run')
    def test_validate_storage_setup(self, mock_subprocess):
        """Test storage setup validation"""
        # Mock kubectl get storageclass
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"items": [{"metadata": {"name": "local-path"}}]}'
        mock_subprocess.return_value = mock_result
        
        self.storage_setup.storage_config = Mock()
        self.storage_setup.storage_config.storage_class = 'local-path'
        
        result = self.storage_setup.validate_storage_setup()
        
        assert result == True

class TestNetworkingSetup:
    """Test NetworkingSetup module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'networking': {
                'metallb': {
                    'enabled': True,
                    'version': 'v0.14.8',
                    'address_pools': [{
                        'name': 'default',
                        'protocol': 'layer2',
                        'addresses': ['192.168.1.240-192.168.1.250']
                    }]
                },
                'wireguard': {
                    'enabled': False
                }
            }
        }
        self.networking_setup = NetworkingSetup(self.config)
    
    def test_validate_address_range_valid_range(self):
        """Test address range validation with valid range"""
        result = self.networking_setup._validate_address_range('192.168.1.240-192.168.1.250')
        assert result == True
    
    def test_validate_address_range_valid_cidr(self):
        """Test address range validation with valid CIDR"""
        result = self.networking_setup._validate_address_range('192.168.1.0/24')
        assert result == True
    
    def test_validate_address_range_valid_single_ip(self):
        """Test address range validation with valid single IP"""
        result = self.networking_setup._validate_address_range('192.168.1.100')
        assert result == True
    
    def test_validate_address_range_invalid(self):
        """Test address range validation with invalid range"""
        result = self.networking_setup._validate_address_range('invalid-range')
        assert result == False

class TestTLSManager:
    """Test TLSManager module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'tls': {
                'auto_generate': True,
                'cert_manager': {
                    'enabled': True,
                    'version': 'v1.15.3',
                    'email': 'test@example.com'
                }
            }
        }
        self.tls_manager = TLSManager(self.config)
    
    def test_tls_config_initialization(self):
        """Test TLS configuration initialization"""
        assert self.tls_manager.config['auto_generate'] == True
        assert self.tls_manager.config['cert_manager']['enabled'] == True
        assert self.tls_manager.tls_config.cert_manager_enabled == False  # Not deployed yet
    
    def test_create_letsencrypt_issuer_staging(self):
        """Test Let's Encrypt staging issuer creation"""
        issuer_yaml = self.tls_manager._create_letsencrypt_issuer(
            'test-staging', 'test@example.com', staging=True
        )
        
        assert 'acme-staging-v02.api.letsencrypt.org' in issuer_yaml
        assert 'test@example.com' in issuer_yaml
        assert 'test-staging' in issuer_yaml
    
    def test_create_letsencrypt_issuer_production(self):
        """Test Let's Encrypt production issuer creation"""
        issuer_yaml = self.tls_manager._create_letsencrypt_issuer(
            'test-prod', 'test@example.com', staging=False
        )
        
        assert 'acme-v02.api.letsencrypt.org' in issuer_yaml
        assert 'test@example.com' in issuer_yaml
        assert 'test-prod' in issuer_yaml

class TestBackupManager:
    """Test BackupManager module"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'backup': {
                'enabled': True,
                'schedule': '0 2 * * *',
                'retention': '30d',
                'destinations': {
                    'local': {
                        'enabled': True,
                        'path': '/tmp/test-backups'
                    },
                    's3': {
                        'enabled': False
                    }
                }
            }
        }
        self.backup_manager = BackupManager(self.config)
    
    def test_backup_config_initialization(self):
        """Test backup configuration initialization"""
        assert self.backup_manager.backup_config.enabled == True
        assert self.backup_manager.backup_config.schedule == '0 2 * * *'
        assert self.backup_manager.backup_config.retention == '30d'
    
    def test_create_backup_directories(self):
        """Test backup directory creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.backup_manager.config['destinations']['local']['path'] = temp_dir
            
            result = self.backup_manager._create_backup_directories()
            
            assert result == True
            assert Path(temp_dir).exists()
    
    def test_calculate_checksum(self):
        """Test checksum calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name
        
        try:
            checksum = self.backup_manager._calculate_checksum(temp_file_path)
            assert len(checksum) == 64  # SHA256 hash length
            assert isinstance(checksum, str)
        finally:
            os.unlink(temp_file_path)

class TestK3sInstaller:
    """Test main K3sInstaller class"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        config_data = {
            'k3s': {
                'version': 'v1.31.1+k3s1',
                'server': {
                    'cluster_init': True,
                    'disable': ['traefik']
                }
            },
            'gpu': {'enabled': False},
            'storage': {'provider': 'local-path'},
            'networking': {
                'metallb': {'enabled': False},
                'wireguard': {'enabled': False}
            },
            'tls': {'auto_generate': False},
            'backup': {'enabled': False}
        }
        yaml.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.installer = K3sInstaller(self.temp_config.name)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        os.unlink(self.temp_config.name)
    
    def test_load_config_success(self):
        """Test successful configuration loading"""
        result = self.installer.load_config()
        
        assert result == True
        assert 'k3s' in self.installer.config
        assert self.installer.config['k3s']['version'] == 'v1.31.1+k3s1'
    
    def test_load_config_file_not_found(self):
        """Test configuration loading with non-existent file"""
        installer = K3sInstaller('/nonexistent/config.yaml')
        
        result = installer.load_config()
        
        assert result == False
    
    def test_initialize_components(self):
        """Test component initialization"""
        self.installer.load_config()
        self.installer.initialize_components()
        
        assert self.installer.system_utils is not None
        assert self.installer.gpu_configurator is not None
        assert self.installer.storage_setup is not None
        assert self.installer.networking_setup is not None
        assert self.installer.tls_manager is not None
        assert self.installer.backup_manager is not None
    
    @patch('subprocess.run')
    def test_validate_k3s_success(self, mock_subprocess):
        """Test K3s validation when service is running"""
        # Mock systemctl is-active k3s
        mock_result_active = Mock()
        mock_result_active.returncode = 0
        mock_result_active.stdout = 'active'
        
        # Mock kubectl get nodes
        mock_result_kubectl = Mock()
        mock_result_kubectl.returncode = 0
        mock_result_kubectl.stdout = 'node1   Ready   control-plane'
        
        mock_subprocess.side_effect = [mock_result_active, mock_result_kubectl]
        
        self.installer.status.k3s_installed = True
        result = self.installer._validate_k3s()
        
        assert result == True
    
    @patch('subprocess.run')
    def test_validate_k3s_service_not_running(self, mock_subprocess):
        """Test K3s validation when service is not running"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'inactive'
        mock_subprocess.return_value = mock_result
        
        self.installer.status.k3s_installed = True
        result = self.installer._validate_k3s()
        
        assert result == False

class TestIntegration:
    """Integration tests for the complete installer"""
    
    def setup_method(self):
        """Setup for integration tests"""
        # Create a minimal valid configuration
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        config_data = {
            'k3s': {
                'version': 'v1.31.1+k3s1',
                'server': {'cluster_init': True}
            },
            'gpu': {'enabled': False},
            'storage': {'provider': 'local-path'},
            'networking': {'metallb': {'enabled': False}},
            'tls': {'auto_generate': False},
            'backup': {'enabled': False}
        }
        yaml.dump(config_data, self.temp_config)
        self.temp_config.close()
    
    def teardown_method(self):
        """Cleanup after integration tests"""
        os.unlink(self.temp_config.name)
    
    def test_config_loading_and_validation(self):
        """Test configuration loading and basic validation"""
        installer = K3sInstaller(self.temp_config.name)
        
        # Load configuration
        assert installer.load_config() == True
        
        # Initialize components
        installer.initialize_components()
        
        # Verify all components are initialized
        assert installer.system_utils is not None
        assert installer.gpu_configurator is not None
        assert installer.storage_setup is not None
        assert installer.networking_setup is not None
        assert installer.tls_manager is not None
        assert installer.backup_manager is not None
    
    @patch('modules.system_utils.SystemUtils.detect_system')
    @patch('modules.system_utils.SystemUtils.check_compatibility')
    @patch('modules.system_utils.SystemUtils.check_resources')
    @patch('modules.system_utils.SystemUtils.check_prerequisites')
    def test_system_checks_integration(self, mock_prereq, mock_resources, 
                                     mock_compat, mock_detect):
        """Test integrated system checks"""
        # Mock all system check methods
        mock_detect.return_value = SystemInfo(
            os_name='Ubuntu', os_version='22.04', architecture='x86_64',
            kernel_version='5.15.0', cpu_count=4, memory_gb=8.0,
            disk_space_gb=50.0, hostname='test-host'
        )
        mock_compat.return_value = True
        mock_resources.return_value = True
        mock_prereq.return_value = True
        
        installer = K3sInstaller(self.temp_config.name)
        installer.load_config()
        installer.initialize_components()
        
        result = installer.run_system_checks()
        
        assert result == True
        assert installer.status.system_check == True

# Test fixtures and utilities
@pytest.fixture
def sample_config():
    """Fixture providing a sample configuration"""
    return {
        'k3s': {
            'version': 'v1.31.1+k3s1',
            'server': {
                'cluster_init': True,
                'disable': ['traefik', 'servicelb']
            }
        },
        'gpu': {
            'enabled': True,
            'auto_detect': True,
            'nvidia': {'install_driver': True}
        },
        'storage': {
            'provider': 'local-path'
        },
        'networking': {
            'metallb': {
                'enabled': True,
                'address_pools': [{
                    'name': 'default',
                    'addresses': ['192.168.1.240-192.168.1.250']
                }]
            }
        },
        'tls': {
            'auto_generate': True,
            'cert_manager': {
                'enabled': True,
                'email': 'admin@example.com'
            }
        },
        'backup': {
            'enabled': True,
            'destinations': {
                'local': {'enabled': True, 'path': '/var/backups/k3s'}
            }
        }
    }

@pytest.fixture
def mock_system_info():
    """Fixture providing mock system information"""
    return SystemInfo(
        os_name='Ubuntu',
        os_version='22.04',
        architecture='x86_64',
        kernel_version='5.15.0',
        cpu_count=4,
        memory_gb=8.0,
        disk_space_gb=50.0,
        hostname='test-host'
    )

# Performance tests
class TestPerformance:
    """Performance tests for installer components"""
    
    def test_config_loading_performance(self):
        """Test configuration loading performance"""
        import time
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            # Create a large config for performance testing
            large_config = {f'section_{i}': {f'key_{j}': f'value_{j}' 
                           for j in range(100)} for i in range(100)}
            yaml.dump(large_config, temp_file)
            temp_file_path = temp_file.name
        
        try:
            installer = K3sInstaller(temp_file_path)
            
            start_time = time.time()
            installer.load_config()
            end_time = time.time()
            
            # Config loading should be fast (< 1 second even for large configs)
            assert (end_time - start_time) < 1.0
            
        finally:
            os.unlink(temp_file_path)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])