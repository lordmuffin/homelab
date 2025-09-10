"""
Dynamic Ansible inventory generator.

Implements Feature 4: Dynamic Ansible Inventory Generation
User Stories:
1. As a System Administrator, I want the orchestrator to automatically generate my Ansible hosts.yml file 
   so that my configuration management playbooks always run against an up-to-date list of hosts.
2. As a System Administrator, I want the orchestrator to automatically assign hosts to groups like 
   ai_nodes, compute_nodes, and storage_nodes so that the correct, role-specific configurations 
   are applied to the right machines without manual intervention.
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from jinja2 import Template

from ..core.config_manager import AnsibleConfig
from ..core.logger import get_logger
from .group_classifier import GroupClassifier

logger = get_logger(__name__)


class InventoryGenerator:
    """Dynamic Ansible inventory generator with automatic host grouping."""
    
    def __init__(self, config: AnsibleConfig, group_rules: Dict[str, Any]):
        """
        Initialize inventory generator.
        
        Args:
            config: Ansible configuration
            group_rules: Custom grouping rules
        """
        self.config = config
        self.group_rules = group_rules
        self.logger = get_logger(f"{__name__}.InventoryGenerator")
        
        # Initialize group classifier
        self.group_classifier = GroupClassifier(config, group_rules)
        
        # Standard Ansible group names
        self.standard_groups = {
            'all': 'All managed hosts',
            'ungrouped': 'Hosts not in any other group'
        }
        
        # Common homelab groups
        self.common_groups = {
            'ai_nodes': 'Hosts with GPU/AI capabilities',
            'compute_nodes': 'High-performance compute hosts',
            'storage_nodes': 'Storage and NAS systems',
            'k8s_nodes': 'Kubernetes cluster nodes',
            'k8s_masters': 'Kubernetes master nodes',
            'k8s_workers': 'Kubernetes worker nodes',
            'hypervisor_nodes': 'Virtualization hosts (Proxmox, ESXi)',
            'web_servers': 'HTTP/HTTPS service hosts',
            'database_servers': 'Database service hosts',
            'monitoring_nodes': 'Monitoring and observability hosts',
            'network_devices': 'Network infrastructure (switches, routers)',
            'windows_hosts': 'Windows-based systems',
            'linux_hosts': 'Linux-based systems',
            'development_nodes': 'Development and CI/CD hosts',
            'media_servers': 'Media streaming and management hosts'
        }
    
    async def generate_inventory(self, assets: List[Dict[str, Any]], output_dir: Optional[Path] = None) -> Path:
        """
        Generate Ansible inventory from asset data.
        
        Args:
            assets: List of asset dictionaries
            output_dir: Optional output directory. If None, uses current directory.
            
        Returns:
            Path to generated inventory file
        """
        self.logger.info(f"Generating Ansible inventory for {len(assets)} assets")
        
        try:
            # Set output directory
            if output_dir is None:
                output_dir = Path.cwd()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Filter assets to only include valid hosts
            valid_hosts = self._filter_valid_hosts(assets)
            self.logger.info(f"Found {len(valid_hosts)} valid hosts for inventory")
            
            # Classify hosts into groups
            host_groups = await self._classify_hosts(valid_hosts)
            
            # Generate inventory data structure
            inventory_data = self._build_inventory_structure(valid_hosts, host_groups)
            
            # Generate inventory file based on format
            if self.config.output_format.lower() == 'yaml':
                output_file = output_dir / "hosts.yml"
                await self._write_yaml_inventory(inventory_data, output_file)
            elif self.config.output_format.lower() == 'json':
                output_file = output_dir / "hosts.json"
                await self._write_json_inventory(inventory_data, output_file)
            else:  # ini format
                output_file = output_dir / "hosts.ini"
                await self._write_ini_inventory(inventory_data, output_file)
            
            # Generate additional files
            await self._generate_group_vars(host_groups, output_dir)
            await self._generate_host_vars(valid_hosts, output_dir)
            
            self.logger.info(f"Generated Ansible inventory: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ansible inventory: {e}")
            raise
    
    def _filter_valid_hosts(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter assets to only include those suitable for Ansible management.
        
        Args:
            assets: List of all assets
            
        Returns:
            List of valid host assets
        """
        valid_hosts = []
        
        for asset in assets:
            # Must have IP address
            if not asset.get('ip'):
                continue
            
            # Skip network devices that don't support SSH
            if asset.get('classification') == 'network_device':
                # Only include if SSH is available
                services = asset.get('services', [])
                has_ssh = any(service.get('name') == 'ssh' for service in services)
                if not has_ssh:
                    continue
            
            # Skip hosts with no accessible services
            services = asset.get('services', [])
            if not services:
                # Still include if it responded to ping or has known classification
                classification = asset.get('classification', 'unknown')
                if classification == 'unknown' and asset.get('source') == 'ping_only':
                    continue
            
            valid_hosts.append(asset)
        
        return valid_hosts
    
    async def _classify_hosts(self, hosts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Classify hosts into Ansible groups.
        
        Args:
            hosts: List of host assets
            
        Returns:
            Dictionary mapping group names to lists of hosts
        """
        host_groups = {}
        
        for host in hosts:
            # Get groups for this host
            groups = self.group_classifier.classify_host(host)
            
            # Add host to each group
            for group in groups:
                if group not in host_groups:
                    host_groups[group] = []
                host_groups[group].append(host)
        
        # Ensure ungrouped exists for hosts with no specific groups
        ungrouped_hosts = []
        for host in hosts:
            # Check if host is in any group (excluding 'all')
            in_group = False
            for group_name, group_hosts in host_groups.items():
                if group_name != 'all' and host in group_hosts:
                    in_group = True
                    break
            
            if not in_group:
                ungrouped_hosts.append(host)
        
        if ungrouped_hosts:
            host_groups['ungrouped'] = ungrouped_hosts
        
        # Add all hosts to 'all' group
        host_groups['all'] = hosts
        
        self.logger.debug(f"Classified hosts into {len(host_groups)} groups")
        return host_groups
    
    def _build_inventory_structure(self, hosts: List[Dict[str, Any]], host_groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Build Ansible inventory data structure.
        
        Args:
            hosts: List of all hosts
            host_groups: Dictionary of group classifications
            
        Returns:
            Ansible inventory data structure
        """
        inventory = {
            '_meta': {
                'hostvars': {}
            }
        }
        
        # Add host variables
        for host in hosts:
            host_vars = self._build_host_vars(host)
            hostname = host_vars['inventory_hostname']
            inventory['_meta']['hostvars'][hostname] = host_vars
        
        # Add groups
        for group_name, group_hosts in host_groups.items():
            if group_name == 'all':
                continue  # Skip 'all' group, it's implicit in Ansible
            
            inventory[group_name] = {
                'hosts': [self._get_inventory_hostname(host) for host in group_hosts]
            }
            
            # Add group variables if configured
            group_vars = self._build_group_vars(group_name, group_hosts)
            if group_vars:
                inventory[group_name]['vars'] = group_vars
        
        # Add metadata
        if self.config.include_metadata:
            inventory['_meta']['generated_by'] = 'automation_orchestrator'
            inventory['_meta']['generated_at'] = datetime.now().isoformat()
            inventory['_meta']['total_hosts'] = len(hosts)
            inventory['_meta']['groups'] = list(host_groups.keys())
        
        return inventory
    
    def _build_host_vars(self, host: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Ansible host variables from asset data.
        
        Args:
            host: Host asset dictionary
            
        Returns:
            Ansible host variables
        """
        # Basic host variables
        host_vars = {
            'inventory_hostname': self._get_inventory_hostname(host),
            'ansible_host': host['ip'],
            'discovered_at': host.get('discovered_at'),
            'last_updated': host.get('last_updated')
        }
        
        # Add hostname if different from IP
        hostname = host.get('hostname')
        if hostname and hostname != host['ip']:
            host_vars['discovered_hostname'] = hostname
        
        # Operating system information
        os_info = host.get('os')
        if os_info:
            host_vars['ansible_os'] = os_info
            
            # Set Ansible connection parameters based on OS
            if 'windows' in os_info.lower():
                host_vars['ansible_connection'] = 'winrm'
                host_vars['ansible_winrm_transport'] = 'ntlm'
            else:
                host_vars['ansible_connection'] = 'ssh'
        
        # Network information
        if host.get('location'):
            host_vars['location'] = host['location']
        
        if host.get('network_name'):
            host_vars['network'] = host['network_name']
        
        if host.get('vlan_id'):
            host_vars['vlan_id'] = host['vlan_id']
        
        # Hardware information
        gpu_info = host.get('gpu_info', {})
        if gpu_info.get('has_gpu'):
            host_vars['has_gpu'] = True
            host_vars['gpu_type'] = gpu_info.get('gpu_type')
            host_vars['gpu_count'] = gpu_info.get('gpu_count', 1)
            
            if gpu_info.get('gpus'):
                host_vars['gpu_models'] = [gpu.get('name') for gpu in gpu_info['gpus']]
        
        # CPU and memory info
        cpu_info = host.get('cpu_info', {})
        if cpu_info:
            if 'logical_cores' in cpu_info:
                host_vars['cpu_cores'] = cpu_info['logical_cores']
            if 'physical_cores' in cpu_info:
                host_vars['cpu_physical_cores'] = cpu_info['physical_cores']
        
        memory_info = host.get('memory_info', {})
        if memory_info.get('total'):
            host_vars['memory_bytes'] = memory_info['total']
            host_vars['memory_gb'] = round(memory_info['total'] / (1024**3), 1)
        
        # Service information
        services = host.get('services', [])
        if services:
            host_vars['services'] = [service.get('name') for service in services]
            host_vars['service_ports'] = [{'name': s.get('name'), 'port': s.get('port')} for s in services]
            
            # Set connection parameters based on available services
            if any(service.get('name') == 'ssh' for service in services):
                ssh_service = next(s for s in services if s.get('name') == 'ssh')
                if ssh_service.get('port') != 22:
                    host_vars['ansible_port'] = ssh_service['port']
        
        # Classification and capabilities
        classification = host.get('classification')
        if classification:
            host_vars['host_type'] = classification
        
        # Add custom metadata if configured
        if self.config.include_metadata:
            host_vars['discovery_source'] = host.get('source')
            host_vars['open_ports'] = len(host.get('open_ports', []))
            
            # Security assessment
            security_services = []
            for service in services:
                security_info = service.get('security', {})
                if security_info.get('risk_level') == 'high':
                    security_services.append(service.get('name'))
            
            if security_services:
                host_vars['security_concerns'] = security_services
        
        return host_vars
    
    def _build_group_vars(self, group_name: str, group_hosts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build group variables for Ansible.
        
        Args:
            group_name: Name of the group
            group_hosts: List of hosts in the group
            
        Returns:
            Group variables dictionary
        """
        group_vars = {}
        
        # Add custom group variables from configuration
        if group_name in self.config.custom_groups:
            group_vars.update(self.config.custom_groups[group_name])
        
        # Add group-specific variables based on group type
        if group_name == 'ai_nodes':
            group_vars.update({
                'nvidia_docker_runtime': True,
                'cuda_enabled': True,
                'install_nvidia_drivers': True
            })
        
        elif group_name == 'k8s_masters':
            group_vars.update({
                'k8s_role': 'master',
                'k8s_master': True,
                'k8s_scheduler': True
            })
        
        elif group_name == 'k8s_workers':
            group_vars.update({
                'k8s_role': 'worker',
                'k8s_worker': True
            })
        
        elif group_name == 'storage_nodes':
            group_vars.update({
                'nfs_server': True,
                'storage_role': True
            })
        
        elif group_name == 'windows_hosts':
            group_vars.update({
                'ansible_connection': 'winrm',
                'ansible_winrm_transport': 'ntlm',
                'ansible_winrm_server_cert_validation': 'ignore'
            })
        
        # Add metadata
        if self.config.include_metadata:
            group_vars['group_size'] = len(group_hosts)
            group_vars['group_description'] = self.common_groups.get(group_name, f"Custom group: {group_name}")
        
        return group_vars
    
    def _get_inventory_hostname(self, host: Dict[str, Any]) -> str:
        """
        Get the inventory hostname for a host.
        
        Args:
            host: Host asset dictionary
            
        Returns:
            Inventory hostname string
        """
        # Prefer meaningful hostname over IP
        hostname = host.get('hostname')
        ip = host.get('ip')
        
        if hostname and hostname != ip:
            # Clean hostname for Ansible (remove invalid characters)
            clean_hostname = hostname.replace('.', '-').replace(' ', '_')
            return clean_hostname
        else:
            # Use IP with underscores instead of dots
            return ip.replace('.', '_')
    
    async def _write_yaml_inventory(self, inventory_data: Dict[str, Any], output_file: Path):
        """Write inventory in YAML format."""
        try:
            with open(output_file, 'w') as f:
                yaml.dump(inventory_data, f, default_flow_style=False, indent=2, sort_keys=True)
            
            self.logger.debug(f"Wrote YAML inventory to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to write YAML inventory: {e}")
            raise
    
    async def _write_json_inventory(self, inventory_data: Dict[str, Any], output_file: Path):
        """Write inventory in JSON format."""
        try:
            with open(output_file, 'w') as f:
                json.dump(inventory_data, f, indent=2, default=str, sort_keys=True)
            
            self.logger.debug(f"Wrote JSON inventory to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to write JSON inventory: {e}")
            raise
    
    async def _write_ini_inventory(self, inventory_data: Dict[str, Any], output_file: Path):
        """Write inventory in INI format."""
        try:
            lines = []
            
            # Add groups and hosts
            for group_name, group_data in inventory_data.items():
                if group_name.startswith('_'):
                    continue  # Skip metadata
                
                lines.append(f"[{group_name}]")
                
                if isinstance(group_data, dict) and 'hosts' in group_data:
                    for hostname in group_data['hosts']:
                        # Get host variables from _meta.hostvars
                        host_vars = inventory_data.get('_meta', {}).get('hostvars', {}).get(hostname, {})
                        
                        # Build host line with key variables
                        host_line = hostname
                        
                        # Add key variables to host line
                        if 'ansible_host' in host_vars:
                            host_line += f" ansible_host={host_vars['ansible_host']}"
                        
                        if 'ansible_port' in host_vars:
                            host_line += f" ansible_port={host_vars['ansible_port']}"
                        
                        if 'ansible_connection' in host_vars:
                            host_line += f" ansible_connection={host_vars['ansible_connection']}"
                        
                        lines.append(host_line)
                    
                    # Add group variables
                    if 'vars' in group_data and group_data['vars']:
                        lines.append(f"[{group_name}:vars]")
                        for var_name, var_value in group_data['vars'].items():
                            lines.append(f"{var_name}={var_value}")
                
                lines.append("")  # Empty line between groups
            
            # Write to file
            with open(output_file, 'w') as f:
                f.write('\n'.join(lines))
            
            self.logger.debug(f"Wrote INI inventory to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to write INI inventory: {e}")
            raise
    
    async def _generate_group_vars(self, host_groups: Dict[str, List[Dict[str, Any]]], output_dir: Path):
        """Generate group_vars directory with group-specific variables."""
        try:
            group_vars_dir = output_dir / "group_vars"
            group_vars_dir.mkdir(exist_ok=True)
            
            for group_name, group_hosts in host_groups.items():
                if group_name in ['all', 'ungrouped']:
                    continue
                
                group_vars = self._build_detailed_group_vars(group_name, group_hosts)
                
                if group_vars:
                    group_file = group_vars_dir / f"{group_name}.yml"
                    with open(group_file, 'w') as f:
                        yaml.dump(group_vars, f, default_flow_style=False, indent=2)
            
            self.logger.debug(f"Generated group_vars in {group_vars_dir}")
            
        except Exception as e:
            self.logger.warning(f"Failed to generate group_vars: {e}")
    
    async def _generate_host_vars(self, hosts: List[Dict[str, Any]], output_dir: Path):
        """Generate host_vars directory with host-specific variables."""
        try:
            host_vars_dir = output_dir / "host_vars"
            host_vars_dir.mkdir(exist_ok=True)
            
            for host in hosts:
                hostname = self._get_inventory_hostname(host)
                host_vars = self._build_detailed_host_vars(host)
                
                if host_vars:
                    host_file = host_vars_dir / f"{hostname}.yml"
                    with open(host_file, 'w') as f:
                        yaml.dump(host_vars, f, default_flow_style=False, indent=2)
            
            self.logger.debug(f"Generated host_vars in {host_vars_dir}")
            
        except Exception as e:
            self.logger.warning(f"Failed to generate host_vars: {e}")
    
    def _build_detailed_group_vars(self, group_name: str, group_hosts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build detailed group variables for group_vars files."""
        group_vars = {}
        
        # Add description and metadata
        group_vars['group_description'] = self.common_groups.get(group_name, f"Custom group: {group_name}")
        group_vars['group_size'] = len(group_hosts)
        group_vars['generated_at'] = datetime.now().isoformat()
        
        # Group-specific configurations
        if group_name == 'ai_nodes':
            group_vars.update({
                'nvidia_docker_runtime': True,
                'cuda_enabled': True,
                'install_nvidia_drivers': True,
                'docker_daemon_options': {
                    'default-runtime': 'nvidia'
                },
                'packages': [
                    'nvidia-docker2',
                    'nvidia-container-toolkit'
                ]
            })
        
        elif group_name == 'k8s_masters':
            group_vars.update({
                'k8s_role': 'master',
                'k8s_master': True,
                'k8s_allow_schedule': False,
                'k8s_api_secure_port': 6443,
                'packages': [
                    'kubeadm',
                    'kubelet',
                    'kubectl'
                ]
            })
        
        elif group_name == 'storage_nodes':
            group_vars.update({
                'nfs_exports_enabled': True,
                'samba_shares_enabled': True,
                'storage_monitoring': True,
                'packages': [
                    'nfs-kernel-server',
                    'samba',
                    'smartmontools'
                ]
            })
        
        return group_vars
    
    def _build_detailed_host_vars(self, host: Dict[str, Any]) -> Dict[str, Any]:
        """Build detailed host variables for host_vars files."""
        # Start with basic host vars
        host_vars = self._build_host_vars(host)
        
        # Add detailed information
        host_vars['asset_data'] = {
            'discovery_method': host.get('detection_method'),
            'classification': host.get('classification'),
            'open_ports_count': len(host.get('open_ports', [])),
            'services_count': len(host.get('services', []))
        }
        
        # Add service details
        services = host.get('services', [])
        if services:
            host_vars['detected_services'] = {}
            for service in services:
                service_name = service.get('name')
                if service_name:
                    host_vars['detected_services'][service_name] = {
                        'port': service.get('port'),
                        'protocol': service.get('protocol'),
                        'version': service.get('version', 'unknown'),
                        'state': service.get('state', 'detected')
                    }
        
        return host_vars
    
    def get_inventory_summary(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics for the inventory.
        
        Args:
            inventory_data: Generated inventory data
            
        Returns:
            Inventory summary dictionary
        """
        try:
            summary = {
                'total_hosts': 0,
                'total_groups': 0,
                'groups': {},
                'host_types': {},
                'locations': {},
                'capabilities': {
                    'gpu_hosts': 0,
                    'k8s_hosts': 0,
                    'windows_hosts': 0,
                    'linux_hosts': 0
                }
            }
            
            # Count hosts and analyze host vars
            hostvars = inventory_data.get('_meta', {}).get('hostvars', {})
            summary['total_hosts'] = len(hostvars)
            
            for hostname, host_vars in hostvars.items():
                # Count by host type
                host_type = host_vars.get('host_type', 'unknown')
                summary['host_types'][host_type] = summary['host_types'].get(host_type, 0) + 1
                
                # Count by location
                location = host_vars.get('location', 'unknown')
                summary['locations'][location] = summary['locations'].get(location, 0) + 1
                
                # Count capabilities
                if host_vars.get('has_gpu'):
                    summary['capabilities']['gpu_hosts'] += 1
                
                if 'k8s' in host_vars.get('services', []):
                    summary['capabilities']['k8s_hosts'] += 1
                
                if host_vars.get('ansible_connection') == 'winrm':
                    summary['capabilities']['windows_hosts'] += 1
                else:
                    summary['capabilities']['linux_hosts'] += 1
            
            # Count groups
            for key in inventory_data.keys():
                if not key.startswith('_'):
                    summary['total_groups'] += 1
                    
                    # Get group info
                    group_data = inventory_data[key]
                    if isinstance(group_data, dict) and 'hosts' in group_data:
                        summary['groups'][key] = len(group_data['hosts'])
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate inventory summary: {e}")
            return {'error': str(e)}