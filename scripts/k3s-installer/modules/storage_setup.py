#!/usr/bin/env python3
"""
Storage Setup Module for K3s Intelligent Installer

This module handles:
- OpenEBS local storage setup
- Local-path provisioner (K3s default)
- Storage class configuration
- Storage monitoring and validation
"""

import os
import subprocess
import logging
import json
import time
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Storage configuration dataclass"""
    provider: str
    version: str
    replicas: int
    storage_class: str
    backup_enabled: bool = False
    monitoring_enabled: bool = False
    deployed: bool = False

class StorageSetup:
    """Main storage setup class"""
    
    def __init__(self, config: Dict):
        self.config = config.get('storage', {})
        self.k3s_config = config.get('k3s', {})
        self.provider = self.config.get('provider', 'local-path')
        self.storage_config: Optional[StorageConfig] = None
        
    def setup_storage(self) -> bool:
        """Main method to setup storage provider"""
        logger.info(f"🗄️ Setting up {self.provider} storage...")
        
        if self.provider == 'openebs':
            return self._setup_openebs()
        elif self.provider == 'local-path':
            return self._setup_local_path()
        else:
            logger.error(f"❌ Unsupported storage provider: {self.provider}")
            return False
    
    
    
    
    
    
    
    
    
    
    def _setup_openebs(self) -> bool:
        """Setup OpenEBS storage"""
        logger.info("📦 Setting up OpenEBS storage...")
        
        openebs_config = self.config.get('openebs', {})
        version = openebs_config.get('version', 'v4.1.0')
        engine = openebs_config.get('engine', 'hostpath')
        
        self.storage_config = StorageConfig(
            provider='openebs',
            version=version,
            replicas=1,  # OpenEBS typically uses local storage
            storage_class=openebs_config.get('storage_class', 'openebs-hostpath')
        )
        
        try:
            # Deploy OpenEBS
            if not self._deploy_openebs(version, engine):
                return False
            
            # Wait for OpenEBS to be ready
            if not self._wait_for_openebs_ready():
                return False
            
            # Configure storage class
            if not self._configure_openebs_storage_class(engine):
                return False
            
            self.storage_config.deployed = True
            logger.info("✅ OpenEBS storage setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up OpenEBS: {e}")
            return False
    
    def _deploy_openebs(self, version: str, engine: str) -> bool:
        """Deploy OpenEBS"""
        logger.info(f"🚀 Deploying OpenEBS {version} with {engine} engine...")
        
        try:
            # Deploy OpenEBS operator
            manifest_url = f"https://openebs.github.io/charts/openebs-operator-{version}.yaml"
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", manifest_url],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying OpenEBS: {result.stderr}")
                return False
            
            logger.info("✅ OpenEBS deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying OpenEBS: {e}")
            return False
    
    def _wait_for_openebs_ready(self, timeout: int = 300) -> bool:
        """Wait for OpenEBS to be ready"""
        logger.info("⏳ Waiting for OpenEBS to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "openebs", "-o", "json"],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    pods_data = json.loads(result.stdout)
                    pods = pods_data.get('items', [])
                    
                    if pods:
                        ready_pods = sum(1 for pod in pods 
                                       if pod.get('status', {}).get('phase') == 'Running')
                        total_pods = len(pods)
                        
                        logger.info(f"⏳ OpenEBS pods ready: {ready_pods}/{total_pods}")
                        
                        if ready_pods == total_pods:
                            logger.info("✅ OpenEBS is ready!")
                            return True
                
            except Exception as e:
                logger.warning(f"⚠️ Error checking OpenEBS status: {e}")
            
            time.sleep(10)
        
        logger.error("❌ Timeout waiting for OpenEBS to be ready")
        return False
    
    def _configure_openebs_storage_class(self, engine: str) -> bool:
        """Configure OpenEBS storage class"""
        logger.info(f"🔧 Configuring OpenEBS {engine} storage class...")
        
        if engine == 'hostpath':
            storage_class_yaml = """
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: openebs-hostpath
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
    openebs.io/cas-type: local
    cas.openebs.io/config: |
      - name: StorageType
        value: "hostpath"
      - name: BasePath
        value: "/var/openebs/local"
