"""
Main automation orchestrator that coordinates all discovery, storage, and inventory operations.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .config_manager import ConfigManager, OrchestratorConfig
from .logger import get_logger
from ..seed.seed_parser import SeedParser
from ..discovery.network_scanner import NetworkScanner
from ..discovery.hardware_detector import HardwareDetector
from ..discovery.service_scanner import ServiceScanner
from ..storage.asset_store import AssetStore
from ..ansible.inventory_generator import InventoryGenerator

logger = get_logger(__name__)


@dataclass
class OrchestrationResult:
    """Result of an orchestration operation."""
    success: bool
    timestamp: datetime
    assets_discovered: int
    assets_updated: int
    errors: List[str]
    warnings: List[str]
    execution_time: float
    inventory_generated: bool = False
    inventory_path: Optional[Path] = None


class AutomationOrchestrator:
    """
    Main orchestrator class that coordinates infrastructure discovery and management.
    
    This class implements the four main user stories:
    1. Seed inventory ingestion
    2. Automated asset discovery  
    3. Centralized source of truth management
    4. Dynamic Ansible inventory generation
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the orchestrator.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_manager = ConfigManager(config_dir)
        self.config: Optional[OrchestratorConfig] = None
        
        # Initialize components (will be created on first use)
        self._seed_parser: Optional[SeedParser] = None
        self._network_scanner: Optional[NetworkScanner] = None
        self._hardware_detector: Optional[HardwareDetector] = None
        self._service_scanner: Optional[ServiceScanner] = None
        self._asset_store: Optional[AssetStore] = None
        self._inventory_generator: Optional[InventoryGenerator] = None
    
    def initialize(self) -> None:
        """Initialize the orchestrator and all components."""
        logger.info("Initializing automation orchestrator")
        
        # Load configuration
        self.config = self.config_manager.load_config()
        
        # Initialize components lazily
        logger.info("Orchestrator initialized successfully")
    
    @property
    def seed_parser(self) -> SeedParser:
        """Get or create seed parser."""
        if self._seed_parser is None:
            self._seed_parser = SeedParser()
        return self._seed_parser
    
    @property
    def network_scanner(self) -> NetworkScanner:
        """Get or create network scanner."""
        if self._network_scanner is None:
            if self.config is None:
                raise RuntimeError("Orchestrator not initialized")
            self._network_scanner = NetworkScanner(self.config.discovery)
        return self._network_scanner
    
    @property
    def hardware_detector(self) -> HardwareDetector:
        """Get or create hardware detector."""
        if self._hardware_detector is None:
            if self.config is None:
                raise RuntimeError("Orchestrator not initialized")
            self._hardware_detector = HardwareDetector(self.config.discovery)
        return self._hardware_detector
    
    @property
    def service_scanner(self) -> ServiceScanner:
        """Get or create service scanner."""
        if self._service_scanner is None:
            if self.config is None:
                raise RuntimeError("Orchestrator not initialized")
            self._service_scanner = ServiceScanner(self.config.discovery)
        return self._service_scanner
    
    @property
    def asset_store(self) -> AssetStore:
        """Get or create asset store."""
        if self._asset_store is None:
            if self.config is None:
                raise RuntimeError("Orchestrator not initialized")
            self._asset_store = AssetStore(self.config.storage)
        return self._asset_store
    
    @property
    def inventory_generator(self) -> InventoryGenerator:
        """Get or create inventory generator."""
        if self._inventory_generator is None:
            if self.config is None:
                raise RuntimeError("Orchestrator not initialized")
            self._inventory_generator = InventoryGenerator(
                self.config.ansible,
                self.config_manager.get_group_rules()
            )
        return self._inventory_generator
    
    async def run_full_discovery(
        self,
        seed_file: Path,
        generate_inventory: bool = True
    ) -> OrchestrationResult:
        """
        Run complete discovery pipeline from seed file to Ansible inventory.
        
        Args:
            seed_file: Path to seed inventory file
            generate_inventory: Whether to generate Ansible inventory
            
        Returns:
            Orchestration result with metrics and status
        """
        start_time = datetime.now()
        result = OrchestrationResult(
            success=False,
            timestamp=start_time,
            assets_discovered=0,
            assets_updated=0,
            errors=[],
            warnings=[],
            execution_time=0.0
        )
        
        try:
            logger.info(f"Starting full discovery pipeline with seed file: {seed_file}")
            
            # Step 1: Parse seed inventory
            logger.info("Step 1: Parsing seed inventory")
            seed_data = await self._parse_seed_file(seed_file, result)
            if not seed_data:
                result.success = False
                return result
            
            # Step 2: Discover assets
            logger.info("Step 2: Discovering network assets")
            discovered_assets = await self._discover_assets(seed_data, result)
            
            # Step 3: Store assets in centralized source of truth
            logger.info("Step 3: Storing assets in centralized database")
            await self._store_assets(discovered_assets, result)
            
            # Step 4: Generate Ansible inventory
            if generate_inventory:
                logger.info("Step 4: Generating Ansible inventory")
                await self._generate_inventory(result)
            
            result.success = True
            logger.info(f"Discovery pipeline completed successfully. Discovered {result.assets_discovered} assets")
            
        except Exception as e:
            logger.error(f"Discovery pipeline failed: {e}")
            result.errors.append(str(e))
            result.success = False
            
        finally:
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def _parse_seed_file(self, seed_file: Path, result: OrchestrationResult) -> Optional[Dict[str, Any]]:
        """Parse and validate seed inventory file."""
        try:
            seed_data = self.seed_parser.parse_seed_file(seed_file)
            logger.info(f"Parsed seed file with {len(seed_data.get('networks', []))} networks "
                       f"and {len(seed_data.get('known_hosts', []))} known hosts")
            return seed_data
            
        except Exception as e:
            error_msg = f"Failed to parse seed file: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return None
    
    async def _discover_assets(self, seed_data: Dict[str, Any], result: OrchestrationResult) -> List[Dict[str, Any]]:
        """Discover assets based on seed data."""
        discovered_assets = []
        
        try:
            # Get discovery targets from seed data
            networks = seed_data.get('networks', [])
            known_hosts = seed_data.get('known_hosts', [])
            
            # Discover from networks
            for network in networks:
                logger.debug(f"Scanning network: {network}")
                network_assets = await self.network_scanner.scan_network(network)
                discovered_assets.extend(network_assets)
            
            # Process known hosts
            for host in known_hosts:
                logger.debug(f"Processing known host: {host}")
                host_data = await self._process_known_host(host)
                if host_data:
                    discovered_assets.append(host_data)
            
            # Enhance with hardware and service detection
            enhanced_assets = await self._enhance_asset_discovery(discovered_assets)
            
            result.assets_discovered = len(enhanced_assets)
            logger.info(f"Discovered {len(enhanced_assets)} total assets")
            
            return enhanced_assets
            
        except Exception as e:
            error_msg = f"Asset discovery failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return []
    
    async def _process_known_host(self, host_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a known host from seed data."""
        try:
            ip = host_info.get('ip')
            hostname = host_info.get('hostname')
            
            if not ip:
                return None
            
            # Get basic host info
            asset = {
                'ip': ip,
                'hostname': hostname or ip,
                'source': 'seed_known_host',
                'discovered_at': datetime.now().isoformat()
            }
            
            # Add any additional metadata from seed
            for key, value in host_info.items():
                if key not in ['ip', 'hostname']:
                    asset[key] = value
            
            return asset
            
        except Exception as e:
            logger.warning(f"Failed to process known host {host_info}: {e}")
            return None
    
    async def _enhance_asset_discovery(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance discovered assets with hardware and service detection."""
        enhanced_assets = []
        
        for asset in assets:
            try:
                ip = asset.get('ip')
                if not ip:
                    enhanced_assets.append(asset)
                    continue
                
                # Hardware detection
                if self.config.discovery.enable_gpu_detection:
                    hardware_info = await self.hardware_detector.detect_hardware(ip)
                    if hardware_info:
                        asset.update(hardware_info)
                
                # Service detection
                if self.config.discovery.enable_service_detection:
                    services = await self.service_scanner.scan_services(ip)
                    if services:
                        asset['services'] = services
                
                enhanced_assets.append(asset)
                
            except Exception as e:
                logger.warning(f"Failed to enhance asset {asset.get('ip', 'unknown')}: {e}")
                enhanced_assets.append(asset)
        
        return enhanced_assets
    
    async def _store_assets(self, assets: List[Dict[str, Any]], result: OrchestrationResult) -> None:
        """Store assets in centralized source of truth."""
        try:
            # Store or update assets
            updated_count = 0
            for asset in assets:
                was_updated = await self.asset_store.store_asset(asset)
                if was_updated:
                    updated_count += 1
            
            result.assets_updated = updated_count
            
            # Commit changes if git versioning is enabled
            if self.config.storage.enable_git_versioning:
                await self.asset_store.commit_changes(f"Discovered {len(assets)} assets")
            
            logger.info(f"Stored {len(assets)} assets, {updated_count} were new/updated")
            
        except Exception as e:
            error_msg = f"Failed to store assets: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
    
    async def _generate_inventory(self, result: OrchestrationResult) -> None:
        """Generate Ansible inventory from stored assets."""
        try:
            # Get all assets from store
            assets = await self.asset_store.get_all_assets()
            
            # Generate inventory
            inventory_path = await self.inventory_generator.generate_inventory(assets)
            
            result.inventory_generated = True
            result.inventory_path = inventory_path
            
            logger.info(f"Generated Ansible inventory at: {inventory_path}")
            
        except Exception as e:
            error_msg = f"Failed to generate inventory: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
    
    async def discover_from_seed(self, seed_file: Path) -> OrchestrationResult:
        """
        Discover assets from seed file without generating inventory.
        
        Args:
            seed_file: Path to seed inventory file
            
        Returns:
            Orchestration result
        """
        return await self.run_full_discovery(seed_file, generate_inventory=False)
    
    async def generate_inventory_only(self) -> OrchestrationResult:
        """
        Generate Ansible inventory from existing assets.
        
        Returns:
            Orchestration result
        """
        start_time = datetime.now()
        result = OrchestrationResult(
            success=False,
            timestamp=start_time,
            assets_discovered=0,
            assets_updated=0,
            errors=[],
            warnings=[],
            execution_time=0.0
        )
        
        try:
            logger.info("Generating Ansible inventory from stored assets")
            await self._generate_inventory(result)
            result.success = True
            
        except Exception as e:
            logger.error(f"Inventory generation failed: {e}")
            result.errors.append(str(e))
            result.success = False
            
        finally:
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
        
        return result
    
    async def get_asset_summary(self) -> Dict[str, Any]:
        """
        Get summary of all stored assets.
        
        Returns:
            Asset summary with counts and statistics
        """
        try:
            assets = await self.asset_store.get_all_assets()
            
            summary = {
                'total_assets': len(assets),
                'by_type': {},
                'by_location': {},
                'by_hardware': {},
                'services': {},
                'last_discovery': None
            }
            
            for asset in assets:
                # Count by type
                asset_type = asset.get('type', 'unknown')
                summary['by_type'][asset_type] = summary['by_type'].get(asset_type, 0) + 1
                
                # Count by location
                location = asset.get('location', 'unknown')
                summary['by_location'][location] = summary['by_location'].get(location, 0) + 1
                
                # Count by hardware features
                if asset.get('has_gpu'):
                    gpu_type = asset.get('gpu_type', 'unknown')
                    if 'gpu_nodes' not in summary['by_hardware']:
                        summary['by_hardware']['gpu_nodes'] = {}
                    summary['by_hardware']['gpu_nodes'][gpu_type] = summary['by_hardware']['gpu_nodes'].get(gpu_type, 0) + 1
                
                # Count services
                for service in asset.get('services', []):
                    service_name = service.get('name', 'unknown')
                    summary['services'][service_name] = summary['services'].get(service_name, 0) + 1
                
                # Track latest discovery time
                discovered_at = asset.get('discovered_at')
                if discovered_at and (not summary['last_discovery'] or discovered_at > summary['last_discovery']):
                    summary['last_discovery'] = discovered_at
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get asset summary: {e}")
            return {'error': str(e)}
    
    def get_config(self) -> OrchestratorConfig:
        """Get current configuration."""
        if self.config is None:
            raise RuntimeError("Orchestrator not initialized")
        return self.config