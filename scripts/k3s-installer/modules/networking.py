#!/usr/bin/env python3
"""
Networking Module for K3s Intelligent Installer

This module handles:
- MetalLB load balancer setup and configuration
- Wireguard VPN setup for cross-cluster networking
- Network policy configuration
- Ingress controller setup
- Network validation and testing
"""

import os
import subprocess
import logging
import json
import time
import yaml
import ipaddress
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class NetworkConfig:
    """Network configuration dataclass"""
    metallb_enabled: bool = False
    metallb_deployed: bool = False
    wireguard_enabled: bool = False
    wireguard_configured: bool = False
    ingress_configured: bool = False

@dataclass
class MetalLBPool:
    """MetalLB address pool configuration"""
    name: str
    protocol: str
    addresses: List[str]
    auto_assign: bool = True

@dataclass
class WireguardPeer:
    """Wireguard peer configuration"""
    public_key: str
    endpoint: str
    allowed_ips: List[str]
    persistent_keepalive: Optional[int] = None

class NetworkingSetup:
    """Main networking setup class"""
    
    def __init__(self, config: Dict):
        self.config = config.get('networking', {})
        self.k3s_config = config.get('k3s', {})
        self.network_config = NetworkConfig()
        
    def setup_networking(self) -> bool:
        """Main method to setup networking components"""
        logger.info("🌐 Setting up networking components...")
        
        success = True
        
        # Setup MetalLB if enabled
        if self.config.get('metallb', {}).get('enabled', False):
            if not self._setup_metallb():
                success = False
            else:
                self.network_config.metallb_enabled = True
                self.network_config.metallb_deployed = True
        
        # Setup Wireguard if enabled
        if self.config.get('wireguard', {}).get('enabled', False):
            if not self._setup_wireguard():
                success = False
            else:
                self.network_config.wireguard_enabled = True
                self.network_config.wireguard_configured = True
        
        # Setup ingress controller (Traefik is default in K3s)
        if not self._configure_ingress():
            logger.warning("⚠️ Ingress configuration failed")
        else:
            self.network_config.ingress_configured = True
        
        if success:
            logger.info("✅ Networking setup completed")
        else:
            logger.error("❌ Some networking components failed to setup")
        
        return success
    
    def _setup_metallb(self) -> bool:
        """Setup MetalLB load balancer"""
        logger.info("⚖️ Setting up MetalLB load balancer...")
        
        metallb_config = self.config.get('metallb', {})
        version = metallb_config.get('version', 'v0.14.8')
        
        try:
            # Deploy MetalLB
            if not self._deploy_metallb(version):
                return False
            
            # Wait for MetalLB to be ready
            if not self._wait_for_metallb_ready():
                return False
            
            # Configure address pools
            if not self._configure_metallb_pools():
                return False
            
            logger.info("✅ MetalLB setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up MetalLB: {e}")
            return False
    
    def _deploy_metallb(self, version: str) -> bool:
        """Deploy MetalLB"""
        logger.info(f"🚀 Deploying MetalLB {version}...")
        
        try:
            # Deploy MetalLB namespace and components
            manifest_url = f"https://raw.githubusercontent.com/metallb/metallb/{version}/config/manifests/metallb-native.yaml"
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", manifest_url],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying MetalLB: {result.stderr}")
                return False
            
            logger.info("✅ MetalLB deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying MetalLB: {e}")
            return False
    
    def _wait_for_metallb_ready(self, timeout: int = 300) -> bool:
        """Wait for MetalLB to be ready"""
        logger.info("⏳ Waiting for MetalLB to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "metallb-system", "-o", "json"],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    pods_data = json.loads(result.stdout)
                    pods = pods_data.get('items', [])
                    
                    if pods:
                        ready_pods = 0
                        total_pods = len(pods)
                        
                        for pod in pods:
                            status = pod.get('status', {})
                            phase = status.get('phase', '')
                            
                            if phase == 'Running':
                                conditions = status.get('conditions', [])
                                ready = any(c.get('type') == 'Ready' and c.get('status') == 'True' 
                                          for c in conditions)
                                if ready:
                                    ready_pods += 1
                        
                        logger.info(f"⏳ MetalLB pods ready: {ready_pods}/{total_pods}")
                        
                        if ready_pods == total_pods:
                            logger.info("✅ MetalLB is ready!")
                            return True
                
            except Exception as e:
                logger.warning(f"⚠️ Error checking MetalLB status: {e}")
            
            time.sleep(10)
        
        logger.error("❌ Timeout waiting for MetalLB to be ready")
        return False
    
    def _configure_metallb_pools(self) -> bool:
        """Configure MetalLB address pools"""
        logger.info("🔧 Configuring MetalLB address pools...")
        
        metallb_config = self.config.get('metallb', {})
        address_pools = metallb_config.get('address_pools', [])
        
        if not address_pools:
            logger.error("❌ No MetalLB address pools configured")
            return False
        
        try:
            for pool_config in address_pools:
                pool = MetalLBPool(
                    name=pool_config.get('name', 'default'),
                    protocol=pool_config.get('protocol', 'layer2'),
                    addresses=pool_config.get('addresses', []),
                    auto_assign=pool_config.get('auto_assign', True)
                )
                
                if not self._create_metallb_pool(pool):
                    return False
            
            logger.info("✅ MetalLB address pools configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring MetalLB pools: {e}")
            return False
    
    def _create_metallb_pool(self, pool: MetalLBPool) -> bool:
        """Create a MetalLB address pool"""
        logger.info(f"📝 Creating MetalLB pool '{pool.name}'...")
        
        # Validate addresses
        for addr_range in pool.addresses:
            if not self._validate_address_range(addr_range):
                logger.error(f"❌ Invalid address range: {addr_range}")
                return False
        
        # Create IPAddressPool
        ip_pool_yaml = f"""
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: {pool.name}
  namespace: metallb-system
spec:
  addresses:
{yaml.dump(pool.addresses, default_flow_style=False, indent=2).rstrip()}
  autoAssign: {str(pool.auto_assign).lower()}
"""
        
        # Create L2Advertisement for layer2 protocol
        l2_adv_yaml = f"""
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: {pool.name}-l2adv
  namespace: metallb-system
spec:
  ipAddressPools:
  - {pool.name}
"""
        
        try:
            # Create IP pool
            with open(f'/tmp/metallb-pool-{pool.name}.yaml', 'w') as f:
                f.write(ip_pool_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", f"/tmp/metallb-pool-{pool.name}.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating IP pool: {result.stderr}")
                return False
            
            # Create L2 advertisement if layer2 protocol
            if pool.protocol == 'layer2':
                with open(f'/tmp/metallb-l2adv-{pool.name}.yaml', 'w') as f:
                    f.write(l2_adv_yaml)
                
                result = subprocess.run(
                    ["kubectl", "apply", "-f", f"/tmp/metallb-l2adv-{pool.name}.yaml"],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode != 0:
                    logger.error(f"❌ Error creating L2 advertisement: {result.stderr}")
                    return False
                
                os.remove(f'/tmp/metallb-l2adv-{pool.name}.yaml')
            
            os.remove(f'/tmp/metallb-pool-{pool.name}.yaml')
            
            logger.info(f"✅ MetalLB pool '{pool.name}' created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating MetalLB pool: {e}")
            return False
    
    def _validate_address_range(self, addr_range: str) -> bool:
        """Validate MetalLB address range"""
        try:
            if '-' in addr_range:
                # Range format: 192.168.1.240-192.168.1.250
                start_ip, end_ip = addr_range.split('-')
                start_addr = ipaddress.IPv4Address(start_ip.strip())
                end_addr = ipaddress.IPv4Address(end_ip.strip())
                return start_addr <= end_addr
            elif '/' in addr_range:
                # CIDR format: 192.168.1.0/24
                ipaddress.IPv4Network(addr_range)
                return True
            else:
                # Single IP
                ipaddress.IPv4Address(addr_range)
                return True
                
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def _setup_wireguard(self) -> bool:
        """Setup Wireguard VPN"""
        logger.info("🔒 Setting up Wireguard VPN...")
        
        wireguard_config = self.config.get('wireguard', {})
        
        try:
            # Install Wireguard
            if not self._install_wireguard():
                return False
            
            # Generate keys if not provided
            if not self._setup_wireguard_keys():
                return False
            
            # Configure Wireguard interface
            if not self._configure_wireguard_interface():
                return False
            
            # Setup peers
            if not self._configure_wireguard_peers():
                return False
            
            # Enable and start Wireguard
            if not self._start_wireguard():
                return False
            
            logger.info("✅ Wireguard setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up Wireguard: {e}")
            return False
    
    def _install_wireguard(self) -> bool:
        """Install Wireguard"""
        logger.info("📦 Installing Wireguard...")
        
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
            
            if 'ubuntu' in os_info.lower() or 'debian' in os_info.lower():
                cmd = "sudo apt-get update && sudo apt-get install -y wireguard wireguard-tools"
            elif 'centos' in os_info.lower() or 'rhel' in os_info.lower() or 'fedora' in os_info.lower():
                cmd = "sudo dnf install -y wireguard-tools"
            else:
                logger.error("❌ Unsupported OS for Wireguard installation")
                return False
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"❌ Error installing Wireguard: {result.stderr}")
                return False
            
            logger.info("✅ Wireguard installed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error installing Wireguard: {e}")
            return False
    
    def _setup_wireguard_keys(self) -> bool:
        """Setup Wireguard keys"""
        logger.info("🔑 Setting up Wireguard keys...")
        
        wireguard_config = self.config.get('wireguard', {})
        private_key = wireguard_config.get('private_key')
        
        try:
            # Create Wireguard directory
            os.makedirs('/etc/wireguard', mode=0o700, exist_ok=True)
            
            if not private_key:
                # Generate private key
                result = subprocess.run(
                    ["wg", "genkey"],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode != 0:
                    logger.error("❌ Error generating Wireguard private key")
                    return False
                
                private_key = result.stdout.strip()
                logger.info("🔑 Generated new Wireguard private key")
            
            # Generate public key
            result = subprocess.run(
                ["wg", "pubkey"],
                input=private_key, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Error generating Wireguard public key")
                return False
            
            public_key = result.stdout.strip()
            
            # Store keys
            self.wireguard_private_key = private_key
            self.wireguard_public_key = public_key
            
            logger.info(f"✅ Wireguard public key: {public_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up Wireguard keys: {e}")
            return False
    
    def _configure_wireguard_interface(self) -> bool:
        """Configure Wireguard interface"""
        logger.info("🔧 Configuring Wireguard interface...")
        
        wireguard_config = self.config.get('wireguard', {})
        interface = wireguard_config.get('interface', 'wg0')
        listen_port = wireguard_config.get('listen_port', 51820)
        
        # For K3s integration, we'll use a simple subnet
        # This can be customized based on your network requirements
        wg_subnet = "10.200.0.1/24"
        
        wg_config = f"""[Interface]
PrivateKey = {self.wireguard_private_key}
Address = {wg_subnet}
ListenPort = {listen_port}
SaveConfig = true

# Enable IP forwarding
PostUp = echo 1 > /proc/sys/net/ipv4/ip_forward
PostUp = iptables -A FORWARD -i {interface} -j ACCEPT
PostUp = iptables -A FORWARD -o {interface} -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

PostDown = iptables -D FORWARD -i {interface} -j ACCEPT
PostDown = iptables -D FORWARD -o {interface} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
"""
        
        try:
            # Write Wireguard config
            with open(f'/etc/wireguard/{interface}.conf', 'w') as f:
                f.write(wg_config)
            
            # Set proper permissions
            os.chmod(f'/etc/wireguard/{interface}.conf', 0o600)
            
            logger.info(f"✅ Wireguard interface {interface} configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring Wireguard interface: {e}")
            return False
    
    def _configure_wireguard_peers(self) -> bool:
        """Configure Wireguard peers"""
        logger.info("👥 Configuring Wireguard peers...")
        
        wireguard_config = self.config.get('wireguard', {})
        peers = wireguard_config.get('peers', [])
        interface = wireguard_config.get('interface', 'wg0')
        
        if not peers:
            logger.info("ℹ️ No Wireguard peers configured")
            return True
        
        try:
            for peer_config in peers:
                peer = WireguardPeer(
                    public_key=peer_config.get('public_key'),
                    endpoint=peer_config.get('endpoint'),
                    allowed_ips=peer_config.get('allowed_ips', []),
                    persistent_keepalive=peer_config.get('persistent_keepalive')
                )
                
                if not peer.public_key or not peer.endpoint:
                    logger.error("❌ Peer must have public_key and endpoint")
                    continue
                
                # Add peer to config
                peer_config_text = f"""
[Peer]
PublicKey = {peer.public_key}
Endpoint = {peer.endpoint}
AllowedIPs = {', '.join(peer.allowed_ips)}
"""
                
                if peer.persistent_keepalive:
                    peer_config_text += f"PersistentKeepalive = {peer.persistent_keepalive}\n"
                
                # Append to Wireguard config
                with open(f'/etc/wireguard/{interface}.conf', 'a') as f:
                    f.write(peer_config_text)
                
                logger.info(f"✅ Added Wireguard peer: {peer.endpoint}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring Wireguard peers: {e}")
            return False
    
    def _start_wireguard(self) -> bool:
        """Start and enable Wireguard"""
        logger.info("🚀 Starting Wireguard service...")
        
        wireguard_config = self.config.get('wireguard', {})
        interface = wireguard_config.get('interface', 'wg0')
        
        try:
            # Enable and start Wireguard
            result = subprocess.run(
                ["sudo", "systemctl", "enable", "--now", f"wg-quick@{interface}"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error starting Wireguard: {result.stderr}")
                return False
            
            # Verify interface is up
            result = subprocess.run(
                ["wg", "show", interface],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                logger.info("✅ Wireguard service started successfully")
                return True
            else:
                logger.error("❌ Wireguard interface not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting Wireguard: {e}")
            return False
    
    def _configure_ingress(self) -> bool:
        """Configure ingress controller (Traefik is default in K3s)"""
        logger.info("🌐 Configuring ingress controller...")
        
        try:
            # K3s comes with Traefik by default, just verify it's running
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "kube-system", "-l", "app.kubernetes.io/name=traefik"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                logger.info("✅ Traefik ingress controller is running")
                return True
            else:
                logger.warning("⚠️ Traefik ingress controller not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking ingress controller: {e}")
            return False
    
    def validate_networking(self) -> bool:
        """Validate networking setup"""
        logger.info("🔍 Validating networking setup...")
        
        success = True
        
        # Validate MetalLB if enabled
        if self.network_config.metallb_enabled:
            if not self._validate_metallb():
                success = False
        
        # Validate Wireguard if enabled
        if self.network_config.wireguard_enabled:
            if not self._validate_wireguard():
                success = False
        
        # Test connectivity
        if not self._test_networking():
            success = False
        
        if success:
            logger.info("✅ Networking validation completed")
        else:
            logger.error("❌ Networking validation failed")
        
        return success
    
    def _validate_metallb(self) -> bool:
        """Validate MetalLB setup"""
        logger.info("🔍 Validating MetalLB...")
        
        try:
            # Check MetalLB pods
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "metallb-system", "--no-headers"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Error checking MetalLB pods")
                return False
            
            pods = result.stdout.strip().split('\n')
            running_pods = sum(1 for pod in pods if 'Running' in pod)
            total_pods = len(pods) if pods != [''] else 0
            
            if running_pods != total_pods:
                logger.error(f"❌ Not all MetalLB pods are running: {running_pods}/{total_pods}")
                return False
            
            # Check IP pools
            result = subprocess.run(
                ["kubectl", "get", "ipaddresspool", "-n", "metallb-system"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Error checking IP address pools")
                return False
            
            logger.info("✅ MetalLB validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ MetalLB validation failed: {e}")
            return False
    
    def _validate_wireguard(self) -> bool:
        """Validate Wireguard setup"""
        logger.info("🔍 Validating Wireguard...")
        
        wireguard_config = self.config.get('wireguard', {})
        interface = wireguard_config.get('interface', 'wg0')
        
        try:
            # Check if Wireguard interface is up
            result = subprocess.run(
                ["wg", "show", interface],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Wireguard interface {interface} not found")
                return False
            
            # Check service status
            result = subprocess.run(
                ["systemctl", "is-active", f"wg-quick@{interface}"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0 or result.stdout.strip() != 'active':
                logger.error(f"❌ Wireguard service not active")
                return False
            
            logger.info("✅ Wireguard validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Wireguard validation failed: {e}")
            return False
    
    def _test_networking(self) -> bool:
        """Test basic networking functionality"""
        logger.info("🧪 Testing networking functionality...")
        
        try:
            # Create a test service to validate load balancer
            if self.network_config.metallb_enabled:
                if not self._test_metallb_service():
                    return False
            
            logger.info("✅ Networking tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Networking tests failed: {e}")
            return False
    
    def _test_metallb_service(self) -> bool:
        """Test MetalLB with a sample service"""
        logger.info("🧪 Testing MetalLB with sample service...")
        
        test_service_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: metallb-test-service
  namespace: default
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: metallb-test
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metallb-test-deployment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: metallb-test
  template:
    metadata:
      labels:
        app: metallb-test
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
"""
        
        try:
            # Create test service
            with open('/tmp/metallb-test.yaml', 'w') as f:
                f.write(test_service_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/metallb-test.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating test service: {result.stderr}")
                return False
            
            # Wait for external IP assignment
            for i in range(30):  # Wait up to 30 seconds
                result = subprocess.run(
                    ["kubectl", "get", "service", "metallb-test-service", "-o", "jsonpath={.status.loadBalancer.ingress[0].ip}"],
                    capture_output=True, text=True, timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    external_ip = result.stdout.strip()
                    logger.info(f"✅ MetalLB assigned external IP: {external_ip}")
                    break
                    
                time.sleep(1)
            else:
                logger.error("❌ MetalLB failed to assign external IP")
                return False
            
            # Clean up test service
            subprocess.run(
                ["kubectl", "delete", "-f", "/tmp/metallb-test.yaml"],
                capture_output=True, timeout=30
            )
            
            os.remove('/tmp/metallb-test.yaml')
            
            logger.info("✅ MetalLB test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ MetalLB test failed: {e}")
            return False
    
    def get_network_status(self) -> Dict:
        """Get current networking configuration status"""
        status = {
            'metallb': {
                'enabled': self.network_config.metallb_enabled,
                'deployed': self.network_config.metallb_deployed,
            },
            'wireguard': {
                'enabled': self.network_config.wireguard_enabled,
                'configured': self.network_config.wireguard_configured,
            },
            'ingress': {
                'configured': self.network_config.ingress_configured,
            }
        }
        
        # Add Wireguard public key if configured
        if hasattr(self, 'wireguard_public_key'):
            status['wireguard']['public_key'] = self.wireguard_public_key
        
        return status