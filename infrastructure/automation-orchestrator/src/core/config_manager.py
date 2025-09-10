"""
Configuration management for the automation orchestrator.
Handles loading, validation, and management of all configuration files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError
from .logger import get_logger

logger = get_logger(__name__)


class DiscoveryConfig(BaseModel):
    """Discovery engine configuration."""
    network_timeout: int = Field(default=30, ge=1, le=300)
    port_scan_timeout: int = Field(default=10, ge=1, le=60)
    max_parallel_scans: int = Field(default=50, ge=1, le=500)
    default_ports: List[int] = Field(default_factory=lambda: [22, 80, 443, 3389])
    enable_gpu_detection: bool = Field(default=True)
    enable_service_detection: bool = Field(default=True)
    nmap_arguments: str = Field(default="-sS -O")


class StorageConfig(BaseModel):
    """Asset storage configuration."""
    data_directory: Path = Field(default=Path("data"))
    enable_git_versioning: bool = Field(default=True)
    backup_retention_days: int = Field(default=30, ge=1, le=365)
    auto_commit: bool = Field(default=True)
    compression_enabled: bool = Field(default=True)


class AnsibleConfig(BaseModel):
    """Ansible inventory configuration."""
    output_format: str = Field(default="yaml", regex="^(yaml|json|ini)$")
    group_by_role: bool = Field(default=True)
    group_by_location: bool = Field(default=True)
    group_by_hardware: bool = Field(default=True)
    include_metadata: bool = Field(default=True)
    custom_groups: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class OrchestratorConfig(BaseModel):
    """Main orchestrator configuration."""
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file: Optional[Path] = None
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ansible: AnsibleConfig = Field(default_factory=AnsibleConfig)


class ConfigManager:
    """Manages configuration loading, validation, and access."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent.parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        self.config: Optional[OrchestratorConfig] = None
        self.custom_rules: Dict[str, Any] = {}
        
    def load_config(self, config_file: Optional[Path] = None) -> OrchestratorConfig:
        """
        Load and validate orchestrator configuration.
        
        Args:
            config_file: Path to main config file. If None, uses default.
            
        Returns:
            Validated configuration object
            
        Raises:
            ValidationError: If configuration is invalid
            FileNotFoundError: If required config files are missing
        """
        if config_file is None:
            config_file = self.config_dir / "orchestrator.yml"
        
        logger.info(f"Loading configuration from {config_file}")
        
        # Load main configuration
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            
            self.config = OrchestratorConfig(**config_data)
            logger.info("Configuration loaded successfully")
            
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
            self.config = OrchestratorConfig()
            
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {config_file}: {e}")
            raise
        
        # Load additional rule files
        self._load_discovery_rules()
        self._load_group_rules()
        
        return self.config
    
    def _load_discovery_rules(self):
        """Load discovery rules configuration."""
        rules_file = self.config_dir / "discovery_rules.yml"
        
        try:
            with open(rules_file, 'r') as f:
                self.custom_rules['discovery'] = yaml.safe_load(f) or {}
            logger.debug("Discovery rules loaded")
            
        except FileNotFoundError:
            logger.debug("No discovery rules file found, using defaults")
            self.custom_rules['discovery'] = {}
        except yaml.YAMLError as e:
            logger.warning(f"Error parsing discovery rules: {e}")
            self.custom_rules['discovery'] = {}
    
    def _load_group_rules(self):
        """Load Ansible grouping rules configuration."""
        rules_file = self.config_dir / "group_rules.yml"
        
        try:
            with open(rules_file, 'r') as f:
                self.custom_rules['groups'] = yaml.safe_load(f) or {}
            logger.debug("Group rules loaded")
            
        except FileNotFoundError:
            logger.debug("No group rules file found, using defaults")
            self.custom_rules['groups'] = {}
        except yaml.YAMLError as e:
            logger.warning(f"Error parsing group rules: {e}")
            self.custom_rules['groups'] = {}
    
    def get_config(self) -> OrchestratorConfig:
        """Get the loaded configuration."""
        if self.config is None:
            return self.load_config()
        return self.config
    
    def get_discovery_rules(self) -> Dict[str, Any]:
        """Get discovery rules configuration."""
        return self.custom_rules.get('discovery', {})
    
    def get_group_rules(self) -> Dict[str, Any]:
        """Get Ansible grouping rules configuration."""
        return self.custom_rules.get('groups', {})
    
    def save_default_config(self, config_file: Optional[Path] = None) -> Path:
        """
        Save default configuration to file.
        
        Args:
            config_file: Path to save config. If None, uses default.
            
        Returns:
            Path to saved configuration file
        """
        if config_file is None:
            config_file = self.config_dir / "orchestrator.yml"
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = OrchestratorConfig()
        config_dict = default_config.dict()
        
        # Convert Path objects to strings for YAML serialization
        self._serialize_paths(config_dict)
        
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Default configuration saved to {config_file}")
        return config_file
    
    def _serialize_paths(self, data: Dict[str, Any]):
        """Convert Path objects to strings for YAML serialization."""
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, dict):
                self._serialize_paths(value)
    
    def update_config(self, **kwargs) -> OrchestratorConfig:
        """
        Update configuration with new values.
        
        Args:
            **kwargs: Configuration parameters to update
            
        Returns:
            Updated configuration object
        """
        if self.config is None:
            self.load_config()
        
        config_dict = self.config.dict()
        config_dict.update(kwargs)
        
        self.config = OrchestratorConfig(**config_dict)
        logger.debug("Configuration updated")
        
        return self.config