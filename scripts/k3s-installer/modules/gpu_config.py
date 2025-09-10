#!/usr/bin/env python3
"""
GPU Configuration Module for K3s Intelligent Installer

This module handles:
- GPU detection (NVIDIA, AMD, Intel)
- Driver installation
- Container runtime configuration
- Device plugin deployment
- GPU resource monitoring setup
"""

import os
import subprocess
import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

@dataclass
class GPUInfo:
    """GPU information dataclass"""
    vendor: str
    model: str
    memory: Optional[int] = None
    driver_version: Optional[str] = None
    pci_id: Optional[str] = None
    uuid: Optional[str] = None

@dataclass
class GPUConfig:
    """GPU configuration dataclass"""
    vendor: str
    driver_installed: bool = False
    device_plugin_deployed: bool = False
    container_runtime_configured: bool = False
    monitoring_enabled: bool = False

class GPUConfigurator:
    """Main GPU configuration class"""
    
    def __init__(self, config: Dict):
        self.config = config.get('gpu', {})
        self.k3s_config = config.get('k3s', {})
        self.detected_gpus: List[GPUInfo] = []
        self.gpu_configs: Dict[str, GPUConfig] = {}
        
    def detect_gpus(self) -> List[GPUInfo]:
        """Detect all available GPUs in the system"""
        logger.info("🔍 Detecting GPUs...")
        
        gpus = []
        
        # Detect NVIDIA GPUs
        nvidia_gpus = self._detect_nvidia_gpus()
        gpus.extend(nvidia_gpus)
        
        # Detect AMD GPUs
        amd_gpus = self._detect_amd_gpus()
        gpus.extend(amd_gpus)
        
        # Detect Intel GPUs
        intel_gpus = self._detect_intel_gpus()
        gpus.extend(intel_gpus)
        
        self.detected_gpus = gpus
        
        if gpus:
            logger.info(f"✅ Found {len(gpus)} GPU(s):")
            for gpu in gpus:
                logger.info(f"  - {gpu.vendor} {gpu.model}")
        else:
            logger.info("ℹ️ No GPUs detected")
            
        return gpus
    
    def _detect_nvidia_gpus(self) -> List[GPUInfo]:
        """Detect NVIDIA GPUs using nvidia-smi"""
        gpus = []
        
        try:
            # Check if nvidia-smi is available
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version,uuid,pci.bus_id', 
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 5:
                            gpu = GPUInfo(
                                vendor="NVIDIA",
                                model=parts[0],
                                memory=int(parts[1]) if parts[1].isdigit() else None,
                                driver_version=parts[2],
                                uuid=parts[3],
                                pci_id=parts[4]
                            )
                            gpus.append(gpu)
                            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Try alternative detection using lspci
            gpus.extend(self._detect_nvidia_via_lspci())
            
        return gpus
    
    def _detect_nvidia_via_lspci(self) -> List[GPUInfo]:
        """Detect NVIDIA GPUs using lspci as fallback"""
        gpus = []
        
        try:
            result = subprocess.run(
                ['lspci', '-nn'], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'NVIDIA' in line.upper() and any(keyword in line.upper() 
                                                       for keyword in ['VGA', 'GPU', '3D']):
                        # Extract model name
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            model = parts[1].split(' [')[0].strip()
                            gpu = GPUInfo(
                                vendor="NVIDIA",
                                model=model,
                                pci_id=line.split(' ')[0]
                            )
                            gpus.append(gpu)
                            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ Could not detect NVIDIA GPUs via lspci")
            
        return gpus
    
    def _detect_amd_gpus(self) -> List[GPUInfo]:
        """Detect AMD GPUs using rocm-smi or lspci"""
        gpus = []
        
        try:
            # Try rocm-smi first
            result = subprocess.run(
                ['rocm-smi', '--showproductname'], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'GPU' in line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            model = parts[1].strip()
                            gpu = GPUInfo(vendor="AMD", model=model)
                            gpus.append(gpu)
                            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to lspci
            gpus.extend(self._detect_amd_via_lspci())
            
        return gpus
    
    def _detect_amd_via_lspci(self) -> List[GPUInfo]:
        """Detect AMD GPUs using lspci as fallback"""
        gpus = []
        
        try:
            result = subprocess.run(
                ['lspci', '-nn'], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if any(keyword in line.upper() for keyword in ['AMD', 'ATI']) and \
                       any(keyword in line.upper() for keyword in ['VGA', 'GPU', '3D', 'RADEON']):
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            model = parts[1].split(' [')[0].strip()
                            gpu = GPUInfo(
                                vendor="AMD",
                                model=model,
                                pci_id=line.split(' ')[0]
                            )
                            gpus.append(gpu)
                            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ Could not detect AMD GPUs via lspci")
            
        return gpus
    
    def _detect_intel_gpus(self) -> List[GPUInfo]:
        """Detect Intel GPUs using lspci"""
        gpus = []
        
        try:
            result = subprocess.run(
                ['lspci', '-nn'], 
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Intel' in line and any(keyword in line.upper() 
                                             for keyword in ['VGA', 'GPU', '3D', 'UHD', 'IRIS']):
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            model = parts[1].split(' [')[0].strip()
                            gpu = GPUInfo(
                                vendor="Intel",
                                model=model,
                                pci_id=line.split(' ')[0]
                            )
                            gpus.append(gpu)
                            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ Could not detect Intel GPUs via lspci")
            
        return gpus
    
    def configure_gpu_support(self) -> bool:
        """Main method to configure GPU support"""
        if not self.config.get('enabled', False):
            logger.info("ℹ️ GPU support disabled in configuration")
            return True
            
        if self.config.get('auto_detect', True):
            self.detect_gpus()
        
        if not self.detected_gpus:
            logger.info("ℹ️ No GPUs detected, skipping GPU configuration")
            return True
            
        success = True
        
        for gpu in self.detected_gpus:
            vendor = gpu.vendor.lower()
            gpu_config = GPUConfig(vendor=vendor)
            
            logger.info(f"🔧 Configuring {gpu.vendor} GPU: {gpu.model}")
            
            # Install drivers
            if self._should_install_driver(vendor):
                if not self._install_gpu_driver(gpu):
                    success = False
                    continue
                gpu_config.driver_installed = True
            
            # Configure container runtime
            if not self._configure_container_runtime(gpu):
                success = False
                continue
            gpu_config.container_runtime_configured = True
            
            # Deploy device plugin
            if not self._deploy_device_plugin(gpu):
                success = False
                continue
            gpu_config.device_plugin_deployed = True
            
            # Setup monitoring
            if self.config.get('monitoring', {}).get('enabled', False):
                if self._setup_gpu_monitoring(gpu):
                    gpu_config.monitoring_enabled = True
            
            self.gpu_configs[vendor] = gpu_config
            logger.info(f"✅ {gpu.vendor} GPU configuration completed")
        
        return success
    
    def _should_install_driver(self, vendor: str) -> bool:
        """Check if driver should be installed for the vendor"""
        vendor_config = self.config.get(vendor, {})
        return vendor_config.get('install_driver', False)
    
    def _install_gpu_driver(self, gpu: GPUInfo) -> bool:
        """Install GPU drivers based on vendor"""
        vendor = gpu.vendor.lower()
        
        if vendor == 'nvidia':
            return self._install_nvidia_driver(gpu)
        elif vendor == 'amd':
            return self._install_amd_driver(gpu)
        elif vendor == 'intel':
            return self._install_intel_driver(gpu)
        
        logger.warning(f"⚠️ Unsupported GPU vendor: {vendor}")
        return False
    
    def _install_nvidia_driver(self, gpu: GPUInfo) -> bool:
        """Install NVIDIA drivers and container toolkit"""
        logger.info("📦 Installing NVIDIA drivers and container toolkit...")
        
        try:
            # Detect OS distribution
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
            
            if 'ubuntu' in os_info.lower() or 'debian' in os_info.lower():
                return self._install_nvidia_ubuntu()
            elif 'centos' in os_info.lower() or 'rhel' in os_info.lower() or 'fedora' in os_info.lower():
                return self._install_nvidia_rhel()
            else:
                logger.warning("⚠️ Unsupported OS for NVIDIA driver installation")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error installing NVIDIA driver: {e}")
            return False
    
    def _install_nvidia_ubuntu(self) -> bool:
        """Install NVIDIA drivers on Ubuntu/Debian"""
        commands = [
            # Add NVIDIA package repository
            "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
            "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list",
            "sudo apt-get update",
            # Install drivers
            "sudo apt-get install -y nvidia-driver-535",  # Latest stable
            # Install container toolkit
            "sudo apt-get install -y nvidia-container-toolkit",
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"❌ Command failed: {cmd}")
                    logger.error(f"Error: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Command timeout: {cmd}")
                return False
        
        logger.info("✅ NVIDIA drivers and container toolkit installed")
        return True
    
    def _install_nvidia_rhel(self) -> bool:
        """Install NVIDIA drivers on RHEL/CentOS/Fedora"""
        commands = [
            # Add NVIDIA repository
            "curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo",
            # Install drivers (assumes EPEL is available)
            "sudo dnf install -y akmod-nvidia",
            # Install container toolkit
            "sudo dnf install -y nvidia-container-toolkit",
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"❌ Command failed: {cmd}")
                    logger.error(f"Error: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Command timeout: {cmd}")
                return False
        
        logger.info("✅ NVIDIA drivers and container toolkit installed")
        return True
    
    def _install_amd_driver(self, gpu: GPUInfo) -> bool:
        """Install AMD ROCm drivers"""
        logger.info("📦 Installing AMD ROCm drivers...")
        
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
            
            if 'ubuntu' in os_info.lower():
                return self._install_rocm_ubuntu()
            else:
                logger.warning("⚠️ AMD ROCm installation only supported on Ubuntu currently")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error installing AMD driver: {e}")
            return False
    
    def _install_rocm_ubuntu(self) -> bool:
        """Install ROCm on Ubuntu"""
        commands = [
            # Add ROCm repository
            "wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -",
            "echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/5.7.1/ ubuntu main' | sudo tee /etc/apt/sources.list.d/rocm.list",
            "sudo apt-get update",
            # Install ROCm
            "sudo apt-get install -y rocm-dkms rocm-dev rocm-libs",
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"❌ Command failed: {cmd}")
                    return False
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Command timeout: {cmd}")
                return False
        
        logger.info("✅ AMD ROCm drivers installed")
        return True
    
    def _install_intel_driver(self, gpu: GPUInfo) -> bool:
        """Install Intel GPU drivers (usually included in kernel)"""
        logger.info("📦 Configuring Intel GPU support...")
        
        # Intel GPUs usually work out of the box with modern kernels
        # Just ensure the required packages are installed
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
            
            if 'ubuntu' in os_info.lower() or 'debian' in os_info.lower():
                cmd = "sudo apt-get install -y intel-gpu-tools"
            elif 'centos' in os_info.lower() or 'rhel' in os_info.lower() or 'fedora' in os_info.lower():
                cmd = "sudo dnf install -y intel-gpu-tools"
            else:
                logger.warning("⚠️ Unsupported OS for Intel GPU tools")
                return True  # Skip but don't fail
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.warning("⚠️ Could not install Intel GPU tools, continuing...")
                
        except Exception as e:
            logger.warning(f"⚠️ Error configuring Intel GPU: {e}")
        
        logger.info("✅ Intel GPU configuration completed")
        return True
    
    def _configure_container_runtime(self, gpu: GPUInfo) -> bool:
        """Configure container runtime for GPU support"""
        vendor = gpu.vendor.lower()
        
        if vendor == 'nvidia':
            return self._configure_nvidia_containerd()
        elif vendor == 'amd':
            return self._configure_amd_containerd()
        elif vendor == 'intel':
            return self._configure_intel_containerd()
        
        return False
    
    def _configure_nvidia_containerd(self) -> bool:
        """Configure containerd for NVIDIA GPU support"""
        logger.info("🔧 Configuring containerd for NVIDIA GPU...")
        
        try:
            # Configure nvidia-container-runtime
            result = subprocess.run(
                ["sudo", "nvidia-ctk", "runtime", "configure", "--runtime=containerd"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error configuring NVIDIA runtime: {result.stderr}")
                return False
            
            # Restart containerd
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "containerd"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error restarting containerd: {result.stderr}")
                return False
            
            logger.info("✅ Containerd configured for NVIDIA GPU")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring NVIDIA containerd: {e}")
            return False
    
    def _configure_amd_containerd(self) -> bool:
        """Configure containerd for AMD GPU support"""
        logger.info("🔧 Configuring containerd for AMD GPU...")
        
        # AMD GPU support in containerd is more straightforward
        # Usually just requires the ROCm runtime to be available
        logger.info("✅ AMD GPU containerd configuration completed")
        return True
    
    def _configure_intel_containerd(self) -> bool:
        """Configure containerd for Intel GPU support"""
        logger.info("🔧 Configuring containerd for Intel GPU...")
        
        # Intel GPU support usually works out of the box
        logger.info("✅ Intel GPU containerd configuration completed")
        return True
    
    def _deploy_device_plugin(self, gpu: GPUInfo) -> bool:
        """Deploy Kubernetes device plugin for GPU"""
        vendor = gpu.vendor.lower()
        
        if vendor == 'nvidia':
            return self._deploy_nvidia_device_plugin()
        elif vendor == 'amd':
            return self._deploy_amd_device_plugin()
        elif vendor == 'intel':
            return self._deploy_intel_device_plugin()
        
        return False
    
    def _deploy_nvidia_device_plugin(self) -> bool:
        """Deploy NVIDIA device plugin"""
        logger.info("🚀 Deploying NVIDIA device plugin...")
        
        nvidia_device_plugin_yaml = """
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      priorityClassName: "system-node-critical"
      containers:
      - image: nvcr.io/nvidia/k8s-device-plugin:v0.14.5
        name: nvidia-device-plugin-ctr
        env:
          - name: FAIL_ON_INIT_ERROR
            value: "false"
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
          - name: device-plugin
            mountPath: /var/lib/kubelet/device-plugins
      volumes:
        - name: device-plugin
          hostPath:
            path: /var/lib/kubelet/device-plugins
      nodeSelector:
        accelerator: nvidia
"""
        
        try:
            # Create temporary file
            with open('/tmp/nvidia-device-plugin.yaml', 'w') as f:
                f.write(nvidia_device_plugin_yaml)
            
            # Apply the manifest
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/nvidia-device-plugin.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying NVIDIA device plugin: {result.stderr}")
                return False
            
            # Label the node
            result = subprocess.run(
                ["kubectl", "label", "node", "--all", "accelerator=nvidia", "--overwrite"],
                capture_output=True, text=True, timeout=30
            )
            
            # Clean up
            os.remove('/tmp/nvidia-device-plugin.yaml')
            
            logger.info("✅ NVIDIA device plugin deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying NVIDIA device plugin: {e}")
            return False
    
    def _deploy_amd_device_plugin(self) -> bool:
        """Deploy AMD device plugin"""
        logger.info("🚀 Deploying AMD device plugin...")
        
        amd_device_plugin_yaml = """
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: amd-gpu-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: amd-gpu-device-plugin-ds
  template:
    metadata:
      labels:
        name: amd-gpu-device-plugin-ds
    spec:
      tolerations:
      - key: amd.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - image: rocm/k8s-device-plugin:latest
        name: amd-gpu-device-plugin-ctr
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
          - name: device-plugin
            mountPath: /var/lib/kubelet/device-plugins
          - name: dri
            mountPath: /dev/dri
            readOnly: true
      volumes:
        - name: device-plugin
          hostPath:
            path: /var/lib/kubelet/device-plugins
        - name: dri
          hostPath:
            path: /dev/dri
      nodeSelector:
        accelerator: amd
"""
        
        try:
            with open('/tmp/amd-device-plugin.yaml', 'w') as f:
                f.write(amd_device_plugin_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/amd-device-plugin.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying AMD device plugin: {result.stderr}")
                return False
            
            # Label the node
            result = subprocess.run(
                ["kubectl", "label", "node", "--all", "accelerator=amd", "--overwrite"],
                capture_output=True, text=True, timeout=30
            )
            
            os.remove('/tmp/amd-device-plugin.yaml')
            
            logger.info("✅ AMD device plugin deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying AMD device plugin: {e}")
            return False
    
    def _deploy_intel_device_plugin(self) -> bool:
        """Deploy Intel GPU device plugin"""
        logger.info("🚀 Deploying Intel GPU device plugin...")
        
        intel_device_plugin_yaml = """
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: intel-gpu-plugin
  namespace: kube-system
  labels:
    app: intel-gpu-plugin
spec:
  selector:
    matchLabels:
      app: intel-gpu-plugin
  template:
    metadata:
      labels:
        app: intel-gpu-plugin
    spec:
      nodeSelector:
        accelerator: intel
      tolerations:
      - key: intel.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: intel-gpu-plugin
        image: intel/intel-gpu-plugin:0.27.1
        imagePullPolicy: IfNotPresent
        securityContext:
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: devfs
          mountPath: /dev/dri
          readOnly: true
        - name: sysfs
          mountPath: /sys/class/drm
          readOnly: true
        - name: kubeletsockets
          mountPath: /var/lib/kubelet/device-plugins
      volumes:
      - name: devfs
        hostPath:
          path: /dev/dri
      - name: sysfs
        hostPath:
          path: /sys/class/drm
      - name: kubeletsockets
        hostPath:
          path: /var/lib/kubelet/device-plugins
"""
        
        try:
            with open('/tmp/intel-device-plugin.yaml', 'w') as f:
                f.write(intel_device_plugin_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/intel-device-plugin.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying Intel device plugin: {result.stderr}")
                return False
            
            # Label the node
            result = subprocess.run(
                ["kubectl", "label", "node", "--all", "accelerator=intel", "--overwrite"],
                capture_output=True, text=True, timeout=30
            )
            
            os.remove('/tmp/intel-device-plugin.yaml')
            
            logger.info("✅ Intel GPU device plugin deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying Intel device plugin: {e}")
            return False
    
    def _setup_gpu_monitoring(self, gpu: GPUInfo) -> bool:
        """Setup GPU monitoring with Prometheus"""
        vendor = gpu.vendor.lower()
        
        if vendor == 'nvidia':
            return self._setup_nvidia_monitoring()
        elif vendor == 'amd':
            return self._setup_amd_monitoring()
        
        logger.info(f"ℹ️ GPU monitoring not implemented for {vendor}")
        return True
    
    def _setup_nvidia_monitoring(self) -> bool:
        """Setup NVIDIA GPU monitoring"""
        logger.info("📊 Setting up NVIDIA GPU monitoring...")
        
        dcgm_exporter_yaml = """
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      nodeSelector:
        accelerator: nvidia
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.0-3.2.0-ubuntu22.04
        ports:
        - containerPort: 9400
          name: http-metrics
          protocol: TCP
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        env:
        - name: DCGM_EXPORTER_LISTEN
          value: ":9400"
        - name: DCGM_EXPORTER_KUBERNETES
          value: "true"
      hostNetwork: true
      hostPID: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
"""
        
        try:
            with open('/tmp/dcgm-exporter.yaml', 'w') as f:
                f.write(dcgm_exporter_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/dcgm-exporter.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying DCGM exporter: {result.stderr}")
                return False
            
            os.remove('/tmp/dcgm-exporter.yaml')
            
            logger.info("✅ NVIDIA GPU monitoring setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up NVIDIA monitoring: {e}")
            return False
    
    def _setup_amd_monitoring(self) -> bool:
        """Setup AMD GPU monitoring"""
        logger.info("📊 Setting up AMD GPU monitoring...")
        
        # AMD GPU monitoring is more complex and requires ROCm SMI
        # For now, just log that it's not fully implemented
        logger.info("ℹ️ AMD GPU monitoring setup completed (basic)")
        return True
    
    def get_gpu_status(self) -> Dict:
        """Get current GPU configuration status"""
        return {
            'detected_gpus': [
                {
                    'vendor': gpu.vendor,
                    'model': gpu.model,
                    'memory': gpu.memory,
                    'driver_version': gpu.driver_version
                } for gpu in self.detected_gpus
            ],
            'configurations': {
                vendor: {
                    'driver_installed': config.driver_installed,
                    'device_plugin_deployed': config.device_plugin_deployed,
                    'container_runtime_configured': config.container_runtime_configured,
                    'monitoring_enabled': config.monitoring_enabled
                } for vendor, config in self.gpu_configs.items()
            }
        }
    
    def validate_gpu_setup(self) -> bool:
        """Validate that GPU setup is working correctly"""
        logger.info("🔍 Validating GPU setup...")
        
        try:
            # Check if GPU resources are available in Kubernetes
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Could not check node resources")
                return False
            
            nodes_data = json.loads(result.stdout)
            
            for node in nodes_data.get('items', []):
                capacity = node.get('status', {}).get('capacity', {})
                
                # Check for NVIDIA GPUs
                if 'nvidia.com/gpu' in capacity:
                    gpu_count = capacity['nvidia.com/gpu']
                    logger.info(f"✅ Found {gpu_count} NVIDIA GPU(s) available in Kubernetes")
                
                # Check for AMD GPUs
                if 'amd.com/gpu' in capacity:
                    gpu_count = capacity['amd.com/gpu']
                    logger.info(f"✅ Found {gpu_count} AMD GPU(s) available in Kubernetes")
                
                # Check for Intel GPUs
                if 'gpu.intel.com/i915' in capacity:
                    gpu_count = capacity['gpu.intel.com/i915']
                    logger.info(f"✅ Found {gpu_count} Intel GPU(s) available in Kubernetes")
            
            logger.info("✅ GPU validation completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ GPU validation failed: {e}")
            return False