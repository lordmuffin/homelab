#!/usr/bin/env python3
"""
TLS Certificate Management Module for K3s Intelligent Installer

This module handles:
- cert-manager installation and configuration
- Let's Encrypt integration
- Custom CA certificate management
- Certificate generation and rotation
- DNS and HTTP challenge setup
"""

import os
import subprocess
import logging
import json
import time
import yaml
import base64
import ipaddress
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

logger = logging.getLogger(__name__)

@dataclass
class TLSConfig:
    """TLS configuration dataclass"""
    cert_manager_enabled: bool = False
    cert_manager_deployed: bool = False
    auto_generate: bool = False
    certificates_created: bool = False

class TLSManager:
    """TLS certificate management class"""
    
    def __init__(self, config: Dict):
        self.config = config.get('tls', {})
        self.k3s_config = config.get('k3s', {})
        self.tls_config = TLSConfig()
        
    def setup_tls(self) -> bool:
        """Main method to setup TLS certificates"""
        logger.info("🔐 Setting up TLS certificate management...")
        
        success = True
        
        # Setup cert-manager if enabled
        cert_manager_config = self.config.get('cert_manager', {})
        if cert_manager_config.get('enabled', False):
            if not self._setup_cert_manager():
                success = False
            else:
                self.tls_config.cert_manager_enabled = True
                self.tls_config.cert_manager_deployed = True
        
        # Generate certificates if auto_generate is enabled
        if self.config.get('auto_generate', False):
            if not self._generate_certificates():
                success = False
            else:
                self.tls_config.auto_generate = True
                self.tls_config.certificates_created = True
        
        if success:
            logger.info("✅ TLS setup completed")
        else:
            logger.error("❌ TLS setup failed")
        
        return success
    
    def _setup_cert_manager(self) -> bool:
        """Setup cert-manager for certificate management"""
        logger.info("📜 Setting up cert-manager...")
        
        cert_manager_config = self.config.get('cert_manager', {})
        version = cert_manager_config.get('version', 'v1.15.3')
        
        try:
            # Deploy cert-manager
            if not self._deploy_cert_manager(version):
                return False
            
            # Wait for cert-manager to be ready
            if not self._wait_for_cert_manager_ready():
                return False
            
            # Setup ClusterIssuer
            if not self._setup_cluster_issuer():
                return False
            
            logger.info("✅ cert-manager setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up cert-manager: {e}")
            return False
    
    def _deploy_cert_manager(self, version: str) -> bool:
        """Deploy cert-manager"""
        logger.info(f"🚀 Deploying cert-manager {version}...")
        
        try:
            # Install cert-manager CRDs
            crds_url = f"https://github.com/cert-manager/cert-manager/releases/download/{version}/cert-manager.crds.yaml"
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", crds_url],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error installing cert-manager CRDs: {result.stderr}")
                return False
            
            # Install cert-manager
            manifest_url = f"https://github.com/cert-manager/cert-manager/releases/download/{version}/cert-manager.yaml"
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", manifest_url],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error deploying cert-manager: {result.stderr}")
                return False
            
            logger.info("✅ cert-manager deployed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deploying cert-manager: {e}")
            return False
    
    def _wait_for_cert_manager_ready(self, timeout: int = 300) -> bool:
        """Wait for cert-manager to be ready"""
        logger.info("⏳ Waiting for cert-manager to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "cert-manager", "-o", "json"],
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
                        
                        logger.info(f"⏳ cert-manager pods ready: {ready_pods}/{total_pods}")
                        
                        if ready_pods == total_pods:
                            logger.info("✅ cert-manager is ready!")
                            return True
                
            except Exception as e:
                logger.warning(f"⚠️ Error checking cert-manager status: {e}")
            
            time.sleep(10)
        
        logger.error("❌ Timeout waiting for cert-manager to be ready")
        return False
    
    def _setup_cluster_issuer(self) -> bool:
        """Setup ClusterIssuer for Let's Encrypt"""
        logger.info("🌐 Setting up ClusterIssuer for Let's Encrypt...")
        
        cert_manager_config = self.config.get('cert_manager', {})
        email = cert_manager_config.get('email', 'admin@example.com')
        
        # Setup Let's Encrypt staging issuer
        staging_issuer = self._create_letsencrypt_issuer('letsencrypt-staging', email, staging=True)
        if not self._apply_issuer(staging_issuer, 'letsencrypt-staging'):
            return False
        
        # Setup Let's Encrypt production issuer
        prod_issuer = self._create_letsencrypt_issuer('letsencrypt-prod', email, staging=False)
        if not self._apply_issuer(prod_issuer, 'letsencrypt-prod'):
            return False
        
        # Setup DNS challenge issuer if configured
        dns_challenge = cert_manager_config.get('dns_challenge', {})
        if dns_challenge.get('enabled', False):
            dns_issuer = self._create_dns_challenge_issuer(email, dns_challenge)
            if dns_issuer and not self._apply_issuer(dns_issuer, 'letsencrypt-dns'):
                return False
        
        logger.info("✅ ClusterIssuers configured")
        return True
    
    def _create_letsencrypt_issuer(self, name: str, email: str, staging: bool = False) -> str:
        """Create Let's Encrypt ClusterIssuer YAML"""
        
        server_url = (
            "https://acme-staging-v02.api.letsencrypt.org/directory" if staging 
            else "https://acme-v02.api.letsencrypt.org/directory"
        )
        
        issuer_yaml = f"""
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: {name}
spec:
  acme:
    server: {server_url}
    email: {email}
    privateKeySecretRef:
      name: {name}
    solvers:
    - http01:
        ingress:
          class: traefik
"""
        
        return issuer_yaml
    
    def _create_dns_challenge_issuer(self, email: str, dns_config: Dict) -> Optional[str]:
        """Create DNS challenge ClusterIssuer"""
        
        provider = dns_config.get('provider', 'cloudflare')
        credentials_secret = dns_config.get('credentials_secret', 'cloudflare-api-token')
        
        if provider == 'cloudflare':
            issuer_yaml = f"""
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-dns
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: {email}
    privateKeySecretRef:
      name: letsencrypt-dns
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: {credentials_secret}
            key: api-token
"""
            return issuer_yaml
            
        elif provider == 'route53':
            issuer_yaml = f"""
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-dns
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: {email}
    privateKeySecretRef:
      name: letsencrypt-dns
    solvers:
    - dns01:
        route53:
          region: us-east-1
          accessKeyIDSecretRef:
            name: {credentials_secret}
            key: access-key-id
          secretAccessKeySecretRef:
            name: {credentials_secret}
            key: secret-access-key
"""
            return issuer_yaml
        
        else:
            logger.error(f"❌ Unsupported DNS provider: {provider}")
            return None
    
    def _apply_issuer(self, issuer_yaml: str, name: str) -> bool:
        """Apply ClusterIssuer to the cluster"""
        
        try:
            with open(f'/tmp/issuer-{name}.yaml', 'w') as f:
                f.write(issuer_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", f"/tmp/issuer-{name}.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error applying issuer {name}: {result.stderr}")
                return False
            
            os.remove(f'/tmp/issuer-{name}.yaml')
            
            logger.info(f"✅ ClusterIssuer '{name}' created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying issuer {name}: {e}")
            return False
    
    def _generate_certificates(self) -> bool:
        """Generate self-signed certificates for development"""
        logger.info("📜 Generating self-signed certificates...")
        
        try:
            # Generate CA certificate
            ca_key, ca_cert = self._generate_ca_certificate()
            
            # Generate server certificate
            server_key, server_cert = self._generate_server_certificate(ca_key, ca_cert)
            
            # Create Kubernetes secrets
            if not self._create_certificate_secrets(ca_cert, server_key, server_cert):
                return False
            
            logger.info("✅ Self-signed certificates generated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating certificates: {e}")
            return False
    
    def _generate_ca_certificate(self) -> Tuple:
        """Generate CA certificate and private key"""
        logger.info("🔑 Generating CA certificate...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "K3s Cluster"),
            x509.NameAttribute(NameOID.COMMON_NAME, "K3s CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        return private_key, cert
    
    def _generate_server_certificate(self, ca_key, ca_cert) -> Tuple:
        """Generate server certificate signed by CA"""
        logger.info("🔐 Generating server certificate...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "K3s Cluster"),
            x509.NameAttribute(NameOID.COMMON_NAME, "k3s.local"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("k3s.local"),
                x509.DNSName("*.k3s.local"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256())
        
        return private_key, cert
    
    def _create_certificate_secrets(self, ca_cert, server_key, server_cert) -> bool:
        """Create Kubernetes secrets with certificates"""
        logger.info("🗝️ Creating certificate secrets...")
        
        try:
            # Serialize certificates
            ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM)
            server_cert_pem = server_cert.public_bytes(serialization.Encoding.PEM)
            server_key_pem = server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Create CA secret
            ca_secret_yaml = f"""
apiVersion: v1
kind: Secret
metadata:
  name: k3s-ca-certificate
  namespace: kube-system
type: Opaque
data:
  ca.crt: {base64.b64encode(ca_cert_pem).decode()}
"""
            
            # Create server certificate secret
            server_secret_yaml = f"""
apiVersion: v1
kind: Secret
metadata:
  name: k3s-server-certificate
  namespace: kube-system
type: kubernetes.io/tls
data:
  tls.crt: {base64.b64encode(server_cert_pem).decode()}
  tls.key: {base64.b64encode(server_key_pem).decode()}
  ca.crt: {base64.b64encode(ca_cert_pem).decode()}
"""
            
            # Apply secrets
            with open('/tmp/ca-secret.yaml', 'w') as f:
                f.write(ca_secret_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/ca-secret.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating CA secret: {result.stderr}")
                return False
            
            with open('/tmp/server-secret.yaml', 'w') as f:
                f.write(server_secret_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", "/tmp/server-secret.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating server secret: {result.stderr}")
                return False
            
            # Clean up temporary files
            os.remove('/tmp/ca-secret.yaml')
            os.remove('/tmp/server-secret.yaml')
            
            logger.info("✅ Certificate secrets created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating certificate secrets: {e}")
            return False
    
    def create_certificate(self, name: str, namespace: str, hosts: List[str], issuer: str = 'letsencrypt-prod') -> bool:
        """Create a certificate using cert-manager"""
        logger.info(f"📜 Creating certificate '{name}' for hosts: {hosts}")
        
        certificate_yaml = f"""
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: {name}
  namespace: {namespace}
spec:
  secretName: {name}-tls
  issuerRef:
    name: {issuer}
    kind: ClusterIssuer
  dnsNames:
{yaml.dump(hosts, default_flow_style=False, indent=2).rstrip()}
"""
        
        try:
            with open(f'/tmp/certificate-{name}.yaml', 'w') as f:
                f.write(certificate_yaml)
            
            result = subprocess.run(
                ["kubectl", "apply", "-f", f"/tmp/certificate-{name}.yaml"],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating certificate: {result.stderr}")
                return False
            
            os.remove(f'/tmp/certificate-{name}.yaml')
            
            logger.info(f"✅ Certificate '{name}' created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating certificate: {e}")
            return False
    
    def validate_tls_setup(self) -> bool:
        """Validate TLS setup"""
        logger.info("🔍 Validating TLS setup...")
        
        try:
            # Check cert-manager if enabled
            if self.tls_config.cert_manager_enabled:
                if not self._validate_cert_manager():
                    return False
            
            # Check certificates if auto-generated
            if self.tls_config.auto_generate:
                if not self._validate_certificates():
                    return False
            
            logger.info("✅ TLS validation completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ TLS validation failed: {e}")
            return False
    
    def _validate_cert_manager(self) -> bool:
        """Validate cert-manager installation"""
        logger.info("🔍 Validating cert-manager...")
        
        try:
            # Check cert-manager pods
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "cert-manager", "--no-headers"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Error checking cert-manager pods")
                return False
            
            pods = result.stdout.strip().split('\n')
            running_pods = sum(1 for pod in pods if 'Running' in pod)
            total_pods = len(pods) if pods != [''] else 0
            
            if running_pods != total_pods:
                logger.error(f"❌ Not all cert-manager pods are running: {running_pods}/{total_pods}")
                return False
            
            # Check ClusterIssuers
            result = subprocess.run(
                ["kubectl", "get", "clusterissuer"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error("❌ Error checking ClusterIssuers")
                return False
            
            logger.info("✅ cert-manager validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ cert-manager validation failed: {e}")
            return False
    
    def _validate_certificates(self) -> bool:
        """Validate generated certificates"""
        logger.info("🔍 Validating certificates...")
        
        try:
            # Check if certificate secrets exist
            secrets = ['k3s-ca-certificate', 'k3s-server-certificate']
            
            for secret in secrets:
                result = subprocess.run(
                    ["kubectl", "get", "secret", secret, "-n", "kube-system"],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode != 0:
                    logger.error(f"❌ Certificate secret '{secret}' not found")
                    return False
            
            logger.info("✅ Certificate validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Certificate validation failed: {e}")
            return False
    
    def get_tls_status(self) -> Dict:
        """Get TLS configuration status"""
        return {
            'cert_manager': {
                'enabled': self.tls_config.cert_manager_enabled,
                'deployed': self.tls_config.cert_manager_deployed,
            },
            'certificates': {
                'auto_generate': self.tls_config.auto_generate,
                'created': self.tls_config.certificates_created,
            }
        }