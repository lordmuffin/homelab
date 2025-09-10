#!/usr/bin/env python3
"""
System Utilities Module for K3s Intelligent Installer

This module provides:
- System information detection
- OS compatibility checking
- Hardware resource validation
- System optimization utilities
- Process management
- Logging utilities
"""

import os
import platform
import subprocess
import logging
import json
import psutil
import distro
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemInfo:
    """System information dataclass"""
    os_name: str
    os_version: str
    architecture: str
    kernel_version: str
    cpu_count: int
    memory_gb: float
    disk_space_gb: float
    hostname: str

@dataclass
class ResourceRequirements:
    """Resource requirements dataclass"""
    min_cpu: int = 2
    min_memory_gb: float = 4.0
    min_disk_gb: float = 20.0

class SystemUtils:
    """System utilities and information gathering"""
    
    def __init__(self):
        self.system_info: Optional[SystemInfo] = None
        self.requirements = ResourceRequirements()
        
    def detect_system(self) -> SystemInfo:
        """Detect system information"""
        logger.info("🔍 Detecting system information...")
        
        try:
            # Get OS information
            os_name = distro.name()
            os_version = distro.version()
            architecture = platform.machine()
            kernel_version = platform.release()
            hostname = platform.node()
            
            # Get hardware information
            cpu_count = psutil.cpu_count(logical=False)
            memory_bytes = psutil.virtual_memory().total
            memory_gb = memory_bytes / (1024**3)
            
            # Get disk space (root partition)
            disk_usage = psutil.disk_usage('/')
            disk_space_gb = disk_usage.total / (1024**3)
            
            self.system_info = SystemInfo(
                os_name=os_name,
                os_version=os_version,
                architecture=architecture,
                kernel_version=kernel_version,
                cpu_count=cpu_count,
                memory_gb=round(memory_gb, 1),
                disk_space_gb=round(disk_space_gb, 1),
                hostname=hostname
            )
            
            logger.info(f"✅ System detected: {os_name} {os_version} on {architecture}")
            logger.info(f"   CPU: {cpu_count} cores, RAM: {memory_gb:.1f}GB, Disk: {disk_space_gb:.1f}GB")
            
            return self.system_info
            
        except Exception as e:
            logger.error(f"❌ Error detecting system: {e}")
            raise
    
    def check_compatibility(self) -> bool:
        """Check if system is compatible with K3s"""
        logger.info("🔍 Checking system compatibility...")
        
        if not self.system_info:
            self.detect_system()
        
        compatible = True
        issues = []
        
        # Check supported operating systems
        supported_os = [
            'ubuntu', 'debian', 'centos', 'rhel', 'fedora', 
            'opensuse', 'sles', 'alpine', 'amazon'
        ]
        
        os_lower = self.system_info.os_name.lower()
        if not any(supported in os_lower for supported in supported_os):
            compatible = False
            issues.append(f"Unsupported OS: {self.system_info.os_name}")
        
        # Check architecture
        supported_archs = ['x86_64', 'amd64', 'arm64', 'aarch64', 'armv7l']
        if self.system_info.architecture not in supported_archs:
            compatible = False
            issues.append(f"Unsupported architecture: {self.system_info.architecture}")
        
        # Check kernel version (minimum 3.10)
        try:
            kernel_parts = self.system_info.kernel_version.split('.')
            major = int(kernel_parts[0])
            minor = int(kernel_parts[1])
            
            if major < 3 or (major == 3 and minor < 10):
                compatible = False
                issues.append(f"Kernel version too old: {self.system_info.kernel_version} (minimum 3.10)")
                
        except (ValueError, IndexError):
            logger.warning(f"⚠️ Could not parse kernel version: {self.system_info.kernel_version}")
        
        if compatible:
            logger.info("✅ System is compatible with K3s")
        else:
            logger.error("❌ System compatibility issues found:")
            for issue in issues:
                logger.error(f"  - {issue}")
        
        return compatible
    
    def check_resources(self) -> bool:
        """Check if system meets resource requirements"""
        logger.info("🔍 Checking resource requirements...")
        
        if not self.system_info:
            self.detect_system()
        
        meets_requirements = True
        issues = []
        
        # Check CPU
        if self.system_info.cpu_count < self.requirements.min_cpu:
            meets_requirements = False
            issues.append(f"Insufficient CPU cores: {self.system_info.cpu_count} < {self.requirements.min_cpu}")
        
        # Check memory
        if self.system_info.memory_gb < self.requirements.min_memory_gb:
            meets_requirements = False
            issues.append(f"Insufficient memory: {self.system_info.memory_gb}GB < {self.requirements.min_memory_gb}GB")
        
        # Check disk space
        if self.system_info.disk_space_gb < self.requirements.min_disk_gb:
            meets_requirements = False
            issues.append(f"Insufficient disk space: {self.system_info.disk_space_gb}GB < {self.requirements.min_disk_gb}GB")
        
        if meets_requirements:
            logger.info("✅ System meets resource requirements")
        else:
            logger.error("❌ Resource requirement issues found:")
            for issue in issues:
                logger.error(f"  - {issue}")
        
        return meets_requirements
    
    def optimize_system(self) -> bool:
        """Apply system optimizations for K3s"""
        logger.info("⚙️ Applying system optimizations...")
        
        success = True
        
        try:
            # Enable required kernel modules
            if not self._load_kernel_modules():
                success = False
            
            # Apply sysctl tuning
            if not self._apply_sysctl_tuning():
                success = False
            
            # Configure firewall
            if not self._configure_firewall():
                success = False
            
            # Set resource limits
            if not self._set_resource_limits():
                success = False
            
            if success:
                logger.info("✅ System optimizations applied")
            else:
                logger.warning("⚠️ Some system optimizations failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error applying system optimizations: {e}")
            return False
    
    def _load_kernel_modules(self) -> bool:
        """Load required kernel modules"""
        logger.info("📦 Loading required kernel modules...")
        
        required_modules = [
            'overlay',      # Container overlay filesystem
            'br_netfilter', # Bridge netfilter for iptables
            'iptable_nat',  # NAT table for iptables
            'iptable_filter' # Filter table for iptables
        ]
        
        try:
            for module in required_modules:
                # Check if module is already loaded
                result = subprocess.run(
                    ["lsmod"], capture_output=True, text=True, timeout=10
                )
                
                if module not in result.stdout:
                    # Load the module
                    result = subprocess.run(
                        ["sudo", "modprobe", module],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if result.returncode != 0:
                        logger.warning(f"⚠️ Could not load kernel module: {module}")
                    else:
                        logger.info(f"✅ Loaded kernel module: {module}")
                
                # Ensure module loads on boot
                modules_load_file = "/etc/modules-load.d/k3s.conf"
                if not os.path.exists(modules_load_file):
                    with open(modules_load_file, 'w') as f:
                        f.write("# Kernel modules required by K3s\n")
                
                with open(modules_load_file, 'r') as f:
                    content = f.read()
                
                if module not in content:
                    with open(modules_load_file, 'a') as f:
                        f.write(f"{module}\n")
            
            logger.info("✅ Kernel modules configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading kernel modules: {e}")
            return False
    
    def _apply_sysctl_tuning(self) -> bool:
        """Apply sysctl tuning for K3s"""
        logger.info("⚙️ Applying sysctl tuning...")
        
        sysctl_settings = {
            'net.bridge.bridge-nf-call-iptables': '1',
            'net.bridge.bridge-nf-call-ip6tables': '1',
            'net.ipv4.ip_forward': '1',
            'vm.max_map_count': '262144',
            'fs.inotify.max_user_instances': '8192',
            'fs.inotify.max_user_watches': '524288',
            'kernel.pid_max': '4194304'
        }
        
        try:
            sysctl_file = "/etc/sysctl.d/99-k3s.conf"
            
            with open(sysctl_file, 'w') as f:
                f.write("# K3s sysctl settings\n")
                for key, value in sysctl_settings.items():
                    f.write(f"{key} = {value}\n")
            
            # Apply settings immediately
            result = subprocess.run(
                ["sudo", "sysctl", "--system"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"⚠️ Some sysctl settings may not have been applied: {result.stderr}")
            
            logger.info("✅ Sysctl tuning applied")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying sysctl tuning: {e}")
            return False
    
    def _configure_firewall(self) -> bool:
        """Configure firewall for K3s"""
        logger.info("🔥 Configuring firewall...")
        
        try:
            # Check which firewall is active
            firewall_type = self._detect_firewall()
            
            if firewall_type == 'ufw':
                return self._configure_ufw()
            elif firewall_type == 'firewalld':
                return self._configure_firewalld()
            elif firewall_type == 'iptables':
                return self._configure_iptables()
            else:
                logger.info("ℹ️ No active firewall detected, skipping configuration")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error configuring firewall: {e}")
            return False
    
    def _detect_firewall(self) -> Optional[str]:
        """Detect active firewall"""
        # Check for ufw
        try:
            result = subprocess.run(
                ["ufw", "status"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "Status: active" in result.stdout:
                return 'ufw'
        except FileNotFoundError:
            pass
        
        # Check for firewalld
        try:
            result = subprocess.run(
                ["firewall-cmd", "--state"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "running" in result.stdout:
                return 'firewalld'
        except FileNotFoundError:
            pass
        
        # Check for iptables
        try:
            result = subprocess.run(
                ["iptables", "-L"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return 'iptables'
        except FileNotFoundError:
            pass
        
        return None
    
    def _configure_ufw(self) -> bool:
        """Configure UFW for K3s"""
        logger.info("🔥 Configuring UFW...")
        
        ports = [
            ('6443/tcp', 'K3s API server'),
            ('10250/tcp', 'Kubelet metrics'),
            ('51820/udp', 'Wireguard (if enabled)'),
            ('80/tcp', 'HTTP ingress'),
            ('443/tcp', 'HTTPS ingress')
        ]
        
        try:
            for port, description in ports:
                result = subprocess.run(
                    ["sudo", "ufw", "allow", port, "comment", description],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ UFW: Allowed {port} ({description})")
                else:
                    logger.warning(f"⚠️ UFW: Failed to allow {port}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring UFW: {e}")
            return False
    
    def _configure_firewalld(self) -> bool:
        """Configure firewalld for K3s"""
        logger.info("🔥 Configuring firewalld...")
        
        ports = [
            ('6443/tcp', 'K3s API server'),
            ('10250/tcp', 'Kubelet metrics'),
            ('51820/udp', 'Wireguard'),
            ('80/tcp', 'HTTP ingress'),
            ('443/tcp', 'HTTPS ingress')
        ]
        
        try:
            for port, description in ports:
                # Add port to permanent configuration
                result = subprocess.run(
                    ["sudo", "firewall-cmd", "--permanent", "--add-port=" + port],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ firewalld: Allowed {port} ({description})")
                else:
                    logger.warning(f"⚠️ firewalld: Failed to allow {port}")
            
            # Reload firewall rules
            subprocess.run(
                ["sudo", "firewall-cmd", "--reload"],
                capture_output=True, text=True, timeout=30
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring firewalld: {e}")
            return False
    
    def _configure_iptables(self) -> bool:
        """Configure iptables for K3s"""
        logger.info("🔥 Configuring iptables...")
        
        # Basic iptables configuration for K3s
        # This is a simplified setup - production environments should have more comprehensive rules
        
        commands = [
            # Allow K3s API server
            "iptables -A INPUT -p tcp --dport 6443 -j ACCEPT",
            # Allow kubelet metrics
            "iptables -A INPUT -p tcp --dport 10250 -j ACCEPT",
            # Allow Wireguard
            "iptables -A INPUT -p udp --dport 51820 -j ACCEPT",
            # Allow HTTP/HTTPS
            "iptables -A INPUT -p tcp --dport 80 -j ACCEPT",
            "iptables -A INPUT -p tcp --dport 443 -j ACCEPT",
        ]
        
        try:
            for cmd in commands:
                result = subprocess.run(
                    cmd.split(), capture_output=True, text=True, timeout=30
                )
                
                if result.returncode != 0:
                    logger.warning(f"⚠️ iptables command failed: {cmd}")
            
            logger.info("✅ iptables rules applied")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring iptables: {e}")
            return False
    
    def _set_resource_limits(self) -> bool:
        """Set resource limits for K3s"""
        logger.info("📊 Setting resource limits...")
        
        limits_config = """
# K3s resource limits
* soft nofile 1000000
* hard nofile 1000000
* soft nproc 1000000
* hard nproc 1000000
root soft nofile 1000000
root hard nofile 1000000
root soft nproc 1000000
root hard nproc 1000000
"""
        
        try:
            limits_file = "/etc/security/limits.d/99-k3s.conf"
            
            with open(limits_file, 'w') as f:
                f.write(limits_config)
            
            logger.info("✅ Resource limits configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting resource limits: {e}")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check K3s prerequisites"""
        logger.info("🔍 Checking K3s prerequisites...")
        
        prerequisites = [
            ('curl', 'curl --version'),
            ('systemctl', 'systemctl --version'),
            ('iptables', 'iptables --version'),
        ]
        
        missing = []
        
        for name, cmd in prerequisites:
            try:
                result = subprocess.run(
                    cmd.split(), capture_output=True, text=True, timeout=10
                )
                
                if result.returncode != 0:
                    missing.append(name)
                    
            except FileNotFoundError:
                missing.append(name)
        
        if missing:
            logger.error(f"❌ Missing prerequisites: {', '.join(missing)}")
            return False
        
        logger.info("✅ All prerequisites satisfied")
        return True
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        if not self.system_info:
            self.detect_system()
        
        # Get current resource usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'system_info': {
                'os': f"{self.system_info.os_name} {self.system_info.os_version}",
                'architecture': self.system_info.architecture,
                'kernel': self.system_info.kernel_version,
                'hostname': self.system_info.hostname,
                'cpu_cores': self.system_info.cpu_count,
                'total_memory_gb': self.system_info.memory_gb,
                'total_disk_gb': self.system_info.disk_space_gb
            },
            'resource_usage': {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used_gb': round(memory.used / (1024**3), 1),
                'disk_percent': round(disk.percent, 1),
                'disk_used_gb': round(disk.used / (1024**3), 1)
            },
            'compatibility': {
                'os_supported': self.check_compatibility(),
                'resources_adequate': self.check_resources(),
                'prerequisites_met': self.check_prerequisites()
            }
        }
    
    @staticmethod
    def run_command(cmd: List[str], timeout: int = 60, check: bool = True) -> subprocess.CompletedProcess:
        """Utility method to run commands with proper error handling"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Exit code: {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            raise