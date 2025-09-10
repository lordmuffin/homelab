"""
Seed inventory parser for processing initial infrastructure definition files.

Implements Feature 1: Seed Inventory Ingestion
User Story: As a System Administrator, I want to provide a simple seed_inventory.yml file
so that I can define the initial scope and starting points for automated discovery.
"""

import yaml
import ipaddress
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, ValidationError, validator
from ..core.logger import get_logger

logger = get_logger(__name__)


class NetworkDefinition(BaseModel):
    """Network definition in seed inventory."""
    network: str = Field(..., description="Network CIDR (e.g., 192.168.1.0/24)")
    name: Optional[str] = Field(None, description="Network name/label")
    location: Optional[str] = Field(None, description="Physical location")
    vlan_id: Optional[int] = Field(None, ge=1, le=4094, description="VLAN ID")
    discovery_priority: int = Field(default=1, ge=1, le=10, description="Discovery priority (1-10)")
    scan_ports: Optional[List[int]] = Field(None, description="Specific ports to scan")
    exclude_hosts: Optional[List[str]] = Field(None, description="Hosts to exclude from scanning")
    
    @validator('network')
    def validate_network(cls, v):
        """Validate network CIDR format."""
        try:
            ipaddress.ip_network(v, strict=False)
        except ipaddress.AddressValueError:
            raise ValueError(f"Invalid network CIDR: {v}")
        return v


class KnownHost(BaseModel):
    """Known host definition in seed inventory."""
    ip: str = Field(..., description="Host IP address")
    hostname: Optional[str] = Field(None, description="Host hostname")
    type: Optional[str] = Field(None, description="Host type (server, workstation, etc.)")
    location: Optional[str] = Field(None, description="Physical location")
    role: Optional[str] = Field(None, description="Host role (compute, storage, etc.)")
    os: Optional[str] = Field(None, description="Operating system")
    credentials: Optional[str] = Field(None, description="SSH key or credential reference")
    ports: Optional[List[int]] = Field(None, description="Known open ports")
    services: Optional[List[str]] = Field(None, description="Known services")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('ip')
    def validate_ip(cls, v):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ipaddress.AddressValueError:
            raise ValueError(f"Invalid IP address: {v}")
        return v


class CredentialDefinition(BaseModel):
    """Credential definition for accessing hosts."""
    name: str = Field(..., description="Credential name/reference")
    type: str = Field(..., description="Credential type (ssh_key, password, etc.)")
    username: Optional[str] = Field(None, description="Username")
    ssh_key_path: Optional[Path] = Field(None, description="Path to SSH private key")
    description: Optional[str] = Field(None, description="Credential description")


class DiscoveryHints(BaseModel):
    """Discovery hints and preferences."""
    preferred_discovery_methods: Optional[List[str]] = Field(
        default=['ping', 'port_scan', 'ssh'],
        description="Preferred discovery methods in order"
    )
    network_timeout: Optional[int] = Field(default=30, ge=1, le=300)
    parallel_scan_limit: Optional[int] = Field(default=50, ge=1, le=500)
    enable_os_detection: Optional[bool] = Field(default=True)
    enable_service_detection: Optional[bool] = Field(default=True)
    enable_hardware_detection: Optional[bool] = Field(default=True)
    custom_nmap_args: Optional[str] = Field(None, description="Custom nmap arguments")


class SeedInventory(BaseModel):
    """Complete seed inventory specification."""
    version: str = Field(default="1.0", description="Seed inventory format version")
    name: Optional[str] = Field(None, description="Infrastructure name")
    description: Optional[str] = Field(None, description="Infrastructure description")
    
    networks: List[NetworkDefinition] = Field(default_factory=list, description="Networks to scan")
    known_hosts: List[KnownHost] = Field(default_factory=list, description="Pre-known hosts")
    credentials: Optional[List[CredentialDefinition]] = Field(default_factory=list, description="Access credentials")
    discovery_hints: Optional[DiscoveryHints] = Field(default_factory=DiscoveryHints, description="Discovery preferences")
    
    tags: Optional[Dict[str, str]] = Field(None, description="Global tags/metadata")
    
    @validator('networks', 'known_hosts')
    def must_have_targets(cls, v, values, field):
        """Ensure at least one discovery target is defined."""
        networks = values.get('networks', []) if field.name != 'networks' else v
        known_hosts = values.get('known_hosts', []) if field.name != 'known_hosts' else v
        
        if not networks and not known_hosts:
            raise ValueError("Must specify at least one network or known host for discovery")
        return v


