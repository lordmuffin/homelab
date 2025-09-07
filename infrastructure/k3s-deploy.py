#!/usr/bin/env python3
"""
K3s Infrastructure Deployment Wrapper Script
============================================

Comprehensive deployment orchestrator for K3s clusters on Proxmox infrastructure.
Handles the complete workflow from Terraform provisioning to cluster validation.

Author: Claude Code
Version: 1.0.0
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
import shutil
import random
from functools import wraps

# Optional yaml import - not strictly required for core functionality
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Configure logging with enhanced formatting
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and enhanced formatting"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        # Enhanced format with more context
        if hasattr(record, 'phase'):
            return f"[{record.asctime}] {record.levelname} [{record.phase}] {record.getMessage()}"
        else:
            return f"[{record.asctime}] {record.levelname} {record.getMessage()}"

# Configure logging
log_formatter = ColoredFormatter()
log_formatter.datefmt = '%Y-%m-%d %H:%M:%S'

# File handler (no colors)
file_handler = logging.FileHandler('/tmp/k3s-deploy.log')
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Console handler (with colors)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Progress indicator helper
class ProgressIndicator:
    """Simple progress indicator for long-running operations"""
    
    def __init__(self, message: str, logger: logging.Logger):
        self.message = message
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"🔄 {self.message}...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time if self.start_time else 0
        if exc_type is None:
            self.logger.info(f"✅ {self.message} completed in {elapsed:.1f}s")
        else:
            self.logger.error(f"❌ {self.message} failed after {elapsed:.1f}s")

class K3sDeploymentError(Exception):
    """Custom exception for K3s deployment errors"""
    pass

class K3sTimeoutError(K3sDeploymentError):
    """Exception for timeout-related errors"""
    pass

class K3sRetryError(K3sDeploymentError):
    """Exception for retry-related errors"""
    pass

# Retry decorator with exponential backoff and jitter
def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple = (Exception,)
):
    """
    Decorator for retrying operations with exponential backoff and jitter
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff multiplier
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        raise K3sRetryError(f"All {max_attempts} attempts failed for {func.__name__}") from e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}")
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator

