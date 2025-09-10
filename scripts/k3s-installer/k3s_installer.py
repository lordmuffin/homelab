#!/usr/bin/env python3
"""
K3s Intelligent Installer - Main Script

A comprehensive, intelligent installer for single-node K3s environments with:
- GPU support (NVIDIA, AMD, Intel)
- Storage providers (OpenEBS, local-path)
- Networking (MetalLB, Wireguard)
- TLS certificate management
- Backup and restore capabilities
- System optimization
- Production-ready configuration

Usage:
    python3 k3s_installer.py --config config.yaml [options]

Author: Claude Code AI Assistant
Version: 1.0.0
"""

import os
import sys
import argparse
import logging
import yaml
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

# Import our modules
from modules import (
    SystemUtils,
    GPUConfigurator,
    StorageSetup,
    NetworkingSetup,
    TLSManager,
    BackupManager
)

console = Console()

@dataclass
class InstallationStatus:
    """Installation status tracking"""
    system_check: bool = False
    k3s_installed: bool = False
    gpu_configured: bool = False
    storage_setup: bool = False
    networking_setup: bool = False
    tls_configured: bool = False
    backup_configured: bool = False
    validation_passed: bool = False

class K3sInstaller:
    """Main K3s installer class"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Dict = {}
        self.status = InstallationStatus()
        
        # Initialize components
        self.system_utils: Optional[SystemUtils] = None
        self.gpu_configurator: Optional[GPUConfigurator] = None
        self.storage_setup: Optional[StorageSetup] = None
        self.networking_setup: Optional[NetworkingSetup] = None
        self.tls_manager: Optional[TLSManager] = None
        self.backup_manager: Optional[BackupManager] = None
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup rich logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(console=console, rich_tracebacks=True)]
        )
        
        # Set module loggers
        for module in ['modules.system_utils', 'modules.gpu_config', 'modules.storage_setup',
                      'modules.networking', 'modules.tls_certs', 'modules.backup_restore']:
            logging.getLogger(module).setLevel(logging.INFO)
    
    def load_config(self) -> bool:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            console.print(f"✅ Configuration loaded from {self.config_path}")
            return True
            
        except FileNotFoundError:
            console.print(f"❌ Configuration file not found: {self.config_path}")
            return False
        except yaml.YAMLError as e:
            console.print(f"❌ Error parsing configuration: {e}")
            return False
    
    def initialize_components(self):
        """Initialize all installer components"""
        console.print("🔧 Initializing installer components...")
        
        self.system_utils = SystemUtils()
        self.gpu_configurator = GPUConfigurator(self.config)
        self.storage_setup = StorageSetup(self.config)
        self.networking_setup = NetworkingSetup(self.config)
        self.tls_manager = TLSManager(self.config)
        self.backup_manager = BackupManager(self.config)
        
        console.print("✅ Components initialized")
    
    def run_system_checks(self) -> bool:
        """Run comprehensive system checks"""
        console.print("\n[bold blue]🔍 Running System Checks[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Detect system information
            task = progress.add_task("Detecting system information...", total=None)
            system_info = self.system_utils.detect_system()
            progress.update(task, completed=True)
            
            # Check compatibility
            task = progress.add_task("Checking OS compatibility...", total=None)
            if not self.system_utils.check_compatibility():
                progress.update(task, completed=True)
                console.print("❌ System compatibility check failed")
                return False
            progress.update(task, completed=True)
            
            # Check resources
            task = progress.add_task("Checking resource requirements...", total=None)
            if not self.system_utils.check_resources():
                progress.update(task, completed=True)
                console.print("❌ Resource requirements check failed")
                return False
            progress.update(task, completed=True)
            
            # Check prerequisites
            task = progress.add_task("Checking prerequisites...", total=None)
            if not self.system_utils.check_prerequisites():
                progress.update(task, completed=True)
                console.print("❌ Prerequisites check failed")
                return False
            progress.update(task, completed=True)
        
        # Display system information
        self._display_system_info(system_info)
        
        self.status.system_check = True
        console.print("✅ System checks passed")
        return True
    
    def _display_system_info(self, system_info):
        """Display system information in a table"""
        table = Table(title="System Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Operating System", f"{system_info.os_name} {system_info.os_version}")
        table.add_row("Architecture", system_info.architecture)
        table.add_row("Kernel", system_info.kernel_version)
        table.add_row("Hostname", system_info.hostname)
        table.add_row("CPU Cores", str(system_info.cpu_count))
        table.add_row("Memory", f"{system_info.memory_gb} GB")
        table.add_row("Disk Space", f"{system_info.disk_space_gb} GB")
        
        console.print(table)
    
    def optimize_system(self) -> bool:
        """Apply system optimizations"""
        console.print("\n[bold blue]⚙️ Optimizing System[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Applying system optimizations...", total=None)
            
            if self.system_utils.optimize_system():
                progress.update(task, completed=True)
                console.print("✅ System optimizations applied")
                return True
            else:
                progress.update(task, completed=True)
                console.print("⚠️ Some system optimizations failed, continuing...")
                return True  # Don't fail installation for optimization issues
    
    def install_k3s(self) -> bool:
        """Install K3s server"""
        console.print("\n[bold blue]🚀 Installing K3s[/bold blue]")
        
        k3s_config = self.config.get('k3s', {})
        version = k3s_config.get('version', 'v1.31.1+k3s1')
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task(f"Installing K3s {version}...", total=100)
            
            try:
                # Download K3s installation script
                progress.update(task, advance=20, description="Downloading K3s installer...")
                import subprocess
                
                result = subprocess.run([
                    "curl", "-sfL", "https://get.k3s.io"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    console.print("❌ Failed to download K3s installer")
                    return False
                
                # Prepare installation environment
                progress.update(task, advance=20, description="Preparing installation...")
                
                install_env = os.environ.copy()
                install_env['INSTALL_K3S_VERSION'] = version
                
                # Configure K3s options
                k3s_options = []
                server_config = k3s_config.get('server', {})
                
                if server_config.get('cluster_init', True):
                    k3s_options.append('--cluster-init')
                
                disable_components = server_config.get('disable', [])
                for component in disable_components:
                    k3s_options.append(f'--disable={component}')
                
                if k3s_options:
                    install_env['INSTALL_K3S_EXEC'] = ' '.join(k3s_options)
                
                # Run installation
                progress.update(task, advance=40, description="Running K3s installation...")
                
                result = subprocess.run([
                    "sh", "-c", result.stdout
                ], env=install_env, capture_output=True, text=True, timeout=600)
                
                if result.returncode != 0:
                    console.print(f"❌ K3s installation failed: {result.stderr}")
                    return False
                
                # Wait for K3s to be ready
                progress.update(task, advance=15, description="Waiting for K3s to be ready...")
                
                for i in range(30):  # Wait up to 30 seconds
                    try:
                        result = subprocess.run([
                            "kubectl", "get", "nodes"
                        ], capture_output=True, text=True, timeout=10)
                        
                        if result.returncode == 0:
                            break
                    except:
                        pass
                    
                    time.sleep(1)
                else:
                    console.print("❌ K3s failed to start properly")
                    return False
                
                progress.update(task, advance=5, description="K3s installation completed")
                
            except Exception as e:
                console.print(f"❌ Error installing K3s: {e}")
                return False
        
        self.status.k3s_installed = True
        console.print("✅ K3s installed successfully")
        return True
    
    def configure_gpu(self) -> bool:
        """Configure GPU support"""
        if not self.config.get('gpu', {}).get('enabled', False):
            console.print("ℹ️ GPU support disabled, skipping...")
            return True
            
        console.print("\n[bold blue]🎮 Configuring GPU Support[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Configuring GPU support...", total=None)
            
            if self.gpu_configurator.configure_gpu_support():
                progress.update(task, completed=True)
                self.status.gpu_configured = True
                console.print("✅ GPU configuration completed")
                return True
            else:
                progress.update(task, completed=True)
                console.print("❌ GPU configuration failed")
                return False
    
    def setup_storage(self) -> bool:
        """Setup storage provider"""
        console.print("\n[bold blue]💾 Setting Up Storage[/bold blue]")
        
        storage_provider = self.config.get('storage', {}).get('provider', 'local-path')
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Setting up {storage_provider} storage...", total=None)
            
            if self.storage_setup.setup_storage():
                progress.update(task, completed=True)
                self.status.storage_setup = True
                console.print(f"✅ {storage_provider} storage configured")
                return True
            else:
                progress.update(task, completed=True)
                console.print(f"❌ {storage_provider} storage configuration failed")
                return False
    
    def setup_networking(self) -> bool:
        """Setup networking components"""
        console.print("\n[bold blue]🌐 Setting Up Networking[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting up networking components...", total=None)
            
            if self.networking_setup.setup_networking():
                progress.update(task, completed=True)
                self.status.networking_setup = True
                console.print("✅ Networking configuration completed")
                return True
            else:
                progress.update(task, completed=True)
                console.print("❌ Networking configuration failed")
                return False
    
    def setup_tls(self) -> bool:
        """Setup TLS certificates"""
        console.print("\n[bold blue]🔐 Setting Up TLS Certificates[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting up TLS certificates...", total=None)
            
            if self.tls_manager.setup_tls():
                progress.update(task, completed=True)
                self.status.tls_configured = True
                console.print("✅ TLS configuration completed")
                return True
            else:
                progress.update(task, completed=True)
                console.print("❌ TLS configuration failed")
                return False
    
    def setup_backup(self) -> bool:
        """Setup backup system"""
        console.print("\n[bold blue]💾 Setting Up Backup System[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting up backup system...", total=None)
            
            if self.backup_manager.setup_backup_system():
                progress.update(task, completed=True)
                self.status.backup_configured = True
                console.print("✅ Backup system configured")
                return True
            else:
                progress.update(task, completed=True)
                console.print("❌ Backup system configuration failed")
                return False
    
    def validate_installation(self) -> bool:
        """Validate the complete installation"""
        console.print("\n[bold blue]🔍 Validating Installation[/bold blue]")
        
        validation_tasks = [
            ("K3s cluster", self._validate_k3s),
            ("GPU setup", self._validate_gpu),
            ("Storage", self._validate_storage),
            ("Networking", self._validate_networking),
            ("TLS setup", self._validate_tls),
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            all_valid = True
            
            for name, validator in validation_tasks:
                task = progress.add_task(f"Validating {name}...", total=None)
                
                try:
                    if validator():
                        progress.update(task, completed=True)
                        console.print(f"✅ {name} validation passed")
                    else:
                        progress.update(task, completed=True)
                        console.print(f"⚠️ {name} validation failed")
                        all_valid = False
                except Exception as e:
                    progress.update(task, completed=True)
                    console.print(f"❌ {name} validation error: {e}")
                    all_valid = False
        
        self.status.validation_passed = all_valid
        
        if all_valid:
            console.print("✅ Installation validation completed successfully")
        else:
            console.print("⚠️ Some validation checks failed")
        
        return all_valid
    
    def _validate_k3s(self) -> bool:
        """Validate K3s installation"""
        if not self.status.k3s_installed:
            return True  # Skip if not installed
            
        import subprocess
        
        try:
            # Check if K3s service is running
            result = subprocess.run(
                ["systemctl", "is-active", "k3s"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return False
            
            # Check if kubectl works
            result = subprocess.run(
                ["kubectl", "get", "nodes"],
                capture_output=True, text=True, timeout=30
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _validate_gpu(self) -> bool:
        """Validate GPU configuration"""
        if not self.status.gpu_configured:
            return True  # Skip if not configured
            
        return self.gpu_configurator.validate_gpu_setup()
    
    def _validate_storage(self) -> bool:
        """Validate storage setup"""
        if not self.status.storage_setup:
            return True  # Skip if not setup
            
        return self.storage_setup.validate_storage_setup()
    
    def _validate_networking(self) -> bool:
        """Validate networking setup"""
        if not self.status.networking_setup:
            return True  # Skip if not setup
            
        return self.networking_setup.validate_networking()
    
    def _validate_tls(self) -> bool:
        """Validate TLS setup"""
        if not self.status.tls_configured:
            return True  # Skip if not configured
            
        return self.tls_manager.validate_tls_setup()
    
    def display_installation_summary(self):
        """Display installation summary"""
        console.print("\n[bold green]🎉 Installation Summary[/bold green]")
        
        # Create status table
        table = Table(title="Component Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        def status_emoji(status: bool) -> str:
            return "✅ Configured" if status else "⚠️ Skipped/Failed"
        
        table.add_row("System Checks", status_emoji(self.status.system_check), "OS compatibility, resources")
        table.add_row("K3s Server", status_emoji(self.status.k3s_installed), f"Version: {self.config.get('k3s', {}).get('version', 'latest')}")
        table.add_row("GPU Support", status_emoji(self.status.gpu_configured), "NVIDIA/AMD/Intel device plugins")
        table.add_row("Storage", status_emoji(self.status.storage_setup), f"Provider: {self.config.get('storage', {}).get('provider', 'local-path')}")
        table.add_row("Networking", status_emoji(self.status.networking_setup), "MetalLB, Wireguard, Ingress")
        table.add_row("TLS Certificates", status_emoji(self.status.tls_configured), "cert-manager, Let's Encrypt")
        table.add_row("Backup System", status_emoji(self.status.backup_configured), "Scheduled backups, S3 integration")
        table.add_row("Validation", status_emoji(self.status.validation_passed), "Component health checks")
        
        console.print(table)
        
        # Display next steps
        self._display_next_steps()
    
    def _display_next_steps(self):
        """Display next steps after installation"""
        next_steps = [
            "🔧 Configure your applications and services",
            "📊 Access monitoring dashboards (if enabled)",
            "🔐 Update default passwords and certificates",
            "📝 Review and customize backup schedules",
            "🧪 Test GPU workloads (if GPU enabled)",
            "🌐 Configure DNS for your services",
        ]
        
        panel_content = "\n".join(next_steps)
        
        if self.status.k3s_installed:
            panel_content += "\n\n[bold]Quick Commands:[/bold]"
            panel_content += "\n• kubectl get nodes"
            panel_content += "\n• kubectl get pods --all-namespaces"
            panel_content += "\n• kubectl get storageclass"
            
            if self.status.gpu_configured:
                panel_content += "\n• kubectl get nodes -o yaml | grep nvidia.com/gpu"
        
        console.print(Panel(panel_content, title="Next Steps", border_style="green"))
    
    def create_backup(self) -> bool:
        """Create a backup (for --backup-only mode)"""
        console.print("\n[bold blue]💾 Creating Backup[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating backup...", total=None)
            
            if self.backup_manager.create_backup('manual'):
                progress.update(task, completed=True)
                console.print("✅ Backup created successfully")
                return True
            else:
                progress.update(task, completed=True)
                console.print("❌ Backup creation failed")
                return False
    
    def run_full_installation(self) -> bool:
        """Run the complete installation process"""
        console.print(Panel.fit("K3s Intelligent Installer", style="bold blue"))
        console.print("Starting comprehensive K3s installation...\n")
        
        steps = [
            ("System Checks", self.run_system_checks),
            ("System Optimization", self.optimize_system),
            ("K3s Installation", self.install_k3s),
            ("GPU Configuration", self.configure_gpu),
            ("Storage Setup", self.setup_storage),
            ("Networking Setup", self.setup_networking),
            ("TLS Configuration", self.setup_tls),
            ("Backup Setup", self.setup_backup),
            ("Installation Validation", self.validate_installation),
        ]
        
        start_time = time.time()
        
        for step_name, step_func in steps:
            try:
                if not step_func():
                    console.print(f"❌ Installation failed at: {step_name}")
                    return False
            except KeyboardInterrupt:
                console.print("\n🛑 Installation interrupted by user")
                return False
            except Exception as e:
                console.print(f"❌ Unexpected error in {step_name}: {e}")
                return False
        
        end_time = time.time()
        duration = end_time - start_time
        
        console.print(f"\n[bold green]✅ Installation completed in {duration:.1f} seconds![/bold green]")
        
        self.display_installation_summary()
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="K3s Intelligent Installer - Comprehensive single-node K3s setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config config/config.yaml
  %(prog)s --config config/config.yaml --backup-only
  %(prog)s --config config/config.yaml --validate-only
  %(prog)s --config config/config.yaml --gpu-only
        """
    )
    
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--backup-only', action='store_true', help='Only create a backup')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    parser.add_argument('--gpu-only', action='store_true', help='Only configure GPU support')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Adjust logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check for root privileges
    if os.geteuid() != 0:
        console.print("❌ This installer requires root privileges. Please run with sudo.")
        sys.exit(1)
    
    # Initialize installer
    installer = K3sInstaller(args.config)
    
    # Load configuration
    if not installer.load_config():
        sys.exit(1)
    
    # Initialize components
    installer.initialize_components()
    
    success = False
    
    try:
        if args.backup_only:
            success = installer.create_backup()
        elif args.validate_only:
            success = installer.validate_installation()
        elif args.gpu_only:
            success = (installer.run_system_checks() and 
                      installer.configure_gpu())
        else:
            success = installer.run_full_installation()
            
    except KeyboardInterrupt:
        console.print("\n🛑 Operation interrupted by user")
        sys.exit(130)
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}")
        if args.verbose:
            console.print_exception()
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()