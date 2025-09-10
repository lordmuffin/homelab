"""
Network scanner for automated asset discovery.

Implements Feature 2: Automated Asset Discovery
User Story 1: As a System Administrator, I want the orchestrator to automatically scan my network
so that I can discover all active devices without having to track them manually.
"""

import asyncio
import ipaddress
import socket
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import subprocess
import nmap
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.config_manager import DiscoveryConfig
from ..core.logger import get_logger

logger = get_logger(__name__)


class NetworkScanner:
    """Network scanner for discovering active hosts and basic information."""
    
    def __init__(self, config: DiscoveryConfig):
        """
        Initialize network scanner.
        
        Args:
            config: Discovery configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.NetworkScanner")
        self.nm = nmap.PortScanner()
    
    async def scan_network(self, network_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scan a network for active hosts.
        
        Args:
            network_definition: Network definition from seed inventory
            
        Returns:
            List of discovered host assets
        """
        network_cidr = network_definition['network']
        network_name = network_definition.get('name', network_cidr)
        
        self.logger.info(f"Scanning network: {network_name} ({network_cidr})")
        
        try:
            # Parse network
            network = ipaddress.ip_network(network_cidr, strict=False)
            
            # Get scan parameters
            scan_ports = network_definition.get('scan_ports', self.config.default_ports)
            exclude_hosts = network_definition.get('exclude_hosts', [])
            
            # Build exclude list
            exclude_ips = set()
            for exclude_ip in exclude_hosts:
                try:
                    exclude_ips.add(ipaddress.ip_address(exclude_ip))
                except ipaddress.AddressValueError:
                    self.logger.warning(f"Invalid exclude IP: {exclude_ip}")
            
            # Discover active hosts
            active_hosts = await self._discover_active_hosts(network, exclude_ips)
            
            # Perform detailed scanning on active hosts
            detailed_assets = await self._detailed_host_scan(
                active_hosts, scan_ports, network_definition
            )
            
            self.logger.info(f"Network scan completed. Found {len(detailed_assets)} active hosts "
                           f"in {network_name}")
            
            return detailed_assets
            
        except Exception as e:
            self.logger.error(f"Network scan failed for {network_name}: {e}")
            return []
    
    async def _discover_active_hosts(
        self, 
        network: ipaddress.IPv4Network, 
        exclude_ips: Set[ipaddress.IPv4Address]
    ) -> List[ipaddress.IPv4Address]:
        """
        Discover active hosts in network using ping sweep.
        
        Args:
            network: Network to scan
            exclude_ips: IPs to exclude from scanning
            
        Returns:
            List of active IP addresses
        """
        active_hosts = []
        
        # Use ThreadPoolExecutor for parallel ping scanning
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_scans) as executor:
            # Submit ping tasks for all hosts in network
            ping_tasks = {}
            
            for ip in network.hosts():
                if ip in exclude_ips:
                    continue
                
                task = executor.submit(self._ping_host, str(ip))
                ping_tasks[task] = ip
            
            # Collect results
            for task in as_completed(ping_tasks, timeout=self.config.network_timeout):
                ip = ping_tasks[task]
                try:
                    is_active = task.result()
                    if is_active:
                        active_hosts.append(ip)
                        self.logger.debug(f"Host {ip} is active")
                except Exception as e:
                    self.logger.debug(f"Ping failed for {ip}: {e}")
        
        self.logger.info(f"Ping sweep found {len(active_hosts)} active hosts")
        return active_hosts
    
    def _ping_host(self, ip: str) -> bool:
        """
        Ping a single host to check if it's active.
        
        Args:
            ip: IP address to ping
            
        Returns:
            True if host responds to ping
        """
        try:
            # Use system ping command for reliability
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', ip],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    async def _detailed_host_scan(
        self, 
        active_hosts: List[ipaddress.IPv4Address], 
        scan_ports: List[int],
        network_definition: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Perform detailed scanning on active hosts.
        
        Args:
            active_hosts: List of active IP addresses
            scan_ports: Ports to scan
            network_definition: Network definition from seed
            
        Returns:
            List of detailed host assets
        """
        assets = []
        
        # Convert IPs to strings for nmap
        host_list = [str(ip) for ip in active_hosts]
        
        if not host_list:
            return assets
        
        try:
            # Prepare port string for nmap
            port_string = ','.join(map(str, scan_ports))
            
            # Build nmap arguments
            nmap_args = [
                '-sS',  # SYN scan
                '-O',   # OS detection
                '-sV',  # Service version detection
                '--host-timeout', f'{self.config.port_scan_timeout}s',
                f'--max-parallelism={min(self.config.max_parallel_scans, 50)}'
            ]
            
            # Add custom arguments if specified
            custom_args = self.config.nmap_arguments
            if custom_args:
                nmap_args.extend(custom_args.split())
            
            self.logger.info(f"Performing detailed scan of {len(host_list)} hosts")
            
            # Perform nmap scan
            scan_result = self.nm.scan(
                hosts=' '.join(host_list),
                ports=port_string,
                arguments=' '.join(nmap_args)
            )
            
            # Process results
            for host_ip in self.nm.all_hosts():
                try:
                    host_asset = await self._process_host_scan_result(
                        host_ip, network_definition
                    )
                    if host_asset:
                        assets.append(host_asset)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process scan result for {host_ip}: {e}")
            
        except Exception as e:
            self.logger.error(f"Detailed host scan failed: {e}")
            
            # Fallback to basic host information
            for ip in active_hosts:
                assets.append({
                    'ip': str(ip),
                    'hostname': str(ip),
                    'source': 'ping_only',
                    'discovered_at': datetime.now().isoformat(),
                    'network_name': network_definition.get('name'),
                    'location': network_definition.get('location'),
                    'vlan_id': network_definition.get('vlan_id')
                })
        
        return assets
    
    async def _process_host_scan_result(
        self, 
        host_ip: str, 
        network_definition: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process nmap scan result for a single host.
        
        Args:
            host_ip: Host IP address
            network_definition: Network definition from seed
            
        Returns:
            Host asset dictionary or None if processing failed
        """
        try:
            host_info = self.nm[host_ip]
            
            # Basic host information
            asset = {
                'ip': host_ip,
                'hostname': host_info.hostname() or host_ip,
                'source': 'network_scan',
                'discovered_at': datetime.now().isoformat(),
                'network_name': network_definition.get('name'),
                'location': network_definition.get('location'),
                'vlan_id': network_definition.get('vlan_id')
            }
            
            # Host state
            state = host_info.state()
            asset['state'] = state
            
            if state != 'up':
                return None
            
            # OS detection
            if 'osmatch' in host_info:
                os_matches = host_info['osmatch']
                if os_matches:
                    best_match = os_matches[0]
                    asset['os'] = best_match.get('name', 'Unknown')
                    asset['os_accuracy'] = best_match.get('accuracy', 0)
            
            # Protocol information
            protocols = host_info.all_protocols()
            asset['protocols'] = protocols
            
            # Port scanning results
            open_ports = []
            services = []
            
            for protocol in protocols:
                ports = host_info[protocol].keys()
                
                for port in ports:
                    port_info = host_info[protocol][port]
                    port_state = port_info['state']
                    
                    if port_state == 'open':
                        open_ports.append({
                            'port': port,
                            'protocol': protocol,
                            'state': port_state
                        })
                        
                        # Service information
                        service_name = port_info.get('name', 'unknown')
                        service_product = port_info.get('product', '')
                        service_version = port_info.get('version', '')
                        
                        service_info = {
                            'name': service_name,
                            'port': port,
                            'protocol': protocol,
                            'product': service_product,
                            'version': service_version,
                            'state': port_state
                        }
                        
                        # Add extra info if available
                        if 'extrainfo' in port_info:
                            service_info['extra_info'] = port_info['extrainfo']
                        
                        services.append(service_info)
            
            asset['open_ports'] = open_ports
            asset['services'] = services
            asset['port_count'] = len(open_ports)
            
            # Host classification based on open ports and services
            asset['classification'] = self._classify_host(services, open_ports)
            
            # MAC address if available
            if 'addresses' in host_info:
                addresses = host_info['addresses']
                if 'mac' in addresses:
                    asset['mac_address'] = addresses['mac']
            
            return asset
            
        except Exception as e:
            self.logger.warning(f"Failed to process scan result for {host_ip}: {e}")
            return None
    
    def _classify_host(self, services: List[Dict[str, Any]], open_ports: List[Dict[str, Any]]) -> str:
        """
        Classify host based on running services and open ports.
        
        Args:
            services: List of detected services
            open_ports: List of open ports
            
        Returns:
            Host classification string
        """
        service_names = {service['name'].lower() for service in services}
        port_numbers = {port['port'] for port in open_ports}
        
        # Web servers
        if any(service in service_names for service in ['http', 'https', 'apache', 'nginx']):
            return 'web_server'
        
        # Database servers
        if any(service in service_names for service in ['mysql', 'postgresql', 'mongodb', 'redis']):
            return 'database_server'
        
        # Network infrastructure
        if any(service in service_names for service in ['snmp', 'telnet']) or 161 in port_numbers:
            return 'network_device'
        
        # Virtualization
        if any(port in port_numbers for port in [8006, 5900, 5901]):  # Proxmox, VNC
            return 'hypervisor'
        
        # Kubernetes/Container platforms
        if any(port in port_numbers for port in [6443, 10250, 2379, 2380]):
            return 'k8s_node'
        
        # SSH servers (likely Linux/Unix)
        if 22 in port_numbers or 'ssh' in service_names:
            return 'server'
        
        # Windows systems
        if any(port in port_numbers for port in [135, 139, 445, 3389]):
            return 'windows_host'
        
        # Default classification
        if len(open_ports) > 5:
            return 'server'
        elif len(open_ports) > 0:
            return 'host'
        else:
            return 'unknown'
    
    async def scan_single_host(self, ip: str, ports: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """
        Scan a single host for detailed information.
        
        Args:
            ip: IP address to scan
            ports: Optional list of ports to scan
            
        Returns:
            Host asset dictionary or None if scan failed
        """
        self.logger.info(f"Scanning single host: {ip}")
        
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
            
            # Check if host is active
            if not self._ping_host(ip):
                self.logger.info(f"Host {ip} is not responding to ping")
                return None
            
            # Use default ports if none specified
            if ports is None:
                ports = self.config.default_ports
            
            # Create network definition for compatibility
            network_definition = {
                'name': f'single_host_{ip}',
                'scan_ports': ports
            }
            
            # Perform detailed scan
            results = await self._detailed_host_scan([ipaddress.ip_address(ip)], ports, network_definition)
            
            return results[0] if results else None
            
        except Exception as e:
            self.logger.error(f"Single host scan failed for {ip}: {e}")
            return None
    
    async def get_network_summary(self, network_cidr: str) -> Dict[str, Any]:
        """
        Get summary information about a network.
        
        Args:
            network_cidr: Network CIDR to analyze
            
        Returns:
            Network summary dictionary
        """
        try:
            network = ipaddress.ip_network(network_cidr, strict=False)
            
            summary = {
                'network': network_cidr,
                'network_address': str(network.network_address),
                'broadcast_address': str(network.broadcast_address),
                'netmask': str(network.netmask),
                'num_addresses': network.num_addresses,
                'is_private': network.is_private,
                'is_multicast': network.is_multicast,
                'is_reserved': network.is_reserved,
                'supernet': str(network.supernet()),
                'subnets': [str(subnet) for subnet in network.subnets(prefixlen_diff=1)][:5]  # First 5 subnets
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get network summary for {network_cidr}: {e}")
            return {'error': str(e)}
    
    def validate_network_accessibility(self, network_cidr: str) -> bool:
        """
        Validate that the network is accessible for scanning.
        
        Args:
            network_cidr: Network CIDR to validate
            
        Returns:
            True if network appears accessible
        """
        try:
            network = ipaddress.ip_network(network_cidr, strict=False)
            
            # Check if network is too large for practical scanning
            if network.num_addresses > 65536:  # /16 or larger
                self.logger.warning(f"Network {network_cidr} is very large ({network.num_addresses} addresses)")
                return False
            
            # Try to ping a few hosts to test accessibility
            test_hosts = list(network.hosts())[:3]  # Test first 3 hosts
            
            for host in test_hosts:
                if self._ping_host(str(host)):
                    return True
            
            self.logger.warning(f"No hosts responding in network {network_cidr}")
            return False
            
        except Exception as e:
            self.logger.error(f"Network validation failed for {network_cidr}: {e}")
            return False