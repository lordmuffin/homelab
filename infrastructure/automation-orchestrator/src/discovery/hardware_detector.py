"""
Hardware detector for identifying GPU and specialized hardware.

Implements Feature 2: Automated Asset Discovery
User Story 2: As a System Administrator, I want the orchestrator to detect specific hardware, 
like the presence of NVIDIA or AMD GPUs, so that nodes can be automatically classified for 
specialized roles like AI or gaming.
"""

import asyncio
import json
import subprocess
from typing import Dict, List, Any, Optional, Union
import re
import psutil
import socket

from ..core.config_manager import DiscoveryConfig
from ..core.logger import get_logger

logger = get_logger(__name__)


class HardwareDetector:
    """Hardware detector for identifying GPUs and specialized hardware."""
    
    def __init__(self, config: DiscoveryConfig):
        """
        Initialize hardware detector.
        
        Args:
            config: Discovery configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.HardwareDetector")
    
    async def detect_hardware(self, ip: str) -> Dict[str, Any]:
        """
        Detect hardware information for a host.
        
        Args:
            ip: Host IP address
            
        Returns:
            Dictionary containing hardware information
        """
        self.logger.debug(f"Detecting hardware for host: {ip}")
        
        hardware_info = {
            'hardware_detection_attempted': True,
            'hardware_detection_time': None,
            'cpu_info': {},
            'memory_info': {},
            'gpu_info': {},
            'storage_info': {},
            'network_info': {},
            'system_info': {}
        }
        
        try:
            # Try SSH-based detection first (most comprehensive)
            ssh_result = await self._detect_via_ssh(ip)
            if ssh_result:
                hardware_info.update(ssh_result)
                hardware_info['detection_method'] = 'ssh'
                return hardware_info
            
            # Try SNMP-based detection
            snmp_result = await self._detect_via_snmp(ip)
            if snmp_result:
                hardware_info.update(snmp_result)
                hardware_info['detection_method'] = 'snmp'
                return hardware_info
            
            # Try WMI for Windows hosts
            wmi_result = await self._detect_via_wmi(ip)
            if wmi_result:
                hardware_info.update(wmi_result)
                hardware_info['detection_method'] = 'wmi'
                return hardware_info
            
            # Basic network-based detection
            network_result = await self._detect_via_network(ip)
            if network_result:
                hardware_info.update(network_result)
                hardware_info['detection_method'] = 'network_inference'
                return hardware_info
            
            hardware_info['detection_method'] = 'none'
            self.logger.debug(f"No hardware detection method succeeded for {ip}")
            
        except Exception as e:
            self.logger.warning(f"Hardware detection failed for {ip}: {e}")
            hardware_info['detection_error'] = str(e)
        
        return hardware_info
    
    async def _detect_via_ssh(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Detect hardware via SSH connection (most comprehensive method).
        
        Args:
            ip: Host IP address
            
        Returns:
            Hardware information dictionary or None if SSH detection failed
        """
        try:
            # This is a placeholder for SSH-based detection
            # In a real implementation, you would:
            # 1. Check for SSH connectivity
            # 2. Execute hardware detection commands
            # 3. Parse the results
            
            # For now, return None to indicate SSH detection not available
            # This would be implemented with paramiko or similar SSH library
            return None
            
        except Exception as e:
            self.logger.debug(f"SSH hardware detection failed for {ip}: {e}")
            return None
    
    async def _detect_via_snmp(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Detect hardware via SNMP (good for network devices and servers).
        
        Args:
            ip: Host IP address
            
        Returns:
            Hardware information dictionary or None if SNMP detection failed
        """
        try:
            # Check if SNMP port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, 161))
            sock.close()
            
            if result != 0:
                return None
            
            # Basic SNMP detection would go here
            # This is a placeholder implementation
            hardware_info = {
                'snmp_detected': True,
                'system_info': {
                    'snmp_available': True
                }
            }
            
            return hardware_info
            
        except Exception as e:
            self.logger.debug(f"SNMP hardware detection failed for {ip}: {e}")
            return None
    
    async def _detect_via_wmi(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Detect hardware via WMI (Windows systems).
        
        Args:
            ip: Host IP address
            
        Returns:
            Hardware information dictionary or None if WMI detection failed
        """
        try:
            # Check if this looks like a Windows system (port 135 or 445 open)
            # This is a placeholder implementation
            return None
            
        except Exception as e:
            self.logger.debug(f"WMI hardware detection failed for {ip}: {e}")
            return None
    
    async def _detect_via_network(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Infer hardware information from network characteristics.
        
        Args:
            ip: Host IP address
            
        Returns:
            Hardware information dictionary or None if network detection failed
        """
        try:
            hardware_info = {}
            
            # Basic network connectivity test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            # Check common ports to infer system type and capabilities
            port_results = {}
            common_ports = [22, 80, 443, 3389, 5900, 8006, 6443]
            
            for port in common_ports:
                try:
                    result = sock.connect_ex((ip, port))
                    port_results[port] = (result == 0)
                except:
                    port_results[port] = False
            
            sock.close()
            
            # Infer system type from open ports
            system_type = self._infer_system_type(port_results)
            if system_type:
                hardware_info['system_info'] = {
                    'inferred_type': system_type,
                    'open_ports': [port for port, is_open in port_results.items() if is_open]
                }
            
            # Try to get hostname for additional clues
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                hardware_info['system_info']['hostname'] = hostname
                
                # Infer hardware from hostname patterns
                gpu_hints = self._extract_gpu_hints_from_hostname(hostname)
                if gpu_hints:
                    hardware_info['gpu_info'] = gpu_hints
                    
            except socket.herror:
                pass
            
            return hardware_info if hardware_info else None
            
        except Exception as e:
            self.logger.debug(f"Network-based hardware detection failed for {ip}: {e}")
            return None
    
    def _infer_system_type(self, port_results: Dict[int, bool]) -> Optional[str]:
        """
        Infer system type from open ports.
        
        Args:
            port_results: Dictionary of port -> is_open
            
        Returns:
            Inferred system type or None
        """
        if port_results.get(8006):  # Proxmox
            return 'proxmox_hypervisor'
        elif port_results.get(6443):  # Kubernetes API
            return 'kubernetes_node'
        elif port_results.get(3389):  # RDP
            return 'windows_server'
        elif port_results.get(22):  # SSH
            return 'linux_server'
        elif port_results.get(80) or port_results.get(443):  # HTTP/HTTPS
            return 'web_server'
        elif port_results.get(5900):  # VNC
            return 'remote_desktop_server'
        
        return None
    
    def _extract_gpu_hints_from_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """
        Extract GPU hints from hostname patterns.
        
        Args:
            hostname: Host hostname
            
        Returns:
            GPU information dictionary or None
        """
        hostname_lower = hostname.lower()
        
        gpu_info = {}
        
        # Look for GPU-related keywords in hostname
        if any(keyword in hostname_lower for keyword in ['gpu', 'cuda', 'nvidia', 'rtx', 'gtx']):
            gpu_info['has_gpu'] = True
            gpu_info['gpu_type'] = 'nvidia'
            gpu_info['detection_source'] = 'hostname_inference'
        elif any(keyword in hostname_lower for keyword in ['amd', 'radeon', 'rx']):
            gpu_info['has_gpu'] = True
            gpu_info['gpu_type'] = 'amd'
            gpu_info['detection_source'] = 'hostname_inference'
        elif any(keyword in hostname_lower for keyword in ['ai', 'ml', 'compute']):
            gpu_info['likely_has_gpu'] = True
            gpu_info['detection_source'] = 'hostname_inference'
        
        # Look for specific GPU model hints
        nvidia_models = re.findall(r'(rtx|gtx)\s?(\d+)', hostname_lower)
        if nvidia_models:
            gpu_info['gpu_model_hint'] = f"{nvidia_models[0][0].upper()} {nvidia_models[0][1]}"
        
        return gpu_info if gpu_info else None
    
    async def detect_local_hardware(self) -> Dict[str, Any]:
        """
        Detect hardware information for the local system.
        
        Returns:
            Comprehensive hardware information for local system
        """
        self.logger.info("Detecting local system hardware")
        
        hardware_info = {
            'detection_method': 'local_system',
            'system_info': {},
            'cpu_info': {},
            'memory_info': {},
            'gpu_info': {},
            'storage_info': {},
            'network_info': {}
        }
        
        try:
            # System information
            hardware_info['system_info'] = {
                'platform': psutil.platform,
                'hostname': socket.gethostname(),
                'boot_time': psutil.boot_time()
            }
            
            # CPU information
            cpu_info = {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
            hardware_info['cpu_info'] = cpu_info
            
            # Memory information
            memory = psutil.virtual_memory()
            hardware_info['memory_info'] = {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # GPU detection
            gpu_info = await self._detect_local_gpus()
            if gpu_info:
                hardware_info['gpu_info'] = gpu_info
            
            # Storage information
            storage_info = []
            for partition in psutil.disk_partitions():
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    storage_info.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': partition_usage.total,
                        'used': partition_usage.used,
                        'free': partition_usage.free,
                        'percent': partition_usage.percent
                    })
                except PermissionError:
                    continue
            hardware_info['storage_info'] = storage_info
            
            # Network information
            network_info = []
            for interface, addresses in psutil.net_if_addrs().items():
                interface_info = {
                    'interface': interface,
                    'addresses': []
                }
                for addr in addresses:
                    interface_info['addresses'].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
                network_info.append(interface_info)
            hardware_info['network_info'] = network_info
            
        except Exception as e:
            self.logger.error(f"Local hardware detection failed: {e}")
            hardware_info['detection_error'] = str(e)
        
        return hardware_info
    
    async def _detect_local_gpus(self) -> Optional[Dict[str, Any]]:
        """
        Detect GPU information on local system.
        
        Returns:
            GPU information dictionary or None if no GPUs detected
        """
        gpu_info = {
            'has_gpu': False,
            'gpu_count': 0,
            'gpus': []
        }
        
        try:
            # Try nvidia-smi first
            nvidia_result = await self._run_nvidia_smi()
            if nvidia_result:
                gpu_info.update(nvidia_result)
                return gpu_info
            
            # Try lspci for basic GPU detection
            lspci_result = await self._run_lspci_gpu_detect()
            if lspci_result:
                gpu_info.update(lspci_result)
                return gpu_info
            
            # Try AMD-specific tools
            amd_result = await self._run_amd_gpu_detect()
            if amd_result:
                gpu_info.update(amd_result)
                return gpu_info
            
        except Exception as e:
            self.logger.debug(f"GPU detection failed: {e}")
        
        return None if not gpu_info['has_gpu'] else gpu_info
    
    async def _run_nvidia_smi(self) -> Optional[Dict[str, Any]]:
        """Run nvidia-smi to detect NVIDIA GPUs."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                gpu_info = {
                    'has_gpu': True,
                    'gpu_type': 'nvidia',
                    'gpus': []
                }
                
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [part.strip() for part in line.split(',')]
                        if len(parts) >= 3:
                            gpu_info['gpus'].append({
                                'name': parts[0],
                                'memory_total': f"{parts[1]} MB",
                                'driver_version': parts[2]
                            })
                
                gpu_info['gpu_count'] = len(gpu_info['gpus'])
                return gpu_info
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        return None
    
    async def _run_lspci_gpu_detect(self) -> Optional[Dict[str, Any]]:
        """Use lspci to detect GPUs."""
        try:
            result = subprocess.run(
                ['lspci', '-nn'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                gpu_info = {
                    'has_gpu': False,
                    'gpus': []
                }
                
                for line in result.stdout.split('\n'):
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['vga', '3d controller', 'display']):
                        gpu_entry = {'name': line.strip()}
                        
                        if 'nvidia' in line_lower:
                            gpu_entry['vendor'] = 'nvidia'
                            gpu_info['gpu_type'] = 'nvidia'
                        elif 'amd' in line_lower or 'ati' in line_lower:
                            gpu_entry['vendor'] = 'amd'
                            gpu_info['gpu_type'] = 'amd'
                        elif 'intel' in line_lower:
                            gpu_entry['vendor'] = 'intel'
                            gpu_info['gpu_type'] = 'intel'
                        
                        gpu_info['gpus'].append(gpu_entry)
                        gpu_info['has_gpu'] = True
                
                gpu_info['gpu_count'] = len(gpu_info['gpus'])
                return gpu_info if gpu_info['has_gpu'] else None
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        return None
    
    async def _run_amd_gpu_detect(self) -> Optional[Dict[str, Any]]:
        """Detect AMD GPUs using rocm-smi or similar tools."""
        try:
            # Try rocm-smi
            result = subprocess.run(
                ['rocm-smi', '--showproductname'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                return {
                    'has_gpu': True,
                    'gpu_type': 'amd',
                    'gpu_count': 1,  # Basic detection
                    'gpus': [{'name': 'AMD GPU detected via rocm-smi'}]
                }
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        return None
    
    def classify_host_by_hardware(self, hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify host based on detected hardware for Ansible grouping.
        
        Args:
            hardware_info: Hardware information dictionary
            
        Returns:
            Classification information for Ansible groups
        """
        classification = {
            'ansible_groups': [],
            'capabilities': [],
            'role_suggestions': []
        }
        
        # GPU-based classification
        gpu_info = hardware_info.get('gpu_info', {})
        if gpu_info.get('has_gpu'):
            classification['ansible_groups'].append('gpu_nodes')
            classification['capabilities'].append('gpu_compute')
            
            gpu_type = gpu_info.get('gpu_type')
            if gpu_type == 'nvidia':
                classification['ansible_groups'].append('nvidia_gpu_nodes')
                classification['capabilities'].append('cuda')
                classification['role_suggestions'].append('ai_compute')
            elif gpu_type == 'amd':
                classification['ansible_groups'].append('amd_gpu_nodes')
                classification['capabilities'].append('rocm')
                classification['role_suggestions'].append('amd_compute')
        
        # CPU-based classification
        cpu_info = hardware_info.get('cpu_info', {})
        logical_cores = cpu_info.get('logical_cores', 0)
        if logical_cores >= 16:
            classification['ansible_groups'].append('high_compute_nodes')
            classification['capabilities'].append('high_cpu')
            classification['role_suggestions'].append('compute_intensive')
        
        # Memory-based classification
        memory_info = hardware_info.get('memory_info', {})
        total_memory = memory_info.get('total', 0)
        if total_memory > 32 * 1024 * 1024 * 1024:  # 32GB
            classification['ansible_groups'].append('high_memory_nodes')
            classification['capabilities'].append('high_memory')
            classification['role_suggestions'].append('memory_intensive')
        
        # Storage-based classification
        storage_info = hardware_info.get('storage_info', [])
        total_storage = sum(disk.get('total', 0) for disk in storage_info)
        if total_storage > 1024 * 1024 * 1024 * 1024:  # 1TB
            classification['ansible_groups'].append('storage_nodes')
            classification['capabilities'].append('high_storage')
            classification['role_suggestions'].append('storage')
        
        # System type classification
        system_info = hardware_info.get('system_info', {})
        inferred_type = system_info.get('inferred_type')
        if inferred_type:
            if 'hypervisor' in inferred_type:
                classification['ansible_groups'].append('hypervisor_nodes')
                classification['role_suggestions'].append('virtualization')
            elif 'kubernetes' in inferred_type:
                classification['ansible_groups'].append('k8s_nodes')
                classification['role_suggestions'].append('container_orchestration')
        
        return classification