provisioner: openebs.io/local
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
"""
        else:
            logger.error(f"❌ Unsupported OpenEBS engine: {engine}")
            return False
        
        try:
            with open('/tmp/openebs-storageclass.yaml', 'w') as f:
                f.write(storage_class_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/openebs-storageclass.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating storage class: {result.stderr}")
                return False
            
            os.remove('/tmp/openebs-storageclass.yaml')
            
            logger.info("✅ OpenEBS storage class configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring storage class: {e}")
            return False
    
    def _setup_local_path(self) -> bool:
        """Setup local-path storage (K3s default)"""
        logger.info("📁 Configuring local-path storage...")
        
        self.storage_config = StorageConfig(
            provider='local-path',
            version='N/A',
            replicas=1,
            storage_class='local-path',
            deployed=True
        )
        
        # local-path is installed by default with K3s
        logger.info("✅ Local-path storage configured")
        return True
    
    def _base64_encode(self, value: str) -> str:
        """Base64 encode a string"""
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def validate_storage_setup(self) -> bool:
        """Validate storage setup"""
        logger.info("🔍 Validating storage setup...")
        
        try:
            # Check if storage classes are available
            result = subprocess.run(
                ["kubectl", "get", "storageclass", "-o", "json"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Could not check storage classes")
                return False
            
            sc_data = json.loads(result.stdout)
            storage_classes = [sc.get('metadata', {}).get('name') 
                             for sc in sc_data.get('items', [])]
            
            expected_sc = self.storage_config.storage_class if self.storage_config else 'local-path'
            
            if expected_sc in storage_classes:
                logger.info(f"✅ Storage class '{expected_sc}' found")
            else:
                logger.error(f"❌ Storage class '{expected_sc}' not found")
                return False
            
            # Create a test PVC to validate storage
            if not self._test_storage_provisioning():
                return False
            
            logger.info("✅ Storage validation completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Storage validation failed: {e}")
            return False
    
    def _test_storage_provisioning(self) -> bool:
        """Test storage provisioning with a test PVC"""
        logger.info("🧪 Testing storage provisioning...")
        
        test_pvc_yaml = f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: storage-test-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {self.storage_config.storage_class if self.storage_config else 'local-path'}
  resources:
    requests:
      storage: 1Gi
"""
        
        try:
            # Create test PVC
            with open('/tmp/test-pvc.yaml', 'w') as f:
                f.write(test_pvc_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/test-pvc.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating test PVC: {result.stderr}")
                return False
            
            # Wait for PVC to be bound
            for i in range(30):  # Wait up to 30 seconds
                result = subprocess.run(
                    ["kubectl", "get", "pvc", "storage-test-pvc", "-o", "jsonpath={.status.phase}"],
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip() == 'Bound':
                    logger.info("✅ Test PVC successfully bound")
                    break
                    
                time.sleep(1)
            else:
                logger.error("❌ Test PVC failed to bind")
                return False
            
            # Clean up test PVC
            subprocess.run(
                ["kubectl", "delete", "-f", "/tmp/test-pvc.yaml"],
                capture_output=True, timeout=30
            )
            
            os.remove('/tmp/test-pvc.yaml')
            
            logger.info("✅ Storage provisioning test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Storage provisioning test failed: {e}")
            return False
    
    def get_storage_status(self) -> Dict:
        """Get current storage configuration status"""
        if not self.storage_config:
            return {'provider': 'none', 'status': 'not_configured'}
        
        return {
            'provider': self.storage_config.provider,
            'version': self.storage_config.version,
            'storage_class': self.storage_config.storage_class,
            'replicas': self.storage_config.replicas,
            'backup_enabled': self.storage_config.backup_enabled,
            'monitoring_enabled': self.storage_config.monitoring_enabled,
            'deployed': self.storage_config.deployed
        }