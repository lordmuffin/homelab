#!/usr/bin/env python3
"""
K3s Intelligent Installer - Validation Script

This script provides comprehensive validation of the K3s installation
and all configured components. It can be run independently to check
the health of an existing installation.

Usage:
    python3 validate.py --config config/config.yaml
    python3 validate.py --config config/config.yaml --component gpu
    python3 validate.py --config config/config.yaml --detailed
"""

import os
import sys
import argparse
import subprocess
import json
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add modules to path
sys.path.insert(0, os.path.dirname(__file__))

from modules import SystemUtils, GPUConfigurator, StorageSetup, NetworkingSetup, TLSManager, BackupManager

console = Console()

class K3sValidator:
    """Comprehensive K3s installation validator"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = {}
        self.load_config()
        
        # Initialize components
        self.system_utils = SystemUtils()
        self.gpu_configurator = GPUConfigurator(self.config)
        self.storage_setup = StorageSetup(self.config)
        self.networking_setup = NetworkingSetup(self.config)
        self.tls_manager = TLSManager(self.config)
        self.backup_manager = BackupManager(self.config)
    
    def load_config(self):
        """Load configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            console.print(f"❌ Error loading config: {e}")
            sys.exit(1)
    
    def validate_k3s_cluster(self) -> dict:
        """Validate K3s cluster status"""
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            # Check K3s service
            service_result = subprocess.run(
                ["systemctl", "is-active", "k3s"],
                capture_output=True, text=True, timeout=10
            )
            
            if service_result.returncode == 0:
                result["details"]["service"] = "running"
            else:
                result["details"]["service"] = "stopped"
                result["issues"].append("K3s service is not running")
            
            # Check nodes
            nodes_result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                capture_output=True, text=True, timeout=30
            )
            
            if nodes_result.returncode == 0:
                nodes_data = json.loads(nodes_result.stdout)
                nodes = nodes_data.get("items", [])
                
                ready_nodes = 0
                total_nodes = len(nodes)
                
                for node in nodes:
                    conditions = node.get("status", {}).get("conditions", [])
                    for condition in conditions:
                        if condition.get("type") == "Ready" and condition.get("status") == "True":
                            ready_nodes += 1
                            break
                
                result["details"]["nodes_total"] = total_nodes
                result["details"]["nodes_ready"] = ready_nodes
                
                if ready_nodes == total_nodes and total_nodes > 0:
                    result["details"]["cluster_ready"] = True
                else:
                    result["details"]["cluster_ready"] = False
                    result["issues"].append(f"Not all nodes ready: {ready_nodes}/{total_nodes}")
            else:
                result["issues"].append("Cannot access cluster (kubectl failed)")
            
            # Check system pods
            pods_result = subprocess.run([
                "kubectl", "get", "pods", "-n", "kube-system", 
                "--field-selector=status.phase!=Running", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if pods_result.returncode == 0:
                pods_data = json.loads(pods_result.stdout)
                non_running_pods = len(pods_data.get("items", []))
                
                result["details"]["system_pods_issues"] = non_running_pods
                if non_running_pods > 0:
                    result["issues"].append(f"{non_running_pods} system pods not running")
            
            # Overall status
            if not result["issues"]:
                result["status"] = "healthy"
            elif result["details"].get("cluster_ready", False):
                result["status"] = "warning"
            else:
                result["status"] = "error"
                
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"Validation error: {e}")
        
        return result
    
    def validate_gpu_setup(self) -> dict:
        """Validate GPU configuration"""
        if not self.config.get('gpu', {}).get('enabled', False):
            return {"status": "disabled", "details": {}, "issues": []}
        
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            # Detect GPUs
            gpus = self.gpu_configurator.detect_gpus()
            result["details"]["gpus_detected"] = len(gpus)
            result["details"]["gpu_types"] = list(set(gpu.vendor for gpu in gpus))
            
            # Check GPU resources in Kubernetes
            nodes_result = subprocess.run([
                "kubectl", "get", "nodes", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if nodes_result.returncode == 0:
                nodes_data = json.loads(nodes_result.stdout)
                gpu_resources = {}
                
                for node in nodes_data.get("items", []):
                    capacity = node.get("status", {}).get("capacity", {})
                    
                    for resource, count in capacity.items():
                        if "gpu" in resource.lower():
                            gpu_resources[resource] = count
                
                result["details"]["gpu_resources"] = gpu_resources
                
                if gpu_resources:
                    result["status"] = "healthy"
                elif gpus:
                    result["status"] = "warning" 
                    result["issues"].append("GPUs detected but not available in Kubernetes")
                else:
                    result["status"] = "error"
                    result["issues"].append("No GPUs detected")
            else:
                result["issues"].append("Cannot check GPU resources in cluster")
                result["status"] = "error"
                
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"GPU validation error: {e}")
        
        return result
    
    def validate_storage(self) -> dict:
        """Validate storage configuration"""
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            # Check storage classes
            sc_result = subprocess.run([
                "kubectl", "get", "storageclass", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if sc_result.returncode == 0:
                sc_data = json.loads(sc_result.stdout)
                storage_classes = [sc.get("metadata", {}).get("name") 
                                 for sc in sc_data.get("items", [])]
                
                result["details"]["storage_classes"] = storage_classes
                
                # Check for default storage class
                default_sc = None
                for sc in sc_data.get("items", []):
                    annotations = sc.get("metadata", {}).get("annotations", {})
                    if annotations.get("storageclass.kubernetes.io/is-default-class") == "true":
                        default_sc = sc.get("metadata", {}).get("name")
                        break
                
                result["details"]["default_storage_class"] = default_sc
                
                if default_sc:
                    result["status"] = "healthy"
                else:
                    result["status"] = "warning"
                    result["issues"].append("No default storage class found")
            
            # Check persistent volumes
            pv_result = subprocess.run([
                "kubectl", "get", "pv", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if pv_result.returncode == 0:
                pv_data = json.loads(pv_result.stdout)
                pvs = pv_data.get("items", [])
                
                pv_status = {}
                for pv in pvs:
                    phase = pv.get("status", {}).get("phase", "Unknown")
                    pv_status[phase] = pv_status.get(phase, 0) + 1
                
                result["details"]["persistent_volumes"] = pv_status
            
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"Storage validation error: {e}")
        
        return result
    
    def validate_networking(self) -> dict:
        """Validate networking configuration"""
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            # Check MetalLB if enabled
            if self.config.get('networking', {}).get('metallb', {}).get('enabled', False):
                metallb_result = subprocess.run([
                    "kubectl", "get", "pods", "-n", "metallb-system", "-o", "json"
                ], capture_output=True, text=True, timeout=30)
                
                if metallb_result.returncode == 0:
                    pods_data = json.loads(metallb_result.stdout)
                    pods = pods_data.get("items", [])
                    
                    running_pods = sum(1 for pod in pods 
                                     if pod.get("status", {}).get("phase") == "Running")
                    total_pods = len(pods)
                    
                    result["details"]["metallb_pods"] = f"{running_pods}/{total_pods}"
                    
                    if running_pods == total_pods and total_pods > 0:
                        result["details"]["metallb_status"] = "healthy"
                    else:
                        result["details"]["metallb_status"] = "unhealthy"
                        result["issues"].append("MetalLB pods not all running")
                
                # Check IP address pools
                pool_result = subprocess.run([
                    "kubectl", "get", "ipaddresspool", "-n", "metallb-system", "-o", "json"
                ], capture_output=True, text=True, timeout=30)
                
                if pool_result.returncode == 0:
                    pool_data = json.loads(pool_result.stdout)
                    pools = [pool.get("metadata", {}).get("name") 
                           for pool in pool_data.get("items", [])]
                    result["details"]["metallb_pools"] = pools
            
            # Check Wireguard if enabled
            if self.config.get('networking', {}).get('wireguard', {}).get('enabled', False):
                interface = self.config.get('networking', {}).get('wireguard', {}).get('interface', 'wg0')
                
                wg_result = subprocess.run([
                    "wg", "show", interface
                ], capture_output=True, text=True, timeout=10)
                
                if wg_result.returncode == 0:
                    result["details"]["wireguard_status"] = "active"
                else:
                    result["details"]["wireguard_status"] = "inactive"
                    result["issues"].append(f"Wireguard interface {interface} not found")
            
            # Check ingress controller
            ingress_result = subprocess.run([
                "kubectl", "get", "pods", "-n", "kube-system", 
                "-l", "app.kubernetes.io/name=traefik", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if ingress_result.returncode == 0:
                ingress_data = json.loads(ingress_result.stdout)
                ingress_pods = ingress_data.get("items", [])
                
                if ingress_pods:
                    running = sum(1 for pod in ingress_pods 
                                if pod.get("status", {}).get("phase") == "Running")
                    result["details"]["ingress_pods"] = f"{running}/{len(ingress_pods)}"
                else:
                    result["details"]["ingress_pods"] = "0/0"
                    result["issues"].append("No ingress controller pods found")
            
            # Overall status
            if not result["issues"]:
                result["status"] = "healthy"
            else:
                result["status"] = "warning"
                
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"Networking validation error: {e}")
        
        return result
    
    def validate_tls(self) -> dict:
        """Validate TLS configuration"""
        if not self.config.get('tls', {}).get('cert_manager', {}).get('enabled', False):
            return {"status": "disabled", "details": {}, "issues": []}
        
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            # Check cert-manager pods
            cm_result = subprocess.run([
                "kubectl", "get", "pods", "-n", "cert-manager", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if cm_result.returncode == 0:
                pods_data = json.loads(cm_result.stdout)
                pods = pods_data.get("items", [])
                
                running_pods = sum(1 for pod in pods 
                                 if pod.get("status", {}).get("phase") == "Running")
                total_pods = len(pods)
                
                result["details"]["cert_manager_pods"] = f"{running_pods}/{total_pods}"
                
                if running_pods == total_pods and total_pods > 0:
                    result["status"] = "healthy"
                else:
                    result["status"] = "error"
                    result["issues"].append("cert-manager pods not all running")
            
            # Check cluster issuers
            issuer_result = subprocess.run([
                "kubectl", "get", "clusterissuer", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if issuer_result.returncode == 0:
                issuer_data = json.loads(issuer_result.stdout)
                issuers = [issuer.get("metadata", {}).get("name") 
                          for issuer in issuer_data.get("items", [])]
                result["details"]["cluster_issuers"] = issuers
            
        except Exception as e:
            result["status"] = "error" 
            result["issues"].append(f"TLS validation error: {e}")
        
        return result
    
    def validate_backup_system(self) -> dict:
        """Validate backup configuration"""
        if not self.config.get('backup', {}).get('enabled', False):
            return {"status": "disabled", "details": {}, "issues": []}
        
        result = {"status": "unknown", "details": {}, "issues": []}
        
        try:
            destinations = self.config.get('backup', {}).get('destinations', {})
            
            # Check local backup directory
            local_config = destinations.get('local', {})
            if local_config.get('enabled', False):
                backup_path = Path(local_config.get('path', '/var/backups/k3s'))
                if backup_path.exists():
                    backups = list(backup_path.glob('*.tar.gz'))
                    result["details"]["local_backups"] = len(backups)
                    result["details"]["local_path"] = str(backup_path)
                else:
                    result["issues"].append("Local backup directory does not exist")
            
            # Check cron job
            cron_result = subprocess.run([
                "crontab", "-l"
            ], capture_output=True, text=True, timeout=10)
            
            if cron_result.returncode == 0 and "k3s-backup" in cron_result.stdout:
                result["details"]["cron_scheduled"] = True
            else:
                result["details"]["cron_scheduled"] = False
                result["issues"].append("Backup cron job not found")
            
            # Overall status
            if not result["issues"]:
                result["status"] = "healthy"
            else:
                result["status"] = "warning"
                
        except Exception as e:
            result["status"] = "error"
            result["issues"].append(f"Backup validation error: {e}")
        
        return result
    
    def run_validation(self, component: str = None, detailed: bool = False) -> dict:
        """Run comprehensive validation"""
        results = {}
        
        components = {
            'cluster': self.validate_k3s_cluster,
            'gpu': self.validate_gpu_setup,
            'storage': self.validate_storage,
            'networking': self.validate_networking,
            'tls': self.validate_tls,
            'backup': self.validate_backup_system,
        }
        
        if component:
            if component in components:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Validating {component}...", total=None)
                    results[component] = components[component]()
                    progress.update(task, completed=True)
            else:
                console.print(f"❌ Unknown component: {component}")
                return {}
        else:
            with Progress(
                SpinnerColumn(), 
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                for name, validator in components.items():
                    task = progress.add_task(f"Validating {name}...", total=None)
                    results[name] = validator()
                    progress.update(task, completed=True)
        
        return results
    
    def display_results(self, results: dict, detailed: bool = False):
        """Display validation results"""
        console.print("\n[bold blue]🔍 K3s Installation Validation Results[/bold blue]")
        
        # Create summary table
        table = Table(title="Component Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        overall_status = "healthy"
        
        for component, result in results.items():
            status = result.get("status", "unknown")
            issues = result.get("issues", [])
            details_info = result.get("details", {})
            
            # Status emoji
            if status == "healthy":
                status_display = "✅ Healthy"
            elif status == "warning":
                status_display = "⚠️ Warning"
                if overall_status == "healthy":
                    overall_status = "warning"
            elif status == "error":
                status_display = "❌ Error"
                overall_status = "error"
            elif status == "disabled":
                status_display = "➖ Disabled"
            else:
                status_display = "❓ Unknown"
                if overall_status == "healthy":
                    overall_status = "warning"
            
            # Details summary
            details_summary = []
            if component == "cluster":
                if "nodes_ready" in details_info:
                    details_summary.append(f"Nodes: {details_info['nodes_ready']}/{details_info['nodes_total']}")
            elif component == "gpu":
                if "gpus_detected" in details_info:
                    details_summary.append(f"GPUs: {details_info['gpus_detected']}")
            elif component == "storage":
                if "storage_classes" in details_info:
                    details_summary.append(f"Storage classes: {len(details_info['storage_classes'])}")
            elif component == "networking":
                if "metallb_pods" in details_info:
                    details_summary.append(f"MetalLB: {details_info['metallb_pods']}")
            elif component == "tls":
                if "cert_manager_pods" in details_info:
                    details_summary.append(f"cert-manager: {details_info['cert_manager_pods']}")
            elif component == "backup":
                if "local_backups" in details_info:
                    details_summary.append(f"Local backups: {details_info['local_backups']}")
            
            table.add_row(
                component.title(),
                status_display,
                ", ".join(details_summary) if details_summary else "N/A"
            )
        
        console.print(table)
        
        # Display issues if any
        for component, result in results.items():
            issues = result.get("issues", [])
            if issues:
                console.print(f"\n[red]Issues in {component.title()}:[/red]")
                for issue in issues:
                    console.print(f"  • {issue}")
        
        # Display detailed information if requested
        if detailed:
            console.print("\n[bold]Detailed Information:[/bold]")
            for component, result in results.items():
                details = result.get("details", {})
                if details:
                    console.print(f"\n[cyan]{component.title()} Details:[/cyan]")
                    for key, value in details.items():
                        console.print(f"  {key}: {value}")
        
        # Overall status
        if overall_status == "healthy":
            status_panel = Panel("✅ All systems operational", style="green", title="Overall Status")
        elif overall_status == "warning":
            status_panel = Panel("⚠️ Some issues detected", style="yellow", title="Overall Status")
        else:
            status_panel = Panel("❌ Critical issues found", style="red", title="Overall Status")
        
        console.print(f"\n{status_panel}")
        
        return overall_status == "healthy"

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="K3s Installation Validator")
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--component', choices=['cluster', 'gpu', 'storage', 'networking', 'tls', 'backup'],
                       help='Validate specific component only')
    parser.add_argument('--detailed', action='store_true', help='Show detailed information')
    
    args = parser.parse_args()
    
    if not Path(args.config).exists():
        console.print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    
    validator = K3sValidator(args.config)
    results = validator.run_validation(args.component, args.detailed)
    
    if results:
        success = validator.display_results(results, args.detailed)
        sys.exit(0 if success else 1)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()