def timeout_handler(timeout_seconds: int):
    """
    Decorator to add timeout handling to functions
    
    Args:
        timeout_seconds: Maximum time to wait in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import signal
            
            def timeout_signal_handler(signum, frame):
                raise K3sTimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
            
            # Set the signal alarm
            old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(timeout_seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Restore the old signal handler and cancel the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper
    return decorator

class K3sDeployer:
    """Main K3s deployment orchestrator class"""
    
    def __init__(self, environment: str, terraform_dir: Optional[str] = None, 
                 max_retries: int = 3, timeout_multiplier: float = 1.0):
        """
        Initialize the K3s deployer
        
        Args:
            environment: Target environment (production, staging, dev)
            terraform_dir: Custom Terraform directory path
            max_retries: Maximum number of retries for operations
            timeout_multiplier: Multiplier for default timeouts (1.0 = default, 2.0 = double)
        """
        self.environment = environment
        self.base_dir = Path(__file__).parent.absolute()
        self.max_retries = max_retries
        self.timeout_multiplier = timeout_multiplier
        
        # Default timeouts in seconds (can be adjusted with timeout_multiplier)
        self.timeouts = {
            'terraform_apply': int(1800 * timeout_multiplier),  # 30 minutes default
            'terraform_destroy': int(900 * timeout_multiplier),  # 15 minutes default
            'vm_discovery': int(300 * timeout_multiplier),       # 5 minutes default
            'ansible_playbook': int(2700 * timeout_multiplier),  # 45 minutes default
            'cluster_validation': int(180 * timeout_multiplier), # 3 minutes default
            'ssh_connection': int(30 * timeout_multiplier),      # 30 seconds default
            'vm_boot_wait': int(180 * timeout_multiplier),       # 3 minutes default
        }
        
        # Set up directory paths
        if terraform_dir:
            self.terraform_dir = Path(terraform_dir)
        else:
            # Try to find the terraform directory based on discovered structure
            possible_paths = [
                self.base_dir / "proxmox" / "terraform" / "environments" / environment,
                self.base_dir.parent / "terraform",
                self.base_dir / ".." / "terraform"
            ]
            
            self.terraform_dir = None
            for path in possible_paths:
                if path.exists() and (path / "main.tf").exists():
                    self.terraform_dir = path.resolve()
                    break
            
            if not self.terraform_dir:
                raise K3sDeploymentError(f"Could not find Terraform directory for environment: {environment}")
        
        self.ansible_dir = self.base_dir / "k3s" / "ansible"
        self.scripts_dir = self.ansible_dir / "scripts"
        self.inventory_file = self.ansible_dir / "inventory" / "discovered-hosts.yml"
        self.playbook_file = self.ansible_dir / "playbooks" / "configure-k3s-fixed.yml"
        self.kubeconfig_path = Path.home() / ".kube" / "k3s-cluster-config"
        
        # Validate required paths
        self._validate_paths()
        
        logger.info(f"K3s Deployer initialized for environment: {environment}")
        logger.info(f"Terraform directory: {self.terraform_dir}")
        logger.info(f"Ansible directory: {self.ansible_dir}")
        logger.info(f"Max retries: {self.max_retries}, Timeout multiplier: {self.timeout_multiplier}")
        logger.info(f"Key timeouts: Terraform={self.timeouts['terraform_apply']}s, Ansible={self.timeouts['ansible_playbook']}s")
    
    def _validate_paths(self) -> None:
        """Validate that required paths exist"""
        required_paths = [
            (self.terraform_dir, "Terraform directory"),
            (self.ansible_dir, "Ansible directory"),
            (self.scripts_dir, "Scripts directory"),
        ]
        
        for path, description in required_paths:
            if not path.exists():
                raise K3sDeploymentError(f"{description} not found at: {path}")
        
        # Check for key files
        key_files = [
            (self.scripts_dir / "discover-vm-ips.sh", "VM IP discovery script"),
            (self.playbook_file, "Ansible playbook"),
        ]
        
        for file_path, description in key_files:
            if not file_path.exists():
                raise K3sDeploymentError(f"{description} not found at: {file_path}")
    
    def run_command(self, command: List[str], cwd: Optional[Path] = None, 
                   capture_output: bool = False, stream_output: bool = False, 
                   timeout: Optional[int] = None, phase: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper error handling and logging
        
        Args:
            command: Command to execute as list
            cwd: Working directory for command execution
            capture_output: Whether to capture stdout/stderr
            stream_output: Whether to stream output in real-time
            timeout: Command timeout in seconds
            phase: Current deployment phase for logging context
            
        Returns:
            CompletedProcess object
            
        Raises:
            K3sDeploymentError: If command fails
        """
        cmd_str = ' '.join(command)
        phase_info = f"[{phase}] " if phase else ""
        
        logger.info(f"🔧 {phase_info}Executing: {cmd_str}")
        if cwd:
            logger.debug(f"Working directory: {cwd}")
        if timeout:
            logger.debug(f"Timeout: {timeout}s")
        
        try:
            if stream_output and not capture_output:
                # Stream output in real-time
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                output_lines = []
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line:  # Only log non-empty lines
                            logger.info(f"📄 {phase_info}{line}")
                            output_lines.append(line)
                
                rc = process.poll()
                if rc != 0:
                    raise subprocess.CalledProcessError(rc, command, output='\n'.join(output_lines))
                
                # Create a CompletedProcess-like object
                class StreamResult:
                    def __init__(self, returncode, args, stdout):
                        self.returncode = returncode
                        self.args = args
                        self.stdout = stdout
                        self.stderr = None
                
                return StreamResult(0, command, '\n'.join(output_lines))
            else:
                # Traditional capture mode
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=capture_output,
                    text=True,
                    check=True,
                    timeout=timeout
                )
                
                if capture_output and result.stdout:
                    # Log first and last few lines of output for context
                    output_lines = result.stdout.strip().split('\n')
                    if len(output_lines) <= 10:
                        for line in output_lines:
                            if line.strip():
                                logger.debug(f"📄 {phase_info}{line}")
                    else:
                        logger.debug(f"📄 {phase_info}Command output ({len(output_lines)} lines):")
                        for line in output_lines[:3]:
                            if line.strip():
                                logger.debug(f"📄 {phase_info}{line}")
                        logger.debug(f"📄 {phase_info}... ({len(output_lines) - 6} more lines) ...")
                        for line in output_lines[-3:]:
                            if line.strip():
                                logger.debug(f"📄 {phase_info}{line}")
                
                logger.debug(f"✅ {phase_info}Command completed with exit code 0")
                return result
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"{phase_info}Command timed out after {timeout}s: {cmd_str}"
            logger.error(f"⏰ {error_msg}")
            raise K3sTimeoutError(error_msg) from e
        except subprocess.CalledProcessError as e:
            error_msg = f"{phase_info}Command failed (exit code {e.returncode}): {cmd_str}"
            
            if capture_output and e.stderr:
                logger.error(f"❌ {error_msg}")
                # Log error details
                error_lines = e.stderr.strip().split('\n')
                for line in error_lines:
                    if line.strip():
                        logger.error(f"🔍 {phase_info}ERROR: {line}")
            elif hasattr(e, 'output') and e.output:
                logger.error(f"❌ {error_msg}")
                logger.error(f"🔍 {phase_info}OUTPUT: {e.output}")
            else:
                logger.error(f"❌ {error_msg}")
            
            # Add recovery suggestions based on command type
            self._suggest_recovery(command[0], e, phase)
            
            raise K3sDeploymentError(error_msg) from e
        except Exception as e:
            error_msg = f"{phase_info}Unexpected error executing command: {cmd_str}"
            logger.error(f"💥 {error_msg}: {str(e)}")
            raise K3sDeploymentError(error_msg) from e
    
    def _suggest_recovery(self, command: str, error: subprocess.CalledProcessError, phase: Optional[str]) -> None:
        """Provide recovery suggestions based on command and error"""
        suggestions = []
        
        if command == 'terraform':
            if error.stderr and 'lock' in error.stderr.lower():
                suggestions.extend([
                    "Terraform state is locked - wait for other operations to complete",
                    "If stuck, consider: terraform force-unlock <lock-id>",
                    "Check for running terraform processes: ps aux | grep terraform"
                ])
            elif error.stderr and ('timeout' in error.stderr.lower() or 'connection' in error.stderr.lower()):
                suggestions.extend([
                    "Network or Proxmox connection timeout",
                    "Check Proxmox server accessibility",
                    "Consider increasing --timeout-multiplier"
                ])
            elif error.returncode == 1:
                suggestions.extend([
                    "Review terraform plan output for configuration errors",
                    "Check Proxmox credentials and permissions",
                    "Verify resource quotas and availability"
                ])
        
        elif command == 'ansible-playbook':
            if error.stderr and ('unreachable' in error.stderr.lower() or 'connection' in error.stderr.lower()):
                suggestions.extend([
                    "VM connection failed - VMs may still be booting",
                    "Check VM IP discovery was successful",
                    "Verify SSH key authentication",
                    "Try: ssh ubuntu@<vm-ip> to test connectivity manually"
                ])
            elif error.stderr and 'permission' in error.stderr.lower():
                suggestions.extend([
                    "Permission denied - check SSH key permissions",
                    "Ensure SSH key is in ~/.ssh/id_rsa",
                    "Verify ubuntu user exists on target VMs"
                ])
        
        elif command == 'kubectl':
            suggestions.extend([
                "Kubeconfig may be invalid or cluster not ready",
                "Check cluster status manually",
                "Verify master node accessibility"
            ])
        
        # Generic suggestions
        if not suggestions:
            suggestions.extend([
                f"Check {command} is properly installed and configured",
                "Review command output above for specific error details",
                "Consider increasing retry attempts with --max-retries"
            ])
        
        if suggestions:
            logger.info("💡 Recovery suggestions:")
            for suggestion in suggestions:
                logger.info(f"   • {suggestion}")
    
    def check_prerequisites(self) -> None:
        """Check that all required tools are available"""
        required_tools = ['terraform', 'ansible-playbook', 'kubectl']
        
        with ProgressIndicator("Checking prerequisites", logger):
            logger.info("🔍 Verifying required tools and dependencies...")
            
            missing_tools = []
            for tool in required_tools:
                if not shutil.which(tool):
                    missing_tools.append(tool)
                    logger.error(f"❌ {tool} not found in PATH")
                else:
                    # Get version info for context
                    try:
                        version_cmd = [tool, '--version'] if tool != 'kubectl' else [tool, 'version', '--client', '--short']
                        result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=10)
                        version_info = result.stdout.split('\n')[0].strip() if result.returncode == 0 else "version unknown"
                        logger.info(f"✅ {tool} found ({version_info})")
                    except:
                        logger.info(f"✅ {tool} found")
            
            if missing_tools:
                logger.error("❌ Missing required tools:")
                for tool in missing_tools:
                    logger.error(f"   • {tool}")
                logger.info("💡 Installation suggestions:")
                if 'terraform' in missing_tools:
                    logger.info("   • Terraform: https://developer.hashicorp.com/terraform/downloads")
                if 'ansible-playbook' in missing_tools:
                    logger.info("   • Ansible: pip install ansible")
                if 'kubectl' in missing_tools:
                    logger.info("   • kubectl: https://kubernetes.io/docs/tasks/tools/")
                raise K3sDeploymentError(f"Required tools not found: {', '.join(missing_tools)}")
            
            # Check SSH key
            ssh_key_path = Path.home() / ".ssh" / "id_rsa"
            if not ssh_key_path.exists():
                logger.warning(f"⚠️ SSH private key not found at {ssh_key_path}")
                logger.info("💡 You may need to generate SSH keys: ssh-keygen -t rsa -b 4096")
            else:
                # Check key permissions
                key_perms = oct(ssh_key_path.stat().st_mode)[-3:]
                if key_perms != '600':
                    logger.warning(f"⚠️ SSH key has incorrect permissions: {key_perms} (should be 600)")
                    logger.info(f"💡 Fix with: chmod 600 {ssh_key_path}")
                else:
                    logger.info(f"✅ SSH private key found with correct permissions")
                
                # Check for public key
                pub_key_path = ssh_key_path.with_suffix('.pub')
                if pub_key_path.exists():
                    logger.info(f"✅ SSH public key found at {pub_key_path}")
                else:
                    logger.warning(f"⚠️ SSH public key not found at {pub_key_path}")
            
            logger.info("🎯 Prerequisites check completed")
    
    def terraform_init(self) -> None:
        """Initialize Terraform"""
        with ProgressIndicator("Terraform initialization", logger):
            logger.info(f"🔄 Initializing Terraform in {self.terraform_dir}")
            self.run_command(['terraform', 'init'], cwd=self.terraform_dir, 
                           stream_output=True, phase="TERRAFORM-INIT")
    
    def terraform_plan(self) -> None:
        """Run Terraform plan"""
        with ProgressIndicator("Terraform planning", logger):
            logger.info("📋 Generating Terraform execution plan...")
            logger.info("🔍 This will show what resources will be created/modified/destroyed")
            self.run_command(['terraform', 'plan'], cwd=self.terraform_dir, 
                           stream_output=True, phase="TERRAFORM-PLAN")
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=5.0,
        max_delay=60.0,
        exceptions=(K3sDeploymentError, subprocess.CalledProcessError)
    )
    def terraform_apply(self, auto_approve: bool = False) -> None:
        """
        Apply Terraform configuration with retry logic for common failures
        
        Args:
            auto_approve: Whether to automatically approve the apply
        """
        phase = "TERRAFORM-APPLY"
        
        with ProgressIndicator("Terraform infrastructure deployment", logger):
            logger.info("🚀 Applying Terraform configuration to create infrastructure...")
            logger.info(f"⏱️ Timeout: {self.timeouts['terraform_apply']}s")
            
            command = ['terraform', 'apply']
            if auto_approve:
                command.append('-auto-approve')
                logger.info("✅ Auto-approve enabled - no user confirmation required")
            else:
                logger.warning("⚠️ Manual approval required - Terraform will prompt for confirmation")
            
            # Add parallelism control to reduce Proxmox lock contention
            parallelism = getattr(self, 'terraform_parallelism', 2)
            command.extend([f'-parallelism={parallelism}'])
            logger.info(f"🔄 Using parallelism level: {parallelism}")
            
            try:
                # Use streaming output for long-running terraform operations
                logger.info("🔧 Starting Terraform apply - this may take several minutes...")
                logger.info("📊 Progress will be shown below:")
                
                result = subprocess.run(
                    command,
                    cwd=self.terraform_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.timeouts['terraform_apply']
                )
                
                if result.stdout:
                    # Parse and log key information from terraform output
                    output_lines = result.stdout.split('\n')
                    resources_created = len([line for line in output_lines if 'created' in line and 'resource' in line])
                    resources_modified = len([line for line in output_lines if 'modified' in line and 'resource' in line])
                    resources_destroyed = len([line for line in output_lines if 'destroyed' in line and 'resource' in line])
                    
                    logger.info(f"📈 Terraform apply results:")
                    logger.info(f"   • Resources created: {resources_created}")
                    logger.info(f"   • Resources modified: {resources_modified}")
                    logger.info(f"   • Resources destroyed: {resources_destroyed}")
                    
                    # Log the full output at debug level
                    logger.debug(f"Full Terraform output:\n{result.stdout}")
                
                logger.info("🎉 Terraform apply completed successfully!")
                logger.info("🔍 Infrastructure should now be provisioned and VMs starting up...")
                
            except subprocess.TimeoutExpired as e:
                error_msg = f"Terraform apply timed out after {self.timeouts['terraform_apply']} seconds"
                logger.error(f"⏰ {error_msg}")
                logger.error("💡 Try increasing timeout with --timeout-multiplier 2.0 or higher")
                raise K3sTimeoutError(error_msg) from e
            except subprocess.CalledProcessError as e:
                error_msg = f"Terraform apply failed with exit code {e.returncode}"
                logger.error(f"❌ {error_msg}")
                
                if e.stderr:
                    logger.error("🔍 Terraform error details:")
                    for line in e.stderr.split('\n'):
                        if line.strip():
                            logger.error(f"   {line}")
                
                # Check for specific Proxmox lock errors that can be retried
                if e.stderr and ("lock" in e.stderr.lower() or "timeout" in e.stderr.lower()):
                    logger.warning("🔄 Detected Proxmox lock/timeout error - will retry automatically")
                    raise K3sDeploymentError(error_msg) from e
                elif e.stderr and ("resource already exists" in e.stderr.lower() or "already exists" in e.stderr.lower()):
                    logger.warning("🔄 Resource conflict detected - may be recoverable with retry")
                    raise K3sDeploymentError(error_msg) from e
                else:
                    # For other errors, don't retry
                    logger.error("💥 Non-recoverable Terraform error - check configuration and try again")
                    raise K3sDeploymentError(error_msg) from e
    
    @retry_with_backoff(
        max_attempts=2,  # Fewer retries for destroy operations
        base_delay=10.0,
        max_delay=60.0,
        exceptions=(K3sDeploymentError, subprocess.CalledProcessError)
    )
    def terraform_destroy(self, auto_approve: bool = False) -> None:
        """
        Destroy Terraform infrastructure with timeout and retry handling
        
        Args:
            auto_approve: Whether to automatically approve the destroy
        """
        logger.warning("Destroying Terraform infrastructure...")
        
        command = ['terraform', 'destroy']
        if auto_approve:
            command.append('-auto-approve')
        
        # Add parallelism control
        parallelism = getattr(self, 'terraform_parallelism', 2)
        command.extend([f'-parallelism={parallelism}'])
        
        try:
            result = subprocess.run(
                command,
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeouts['terraform_destroy']
            )
            
            if result.stdout:
                logger.debug(f"Terraform destroy output: {result.stdout}")
            
            logger.info("✓ Terraform destroy completed successfully")
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Terraform destroy timed out after {self.timeouts['terraform_destroy']} seconds"
            logger.error(error_msg)
            raise K3sTimeoutError(error_msg) from e
        except subprocess.CalledProcessError as e:
            error_msg = f"Terraform destroy failed: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise K3sDeploymentError(error_msg) from e
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=10.0,
        max_delay=120.0,
        exceptions=(K3sDeploymentError,)
    )
    def discover_vm_ips(self) -> None:
        """Run VM IP discovery script with retry logic for VM boot delays"""
        phase = "VM-DISCOVERY"
        
        with ProgressIndicator("VM IP address discovery", logger):
            logger.info("🔍 Discovering VM IP addresses from Proxmox...")
            logger.info(f"⏱️ Timeout: {self.timeouts['vm_discovery']}s")
            
            discover_script = self.scripts_dir / "discover-vm-ips.sh"
            
            # Verify script exists and make executable
            if not discover_script.exists():
                raise K3sDeploymentError(f"VM discovery script not found: {discover_script}")
            
            logger.info(f"📜 Using discovery script: {discover_script}")
            discover_script.chmod(0o755)
            
            try:
                logger.info("🚀 Running VM discovery script...")
                result = subprocess.run(
                    [str(discover_script), 'both'],
                    cwd=self.scripts_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.timeouts['vm_discovery']
                )
                
                if result.stdout:
                    # Parse output to show discovered VMs
                    output_lines = result.stdout.strip().split('\n')
                    vm_count = 0
                    logger.info("📋 VM Discovery Results:")
                    
                    for line in output_lines:
                        if line.strip() and not line.startswith('#'):
                            logger.info(f"   {line}")
                            if 'ansible_host' in line:
                                vm_count += 1
                    
                    logger.info(f"🎯 Found {vm_count} VM(s) with IP addresses")
                    logger.debug(f"Full discovery output:\n{result.stdout}")
                    
                    # Check if inventory was created
                    if self.inventory_file.exists():
                        logger.info(f"✅ Inventory file created: {self.inventory_file}")
                    else:
                        logger.warning(f"⚠️ Inventory file not found: {self.inventory_file}")
                else:
                    logger.warning("⚠️ No output from VM discovery script")
                
                logger.info("🎉 VM IP discovery completed successfully!")
                
            except subprocess.TimeoutExpired as e:
                error_msg = f"VM IP discovery timed out after {self.timeouts['vm_discovery']} seconds"
                logger.error(f"⏰ {error_msg}")
                logger.error("💡 VMs may still be booting - try increasing timeout or waiting longer")
                raise K3sTimeoutError(error_msg) from e
            except subprocess.CalledProcessError as e:
                error_msg = f"VM IP discovery failed with exit code {e.returncode}"
                logger.error(f"❌ {error_msg}")
                
                if e.stderr:
                    logger.error("🔍 Discovery script error details:")
                    for line in e.stderr.split('\n'):
                        if line.strip():
                            logger.error(f"   {line}")
                
                logger.error("💡 Possible causes:")
                logger.error("   • VMs are still booting (wait a few minutes)")
                logger.error("   • Proxmox connection issues")
                logger.error("   • VM naming or template issues")
                logger.error("   • Network configuration problems")
                
                raise K3sDeploymentError(error_msg) from e
    
    @retry_with_backoff(
        max_attempts=2,  # Limited retries for Ansible as it can be time-consuming
        base_delay=30.0,
        max_delay=180.0,
        exceptions=(K3sDeploymentError,)
    )
    def run_ansible_playbook(self) -> None:
        """Run Ansible playbook to configure K3s cluster with timeout handling"""
        phase = "ANSIBLE-K3S"
        
        with ProgressIndicator("K3s cluster configuration", logger):
            logger.info("🎯 Running Ansible playbook to configure K3s cluster...")
            logger.info(f"⏱️ Timeout: {self.timeouts['ansible_playbook']}s")
            
            # Verify prerequisites
            if not self.inventory_file.exists():
                raise K3sDeploymentError(f"Inventory file not found: {self.inventory_file}")
            
            if not self.playbook_file.exists():
                raise K3sDeploymentError(f"Playbook file not found: {self.playbook_file}")
            
            logger.info(f"📋 Using inventory: {self.inventory_file}")
            logger.info(f"📜 Using playbook: {self.playbook_file}")
            
            # Show inventory summary
            try:
                with open(self.inventory_file, 'r') as f:
                    inventory_content = f.read()
                    master_count = inventory_content.count('masters:') if 'masters:' in inventory_content else 0
                    worker_count = inventory_content.count('workers:') if 'workers:' in inventory_content else 0
                    logger.info(f"🏗️ Target cluster topology: {master_count} master(s), {worker_count} worker(s)")
            except Exception as e:
                logger.warning(f"⚠️ Could not parse inventory file: {e}")
            
            command = [
                'ansible-playbook',
                '-i', str(self.inventory_file),
                str(self.playbook_file),
                '-v',  # Verbose output
                '--timeout=30',  # SSH timeout
                '--forks=3'  # Limit concurrent connections to reduce load
            ]
            
            logger.info("🔧 Ansible configuration:")
            logger.info("   • Verbose output enabled (-v)")
            logger.info("   • SSH timeout: 30s")
            logger.info("   • Max parallel connections: 3")
            
            try:
                logger.info("🚀 Starting K3s installation and configuration...")
                logger.info("📊 This process includes:")
                logger.info("   • VM connectivity testing")
                logger.info("   • K3s master node setup")
                logger.info("   • K3s worker node joining")
                logger.info("   • Network configuration")
                logger.info("   • Cluster validation")
                
                # Use streaming output to see Ansible progress in real-time
                logger.info("🔄 Starting Ansible execution with real-time output...")
                
                process = subprocess.Popen(
                    command,
                    cwd=self.ansible_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                output_lines = []
                ansible_tasks = 0
                failed_tasks = 0
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line:
                            # Count tasks and failures for summary
                            if "TASK [" in line:
                                ansible_tasks += 1
                                logger.info(f"📋 {line}")
                            elif "FAILED!" in line:
                                failed_tasks += 1
                                logger.error(f"❌ {line}")
                            elif "fatal:" in line:
                                logger.error(f"💀 {line}")
                            elif "ERROR!" in line:
                                logger.error(f"🚨 {line}")
                            elif "ok:" in line and ansible_tasks > 0:
                                logger.debug(f"✅ {line}")
                            elif "changed:" in line:
                                logger.info(f"🔄 {line}")
                            elif "skipping:" in line:
                                logger.debug(f"⏭️ {line}")
                            elif "PLAY [" in line:
                                logger.info(f"🎭 {line}")
                            elif "PLAY RECAP" in line:
                                logger.info(f"📊 {line}")
                            elif line.startswith("k3s-"):
                                logger.info(f"📈 {line}")
                            else:
                                logger.debug(f"📄 {line}")
                            
                            output_lines.append(line)
                
                rc = process.poll()
                
                # Create result object
                class AnsibleResult:
                    def __init__(self, returncode, args, stdout):
                        self.returncode = returncode
                        self.args = args
                        self.stdout = stdout
                        self.stderr = None
                
                result = AnsibleResult(rc, command, '\n'.join(output_lines))
                
                if rc != 0:
                    raise subprocess.CalledProcessError(rc, command, output=result.stdout)
                
                if result.stdout:
                    # Parse Ansible output for key information
                    output_lines = result.stdout.split('\n')
                    ok_count = len([line for line in output_lines if 'ok=' in line])
                    changed_count = len([line for line in output_lines if 'changed=' in line])
                    unreachable_count = len([line for line in output_lines if 'unreachable=' in line])
                    failed_count = len([line for line in output_lines if 'failed=' in line])
                    
                    logger.info("📈 Ansible execution summary:")
                    logger.info(f"   • Tasks OK: {ok_count}")
                    logger.info(f"   • Tasks Changed: {changed_count}")
                    logger.info(f"   • Unreachable hosts: {unreachable_count}")
                    logger.info(f"   • Failed tasks: {failed_count}")
                    
                    # Show key events from Ansible output
                    logger.debug("Key Ansible events:")
                    for line in output_lines:
                        if any(keyword in line.lower() for keyword in ['task', 'play', 'fatal', 'changed']):
                            logger.debug(f"   {line}")
                    
                    logger.debug(f"Full Ansible output:\n{result.stdout}")
                
                logger.info("🎉 K3s cluster configuration completed successfully!")
                logger.info("🔍 Cluster should now be operational")
                
            except subprocess.TimeoutExpired as e:
                error_msg = f"Ansible playbook timed out after {self.timeouts['ansible_playbook']} seconds"
                logger.error(f"⏰ {error_msg}")
                logger.error("💡 This typically means:")
                logger.error("   • VMs are slow to respond (increase timeout)")
                logger.error("   • Network connectivity issues")
                logger.error("   • K3s installation is taking longer than expected")
                logger.error("   • Try: --timeout-multiplier 2.0 or higher")
                raise K3sTimeoutError(error_msg) from e
            except subprocess.CalledProcessError as e:
                error_msg = f"Ansible playbook failed with exit code {e.returncode}"
                logger.error(f"❌ {error_msg}")
                
                if e.stderr:
                    logger.error("🔍 Ansible error details:")
                    for line in e.stderr.split('\n'):
                        if line.strip():
                            logger.error(f"   {line}")
                
                # Check if this is a transient error that might be worth retrying
                if e.stderr and any(keyword in e.stderr.lower() for keyword in ['timeout', 'connection', 'unreachable']):
                    logger.warning("🔄 Detected connection/timeout error - will retry automatically")
                    logger.info("💡 This could be due to:")
                    logger.info("   • Temporary network issues")
                    logger.info("   • VMs still finishing boot process")
                    logger.info("   • SSH authentication delays")
                    raise K3sDeploymentError(error_msg) from e
                else:
                    # Don't retry configuration errors
                    logger.error("💥 Non-recoverable Ansible error")
                    logger.error("💡 Common causes:")
                    logger.error("   • Playbook configuration errors")
                    logger.error("   • VM resource constraints")
                    logger.error("   • K3s installation failures")
                    logger.error("   • Permission or authentication issues")
                    raise K3sDeploymentError(error_msg) from e
    
    def wait_for_vms_ready(self, expected_count: Optional[int] = None) -> None:
        """
        Wait for VMs to be ready and responsive
        
        Args:
            expected_count: Expected number of VMs to wait for (optional)
        """
        phase = "VM-READY-WAIT"
        
        with ProgressIndicator("VM readiness check", logger):
            logger.info("⏳ Waiting for VMs to be ready and responsive...")
            logger.info(f"⏱️ Max wait time: {self.timeouts['vm_boot_wait']}s")
            
            max_wait_time = self.timeouts['vm_boot_wait']
            check_interval = 15  # seconds
            start_time = time.time()
            check_count = 0
            
            logger.info(f"🔄 Will check VM status every {check_interval}s")
            
            while time.time() - start_time < max_wait_time:
                check_count += 1
                elapsed = time.time() - start_time
                
                logger.info(f"📊 VM readiness check #{check_count} (elapsed: {elapsed:.0f}s)")
                
                try:
                    # Try to run VM discovery to see if VMs are responsive
                    test_script = self.scripts_dir / "discover-vm-ips.sh"
                    if not test_script.exists():
                        logger.warning("⚠️ VM discovery script not found, skipping readiness test")
                        break
                    
                    result = subprocess.run(
                        [str(test_script), 'test'],
                        cwd=self.scripts_dir,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0:
                        logger.info("✅ VMs are ready and responsive!")
                        logger.info(f"🎯 VM readiness confirmed after {elapsed:.0f}s")
                        return
                    else:
                        remaining = max_wait_time - elapsed
                        logger.info(f"⏳ VMs not yet ready... ({remaining:.0f}s remaining)")
                        if result.stdout:
                            logger.debug(f"Test output: {result.stdout}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️ VM readiness test timed out (check #{check_count})")
                except subprocess.CalledProcessError as e:
                    logger.debug(f"🔍 VM readiness test failed: {e}")
                    remaining = max_wait_time - elapsed
                    logger.info(f"⏳ VMs still booting... ({remaining:.0f}s remaining)")
                
                if time.time() - start_time < max_wait_time:
                    logger.debug(f"💤 Sleeping {check_interval}s before next check...")
                    time.sleep(check_interval)
            
            elapsed_total = time.time() - start_time
            logger.warning(f"⚠️ VMs may not be fully ready after {elapsed_total:.0f}s wait")
            logger.info("💡 This is not necessarily a problem - proceeding with deployment")
            logger.info("   • VMs might be ready but not responding to test script")
            logger.info("   • VM discovery will retry with more thorough checks")
            logger.info("   • Ansible will also test connectivity before proceeding")
    
    def update_kubeconfig(self) -> None:
        """Update and validate kubeconfig file"""
        logger.info("Updating kubeconfig...")
        
        # Ensure kubeconfig directory exists
        self.kubeconfig_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to get master node IP from inventory
        master_ip = self._get_master_node_ip()
        if not master_ip:
            logger.error("Could not determine master node IP from inventory")
            return
        
        # Check if kubeconfig exists, if not or if it's invalid, fetch it manually
        kubeconfig_valid = False
        if self.kubeconfig_path.exists():
            kubeconfig_valid = self._test_kubeconfig()
        
        if not kubeconfig_valid:
            logger.info("Fetching kubeconfig manually from master node...")
            self._fetch_kubeconfig_from_master(master_ip)
        
        # Final validation
        if self._test_kubeconfig():
            logger.info("✓ Kubeconfig validated successfully")
        else:
            logger.warning("Kubeconfig validation failed - cluster may still be starting")
    
    def _get_master_node_ip(self) -> Optional[str]:
        """Get the primary master node IP from inventory file"""
        try:
            if not YAML_AVAILABLE:
                logger.warning("PyYAML not available, trying to parse inventory manually")
                return self._parse_inventory_for_master_ip()
            
            with open(self.inventory_file, 'r') as f:
                inventory = yaml.safe_load(f)
            
            masters = inventory.get('all', {}).get('children', {}).get('k3s_cluster', {}).get('children', {}).get('masters', {}).get('hosts', {})
            
            # Look for primary master first
            for host_name, host_config in masters.items():
                if host_config.get('is_primary', False):
                    return host_config.get('ansible_host')
            
            # If no primary found, return first master
            for host_name, host_config in masters.items():
                return host_config.get('ansible_host')
                
        except Exception as e:
            logger.warning(f"Could not parse inventory file: {e}")
            return self._parse_inventory_for_master_ip()
        
        return None
    
    def _parse_inventory_for_master_ip(self) -> Optional[str]:
        """Fallback method to parse inventory without YAML library"""
        try:
            with open(self.inventory_file, 'r') as f:
                content = f.read()
            
            # Look for primary master
            lines = content.split('\n')
            in_masters = False
            for i, line in enumerate(lines):
                if 'masters:' in line:
                    in_masters = True
                elif in_masters and line.strip().startswith('ansible_host:'):
                    # Extract IP from ansible_host: "192.168.11.129"
                    ip_match = line.split('"')[1] if '"' in line else None
                    if ip_match:
                        return ip_match
                elif in_masters and line.strip() and not line.startswith(' ') and ':' not in line:
                    in_masters = False
            
        except Exception as e:
            logger.warning(f"Manual inventory parsing failed: {e}")
        
        return None
    
    def _test_kubeconfig(self) -> bool:
        """Test if kubeconfig is valid and working"""
        try:
            env = os.environ.copy()
            env['KUBECONFIG'] = str(self.kubeconfig_path)
            
            subprocess.run(
                ['kubectl', 'cluster-info'],
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    
    def _fetch_kubeconfig_from_master(self, master_ip: str) -> None:
        """Fetch kubeconfig directly from master node and update server address"""
        try:
            logger.info(f"Fetching kubeconfig from master node: {master_ip}")
            
            # Fetch kubeconfig from master node
            result = subprocess.run([
                'ssh', 
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=no',
                f'ubuntu@{master_ip}',
                'sudo cat /etc/rancher/k3s/k3s.yaml'
            ], capture_output=True, text=True, check=True)
            
            kubeconfig_content = result.stdout
            
            # Replace 127.0.0.1 with actual master IP
            kubeconfig_content = kubeconfig_content.replace('127.0.0.1', master_ip)
            
            # Write kubeconfig file
            with open(self.kubeconfig_path, 'w') as f:
                f.write(kubeconfig_content)
            
            # Set proper permissions
            self.kubeconfig_path.chmod(0o600)
            
            logger.info(f"✓ Kubeconfig fetched and saved to {self.kubeconfig_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch kubeconfig from master node: {e}")
            if e.stderr:
                logger.error(f"SSH error: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error fetching kubeconfig: {e}")
    
    def validate_cluster(self) -> Dict:
        """
        Validate K3s cluster health and return status information
        
        Returns:
            Dictionary with cluster validation results
        """
        logger.info("Validating K3s cluster...")
        
        # Ensure kubeconfig is available and valid
        if not self.kubeconfig_path.exists():
            logger.info("Kubeconfig not found, attempting to fetch from cluster...")
            self.update_kubeconfig()
        
        if not self.kubeconfig_path.exists():
            raise K3sDeploymentError(f"Could not create kubeconfig at: {self.kubeconfig_path}")
        
        env = os.environ.copy()
        env['KUBECONFIG'] = str(self.kubeconfig_path)
        
        validation_results = {
            'cluster_info': None,
            'nodes': [],
            'node_count': 0,
            'ready_nodes': 0,
            'master_nodes': 0,
            'worker_nodes': 0,
            'gpu_nodes': 0,
            'all_nodes_ready': False
        }
        
        try:
            # Get cluster info
            result = subprocess.run(
                ['kubectl', 'cluster-info'],
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            validation_results['cluster_info'] = result.stdout
            
            # Get node information
            result = subprocess.run(
                ['kubectl', 'get', 'nodes', '-o', 'json'],
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            nodes_data = json.loads(result.stdout)
            validation_results['nodes'] = nodes_data['items']
            validation_results['node_count'] = len(nodes_data['items'])
            
            # Analyze nodes
            ready_count = 0
            master_count = 0
            worker_count = 0
            gpu_count = 0
            
            for node in nodes_data['items']:
                # Check if node is ready
                for condition in node['status']['conditions']:
                    if condition['type'] == 'Ready' and condition['status'] == 'True':
                        ready_count += 1
                        break
                
                # Check node roles
                labels = node['metadata'].get('labels', {})
                if 'node-role.kubernetes.io/control-plane' in labels:
                    master_count += 1
                elif 'node-role.kubernetes.io/master' in labels:
                    master_count += 1
                else:
                    worker_count += 1
                
                # Check for GPU nodes
                if any('gpu' in key.lower() or 'nvidia' in key.lower() for key in labels.keys()):
                    gpu_count += 1
            
            validation_results['ready_nodes'] = ready_count
            validation_results['master_nodes'] = master_count
            validation_results['worker_nodes'] = worker_count
            validation_results['gpu_nodes'] = gpu_count
            validation_results['all_nodes_ready'] = ready_count == validation_results['node_count']
            
            # Log results
            logger.info(f"✓ Cluster validation completed:")
            logger.info(f"  - Total nodes: {validation_results['node_count']}")
            logger.info(f"  - Ready nodes: {validation_results['ready_nodes']}")
            logger.info(f"  - Master nodes: {validation_results['master_nodes']}")
            logger.info(f"  - Worker nodes: {validation_results['worker_nodes']}")
            logger.info(f"  - GPU nodes: {validation_results['gpu_nodes']}")
            logger.info(f"  - All nodes ready: {validation_results['all_nodes_ready']}")
            
            if not validation_results['all_nodes_ready']:
                logger.warning("Not all nodes are ready - cluster may still be initializing")
            
            return validation_results
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Cluster validation failed: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise K3sDeploymentError(error_msg) from e
    
    def deploy(self, auto_approve: bool = False, skip_terraform: bool = False) -> None:
        """
        Complete deployment workflow with enhanced timeout and retry handling
        
        Args:
            auto_approve: Automatically approve Terraform operations
            skip_terraform: Skip Terraform apply (useful for re-running only Ansible)
        """
        deployment_start_time = time.time()
        
        # Deployment header with configuration summary
        logger.info("=" * 80)
        logger.info("🚀 K3S INFRASTRUCTURE DEPLOYMENT STARTING")
        logger.info("=" * 80)
        logger.info(f"📊 Environment: {self.environment}")
        logger.info(f"📊 Max retries: {self.max_retries}")
        logger.info(f"📊 Timeout multiplier: {self.timeout_multiplier}")
        logger.info(f"📊 Auto-approve: {auto_approve}")
        logger.info(f"📊 Skip Terraform: {skip_terraform}")
        logger.info(f"📊 Terraform directory: {self.terraform_dir}")
        logger.info(f"📊 Ansible directory: {self.ansible_dir}")
        logger.info("=" * 80)
        
        phase_times = {}
        phases = []
        
        try:
            # Phase 0: Prerequisites
            phase_start = time.time()
            logger.info("")
            logger.info("🔍 PHASE 0: Prerequisites Verification")
            logger.info("─" * 50)
            self.check_prerequisites()
            phase_time = time.time() - phase_start
            phase_times['prerequisites'] = phase_time
            phases.append("✅ Prerequisites")
            logger.info(f"✅ Phase 0 completed in {phase_time:.1f}s")
            
            if not skip_terraform:
                # Phase 1: Infrastructure Provisioning
                phase_start = time.time()
                logger.info("")
                logger.info("🏗️ PHASE 1: Infrastructure Provisioning")
                logger.info("─" * 50)
                logger.info("🎯 This phase will create VMs and network infrastructure on Proxmox")
                self.terraform_init()
                self.terraform_plan()
                self.terraform_apply(auto_approve=auto_approve)
                phase_time = time.time() - phase_start
                phase_times['infrastructure'] = phase_time
                phases.append("✅ Infrastructure")
                logger.info(f"✅ Phase 1 completed in {phase_time:.1f}s")
                
                # Phase 2: VM Initialization
                phase_start = time.time()
                logger.info("")
                logger.info("⏳ PHASE 2: VM Initialization")
                logger.info("─" * 50)
                logger.info("🎯 Waiting for VMs to boot and become accessible")
                self.wait_for_vms_ready()
                phase_time = time.time() - phase_start
                phase_times['vm_init'] = phase_time
                phases.append("✅ VM Boot")
                logger.info(f"✅ Phase 2 completed in {phase_time:.1f}s")
            else:
                logger.info("")
                logger.info("⏭️ SKIPPING Terraform phases (--skip-terraform enabled)")
                phases.append("⏭️ Terraform Skipped")
            
            # Phase 3: VM Discovery
            phase_start = time.time()
            logger.info("")
            logger.info("🔍 PHASE 3: VM Discovery")
            logger.info("─" * 50)
            logger.info("🎯 Finding VM IP addresses and creating Ansible inventory")
            self.discover_vm_ips()
            phase_time = time.time() - phase_start
            phase_times['discovery'] = phase_time
            phases.append("✅ VM Discovery")
            logger.info(f"✅ Phase 3 completed in {phase_time:.1f}s")
            
            # Phase 4: K3s Cluster Configuration
            phase_start = time.time()
            logger.info("")
            logger.info("⚙️ PHASE 4: K3s Cluster Configuration")
            logger.info("─" * 50)
            logger.info("🎯 Installing and configuring K3s on all nodes")
            self.run_ansible_playbook()
            phase_time = time.time() - phase_start
            phase_times['k3s_config'] = phase_time
            phases.append("✅ K3s Config")
            logger.info(f"✅ Phase 4 completed in {phase_time:.1f}s")
            
            # Phase 5: Kubeconfig Setup
            phase_start = time.time()
            logger.info("")
            logger.info("🔑 PHASE 5: Kubeconfig Setup")
            logger.info("─" * 50)
            logger.info("🎯 Fetching and configuring kubectl access")
            self.update_kubeconfig()
            phase_time = time.time() - phase_start
            phase_times['kubeconfig'] = phase_time
            phases.append("✅ Kubeconfig")
            logger.info(f"✅ Phase 5 completed in {phase_time:.1f}s")
            
            # Phase 6: Cluster Validation
            phase_start = time.time()
            logger.info("")
            logger.info("✅ PHASE 6: Cluster Validation")
            logger.info("─" * 50)
            logger.info("🎯 Validating cluster health and connectivity")
            validation_results = self.validate_cluster()
            phase_time = time.time() - phase_start
            phase_times['validation'] = phase_time
            phases.append("✅ Validation")
            logger.info(f"✅ Phase 6 completed in {phase_time:.1f}s")
            
            # Deployment Success Summary
            total_time = time.time() - deployment_start_time
            logger.info("")
            logger.info("=" * 80)
            logger.info("🎉 K3S DEPLOYMENT COMPLETED SUCCESSFULLY!")
            logger.info("=" * 80)
            logger.info(f"⏱️ Total deployment time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            logger.info("")
            logger.info("📊 Phase Summary:")
            for phase in phases:
                logger.info(f"   {phase}")
            logger.info("")
            logger.info("⏱️ Phase Timing:")
            for phase_name, phase_time in phase_times.items():
                percentage = (phase_time / total_time) * 100
                logger.info(f"   {phase_name}: {phase_time:.1f}s ({percentage:.1f}%)")
            logger.info("=" * 80)
            
            # Print connection instructions
            self._print_connection_instructions(validation_results)
            
        except (K3sTimeoutError, K3sRetryError) as e:
            total_time = time.time() - deployment_start_time
            logger.error("")
            logger.error("=" * 80)
            logger.error("❌ DEPLOYMENT FAILED - TIMEOUT/RETRY LIMITS EXCEEDED")
            logger.error("=" * 80)
            logger.error(f"⏱️ Failed after: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            logger.error(f"🔍 Error: {str(e)}")
            logger.error("")
            logger.error("🛠️ Troubleshooting suggestions:")
            logger.error("   • Increase timeout: --timeout-multiplier 2.0")
            logger.error("   • Increase retries: --max-retries 5")
            logger.error("   • Check Proxmox server load and connectivity")
            logger.error("   • Verify VM resource requirements")
            logger.error("   • Review logs in /tmp/k3s-deploy.log")
            logger.error("")
            logger.error("📊 Completed phases:")
            for phase in phases:
                logger.error(f"   {phase}")
            logger.error("=" * 80)
            raise
        except Exception as e:
            total_time = time.time() - deployment_start_time
            logger.error("")
            logger.error("=" * 80)
            logger.error("❌ DEPLOYMENT FAILED - UNEXPECTED ERROR")
            logger.error("=" * 80)
            logger.error(f"⏱️ Failed after: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            logger.error(f"🔍 Error: {str(e)}")
            logger.error("")
            logger.error("🛠️ Troubleshooting suggestions:")
            logger.error("   • Check the error details above")
            logger.error("   • Review logs in /tmp/k3s-deploy.log")
            logger.error("   • Verify configuration files and paths")
            logger.error("   • Check system resources and permissions")
            logger.error("")
            logger.error("📊 Completed phases:")
            for phase in phases:
                logger.error(f"   {phase}")
            logger.error("=" * 80)
            raise
    
    def destroy(self, auto_approve: bool = False) -> None:
        """
        Destroy infrastructure
        
        Args:
            auto_approve: Automatically approve Terraform destroy
        """
        logger.info(f"🗑️  Starting infrastructure destruction for environment: {self.environment}")
        
        try:
            self.check_prerequisites()
            self.terraform_destroy(auto_approve=auto_approve)
            
            logger.info("🗑️  Infrastructure destruction completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Destruction failed: {str(e)}")
            raise
    
    def validate(self) -> None:
        """Validate existing cluster"""
        logger.info(f"🔍 Validating K3s cluster for environment: {self.environment}")
        
        try:
            validation_results = self.validate_cluster()
            self._print_connection_instructions(validation_results)
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {str(e)}")
            raise
    
    def _print_connection_instructions(self, validation_results: Dict) -> None:
        """Print cluster connection instructions"""
        print("\n" + "="*80)
        print("🚀 K3S CLUSTER CONNECTION INSTRUCTIONS")
        print("="*80)
        print(f"\nKubeconfig location: {self.kubeconfig_path}")
        print(f"Cluster status: {'✅ All nodes ready' if validation_results.get('all_nodes_ready') else '⚠️ Some nodes not ready'}")
        print(f"Node summary: {validation_results.get('node_count', 0)} total, {validation_results.get('ready_nodes', 0)} ready")
        
        print("\nTo connect to your cluster, use one of these methods:")
        print("\n1. Export kubeconfig (recommended):")
        print(f"   export KUBECONFIG={self.kubeconfig_path}")
        print("   kubectl get nodes")
        
        print(f"\n2. Use the helper script:")
        print(f"   {Path.home()}/k3s-kubectl get nodes")
        
        print(f"\n3. Specify kubeconfig per command:")
        print(f"   kubectl --kubeconfig={self.kubeconfig_path} get nodes")
        
        if validation_results.get('cluster_info'):
            print("\nCluster Info:")
            print(validation_results['cluster_info'])
        
        print("\n" + "="*80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="K3s Infrastructure Deployment Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s deploy --environment production
  %(prog)s deploy --environment production --auto-approve
  %(prog)s deploy --environment production --skip-terraform
  %(prog)s destroy --environment production --auto-approve
  %(prog)s validate --environment production
        """
    )
    
    parser.add_argument(
        'action',
        choices=['deploy', 'destroy', 'validate'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--environment', '-e',
        required=True,
        help='Target environment (production, staging, dev)'
    )
    
    parser.add_argument(
        '--terraform-dir', '-t',
        help='Custom Terraform directory path'
    )
    
    parser.add_argument(
        '--auto-approve', '-y',
        action='store_true',
        help='Automatically approve Terraform operations'
    )
    
    parser.add_argument(
        '--skip-terraform', '-s',
        action='store_true',
        help='Skip Terraform apply (useful for re-running only Ansible)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging (most verbose)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retries for operations (default: 3)'
    )
    
    parser.add_argument(
        '--timeout-multiplier',
        type=float,
        default=1.0,
        help='Multiplier for default timeouts (1.0 = default, 2.0 = double, etc.)'
    )
    
    parser.add_argument(
        '--parallelism',
        type=int,
        default=2,
        help='Terraform parallelism setting (default: 2 for Proxmox stability)'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Debug logging enabled")
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.info("📢 Verbose logging enabled")
    
    try:
        deployer = K3sDeployer(
            environment=args.environment,
            terraform_dir=args.terraform_dir,
            max_retries=args.max_retries,
            timeout_multiplier=args.timeout_multiplier
        )
        
        # Store parallelism setting for Terraform operations
        deployer.terraform_parallelism = args.parallelism
        
        if args.action == 'deploy':
            deployer.deploy(
                auto_approve=args.auto_approve,
                skip_terraform=args.skip_terraform
            )
        elif args.action == 'destroy':
            deployer.destroy(auto_approve=args.auto_approve)
        elif args.action == 'validate':
            deployer.validate()
    
    except K3sDeploymentError as e:
        logger.error(f"Deployment error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()