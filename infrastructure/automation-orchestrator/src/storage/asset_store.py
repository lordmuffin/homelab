"""
Centralized asset storage with version control integration.

Implements Feature 3: Centralized Source of Truth
User Story: As a System Administrator, I want all discovered asset data to be consolidated into 
a single, version-controlled source of truth so that I have a consistent and accurate inventory 
for all future automation tasks.
"""

import json
import yaml
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.config_manager import StorageConfig
from ..core.logger import get_logger
from .version_control import GitVersionControl

logger = get_logger(__name__)


class AssetStore:
    """Centralized storage for discovered assets with versioning and backup capabilities."""
    
    def __init__(self, config: StorageConfig):
        """
        Initialize asset store.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.AssetStore")
        
        # Setup storage directories
        self.data_dir = Path(config.data_directory)
        self.assets_dir = self.data_dir / "assets"
        self.backups_dir = self.data_dir / "backups"
        self.indexes_dir = self.data_dir / "indexes"
        
        # Create directories
        for directory in [self.data_dir, self.assets_dir, self.backups_dir, self.indexes_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Asset files
        self.assets_file = self.assets_dir / "assets.json"
        self.assets_yaml_file = self.assets_dir / "assets.yml"
        self.metadata_file = self.assets_dir / "metadata.json"
        
        # Initialize version control if enabled
        self.version_control: Optional[GitVersionControl] = None
        if config.enable_git_versioning:
            self.version_control = GitVersionControl(self.data_dir)
        
        # In-memory cache
        self._assets_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Thread pool for background operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asset_store")
        
        # Initialize storage
        asyncio.create_task(self._initialize_storage())
    
    async def _initialize_storage(self):
        """Initialize storage system."""
        try:
            # Create initial files if they don't exist
            if not self.assets_file.exists():
                await self._save_assets([])
            
            # Initialize git repo if enabled
            if self.version_control:
                await self.version_control.initialize_repository()
                
            # Perform cleanup
            await self._cleanup_old_backups()
            
            self.logger.info("Asset storage initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Asset storage initialization failed: {e}")
    
    async def store_asset(self, asset: Dict[str, Any]) -> bool:
        """
        Store or update an asset in the centralized database.
        
        Args:
            asset: Asset data dictionary
            
        Returns:
            True if asset was new or updated, False if unchanged
        """
        try:
            # Validate asset data
            if not self._validate_asset(asset):
                return False
            
            # Normalize asset data
            normalized_asset = self._normalize_asset(asset)
            
            # Load existing assets
            existing_assets = await self.get_all_assets()
            
            # Find existing asset by IP
            existing_index = None
            for i, existing_asset in enumerate(existing_assets):
                if existing_asset.get('ip') == normalized_asset.get('ip'):
                    existing_index = i
                    break
            
            # Check if asset has changed
            if existing_index is not None:
                existing_asset = existing_assets[existing_index]
                if self._assets_equal(existing_asset, normalized_asset):
                    self.logger.debug(f"Asset {normalized_asset.get('ip')} unchanged")
                    return False
                
                # Update existing asset
                existing_assets[existing_index] = normalized_asset
                self.logger.debug(f"Updated asset {normalized_asset.get('ip')}")
            else:
                # Add new asset
                existing_assets.append(normalized_asset)
                self.logger.info(f"Added new asset {normalized_asset.get('ip')}")
            
            # Save updated assets
            await self._save_assets(existing_assets)
            
            # Update indexes
            await self._update_indexes(existing_assets)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store asset: {e}")
            return False
    
    async def get_all_assets(self) -> List[Dict[str, Any]]:
        """
        Get all assets from storage.
        
        Returns:
            List of all asset dictionaries
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                return self._assets_cache.copy()
            
            # Load from file
            if self.assets_file.exists():
                with open(self.assets_file, 'r') as f:
                    assets = json.load(f)
                
                # Update cache
                self._assets_cache = assets
                self._cache_timestamp = datetime.now()
                
                return assets.copy()
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to load assets: {e}")
            return []
    
    async def get_asset_by_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Get asset by IP address.
        
        Args:
            ip: IP address to search for
            
        Returns:
            Asset dictionary or None if not found
        """
        assets = await self.get_all_assets()
        
        for asset in assets:
            if asset.get('ip') == ip:
                return asset.copy()
        
        return None
    
    async def get_assets_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get assets matching specific criteria.
        
        Args:
            criteria: Dictionary of criteria to match
            
        Returns:
            List of matching assets
        """
        assets = await self.get_all_assets()
        matching_assets = []
        
        for asset in assets:
            if self._matches_criteria(asset, criteria):
                matching_assets.append(asset.copy())
        
        return matching_assets
    
    async def delete_asset(self, ip: str) -> bool:
        """
        Delete asset by IP address.
        
        Args:
            ip: IP address of asset to delete
            
        Returns:
            True if asset was deleted, False if not found
        """
        try:
            assets = await self.get_all_assets()
            
            # Find and remove asset
            for i, asset in enumerate(assets):
                if asset.get('ip') == ip:
                    del assets[i]
                    await self._save_assets(assets)
                    await self._update_indexes(assets)
                    self.logger.info(f"Deleted asset {ip}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete asset {ip}: {e}")
            return False
    
    async def _save_assets(self, assets: List[Dict[str, Any]]):
        """
        Save assets to storage files.
        
        Args:
            assets: List of asset dictionaries
        """
        try:
            # Create backup before saving
            if self.assets_file.exists():
                await self._create_backup()
            
            # Save as JSON
            with open(self.assets_file, 'w') as f:
                json.dump(assets, f, indent=2, default=str, sort_keys=True)
            
            # Save as YAML for human readability
            with open(self.assets_yaml_file, 'w') as f:
                yaml.dump(assets, f, default_flow_style=False, indent=2, sort_keys=True)
            
            # Update metadata
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'total_assets': len(assets),
                'schema_version': '1.0'
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Compress if enabled
            if self.config.compression_enabled:
                await self._compress_assets_file()
            
            # Invalidate cache
            self._assets_cache = None
            self._cache_timestamp = None
            
            self.logger.debug(f"Saved {len(assets)} assets to storage")
            
        except Exception as e:
            self.logger.error(f"Failed to save assets: {e}")
            raise
    
    async def _create_backup(self):
        """Create backup of current assets file."""
        if not self.assets_file.exists():
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backups_dir / f"assets_backup_{timestamp}.json"
            
            # Copy current file to backup
            shutil.copy2(self.assets_file, backup_file)
            
            # Compress backup if enabled
            if self.config.compression_enabled:
                compressed_backup = backup_file.with_suffix('.json.gz')
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_backup, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file.unlink()  # Remove uncompressed backup
            
            self.logger.debug(f"Created backup: {backup_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
    
    async def _compress_assets_file(self):
        """Compress the main assets file."""
        try:
            compressed_file = self.assets_file.with_suffix('.json.gz')
            
            with open(self.assets_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            self.logger.debug("Compressed assets file")
            
        except Exception as e:
            self.logger.warning(f"Failed to compress assets file: {e}")
    
    async def _update_indexes(self, assets: List[Dict[str, Any]]):
        """
        Update search indexes for faster queries.
        
        Args:
            assets: List of all assets
        """
        try:
            # Create indexes by various fields
            indexes = {
                'by_ip': {},
                'by_hostname': {},
                'by_type': {},
                'by_location': {},
                'by_network': {},
                'by_service': {},
                'by_gpu_type': {},
                'by_classification': {}
            }
            
            for i, asset in enumerate(assets):
                # Index by IP
                ip = asset.get('ip')
                if ip:
                    indexes['by_ip'][ip] = i
                
                # Index by hostname
                hostname = asset.get('hostname')
                if hostname and hostname != ip:
                    indexes['by_hostname'][hostname] = i
                
                # Index by type
                asset_type = asset.get('type') or asset.get('classification', 'unknown')
                if asset_type not in indexes['by_type']:
                    indexes['by_type'][asset_type] = []
                indexes['by_type'][asset_type].append(i)
                
                # Index by location
                location = asset.get('location')
                if location:
                    if location not in indexes['by_location']:
                        indexes['by_location'][location] = []
                    indexes['by_location'][location].append(i)
                
                # Index by network
                network_name = asset.get('network_name')
                if network_name:
                    if network_name not in indexes['by_network']:
                        indexes['by_network'][network_name] = []
                    indexes['by_network'][network_name].append(i)
                
                # Index by services
                services = asset.get('services', [])
                for service in services:
                    service_name = service.get('name')
                    if service_name:
                        if service_name not in indexes['by_service']:
                            indexes['by_service'][service_name] = []
                        indexes['by_service'][service_name].append(i)
                
                # Index by GPU type
                gpu_info = asset.get('gpu_info', {})
                gpu_type = gpu_info.get('gpu_type')
                if gpu_type:
                    if gpu_type not in indexes['by_gpu_type']:
                        indexes['by_gpu_type'][gpu_type] = []
                    indexes['by_gpu_type'][gpu_type].append(i)
                
                # Index by classification
                classification = asset.get('classification')
                if classification:
                    if classification not in indexes['by_classification']:
                        indexes['by_classification'][classification] = []
                    indexes['by_classification'][classification].append(i)
            
            # Save indexes
            index_file = self.indexes_dir / "search_indexes.json"
            with open(index_file, 'w') as f:
                json.dump(indexes, f, indent=2)
            
            self.logger.debug("Updated search indexes")
            
        except Exception as e:
            self.logger.warning(f"Failed to update indexes: {e}")
    
    async def _cleanup_old_backups(self):
        """Clean up old backup files based on retention policy."""
        try:
            if not self.backups_dir.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)
            
            for backup_file in self.backups_dir.glob("assets_backup_*.json*"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    self.logger.debug(f"Cleaned up old backup: {backup_file.name}")
            
        except Exception as e:
            self.logger.warning(f"Backup cleanup failed: {e}")
    
    def _validate_asset(self, asset: Dict[str, Any]) -> bool:
        """
        Validate asset data structure.
        
        Args:
            asset: Asset data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        # Required fields
        required_fields = ['ip']
        
        for field in required_fields:
            if field not in asset or not asset[field]:
                self.logger.warning(f"Asset validation failed: missing required field '{field}'")
                return False
        
        # Validate IP format
        ip = asset['ip']
        try:
            import ipaddress
            ipaddress.ip_address(ip)
        except ipaddress.AddressValueError:
            self.logger.warning(f"Asset validation failed: invalid IP address '{ip}'")
            return False
        
        return True
    
    def _normalize_asset(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize asset data for consistent storage.
        
        Args:
            asset: Raw asset data
            
        Returns:
            Normalized asset data
        """
        normalized = asset.copy()
        
        # Add/update timestamps
        current_time = datetime.now().isoformat()
        if 'discovered_at' not in normalized:
            normalized['discovered_at'] = current_time
        normalized['last_updated'] = current_time
        
        # Normalize hostname
        if 'hostname' not in normalized or not normalized['hostname']:
            normalized['hostname'] = normalized['ip']
        
        # Add asset hash for change detection
        normalized['asset_hash'] = self._calculate_asset_hash(normalized)
        
        # Ensure services list exists
        if 'services' not in normalized:
            normalized['services'] = []
        
        # Ensure consistent field types
        if 'port_count' in normalized:
            normalized['port_count'] = int(normalized['port_count'])
        
        # Add derived fields
        normalized['has_services'] = len(normalized.get('services', [])) > 0
        normalized['service_count'] = len(normalized.get('services', []))
        
        return normalized
    
    def _calculate_asset_hash(self, asset: Dict[str, Any]) -> str:
        """
        Calculate hash of asset data for change detection.
        
        Args:
            asset: Asset data dictionary
            
        Returns:
            Asset hash string
        """
        # Create a copy without timestamp fields for hashing
        hash_data = asset.copy()
        
        # Remove fields that change frequently but don't affect core asset data
        exclude_fields = ['discovered_at', 'last_updated', 'asset_hash']
        for field in exclude_fields:
            hash_data.pop(field, None)
        
        # Create deterministic JSON string
        json_str = json.dumps(hash_data, sort_keys=True, default=str)
        
        # Calculate SHA256 hash
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]  # First 16 chars
    
    def _assets_equal(self, asset1: Dict[str, Any], asset2: Dict[str, Any]) -> bool:
        """
        Check if two assets are equal (ignoring timestamps).
        
        Args:
            asset1: First asset
            asset2: Second asset
            
        Returns:
            True if assets are equal
        """
        hash1 = self._calculate_asset_hash(asset1)
        hash2 = self._calculate_asset_hash(asset2)
        return hash1 == hash2
    
    def _matches_criteria(self, asset: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """
        Check if asset matches search criteria.
        
        Args:
            asset: Asset to check
            criteria: Search criteria dictionary
            
        Returns:
            True if asset matches criteria
        """
        for key, value in criteria.items():
            asset_value = asset.get(key)
            
            if isinstance(value, list):
                # Match any value in list
                if asset_value not in value:
                    return False
            elif isinstance(value, dict):
                # Nested criteria matching
                if not isinstance(asset_value, dict):
                    return False
                if not self._matches_criteria(asset_value, value):
                    return False
            elif isinstance(value, str) and '*' in value:
                # Wildcard matching
                import fnmatch
                if not fnmatch.fnmatch(str(asset_value), value):
                    return False
            else:
                # Exact matching
                if asset_value != value:
                    return False
        
        return True
    
    def _is_cache_valid(self) -> bool:
        """Check if the in-memory cache is still valid."""
        if self._assets_cache is None or self._cache_timestamp is None:
            return False
        
        # Cache is valid for 5 minutes
        cache_ttl = timedelta(minutes=5)
        return datetime.now() - self._cache_timestamp < cache_ttl
    
    async def commit_changes(self, message: str) -> bool:
        """
        Commit changes to version control.
        
        Args:
            message: Commit message
            
        Returns:
            True if commit successful
        """
        if not self.version_control:
            self.logger.debug("Version control not enabled")
            return False
        
        try:
            success = await self.version_control.commit_changes(message)
            if success:
                self.logger.info(f"Committed changes: {message}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
            return False
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage system statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            assets = await self.get_all_assets()
            
            stats = {
                'total_assets': len(assets),
                'storage_path': str(self.data_dir),
                'version_control_enabled': self.config.enable_git_versioning,
                'compression_enabled': self.config.compression_enabled,
                'backup_retention_days': self.config.backup_retention_days,
                'assets_by_type': {},
                'assets_by_location': {},
                'services_summary': {},
                'discovery_sources': {},
                'last_updated': None
            }
            
            # Analyze assets
            for asset in assets:
                # Count by type
                asset_type = asset.get('type') or asset.get('classification', 'unknown')
                stats['assets_by_type'][asset_type] = stats['assets_by_type'].get(asset_type, 0) + 1
                
                # Count by location
                location = asset.get('location', 'unknown')
                stats['assets_by_location'][location] = stats['assets_by_location'].get(location, 0) + 1
                
                # Count services
                for service in asset.get('services', []):
                    service_name = service.get('name', 'unknown')
                    stats['services_summary'][service_name] = stats['services_summary'].get(service_name, 0) + 1
                
                # Count discovery sources
                source = asset.get('source', 'unknown')
                stats['discovery_sources'][source] = stats['discovery_sources'].get(source, 0) + 1
                
                # Track latest update
                last_updated = asset.get('last_updated')
                if last_updated and (not stats['last_updated'] or last_updated > stats['last_updated']):
                    stats['last_updated'] = last_updated
            
            # File system statistics
            if self.assets_file.exists():
                file_stat = self.assets_file.stat()
                stats['assets_file_size'] = file_stat.st_size
                stats['assets_file_modified'] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            # Backup statistics
            backup_files = list(self.backups_dir.glob("assets_backup_*.json*"))
            stats['backup_count'] = len(backup_files)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {'error': str(e)}
    
    async def export_assets(self, output_file: Path, format: str = 'json') -> bool:
        """
        Export assets to external file.
        
        Args:
            output_file: Output file path
            format: Export format ('json', 'yaml', 'csv')
            
        Returns:
            True if export successful
        """
        try:
            assets = await self.get_all_assets()
            
            if format.lower() == 'json':
                with open(output_file, 'w') as f:
                    json.dump(assets, f, indent=2, default=str)
                    
            elif format.lower() == 'yaml':
                with open(output_file, 'w') as f:
                    yaml.dump(assets, f, default_flow_style=False, indent=2)
                    
            elif format.lower() == 'csv':
                import csv
                
                if not assets:
                    return True
                
                # Get all possible field names
                all_fields = set()
                for asset in assets:
                    all_fields.update(asset.keys())
                
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
                    writer.writeheader()
                    
                    for asset in assets:
                        # Flatten complex fields
                        flattened_asset = {}
                        for key, value in asset.items():
                            if isinstance(value, (dict, list)):
                                flattened_asset[key] = json.dumps(value, default=str)
                            else:
                                flattened_asset[key] = value
                        writer.writerow(flattened_asset)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported {len(assets)} assets to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export assets: {e}")
            return False
    
    def __del__(self):
        """Clean up thread pool executor."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)