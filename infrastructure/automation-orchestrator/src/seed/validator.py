"""
Additional validation utilities for seed inventory files.
"""

import ipaddress
from typing import Dict, List, Any, Set, Tuple
from ..core.logger import get_logger

logger = get_logger(__name__)


class SeedValidator:
    """Advanced validation for seed inventory data beyond basic schema validation."""
    
    def __init__(self):
        """Initialize validator."""
        self.logger = get_logger(f"{__name__}.SeedValidator")
    
    def validate_network_overlaps(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Check for overlapping network definitions.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings about overlapping networks
        """
        warnings = []
        networks = seed_data.get('networks', [])
        
        if len(networks) < 2:
            return warnings
        
        # Convert networks to ipaddress objects for comparison
        network_objects = []
        for i, network_def in enumerate(networks):
            try:
                network = ipaddress.ip_network(network_def['network'], strict=False)
                network_objects.append((i, network, network_def))
            except ipaddress.AddressValueError:
                warnings.append(f"Invalid network CIDR in position {i}: {network_def['network']}")
        
        # Check for overlaps
        for i, (idx1, net1, def1) in enumerate(network_objects):
            for j, (idx2, net2, def2) in enumerate(network_objects[i+1:], i+1):
                if net1.overlaps(net2):
                    name1 = def1.get('name', net1.compressed)
                    name2 = def2.get('name', net2.compressed)
                    warnings.append(f"Networks overlap: '{name1}' ({net1.compressed}) "
                                  f"and '{name2}' ({net2.compressed})")
        
        return warnings
    
    def validate_known_host_consistency(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Validate known hosts for consistency and conflicts.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        known_hosts = seed_data.get('known_hosts', [])
        
        # Check for duplicate IPs
        ip_to_hosts = {}
        for host in known_hosts:
            ip = host.get('ip')
            if not ip:
                continue
            
            if ip in ip_to_hosts:
                existing_hostname = ip_to_hosts[ip].get('hostname', 'unnamed')
                current_hostname = host.get('hostname', 'unnamed')
                warnings.append(f"Duplicate IP {ip} found for hosts: "
                              f"'{existing_hostname}' and '{current_hostname}'")
            else:
                ip_to_hosts[ip] = host
        
        # Check for duplicate hostnames
        hostname_to_hosts = {}
        for host in known_hosts:
            hostname = host.get('hostname')
            if not hostname:
                continue
            
            if hostname in hostname_to_hosts:
                existing_ip = hostname_to_hosts[hostname].get('ip', 'unknown')
                current_ip = host.get('ip', 'unknown')
                warnings.append(f"Duplicate hostname '{hostname}' found for IPs: "
                              f"{existing_ip} and {current_ip}")
            else:
                hostname_to_hosts[hostname] = host
        
        return warnings
    
    def validate_network_host_consistency(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Check if known hosts are within defined networks.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        networks = seed_data.get('networks', [])
        known_hosts = seed_data.get('known_hosts', [])
        
        if not networks:
            return warnings
        
        # Parse networks
        network_objects = []
        for network_def in networks:
            try:
                network = ipaddress.ip_network(network_def['network'], strict=False)
                network_objects.append((network, network_def))
            except ipaddress.AddressValueError:
                continue
        
        # Check each known host
        for host in known_hosts:
            ip_str = host.get('ip')
            if not ip_str:
                continue
            
            try:
                host_ip = ipaddress.ip_address(ip_str)
                
                # Check if host is in any defined network
                in_network = False
                for network, network_def in network_objects:
                    if host_ip in network:
                        in_network = True
                        break
                
                if not in_network:
                    hostname = host.get('hostname', 'unnamed')
                    warnings.append(f"Known host '{hostname}' ({ip_str}) is not within "
                                  f"any defined network range")
                
            except ipaddress.AddressValueError:
                hostname = host.get('hostname', 'unnamed')
                warnings.append(f"Invalid IP address for host '{hostname}': {ip_str}")
        
        return warnings
    
    def validate_credential_references(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Validate credential references in known hosts.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        credentials = seed_data.get('credentials', [])
        known_hosts = seed_data.get('known_hosts', [])
        
        # Get available credential names
        available_credentials = {cred.get('name') for cred in credentials if cred.get('name')}
        
        # Check known host credential references
        for host in known_hosts:
            cred_ref = host.get('credentials')
            if cred_ref and cred_ref not in available_credentials:
                hostname = host.get('hostname', host.get('ip', 'unnamed'))
                warnings.append(f"Host '{hostname}' references unknown credential: '{cred_ref}'")
        
        return warnings
    
    def validate_port_ranges(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Validate port ranges in network and host definitions.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        def validate_ports(ports: List[int], context: str) -> List[str]:
            """Validate a list of ports."""
            port_warnings = []
            for port in ports:
                if not isinstance(port, int) or port < 1 or port > 65535:
                    port_warnings.append(f"Invalid port {port} in {context}")
            return port_warnings
        
        # Check network scan ports
        for network in seed_data.get('networks', []):
            ports = network.get('scan_ports', [])
            if ports:
                network_name = network.get('name', network.get('network', 'unnamed'))
                warnings.extend(validate_ports(ports, f"network '{network_name}'"))
        
        # Check known host ports
        for host in known_hosts:
            ports = host.get('ports', [])
            if ports:
                hostname = host.get('hostname', host.get('ip', 'unnamed'))
                warnings.extend(validate_ports(ports, f"host '{hostname}'"))
        
        return warnings
    
    def validate_discovery_hints(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Validate discovery hints configuration.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of validation warnings
        """
        warnings = []
        hints = seed_data.get('discovery_hints', {})
        
        # Check discovery methods
        valid_methods = {'ping', 'port_scan', 'ssh', 'snmp', 'http', 'https', 'arp'}
        preferred_methods = hints.get('preferred_discovery_methods', [])
        
        for method in preferred_methods:
            if method not in valid_methods:
                warnings.append(f"Unknown discovery method: '{method}'. "
                              f"Valid methods: {', '.join(sorted(valid_methods))}")
        
        # Check timeout values
        network_timeout = hints.get('network_timeout')
        if network_timeout is not None:
            if not isinstance(network_timeout, int) or network_timeout < 1 or network_timeout > 300:
                warnings.append(f"Invalid network_timeout: {network_timeout}. Must be 1-300 seconds")
        
        # Check parallel scan limit
        parallel_limit = hints.get('parallel_scan_limit')
        if parallel_limit is not None:
            if not isinstance(parallel_limit, int) or parallel_limit < 1 or parallel_limit > 1000:
                warnings.append(f"Invalid parallel_scan_limit: {parallel_limit}. Must be 1-1000")
        
        return warnings
    
    def comprehensive_validation(self, seed_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Run comprehensive validation on seed data.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            # Collect all validation warnings
            warnings.extend(self.validate_network_overlaps(seed_data))
            warnings.extend(self.validate_known_host_consistency(seed_data))
            warnings.extend(self.validate_network_host_consistency(seed_data))
            warnings.extend(self.validate_credential_references(seed_data))
            warnings.extend(self.validate_port_ranges(seed_data))
            warnings.extend(self.validate_discovery_hints(seed_data))
            
            # Check for critical errors that would prevent discovery
            networks = seed_data.get('networks', [])
            known_hosts = seed_data.get('known_hosts', [])
            
            if not networks and not known_hosts:
                errors.append("No networks or known hosts defined for discovery")
            
            # Count duplicates that would cause conflicts
            duplicate_ips = self._count_duplicate_ips(seed_data)
            if duplicate_ips > 0:
                errors.append(f"Found {duplicate_ips} duplicate IP addresses that must be resolved")
            
            is_valid = len(errors) == 0
            
            self.logger.info(f"Validation completed: {'PASS' if is_valid else 'FAIL'}, "
                           f"{len(warnings)} warnings, {len(errors)} errors")
            
            return is_valid, errors, warnings
            
        except Exception as e:
            self.logger.error(f"Validation failed with exception: {e}")
            return False, [f"Validation exception: {e}"], warnings
    
    def _count_duplicate_ips(self, seed_data: Dict[str, Any]) -> int:
        """Count duplicate IP addresses in known hosts."""
        known_hosts = seed_data.get('known_hosts', [])
        seen_ips = set()
        duplicates = 0
        
        for host in known_hosts:
            ip = host.get('ip')
            if ip:
                if ip in seen_ips:
                    duplicates += 1
                else:
                    seen_ips.add(ip)
        
        return duplicates
    
    def suggest_fixes(self, seed_data: Dict[str, Any]) -> List[str]:
        """
        Suggest fixes for common validation issues.
        
        Args:
            seed_data: Parsed seed inventory data
            
        Returns:
            List of suggested fixes
        """
        suggestions = []
        
        # Run validation to identify issues
        is_valid, errors, warnings = self.comprehensive_validation(seed_data)
        
        if not is_valid:
            suggestions.append("Critical errors found that must be fixed:")
            for error in errors:
                suggestions.append(f"  - {error}")
        
        if warnings:
            suggestions.append("Recommended improvements:")
            for warning in warnings:
                suggestions.append(f"  - {warning}")
        
        # General suggestions
        networks = seed_data.get('networks', [])
        known_hosts = seed_data.get('known_hosts', [])
        
        if len(networks) == 0 and len(known_hosts) > 0:
            suggestions.append("Consider adding network ranges to discover additional hosts")
        
        if len(known_hosts) == 0 and len(networks) > 0:
            suggestions.append("Consider adding known critical hosts for reliable discovery")
        
        discovery_hints = seed_data.get('discovery_hints', {})
        if not discovery_hints:
            suggestions.append("Consider adding discovery_hints section to optimize scanning")
        
        credentials = seed_data.get('credentials', [])
        if not credentials and known_hosts:
            suggestions.append("Consider defining credentials for authenticated host discovery")
        
        return suggestions