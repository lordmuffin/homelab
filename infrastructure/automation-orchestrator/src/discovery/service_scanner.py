"""
Service scanner for detecting running services on discovered hosts.
"""

import asyncio
import socket
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
import subprocess
import re

from ..core.config_manager import DiscoveryConfig
from ..core.logger import get_logger

logger = get_logger(__name__)


class ServiceScanner:
    """Scanner for detecting and cataloging services running on hosts."""
    
    def __init__(self, config: DiscoveryConfig):
        """
        Initialize service scanner.
        
        Args:
            config: Discovery configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.ServiceScanner")
        
        # Common service patterns and their standard ports
        self.service_patterns = {
            'ssh': {'ports': [22], 'protocols': ['tcp']},
            'http': {'ports': [80, 8080, 8000, 3000], 'protocols': ['tcp']},
            'https': {'ports': [443, 8443, 9443], 'protocols': ['tcp']},
            'ftp': {'ports': [21], 'protocols': ['tcp']},
            'telnet': {'ports': [23], 'protocols': ['tcp']},
            'smtp': {'ports': [25, 587], 'protocols': ['tcp']},
            'dns': {'ports': [53], 'protocols': ['tcp', 'udp']},
            'dhcp': {'ports': [67, 68], 'protocols': ['udp']},
            'pop3': {'ports': [110, 995], 'protocols': ['tcp']},
            'imap': {'ports': [143, 993], 'protocols': ['tcp']},
            'snmp': {'ports': [161], 'protocols': ['udp']},
            'ldap': {'ports': [389, 636], 'protocols': ['tcp']},
            'smb': {'ports': [139, 445], 'protocols': ['tcp']},
            'rdp': {'ports': [3389], 'protocols': ['tcp']},
            'vnc': {'ports': [5900, 5901, 5902], 'protocols': ['tcp']},
            'mysql': {'ports': [3306], 'protocols': ['tcp']},
            'postgresql': {'ports': [5432], 'protocols': ['tcp']},
            'mongodb': {'ports': [27017], 'protocols': ['tcp']},
            'redis': {'ports': [6379], 'protocols': ['tcp']},
            'elasticsearch': {'ports': [9200, 9300], 'protocols': ['tcp']},
            'kubernetes': {'ports': [6443, 10250, 2379, 2380], 'protocols': ['tcp']},
            'docker': {'ports': [2375, 2376], 'protocols': ['tcp']},
            'proxmox': {'ports': [8006], 'protocols': ['tcp']},
            'grafana': {'ports': [3000], 'protocols': ['tcp']},
            'prometheus': {'ports': [9090], 'protocols': ['tcp']},
            'node_exporter': {'ports': [9100], 'protocols': ['tcp']},
            'alertmanager': {'ports': [9093], 'protocols': ['tcp']}
        }
    
    async def scan_services(self, ip: str, open_ports: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Scan for services on a host.
        
        Args:
            ip: Host IP address
            open_ports: Optional list of already discovered open ports
            
        Returns:
            List of detected services
        """
        self.logger.debug(f"Scanning services for host: {ip}")
        
        services = []
        
        try:
            # If we have open ports from previous scan, use them
            if open_ports:
                services.extend(await self._analyze_known_ports(ip, open_ports))
            else:
                # Perform our own port scan for common services
                detected_ports = await self._scan_common_service_ports(ip)
                services.extend(await self._analyze_known_ports(ip, detected_ports))
            
            # Enhance with service-specific detection
            enhanced_services = await self._enhance_service_detection(ip, services)
            
            # Add service metadata
            for service in enhanced_services:
                service['discovered_at'] = datetime.now().isoformat()
                service['scanner'] = 'automation_orchestrator'
            
            self.logger.debug(f"Detected {len(enhanced_services)} services on {ip}")
            return enhanced_services
            
        except Exception as e:
            self.logger.error(f"Service scanning failed for {ip}: {e}")
            return []
    
    async def _scan_common_service_ports(self, ip: str) -> List[Dict[str, Any]]:
        """
        Scan common service ports on a host.
        
        Args:
            ip: Host IP address
            
        Returns:
            List of open port dictionaries
        """
        open_ports = []
        
        # Get all unique ports from service patterns
        all_ports = set()
        for service_info in self.service_patterns.values():
            all_ports.update(service_info['ports'])
        
        # Add configured default ports
        all_ports.update(self.config.default_ports)
        
        # Scan ports in parallel
        port_tasks = []
        for port in sorted(all_ports):
            task = asyncio.create_task(self._check_tcp_port(ip, port))
            port_tasks.append((port, task))
        
        # Collect results
        for port, task in port_tasks:
            try:
                is_open = await asyncio.wait_for(task, timeout=self.config.port_scan_timeout)
                if is_open:
                    open_ports.append({
                        'port': port,
                        'protocol': 'tcp',
                        'state': 'open'
                    })
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.debug(f"Port scan error for {ip}:{port}: {e}")
        
        return open_ports
    
    async def _check_tcp_port(self, ip: str, port: int) -> bool:
        """
        Check if a TCP port is open on a host.
        
        Args:
            ip: Host IP address
            port: Port number to check
            
        Returns:
            True if port is open
        """
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def _analyze_known_ports(self, ip: str, open_ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze open ports to identify services.
        
        Args:
            ip: Host IP address
            open_ports: List of open port dictionaries
            
        Returns:
            List of identified services
        """
        services = []
        
        for port_info in open_ports:
            port = port_info.get('port')
            protocol = port_info.get('protocol', 'tcp')
            
            # Find matching services for this port
            matching_services = self._find_services_for_port(port, protocol)
            
            for service_name in matching_services:
                service = {
                    'name': service_name,
                    'port': port,
                    'protocol': protocol,
                    'state': 'detected',
                    'confidence': 'high' if len(matching_services) == 1 else 'medium'
                }
                
                # Add service-specific metadata
                service.update(await self._get_service_metadata(ip, service_name, port))
                
                services.append(service)
            
            # If no known service matches, create generic service entry
            if not matching_services:
                services.append({
                    'name': f'unknown_service_{port}',
                    'port': port,
                    'protocol': protocol,
                    'state': 'detected',
                    'confidence': 'low',
                    'description': f'Unknown service on port {port}'
                })
        
        return services
    
    def _find_services_for_port(self, port: int, protocol: str) -> List[str]:
        """
        Find known services that typically run on a given port.
        
        Args:
            port: Port number
            protocol: Protocol (tcp/udp)
            
        Returns:
            List of service names
        """
        matching_services = []
        
        for service_name, service_info in self.service_patterns.items():
            if port in service_info['ports'] and protocol in service_info['protocols']:
                matching_services.append(service_name)
        
        return matching_services
    
    async def _get_service_metadata(self, ip: str, service_name: str, port: int) -> Dict[str, Any]:
        """
        Get additional metadata for a detected service.
        
        Args:
            ip: Host IP address
            service_name: Name of the service
            port: Port number
            
        Returns:
            Service metadata dictionary
        """
        metadata = {}
        
        try:
            if service_name == 'http':
                metadata.update(await self._probe_http_service(ip, port, False))
            elif service_name == 'https':
                metadata.update(await self._probe_http_service(ip, port, True))
            elif service_name == 'ssh':
                metadata.update(await self._probe_ssh_service(ip, port))
            elif service_name == 'snmp':
                metadata.update(await self._probe_snmp_service(ip, port))
            elif service_name in ['mysql', 'postgresql', 'mongodb']:
                metadata.update(await self._probe_database_service(ip, port, service_name))
            elif service_name == 'kubernetes':
                metadata.update(await self._probe_kubernetes_service(ip, port))
                
        except Exception as e:
            self.logger.debug(f"Service metadata probe failed for {service_name} on {ip}:{port}: {e}")
            metadata['probe_error'] = str(e)
        
        return metadata
    
    async def _probe_http_service(self, ip: str, port: int, is_https: bool) -> Dict[str, Any]:
        """
        Probe HTTP/HTTPS service for additional information.
        
        Args:
            ip: Host IP address
            port: Port number
            is_https: Whether this is HTTPS
            
        Returns:
            HTTP service metadata
        """
        metadata = {'service_type': 'web_server'}
        
        try:
            # Simple HTTP request to get server information
            protocol = 'https' if is_https else 'http'
            url = f"{protocol}://{ip}:{port}/"
            
            # Use curl for reliability (avoids certificate issues with HTTPS)
            curl_args = ['curl', '-I', '-m', '5', '--connect-timeout', '3']
            if is_https:
                curl_args.extend(['-k', '--insecure'])  # Ignore cert errors
            curl_args.append(url)
            
            result = subprocess.run(curl_args, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                headers = result.stdout
                
                # Parse server header
                server_match = re.search(r'Server:\s*([^\r\n]+)', headers, re.IGNORECASE)
                if server_match:
                    metadata['server'] = server_match.group(1).strip()
                
                # Parse other interesting headers
                if 'nginx' in headers.lower():
                    metadata['web_server'] = 'nginx'
                elif 'apache' in headers.lower():
                    metadata['web_server'] = 'apache'
                elif 'iis' in headers.lower():
                    metadata['web_server'] = 'iis'
                
                # Check for specific applications
                if 'proxmox' in headers.lower():
                    metadata['application'] = 'proxmox'
                elif 'grafana' in headers.lower():
                    metadata['application'] = 'grafana'
                elif 'prometheus' in headers.lower():
                    metadata['application'] = 'prometheus'
                
                metadata['http_accessible'] = True
            
        except Exception as e:
            self.logger.debug(f"HTTP probe failed for {ip}:{port}: {e}")
            metadata['http_accessible'] = False
        
        return metadata
    
    async def _probe_ssh_service(self, ip: str, port: int) -> Dict[str, Any]:
        """
        Probe SSH service for version and configuration info.
        
        Args:
            ip: Host IP address
            port: Port number
            
        Returns:
            SSH service metadata
        """
        metadata = {'service_type': 'remote_access'}
        
        try:
            # Connect and get SSH banner
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=5
            )
            
            # Read SSH banner
            banner = await asyncio.wait_for(reader.readline(), timeout=3)
            banner = banner.decode('utf-8', errors='ignore').strip()
            
            if banner.startswith('SSH-'):
                metadata['ssh_version'] = banner
                metadata['ssh_accessible'] = True
                
                # Parse SSH version
                version_parts = banner.split()
                if len(version_parts) > 0:
                    version_info = version_parts[0].replace('SSH-', '')
                    metadata['protocol_version'] = version_info
            
            writer.close()
            await writer.wait_closed()
            
        except Exception as e:
            self.logger.debug(f"SSH probe failed for {ip}:{port}: {e}")
            metadata['ssh_accessible'] = False
        
        return metadata
    
    async def _probe_snmp_service(self, ip: str, port: int) -> Dict[str, Any]:
        """
        Probe SNMP service.
        
        Args:
            ip: Host IP address
            port: Port number
            
        Returns:
            SNMP service metadata
        """
        metadata = {'service_type': 'monitoring'}
        
        # Basic SNMP probe would go here
        # This is a placeholder implementation
        metadata['snmp_detected'] = True
        
        return metadata
    
    async def _probe_database_service(self, ip: str, port: int, db_type: str) -> Dict[str, Any]:
        """
        Probe database service.
        
        Args:
            ip: Host IP address
            port: Port number
            db_type: Database type (mysql, postgresql, mongodb)
            
        Returns:
            Database service metadata
        """
        metadata = {'service_type': 'database', 'database_type': db_type}
        
        # Basic database probing would go here
        # This is a placeholder implementation
        metadata[f'{db_type}_detected'] = True
        
        return metadata
    
    async def _probe_kubernetes_service(self, ip: str, port: int) -> Dict[str, Any]:
        """
        Probe Kubernetes API service.
        
        Args:
            ip: Host IP address
            port: Port number
            
        Returns:
            Kubernetes service metadata
        """
        metadata = {'service_type': 'orchestration', 'platform': 'kubernetes'}
        
        try:
            if port == 6443:  # API server
                # Try to get API version
                curl_args = ['curl', '-k', '-m', '5', f'https://{ip}:{port}/version']
                result = subprocess.run(curl_args, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    try:
                        version_info = json.loads(result.stdout)
                        metadata['kubernetes_version'] = version_info.get('gitVersion', 'unknown')
                        metadata['api_accessible'] = True
                    except json.JSONDecodeError:
                        metadata['api_accessible'] = True  # Accessible but couldn't parse
                else:
                    metadata['api_accessible'] = False
                    
            elif port == 10250:  # Kubelet
                metadata['component'] = 'kubelet'
            elif port in [2379, 2380]:  # etcd
                metadata['component'] = 'etcd'
        
        except Exception as e:
            self.logger.debug(f"Kubernetes probe failed for {ip}:{port}: {e}")
        
        return metadata
    
    async def _enhance_service_detection(self, ip: str, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance service detection with additional analysis.
        
        Args:
            ip: Host IP address
            services: List of detected services
            
        Returns:
            Enhanced services list
        """
        enhanced_services = []
        
        for service in services:
            enhanced_service = service.copy()
            
            # Add service categorization
            service_category = self._categorize_service(service['name'])
            if service_category:
                enhanced_service['category'] = service_category
            
            # Add security assessment
            security_info = self._assess_service_security(service)
            if security_info:
                enhanced_service['security'] = security_info
            
            # Add operational metadata
            operational_info = self._get_operational_metadata(service)
            if operational_info:
                enhanced_service['operational'] = operational_info
            
            enhanced_services.append(enhanced_service)
        
        return enhanced_services
    
    def _categorize_service(self, service_name: str) -> Optional[str]:
        """
        Categorize a service by function.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service category or None
        """
        categories = {
            'web': ['http', 'https'],
            'database': ['mysql', 'postgresql', 'mongodb', 'redis'],
            'remote_access': ['ssh', 'rdp', 'vnc', 'telnet'],
            'file_sharing': ['smb', 'ftp'],
            'messaging': ['smtp', 'pop3', 'imap'],
            'monitoring': ['snmp', 'prometheus', 'grafana', 'node_exporter', 'alertmanager'],
            'infrastructure': ['dns', 'dhcp', 'ldap'],
            'virtualization': ['proxmox'],
            'container_orchestration': ['kubernetes', 'docker']
        }
        
        for category, services in categories.items():
            if service_name in services:
                return category
        
        return None
    
    def _assess_service_security(self, service: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess security implications of a service.
        
        Args:
            service: Service dictionary
            
        Returns:
            Security assessment information
        """
        security_info = {}
        service_name = service['name']
        port = service['port']
        
        # Define security risk levels
        high_risk_services = ['telnet', 'ftp', 'http']  # Unencrypted protocols
        medium_risk_services = ['ssh', 'rdp', 'vnc', 'snmp']  # Authentication-based
        
        if service_name in high_risk_services:
            security_info['risk_level'] = 'high'
            security_info['reason'] = 'Unencrypted protocol'
        elif service_name in medium_risk_services:
            security_info['risk_level'] = 'medium'
            security_info['reason'] = 'Requires proper authentication'
        else:
            security_info['risk_level'] = 'low'
        
        # Check for services on non-standard ports
        standard_ports = self.service_patterns.get(service_name, {}).get('ports', [])
        if port not in standard_ports:
            security_info['non_standard_port'] = True
        
        return security_info
    
    def _get_operational_metadata(self, service: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get operational metadata for a service.
        
        Args:
            service: Service dictionary
            
        Returns:
            Operational metadata
        """
        operational_info = {}
        service_name = service['name']
        
        # Define service criticality
        critical_services = ['kubernetes', 'dns', 'dhcp', 'ssh']
        important_services = ['http', 'https', 'mysql', 'postgresql']
        
        if service_name in critical_services:
            operational_info['criticality'] = 'critical'
        elif service_name in important_services:
            operational_info['criticality'] = 'important'
        else:
            operational_info['criticality'] = 'normal'
        
        # Add monitoring recommendations
        if service_name in ['http', 'https']:
            operational_info['monitoring'] = ['http_check', 'response_time']
        elif service_name in ['mysql', 'postgresql', 'mongodb']:
            operational_info['monitoring'] = ['connection_check', 'query_performance']
        elif service_name == 'kubernetes':
            operational_info['monitoring'] = ['api_health', 'node_status', 'pod_status']
        
        return operational_info
    
    def get_service_summary(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for discovered services.
        
        Args:
            services: List of service dictionaries
            
        Returns:
            Service summary dictionary
        """
        summary = {
            'total_services': len(services),
            'by_category': {},
            'by_risk_level': {},
            'by_protocol': {},
            'critical_services': [],
            'security_concerns': []
        }
        
        for service in services:
            # Count by category
            category = service.get('category', 'unknown')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by risk level
            risk_level = service.get('security', {}).get('risk_level', 'unknown')
            summary['by_risk_level'][risk_level] = summary['by_risk_level'].get(risk_level, 0) + 1
            
            # Count by protocol
            protocol = service.get('protocol', 'unknown')
            summary['by_protocol'][protocol] = summary['by_protocol'].get(protocol, 0) + 1
            
            # Track critical services
            criticality = service.get('operational', {}).get('criticality')
            if criticality == 'critical':
                summary['critical_services'].append({
                    'name': service['name'],
                    'port': service['port']
                })
            
            # Track security concerns
            if risk_level == 'high':
                summary['security_concerns'].append({
                    'service': service['name'],
                    'port': service['port'],
                    'reason': service.get('security', {}).get('reason', 'Unknown risk')
                })
        
        return summary