class SeedParser:
    """Parser and validator for seed inventory files."""
    
    def __init__(self):
        """Initialize seed parser."""
        self.logger = get_logger(f"{__name__}.SeedParser")
    
    def parse_seed_file(self, seed_file: Path) -> Dict[str, Any]:
        """
        Parse and validate seed inventory file.
        
        Args:
            seed_file: Path to seed inventory YAML file
            
        Returns:
            Parsed and validated seed data as dictionary
            
        Raises:
            FileNotFoundError: If seed file doesn't exist
            ValidationError: If seed file format is invalid
            yaml.YAMLError: If YAML parsing fails
        """
        self.logger.info(f"Parsing seed inventory file: {seed_file}")
        
        if not seed_file.exists():
            raise FileNotFoundError(f"Seed inventory file not found: {seed_file}")
        
        # Load YAML content
        try:
            with open(seed_file, 'r') as f:
                raw_data = yaml.safe_load(f)
            
            if not raw_data:
                raise ValueError("Seed inventory file is empty")
                
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {seed_file}: {e}")
            raise
        
        # Validate against schema
        try:
            seed_inventory = SeedInventory(**raw_data)
            self.logger.info(f"Successfully parsed seed inventory with "
                           f"{len(seed_inventory.networks)} networks and "
                           f"{len(seed_inventory.known_hosts)} known hosts")
            
            # Convert to dictionary for compatibility
            return seed_inventory.dict()
            
        except ValidationError as e:
            self.logger.error(f"Seed inventory validation failed: {e}")
            raise
    
    def validate_seed_data(self, seed_data: Dict[str, Any]) -> bool:
        """
        Validate seed data structure.
        
        Args:
            seed_data: Seed inventory data dictionary
            
        Returns:
            True if valid, raises ValidationError if not
        """
        try:
            SeedInventory(**seed_data)
            return True
        except ValidationError as e:
            self.logger.error(f"Seed data validation failed: {e}")
            raise
    
    def create_sample_seed_file(self, output_path: Path) -> Path:
        """
        Create a sample seed inventory file with examples.
        
        Args:
            output_path: Path where to create the sample file
            
        Returns:
            Path to created sample file
        """
        self.logger.info(f"Creating sample seed inventory at: {output_path}")
        
        sample_seed = {
            'version': '1.0',
            'name': 'Homelab Infrastructure',
            'description': 'Primary homelab infrastructure discovery seed',
            
            'networks': [
                {
                    'network': '192.168.1.0/24',
                    'name': 'Main Network',
                    'location': 'Home Lab',
                    'discovery_priority': 1,
                    'scan_ports': [22, 80, 443, 3389, 5900],
                    'exclude_hosts': ['192.168.1.1', '192.168.1.255']
                },
                {
                    'network': '10.0.0.0/24',
                    'name': 'Management Network',
                    'location': 'Home Lab',
                    'vlan_id': 100,
                    'discovery_priority': 2
                }
            ],
            
            'known_hosts': [
                {
                    'ip': '192.168.1.10',
                    'hostname': 'proxmox-host',
                    'type': 'hypervisor',
                    'location': 'Home Lab',
                    'role': 'compute',
                    'os': 'Proxmox VE',
                    'services': ['ssh', 'https'],
                    'metadata': {
                        'cluster_member': True,
                        'gpu_passthrough': True
                    }
                },
                {
                    'ip': '192.168.1.20',
                    'hostname': 'nas-server',
                    'type': 'storage',
                    'location': 'Home Lab',
                    'role': 'storage',
                    'os': 'TrueNAS SCALE',
                    'services': ['ssh', 'nfs', 'smb', 'https']
                },
                {
                    'ip': '192.168.1.30',
                    'hostname': 'k3s-master',
                    'type': 'server',
                    'location': 'Home Lab',
                    'role': 'k8s_master',
                    'os': 'Ubuntu 22.04',
                    'services': ['ssh', 'k3s-api']
                }
            ],
            
            'credentials': [
                {
                    'name': 'homelab_ssh',
                    'type': 'ssh_key',
                    'username': 'admin',
                    'ssh_key_path': '~/.ssh/homelab_rsa',
                    'description': 'Main SSH key for homelab access'
                }
            ],
            
            'discovery_hints': {
                'preferred_discovery_methods': ['ping', 'port_scan', 'ssh', 'snmp'],
                'network_timeout': 30,
                'parallel_scan_limit': 100,
                'enable_os_detection': True,
                'enable_service_detection': True,
                'enable_hardware_detection': True,
                'custom_nmap_args': '-sS -O --version-detection'
            },
            
            'tags': {
                'environment': 'homelab',
                'owner': 'admin',
                'created_by': 'automation_orchestrator'
            }
        }
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write sample file
        with open(output_path, 'w') as f:
            yaml.dump(sample_seed, f, default_flow_style=False, indent=2, sort_keys=False)
        
        self.logger.info(f"Sample seed inventory created at: {output_path}")
        return output_path
    
    def get_networks_for_discovery(self, seed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract network definitions for discovery, sorted by priority.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of network definitions sorted by discovery priority
        """
        networks = seed_data.get('networks', [])
        
        # Sort by discovery priority (lower number = higher priority)
        sorted_networks = sorted(networks, key=lambda x: x.get('discovery_priority', 999))
        
        self.logger.debug(f"Found {len(sorted_networks)} networks for discovery")
        return sorted_networks
    
    def get_known_hosts_for_discovery(self, seed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract known hosts for discovery.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of known host definitions
        """
        known_hosts = seed_data.get('known_hosts', [])
        
        self.logger.debug(f"Found {len(known_hosts)} known hosts for discovery")
        return known_hosts
    
    def get_discovery_hints(self, seed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract discovery hints and preferences.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            Discovery hints dictionary
        """
        return seed_data.get('discovery_hints', {})
    
    def merge_seed_files(self, seed_files: List[Path]) -> Dict[str, Any]:
        """
        Merge multiple seed inventory files into one.
        
        Args:
            seed_files: List of seed file paths to merge
            
        Returns:
            Merged seed inventory data
        """
        self.logger.info(f"Merging {len(seed_files)} seed inventory files")
        
        merged_data = {
            'version': '1.0',
            'name': 'Merged Infrastructure',
            'networks': [],
            'known_hosts': [],
            'credentials': [],
            'tags': {}
        }
        
        for seed_file in seed_files:
            try:
                seed_data = self.parse_seed_file(seed_file)
                
                # Merge networks (avoid duplicates by CIDR)
                existing_networks = {net.get('network') for net in merged_data['networks']}
                for network in seed_data.get('networks', []):
                    if network.get('network') not in existing_networks:
                        merged_data['networks'].append(network)
                
                # Merge known hosts (avoid duplicates by IP)
                existing_ips = {host.get('ip') for host in merged_data['known_hosts']}
                for host in seed_data.get('known_hosts', []):
                    if host.get('ip') not in existing_ips:
                        merged_data['known_hosts'].append(host)
                
                # Merge credentials (avoid duplicates by name)
                existing_creds = {cred.get('name') for cred in merged_data['credentials']}
                for cred in seed_data.get('credentials', []):
                    if cred.get('name') not in existing_creds:
                        merged_data['credentials'].append(cred)
                
                # Merge tags
                merged_data['tags'].update(seed_data.get('tags', {}))
                
            except Exception as e:
                self.logger.warning(f"Failed to merge seed file {seed_file}: {e}")
        
        self.logger.info(f"Merged seed inventory contains {len(merged_data['networks'])} networks "
                        f"and {len(merged_data['known_hosts'])} known hosts")
        
        return merged_data