"""
Host classification system for Ansible group assignment.
"""

from typing import Dict, List, Any, Set
from ..core.config_manager import AnsibleConfig
from ..core.logger import get_logger

logger = get_logger(__name__)


class GroupClassifier:
    """Classifies hosts into Ansible groups based on their characteristics."""
    
    def __init__(self, config: AnsibleConfig, group_rules: Dict[str, Any]):
        """
        Initialize group classifier.
        
        Args:
            config: Ansible configuration
            group_rules: Custom grouping rules
        """
        self.config = config
        self.group_rules = group_rules
        self.logger = get_logger(f"{__name__}.GroupClassifier")
        
        # Standard classification rules
        self.classification_rules = {
            'ai_nodes': self._is_ai_node,
            'compute_nodes': self._is_compute_node,
            'storage_nodes': self._is_storage_node,
            'k8s_nodes': self._is_k8s_node,
            'k8s_masters': self._is_k8s_master,
            'k8s_workers': self._is_k8s_worker,
            'hypervisor_nodes': self._is_hypervisor_node,
            'web_servers': self._is_web_server,
            'database_servers': self._is_database_server,
            'monitoring_nodes': self._is_monitoring_node,
            'network_devices': self._is_network_device,
            'windows_hosts': self._is_windows_host,
            'linux_hosts': self._is_linux_host,
            'development_nodes': self._is_development_node,
            'media_servers': self._is_media_server
        }
    
    def classify_host(self, host: Dict[str, Any]) -> List[str]:
        """
        Classify a host into appropriate Ansible groups.
        
        Args:
            host: Host asset dictionary
            
        Returns:
            List of group names this host belongs to
        """
        groups = []
        
        try:
            # Apply standard classification rules
            for group_name, rule_func in self.classification_rules.items():
                if rule_func(host):
                    groups.append(group_name)
            
            # Apply location-based grouping if enabled
            if self.config.group_by_location:
                location_group = self._get_location_group(host)
                if location_group:
                    groups.append(location_group)
            
            # Apply hardware-based grouping if enabled
            if self.config.group_by_hardware:
                hardware_groups = self._get_hardware_groups(host)
                groups.extend(hardware_groups)
            
            # Apply role-based grouping if enabled
            if self.config.group_by_role:
                role_groups = self._get_role_groups(host)
                groups.extend(role_groups)
            
            # Apply custom rules
            custom_groups = self._apply_custom_rules(host)
            groups.extend(custom_groups)
            
            # Remove duplicates and sort
            groups = sorted(list(set(groups)))
            
            self.logger.debug(f"Classified host {host.get('ip')} into groups: {groups}")
            return groups
            
        except Exception as e:
            self.logger.warning(f"Failed to classify host {host.get('ip', 'unknown')}: {e}")
            return ['ungrouped']
    
    def _is_ai_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is suitable for AI/ML workloads."""
        gpu_info = host.get('gpu_info', {})
        
        # Has GPU
        if gpu_info.get('has_gpu'):
            return True
        
        # Check hostname for AI indicators
        hostname = host.get('hostname', '').lower()
        ai_keywords = ['ai', 'ml', 'gpu', 'cuda', 'tensorflow', 'pytorch']
        if any(keyword in hostname for keyword in ai_keywords):
            return True
        
        # Check services for AI/ML related services
        services = host.get('services', [])
        ai_services = ['jupyter', 'tensorboard', 'mlflow']
        for service in services:
            if any(ai_service in service.get('name', '').lower() for ai_service in ai_services):
                return True
        
        return False
    
    def _is_compute_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is a high-performance compute node."""
        cpu_info = host.get('cpu_info', {})
        memory_info = host.get('memory_info', {})
        
        # High CPU core count
        logical_cores = cpu_info.get('logical_cores', 0)
        if logical_cores >= 16:
            return True
        
        # High memory
        total_memory = memory_info.get('total', 0)
        if total_memory > 32 * 1024 * 1024 * 1024:  # 32GB
            return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        compute_keywords = ['compute', 'worker', 'node', 'hpc']
        if any(keyword in hostname for keyword in compute_keywords):
            return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if 'server' in classification and logical_cores >= 8:
            return True
        
        return False
    
    def _is_storage_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is a storage/NAS system."""
        services = host.get('services', [])
        service_names = [service.get('name', '').lower() for service in services]
        
        # Storage services
        storage_services = ['nfs', 'smb', 'ftp', 'sftp', 'samba']
        if any(storage_service in service_names for storage_service in storage_services):
            return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        storage_keywords = ['nas', 'storage', 'file', 'backup', 'archive']
        if any(keyword in hostname for keyword in storage_keywords):
            return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if classification == 'storage':
            return True
        
        # High storage capacity
        storage_info = host.get('storage_info', [])
        total_storage = sum(disk.get('total', 0) for disk in storage_info)
        if total_storage > 2 * 1024 * 1024 * 1024 * 1024:  # 2TB
            return True
        
        return False
    
    def _is_k8s_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is part of Kubernetes cluster."""
        services = host.get('services', [])
        
        # Kubernetes services
        k8s_ports = [6443, 10250, 2379, 2380, 10251, 10252]
        for service in services:
            if service.get('port') in k8s_ports:
                return True
        
        # Check for kubelet service
        service_names = [service.get('name', '').lower() for service in services]
        if 'kubernetes' in service_names:
            return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        k8s_keywords = ['k8s', 'kube', 'kubernetes', 'master', 'worker', 'node']
        if any(keyword in hostname for keyword in k8s_keywords):
            return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if 'k8s' in classification or 'kubernetes' in classification:
            return True
        
        return False
    
    def _is_k8s_master(self, host: Dict[str, Any]) -> bool:
        """Check if host is a Kubernetes master node."""
        if not self._is_k8s_node(host):
            return False
        
        services = host.get('services', [])
        
        # API server port
        for service in services:
            if service.get('port') == 6443:
                return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        master_keywords = ['master', 'control', 'api']
        if any(keyword in hostname for keyword in master_keywords):
            return True
        
        return False
    
    def _is_k8s_worker(self, host: Dict[str, Any]) -> bool:
        """Check if host is a Kubernetes worker node."""
        if not self._is_k8s_node(host):
            return False
        
        # If it's a K8s node but not a master, it's likely a worker
        if not self._is_k8s_master(host):
            return True
        
        return False
    
    def _is_hypervisor_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is a virtualization hypervisor."""
        services = host.get('services', [])
        
        # Proxmox
        for service in services:
            if service.get('port') == 8006:
                return True
        
        # VMware ESXi
        for service in services:
            if service.get('port') == 902:  # VMware auth daemon
                return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if 'hypervisor' in classification or 'proxmox' in classification:
            return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        hypervisor_keywords = ['proxmox', 'esxi', 'vmware', 'hyperv', 'xen', 'kvm']
        if any(keyword in hostname for keyword in hypervisor_keywords):
            return True
        
        return False
    
    def _is_web_server(self, host: Dict[str, Any]) -> bool:
        """Check if host is running web services."""
        services = host.get('services', [])
        service_names = [service.get('name', '').lower() for service in services]
        
        web_services = ['http', 'https', 'apache', 'nginx']
        return any(web_service in service_names for web_service in web_services)
    
    def _is_database_server(self, host: Dict[str, Any]) -> bool:
        """Check if host is running database services."""
        services = host.get('services', [])
        service_names = [service.get('name', '').lower() for service in services]
        
        db_services = ['mysql', 'postgresql', 'mongodb', 'redis', 'influxdb', 'elasticsearch']
        return any(db_service in service_names for db_service in db_services)
    
    def _is_monitoring_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is running monitoring services."""
        services = host.get('services', [])
        service_names = [service.get('name', '').lower() for service in services]
        
        monitoring_services = ['prometheus', 'grafana', 'alertmanager', 'node_exporter', 'influxdb']
        if any(monitoring_service in service_names for monitoring_service in monitoring_services):
            return True
        
        # Check hostname
        hostname = host.get('hostname', '').lower()
        monitoring_keywords = ['monitoring', 'metrics', 'grafana', 'prometheus']
        return any(keyword in hostname for keyword in monitoring_keywords)
    
    def _is_network_device(self, host: Dict[str, Any]) -> bool:
        """Check if host is a network device."""
        classification = host.get('classification', '').lower()
        return classification == 'network_device'
    
    def _is_windows_host(self, host: Dict[str, Any]) -> bool:
        """Check if host is running Windows."""
        services = host.get('services', [])
        
        # Windows-specific ports
        windows_ports = [135, 139, 445, 3389]
        for service in services:
            if service.get('port') in windows_ports:
                return True
        
        # Check OS information
        os_info = host.get('os', '').lower()
        if 'windows' in os_info:
            return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if 'windows' in classification:
            return True
        
        return False
    
    def _is_linux_host(self, host: Dict[str, Any]) -> bool:
        """Check if host is running Linux."""
        # If it has SSH and it's not Windows, likely Linux
        services = host.get('services', [])
        has_ssh = any(service.get('name') == 'ssh' for service in services)
        
        if has_ssh and not self._is_windows_host(host):
            return True
        
        # Check OS information
        os_info = host.get('os', '').lower()
        linux_keywords = ['linux', 'ubuntu', 'debian', 'centos', 'redhat', 'fedora', 'arch']
        if any(keyword in os_info for keyword in linux_keywords):
            return True
        
        # Check classification
        classification = host.get('classification', '').lower()
        if classification == 'server' and not self._is_windows_host(host):
            return True
        
        return False
    
    def _is_development_node(self, host: Dict[str, Any]) -> bool:
        """Check if host is used for development."""
        hostname = host.get('hostname', '').lower()
        dev_keywords = ['dev', 'devel', 'build', 'ci', 'cd', 'jenkins', 'gitlab', 'github']
        
        return any(keyword in hostname for keyword in dev_keywords)
    
    def _is_media_server(self, host: Dict[str, Any]) -> bool:
        """Check if host is running media services."""
        hostname = host.get('hostname', '').lower()
        media_keywords = ['plex', 'jellyfin', 'emby', 'media', 'stream']
        
        if any(keyword in hostname for keyword in media_keywords):
            return True
        
        # Check services
        services = host.get('services', [])
        for service in services:
            service_name = service.get('name', '').lower()
            if any(keyword in service_name for keyword in media_keywords):
                return True
        
        return False
    
    def _get_location_group(self, host: Dict[str, Any]) -> str:
        """Get location-based group name."""
        location = host.get('location')
        if location:
            # Clean location name for group name
            clean_location = location.lower().replace(' ', '_').replace('-', '_')
            return f"location_{clean_location}"
        return None
    
    def _get_hardware_groups(self, host: Dict[str, Any]) -> List[str]:
        """Get hardware-based group names."""
        groups = []
        
        # GPU groups
        gpu_info = host.get('gpu_info', {})
        if gpu_info.get('has_gpu'):
            gpu_type = gpu_info.get('gpu_type')
            if gpu_type:
                groups.append(f"{gpu_type}_gpu_nodes")
        
        # CPU architecture groups (if available)
        cpu_info = host.get('cpu_info', {})
        if cpu_info.get('architecture'):
            arch = cpu_info['architecture'].lower()
            groups.append(f"{arch}_hosts")
        
        return groups
    
    def _get_role_groups(self, host: Dict[str, Any]) -> List[str]:
        """Get role-based group names."""
        groups = []
        
        # Check for explicit role assignment
        role = host.get('role')
        if role:
            groups.append(f"role_{role}")
        
        # Infer roles from services
        services = host.get('services', [])
        service_names = [service.get('name', '').lower() for service in services]
        
        # Database role
        if any(db in service_names for db in ['mysql', 'postgresql', 'mongodb']):
            groups.append('role_database')
        
        # Web role
        if any(web in service_names for web in ['http', 'https', 'apache', 'nginx']):
            groups.append('role_web')
        
        # Cache role
        if any(cache in service_names for cache in ['redis', 'memcached']):
            groups.append('role_cache')
        
        return groups
    
    def _apply_custom_rules(self, host: Dict[str, Any]) -> List[str]:
        """Apply custom grouping rules from configuration."""
        groups = []
        
        try:
            custom_rules = self.group_rules.get('custom_classification', {})
            
            for group_name, rule_config in custom_rules.items():
                if self._matches_custom_rule(host, rule_config):
                    groups.append(group_name)
            
        except Exception as e:
            self.logger.warning(f"Failed to apply custom rules: {e}")
        
        return groups
    
    def _matches_custom_rule(self, host: Dict[str, Any], rule_config: Dict[str, Any]) -> bool:
        """Check if host matches a custom rule."""
        try:
            # All conditions must match (AND logic)
            conditions = rule_config.get('conditions', {})
            
            for field, expected_value in conditions.items():
                host_value = self._get_nested_value(host, field)
                
                if isinstance(expected_value, list):
                    # Match any value in list
                    if host_value not in expected_value:
                        return False
                elif isinstance(expected_value, dict):
                    # Pattern matching
                    pattern = expected_value.get('pattern')
                    if pattern and pattern not in str(host_value):
                        return False
                else:
                    # Exact match
                    if host_value != expected_value:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Custom rule matching failed: {e}")
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = field.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def get_available_groups(self) -> Dict[str, str]:
        """
        Get list of available groups and their descriptions.
        
        Returns:
            Dictionary mapping group names to descriptions
        """
        groups = {
            'ai_nodes': 'Hosts with GPU/AI capabilities',
            'compute_nodes': 'High-performance compute hosts',
            'storage_nodes': 'Storage and NAS systems',
            'k8s_nodes': 'Kubernetes cluster nodes',
            'k8s_masters': 'Kubernetes master nodes',
            'k8s_workers': 'Kubernetes worker nodes',
            'hypervisor_nodes': 'Virtualization hosts',
            'web_servers': 'HTTP/HTTPS service hosts',
            'database_servers': 'Database service hosts',
            'monitoring_nodes': 'Monitoring and observability hosts',
            'network_devices': 'Network infrastructure',
            'windows_hosts': 'Windows-based systems',
            'linux_hosts': 'Linux-based systems',
            'development_nodes': 'Development and CI/CD hosts',
            'media_servers': 'Media streaming and management hosts'
        }
        
        # Add location-based groups
        if self.config.group_by_location:
            groups['location_*'] = 'Location-based groups'
        
        # Add hardware-based groups
        if self.config.group_by_hardware:
            groups['*_gpu_nodes'] = 'GPU type-based groups'
            groups['*_hosts'] = 'Architecture-based groups'
        
        # Add role-based groups
        if self.config.group_by_role:
            groups['role_*'] = 'Role-based groups'
        
        return groups