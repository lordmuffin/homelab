#!/usr/bin/env python3
"""
Backup and Restore Module for K3s Intelligent Installer

This module handles:
- Cluster state backups (etcd snapshots)
- Application data backups
- S3/remote backup destinations
- Scheduled backup management
- Disaster recovery and restore procedures
- Backup validation and integrity checks
"""

import os
import subprocess
import logging
import json
import time
import yaml
import shutil
import tarfile
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """Backup configuration dataclass"""
    enabled: bool = False
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    retention: str = "30d"
    local_enabled: bool = False
    s3_enabled: bool = False
    remote_enabled: bool = False

@dataclass
class BackupJob:
    """Backup job information"""
    timestamp: str
    backup_type: str
    status: str
    size_mb: float
    location: str
    checksum: str

class BackupManager:
    """Backup and restore management class"""
    
    def __init__(self, config: Dict):
        self.config = config.get('backup', {})
        self.k3s_config = config.get('k3s', {})
        self.backup_config = BackupConfig(
            enabled=self.config.get('enabled', False),
            schedule=self.config.get('schedule', '0 2 * * *'),
            retention=self.config.get('retention', '30d')
        )
        self.backup_history: List[BackupJob] = []
        
    def setup_backup_system(self) -> bool:
        """Setup backup system"""
        if not self.backup_config.enabled:
            logger.info("ℹ️ Backup system disabled")
            return True
            
        logger.info("💾 Setting up backup system...")
        
        try:
            # Create backup directories
            if not self._create_backup_directories():
                return False
            
            # Setup backup destinations
            if not self._setup_backup_destinations():
                return False
            
            # Setup scheduled backups
            if not self._setup_backup_schedule():
                return False
            
            # Create initial backup
            if not self._create_initial_backup():
                return False
            
            logger.info("✅ Backup system setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up backup system: {e}")
            return False
    
    def _create_backup_directories(self) -> bool:
        """Create backup directories"""
        logger.info("📁 Creating backup directories...")
        
        destinations = self.config.get('destinations', {})
        
        try:
            # Local backup directory
            local_config = destinations.get('local', {})
            if local_config.get('enabled', False):
                backup_path = local_config.get('path', '/var/backups/k3s')
                Path(backup_path).mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ Local backup directory created: {backup_path}")
                self.backup_config.local_enabled = True
            
            # Create temporary backup directory
            Path('/tmp/k3s-backups').mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating backup directories: {e}")
            return False
    
    def _setup_backup_destinations(self) -> bool:
        """Setup backup destinations"""
        logger.info("🎯 Setting up backup destinations...")
        
        destinations = self.config.get('destinations', {})
        success = True
        
        # Setup S3 destination
        s3_config = destinations.get('s3', {})
        if s3_config.get('enabled', False):
            if self._setup_s3_destination(s3_config):
                self.backup_config.s3_enabled = True
            else:
                success = False
        
        # Setup remote destination
        remote_config = destinations.get('remote', {})
        if remote_config.get('enabled', False):
            if self._setup_remote_destination(remote_config):
                self.backup_config.remote_enabled = True
            else:
                success = False
        
        return success
    
    def _setup_s3_destination(self, s3_config: Dict) -> bool:
        """Setup S3 backup destination"""
        logger.info("☁️ Setting up S3 backup destination...")
        
        try:
            # Install AWS CLI if not present
            try:
                subprocess.run(["aws", "--version"], capture_output=True, check=True, timeout=10)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.info("📦 Installing AWS CLI...")
                if not self._install_aws_cli():
                    return False
            
            # Configure AWS credentials
            if not self._configure_aws_credentials(s3_config):
                return False
            
            # Test S3 connectivity
            if not self._test_s3_connection(s3_config):
                return False
            
            logger.info("✅ S3 backup destination configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up S3 destination: {e}")
            return False
    
    def _install_aws_cli(self) -> bool:
        """Install AWS CLI"""
        try:
            # Download and install AWS CLI
            commands = [
                "curl -L https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscliv2.zip",
                "cd /tmp && unzip -q awscliv2.zip",
                "sudo /tmp/aws/install --update"
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"❌ Error installing AWS CLI: {result.stderr}")
                    return False
            
            logger.info("✅ AWS CLI installed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error installing AWS CLI: {e}")
            return False
    
    def _configure_aws_credentials(self, s3_config: Dict) -> bool:
        """Configure AWS credentials"""
        try:
            access_key = s3_config.get('access_key', '')
            secret_key = s3_config.get('secret_key', '')
            region = s3_config.get('region', 'us-east-1')
            
            if not access_key or not secret_key:
                logger.error("❌ S3 access key and secret key are required")
                return False
            
            # Configure AWS credentials
            aws_dir = Path.home() / '.aws'
            aws_dir.mkdir(exist_ok=True)
            
            credentials_content = f"""[default]
aws_access_key_id = {access_key}
aws_secret_access_key = {secret_key}
"""
            
            config_content = f"""[default]
region = {region}
output = json
"""
            
            with open(aws_dir / 'credentials', 'w') as f:
                f.write(credentials_content)
            
            with open(aws_dir / 'config', 'w') as f:
                f.write(config_content)
            
            # Set proper permissions
            os.chmod(aws_dir / 'credentials', 0o600)
            os.chmod(aws_dir / 'config', 0o600)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring AWS credentials: {e}")
            return False
    
    def _test_s3_connection(self, s3_config: Dict) -> bool:
        """Test S3 connection"""
        try:
            bucket = s3_config.get('bucket', '')
            if not bucket:
                logger.error("❌ S3 bucket name is required")
                return False
            
            # Test bucket access
            result = subprocess.run(
                ["aws", "s3", "ls", f"s3://{bucket}/"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Cannot access S3 bucket: {result.stderr}")
                return False
            
            logger.info(f"✅ S3 bucket '{bucket}' accessible")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing S3 connection: {e}")
            return False
    
    def _setup_remote_destination(self, remote_config: Dict) -> bool:
        """Setup remote backup destination (SSH/rsync)"""
        logger.info("🌐 Setting up remote backup destination...")
        
        try:
            host = remote_config.get('host', '')
            user = remote_config.get('user', '')
            path = remote_config.get('path', '')
            ssh_key = remote_config.get('ssh_key', '')
            
            if not all([host, user, path]):
                logger.error("❌ Remote host, user, and path are required")
                return False
            
            # Test SSH connection
            ssh_cmd = ["ssh"]
            if ssh_key:
                ssh_cmd.extend(["-i", ssh_key])
            ssh_cmd.extend([f"{user}@{host}", "echo 'SSH connection test'"])
            
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"❌ Cannot connect to remote host: {result.stderr}")
                return False
            
            # Test remote path
            mkdir_cmd = ["ssh"]
            if ssh_key:
                mkdir_cmd.extend(["-i", ssh_key])
            mkdir_cmd.extend([f"{user}@{host}", f"mkdir -p {path}"])
            
            subprocess.run(mkdir_cmd, capture_output=True, text=True, timeout=30)
            
            logger.info(f"✅ Remote backup destination configured: {user}@{host}:{path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up remote destination: {e}")
            return False
    
    def _setup_backup_schedule(self) -> bool:
        """Setup scheduled backups using cron"""
        logger.info("⏰ Setting up backup schedule...")
        
        try:
            # Create backup script
            backup_script_path = "/usr/local/bin/k3s-backup.sh"
            script_content = f"""#!/bin/bash
# K3s Backup Script
# Generated by K3s Intelligent Installer

cd {os.path.dirname(os.path.abspath(__file__))}/../..
python3 k3s_installer.py --backup-only --config config/config.yaml
"""
            
            with open(backup_script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(backup_script_path, 0o755)
            
            # Add cron job
            cron_entry = f"{self.backup_config.schedule} root {backup_script_path} >> /var/log/k3s-backup.log 2>&1"
            
            with open('/etc/cron.d/k3s-backup', 'w') as f:
                f.write(f"# K3s Backup Schedule\n{cron_entry}\n")
            
            logger.info(f"✅ Backup scheduled: {self.backup_config.schedule}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up backup schedule: {e}")
            return False
    
    def _create_initial_backup(self) -> bool:
        """Create initial backup to test the system"""
        logger.info("💾 Creating initial backup...")
        
        return self.create_backup(backup_type='initial')
    
    def create_backup(self, backup_type: str = 'manual') -> bool:
        """Create a new backup"""
        logger.info(f"💾 Creating {backup_type} backup...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_backup_dir = f"/tmp/k3s-backups/{timestamp}"
        
        try:
            # Create temporary backup directory
            Path(temp_backup_dir).mkdir(parents=True, exist_ok=True)
            
            # Create etcd snapshot
            if not self._create_etcd_snapshot(temp_backup_dir):
                return False
            
            # Backup K3s configuration
            if not self._backup_k3s_config(temp_backup_dir):
                return False
            
            # Backup certificates
            if not self._backup_certificates(temp_backup_dir):
                return False
            
            # Backup persistent volumes
            if not self._backup_persistent_volumes(temp_backup_dir):
                logger.warning("⚠️ Some PV backups may have failed")
            
            # Create backup archive
            archive_path = f"{temp_backup_dir}.tar.gz"
            if not self._create_backup_archive(temp_backup_dir, archive_path):
                return False
            
            # Calculate checksum
            checksum = self._calculate_checksum(archive_path)
            
            # Get archive size
            size_mb = os.path.getsize(archive_path) / (1024 * 1024)
            
            # Upload to destinations
            backup_locations = []
            if not self._upload_backup(archive_path, backup_locations):
                logger.warning("⚠️ Some backup uploads failed")
            
            # Record backup job
            backup_job = BackupJob(
                timestamp=timestamp,
                backup_type=backup_type,
                status='completed',
                size_mb=round(size_mb, 2),
                location=','.join(backup_locations),
                checksum=checksum
            )
            self.backup_history.append(backup_job)
            
            # Clean up temporary files
            shutil.rmtree(temp_backup_dir, ignore_errors=True)
            if os.path.exists(archive_path):
                os.remove(archive_path)
            
            logger.info(f"✅ Backup completed: {timestamp} ({size_mb:.1f}MB)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            # Clean up on failure
            shutil.rmtree(temp_backup_dir, ignore_errors=True)
            return False
    
    def _create_etcd_snapshot(self, backup_dir: str) -> bool:
        """Create etcd snapshot"""
        logger.info("📊 Creating etcd snapshot...")
        
        try:
            snapshot_path = f"{backup_dir}/etcd-snapshot.db"
            
            # K3s etcd snapshot command
            result = subprocess.run([
                "k3s", "etcd-snapshot", "save", snapshot_path
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"❌ Error creating etcd snapshot: {result.stderr}")
                return False
            
            logger.info("✅ etcd snapshot created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating etcd snapshot: {e}")
            return False
    
    def _backup_k3s_config(self, backup_dir: str) -> bool:
        """Backup K3s configuration files"""
        logger.info("⚙️ Backing up K3s configuration...")
        
        try:
            config_dir = f"{backup_dir}/config"
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            
            # Backup important K3s files
            files_to_backup = [
                '/etc/rancher/k3s/config.yaml',
                '/var/lib/rancher/k3s/server/token',
                '/var/lib/rancher/k3s/server/node-token',
                '/etc/rancher/k3s/registries.yaml'
            ]
            
            for file_path in files_to_backup:
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    shutil.copy2(file_path, f"{config_dir}/{filename}")
                    logger.info(f"✅ Backed up {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error backing up K3s config: {e}")
            return False
    
    def _backup_certificates(self, backup_dir: str) -> bool:
        """Backup certificates and keys"""
        logger.info("🔐 Backing up certificates...")
        
        try:
            certs_dir = f"{backup_dir}/certificates"
            Path(certs_dir).mkdir(parents=True, exist_ok=True)
            
            # Backup K3s server certificates
            cert_paths = [
                '/var/lib/rancher/k3s/server/tls',
                '/etc/ssl/certs/k3s'  # Custom certificates if they exist
            ]
            
            for cert_path in cert_paths:
                if os.path.exists(cert_path):
                    dest_path = f"{certs_dir}/{os.path.basename(cert_path)}"
                    if os.path.isdir(cert_path):
                        shutil.copytree(cert_path, dest_path, ignore_errors=True)
                    else:
                        shutil.copy2(cert_path, dest_path)
            
            logger.info("✅ Certificates backed up")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error backing up certificates: {e}")
            return False
    
    def _backup_persistent_volumes(self, backup_dir: str) -> bool:
        """Backup persistent volume data"""
        logger.info("💽 Backing up persistent volumes...")
        
        try:
            pvs_dir = f"{backup_dir}/persistent-volumes"
            Path(pvs_dir).mkdir(parents=True, exist_ok=True)
            
            # Get list of persistent volumes
            result = subprocess.run([
                "kubectl", "get", "pv", "-o", "json"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.warning("⚠️ Could not get persistent volumes list")
                return True  # Don't fail the entire backup
            
            pvs_data = json.loads(result.stdout)
            
            for pv in pvs_data.get('items', []):
                pv_name = pv.get('metadata', {}).get('name', '')
                spec = pv.get('spec', {})
                
                # Handle local path volumes (most common in single-node K3s)
                if 'hostPath' in spec:
                    host_path = spec['hostPath']['path']
                    if os.path.exists(host_path):
                        # Create tar archive of the volume data
                        archive_name = f"{pvs_dir}/pv-{pv_name}.tar.gz"
                        try:
                            with tarfile.open(archive_name, "w:gz") as tar:
                                tar.add(host_path, arcname=pv_name)
                            logger.info(f"✅ Backed up PV: {pv_name}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not backup PV {pv_name}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error backing up persistent volumes: {e}")
            return False
    
    def _create_backup_archive(self, backup_dir: str, archive_path: str) -> bool:
        """Create backup archive"""
        logger.info("📦 Creating backup archive...")
        
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=os.path.basename(backup_dir))
            
            logger.info(f"✅ Backup archive created: {archive_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating backup archive: {e}")
            return False
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _upload_backup(self, archive_path: str, locations: List[str]) -> bool:
        """Upload backup to configured destinations"""
        logger.info("⬆️ Uploading backup to destinations...")
        
        success = True
        destinations = self.config.get('destinations', {})
        
        # Upload to local destination
        local_config = destinations.get('local', {})
        if local_config.get('enabled', False):
            if self._upload_to_local(archive_path, local_config):
                locations.append('local')
            else:
                success = False
        
        # Upload to S3
        s3_config = destinations.get('s3', {})
        if s3_config.get('enabled', False):
            if self._upload_to_s3(archive_path, s3_config):
                locations.append('s3')
            else:
                success = False
        
        # Upload to remote
        remote_config = destinations.get('remote', {})
        if remote_config.get('enabled', False):
            if self._upload_to_remote(archive_path, remote_config):
                locations.append('remote')
            else:
                success = False
        
        return success
    
    def _upload_to_local(self, archive_path: str, local_config: Dict) -> bool:
        """Upload backup to local destination"""
        try:
            backup_path = local_config.get('path', '/var/backups/k3s')
            filename = os.path.basename(archive_path)
            destination = f"{backup_path}/{filename}"
            
            shutil.copy2(archive_path, destination)
            logger.info(f"✅ Backup uploaded to local: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error uploading to local destination: {e}")
            return False
    
    def _upload_to_s3(self, archive_path: str, s3_config: Dict) -> bool:
        """Upload backup to S3"""
        try:
            bucket = s3_config.get('bucket', '')
            filename = os.path.basename(archive_path)
            s3_key = f"k3s-backups/{filename}"
            
            result = subprocess.run([
                "aws", "s3", "cp", archive_path, f"s3://{bucket}/{s3_key}"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"❌ Error uploading to S3: {result.stderr}")
                return False
            
            logger.info(f"✅ Backup uploaded to S3: s3://{bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error uploading to S3: {e}")
            return False
    
    def _upload_to_remote(self, archive_path: str, remote_config: Dict) -> bool:
        """Upload backup to remote destination"""
        try:
            host = remote_config.get('host', '')
            user = remote_config.get('user', '')
            path = remote_config.get('path', '')
            ssh_key = remote_config.get('ssh_key', '')
            
            filename = os.path.basename(archive_path)
            
            rsync_cmd = ["rsync", "-avz"]
            if ssh_key:
                rsync_cmd.extend(["-e", f"ssh -i {ssh_key}"])
            
            rsync_cmd.extend([archive_path, f"{user}@{host}:{path}/{filename}"])
            
            result = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"❌ Error uploading to remote: {result.stderr}")
                return False
            
            logger.info(f"✅ Backup uploaded to remote: {user}@{host}:{path}/{filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error uploading to remote: {e}")
            return False
    
    def restore_backup(self, backup_identifier: str) -> bool:
        """Restore from backup"""
        logger.info(f"🔄 Restoring from backup: {backup_identifier}")
        
        # This is a complex operation that should be implemented carefully
        # For now, provide a framework and log the process
        
        logger.warning("⚠️ Backup restoration is a critical operation!")
        logger.info("📋 Restoration process:")
        logger.info("1. Stop K3s service")
        logger.info("2. Download and extract backup archive")
        logger.info("3. Restore etcd snapshot")
        logger.info("4. Restore configuration files")
        logger.info("5. Restore certificates")
        logger.info("6. Restore persistent volume data")
        logger.info("7. Start K3s service")
        logger.info("8. Validate cluster state")
        
        # TODO: Implement actual restoration logic
        logger.error("❌ Backup restoration not yet implemented")
        return False
    
    def cleanup_old_backups(self) -> bool:
        """Clean up old backups based on retention policy"""
        logger.info("🧹 Cleaning up old backups...")
        
        try:
            retention = self.backup_config.retention
            
            # Parse retention period (e.g., "30d", "7d")
            if retention.endswith('d'):
                days = int(retention[:-1])
                cutoff_date = datetime.now() - timedelta(days=days)
            else:
                logger.warning(f"⚠️ Unknown retention format: {retention}")
                return True
            
            destinations = self.config.get('destinations', {})
            
            # Cleanup local backups
            local_config = destinations.get('local', {})
            if local_config.get('enabled', False):
                self._cleanup_local_backups(local_config, cutoff_date)
            
            # Cleanup S3 backups
            s3_config = destinations.get('s3', {})
            if s3_config.get('enabled', False):
                self._cleanup_s3_backups(s3_config, cutoff_date)
            
            logger.info("✅ Backup cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up backups: {e}")
            return False
    
    def _cleanup_local_backups(self, local_config: Dict, cutoff_date: datetime) -> None:
        """Cleanup local backups"""
        try:
            backup_path = Path(local_config.get('path', '/var/backups/k3s'))
            
            if not backup_path.exists():
                return
            
            for backup_file in backup_path.glob('*.tar.gz'):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    logger.info(f"🗑️ Removed old local backup: {backup_file.name}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning up local backups: {e}")
    
    def _cleanup_s3_backups(self, s3_config: Dict, cutoff_date: datetime) -> None:
        """Cleanup S3 backups"""
        try:
            bucket = s3_config.get('bucket', '')
            
            # List S3 objects
            result = subprocess.run([
                "aws", "s3", "ls", f"s3://{bucket}/k3s-backups/", "--recursive"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 4:
                    date_str = f"{parts[0]} {parts[1]}"
                    file_key = ' '.join(parts[3:])
                    
                    try:
                        file_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        if file_date < cutoff_date:
                            subprocess.run([
                                "aws", "s3", "rm", f"s3://{bucket}/{file_key}"
                            ], capture_output=True, timeout=60)
                            logger.info(f"🗑️ Removed old S3 backup: {file_key}")
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning up S3 backups: {e}")
    
    def get_backup_status(self) -> Dict:
        """Get backup system status"""
        return {
            'enabled': self.backup_config.enabled,
            'schedule': self.backup_config.schedule,
            'retention': self.backup_config.retention,
            'destinations': {
                'local': self.backup_config.local_enabled,
                's3': self.backup_config.s3_enabled,
                'remote': self.backup_config.remote_enabled
            },
            'backup_history': [
                {
                    'timestamp': job.timestamp,
                    'type': job.backup_type,
                    'status': job.status,
                    'size_mb': job.size_mb,
                    'checksum': job.checksum[:16] + '...'  # Truncate for display
                } for job in self.backup_history[-10:]  # Show last 10 backups
            ]
        }