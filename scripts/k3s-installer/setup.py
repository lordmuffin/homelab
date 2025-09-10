#!/usr/bin/env python3
"""
Setup script for K3s Intelligent Installer

This script helps with installation and setup of the K3s Intelligent Installer
including dependency installation and initial configuration.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_root_privileges():
    """Check if running with root privileges"""
    if os.geteuid() != 0:
        print("⚠️ Note: Some installation features require root privileges")
        print("   Run with 'sudo python3 setup.py' for full functionality")
        return False
    
    print("✅ Running with root privileges")
    return True

def install_system_dependencies():
    """Install required system packages"""
    print("📦 Installing system dependencies...")
    
    try:
        # Detect OS
        with open('/etc/os-release', 'r') as f:
            os_info = f.read().lower()
        
        if 'ubuntu' in os_info or 'debian' in os_info:
            packages = [
                'python3-pip', 'python3-venv', 'curl', 'wget',
                'software-properties-common', 'apt-transport-https',
                'ca-certificates', 'gnupg', 'lsb-release'
            ]
            
            cmd = ['apt-get', 'update']
            subprocess.run(cmd, check=True)
            
            cmd = ['apt-get', 'install', '-y'] + packages
            subprocess.run(cmd, check=True)
            
        elif any(dist in os_info for dist in ['centos', 'rhel', 'fedora']):
            packages = [
                'python3-pip', 'python3-venv', 'curl', 'wget',
                'dnf-plugins-core'
            ]
            
            cmd = ['dnf', 'install', '-y'] + packages
            subprocess.run(cmd, check=True)
            
        else:
            print("⚠️ Unknown OS, please install dependencies manually:")
            print("   - python3-pip")
            print("   - python3-venv")
            print("   - curl")
            print("   - wget")
            return False
        
        print("✅ System dependencies installed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing system dependencies: {e}")
        return False

def install_python_dependencies():
    """Install Python dependencies"""
    print("🐍 Installing Python dependencies...")
    
    try:
        # Upgrade pip first
        cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip']
        subprocess.run(cmd, check=True)
        
        # Install requirements
        requirements_file = Path(__file__).parent / 'requirements.txt'
        if requirements_file.exists():
            cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)]
            subprocess.run(cmd, check=True)
            print("✅ Python dependencies installed")
            return True
        else:
            print("❌ requirements.txt not found")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Python dependencies: {e}")
        return False

def setup_configuration():
    """Setup initial configuration"""
    print("⚙️ Setting up configuration...")
    
    config_dir = Path(__file__).parent / 'config'
    config_template = config_dir / 'config.yaml.template'
    config_file = config_dir / 'config.yaml'
    
    if not config_file.exists() and config_template.exists():
        shutil.copy2(config_template, config_file)
        print(f"✅ Configuration template copied to {config_file}")
        print("   Please edit config/config.yaml with your settings")
        return True
    elif config_file.exists():
        print("✅ Configuration file already exists")
        return True
    else:
        print("❌ Configuration template not found")
        return False

def check_kubectl():
    """Check if kubectl is available"""
    print("🔍 Checking for kubectl...")
    
    try:
        subprocess.run(['kubectl', 'version', '--client'], 
                      capture_output=True, check=True)
        print("✅ kubectl is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ kubectl not found - will be installed with K3s")
        return True  # Not a failure, K3s will provide kubectl

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        '/var/log',
        '/tmp/k3s-installer',
        '/var/backups/k3s'
    ]
    
    try:
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        print("✅ Directories created")
        return True
        
    except PermissionError:
        print("⚠️ Some directories could not be created (permission denied)")
        print("   Run with sudo for full setup")
        return True  # Don't fail the setup

def run_tests():
    """Run basic tests to verify installation"""
    print("🧪 Running basic tests...")
    
    try:
        # Try to import main modules
        sys.path.insert(0, str(Path(__file__).parent))
        
        from modules import SystemUtils, GPUConfigurator, StorageSetup
        print("✅ Module imports successful")
        
        # Try to run a basic system check
        system_utils = SystemUtils()
        system_info = system_utils.detect_system()
        print(f"✅ System detection successful: {system_info.os_name} {system_info.os_version}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Module import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Test warning: {e}")
        return True  # Don't fail setup for test issues

def main():
    """Main setup function"""
    print("🚀 K3s Intelligent Installer Setup")
    print("=" * 40)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check root privileges
    has_root = check_root_privileges()
    
    # Install system dependencies (requires root)
    if has_root:
        if not install_system_dependencies():
            success = False
    else:
        print("⚠️ Skipping system package installation (no root privileges)")
    
    # Install Python dependencies
    if not install_python_dependencies():
        success = False
    
    # Setup configuration
    if not setup_configuration():
        success = False
    
    # Check kubectl
    check_kubectl()
    
    # Create directories (requires root for some)
    create_directories()
    
    # Run tests
    if not run_tests():
        success = False
    
    print("\n" + "=" * 40)
    
    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config/config.yaml with your settings")
        print("2. Run: sudo python3 k3s_installer.py --config config/config.yaml")
    else:
        print("❌ Setup completed with some issues")
        print("Please review the errors above and fix them before proceeding")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)