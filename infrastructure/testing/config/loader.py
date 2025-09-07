#!/usr/bin/env python3
"""
K3s Testing Framework Configuration Loader
==========================================

Utility for loading and merging test configuration profiles.
Supports YAML configuration files with inheritance and profile extension.

Author: Claude Code
Version: 1.1.0
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not available. Configuration loading will be limited.")

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass

class TestConfigLoader:
    """
    Configuration loader for K3s testing framework with support for:
    - Profile inheritance (extends field)
    - Environment variable substitution
    - Validation and schema checking
    - Default value handling
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration loader
        
        Args:
            config_dir: Path to configuration directory. If None, uses default location.
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.logger = logging.getLogger("config_loader")
        self.loaded_configs = {}  # Cache for loaded configurations
        
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Load a configuration profile by name
        
        Args:
            profile_name: Name of the profile to load (without .yaml extension)
            
        Returns:
            Dictionary containing the complete configuration
            
        Raises:
            ConfigurationError: If profile cannot be loaded or is invalid
        """
        if not YAML_AVAILABLE:
            raise ConfigurationError("PyYAML is required for configuration loading")
        
        # Check cache first
        if profile_name in self.loaded_configs:
            return self.loaded_configs[profile_name].copy()
        
        profile_path = self.config_dir / f"{profile_name}.yaml"
        
        if not profile_path.exists():
            raise ConfigurationError(f"Profile '{profile_name}' not found at {profile_path}")
        
        try:
            with open(profile_path, 'r') as file:
                raw_config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML in profile '{profile_name}': {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading profile '{profile_name}': {e}")
        
        if not isinstance(raw_config, dict):
            raise ConfigurationError(f"Profile '{profile_name}' must contain a dictionary at root level")
        
        # Handle inheritance if 'extends' field is present
        if 'extends' in raw_config:
            base_profile = raw_config['extends']
            self.logger.info(f"Profile '{profile_name}' extends '{base_profile}'")
            
            # Load base configuration recursively
            base_config = self.load_profile(base_profile)
            
            # Merge configurations (child overrides parent)
            config = self._deep_merge(base_config, raw_config)
            
            # Remove the 'extends' field from final config
            config.pop('extends', None)
        else:
            config = raw_config
        
        # Apply environment variable substitution
        config = self._substitute_environment_variables(config)
        
        # Validate the configuration
        self._validate_configuration(config, profile_name)
        
        # Cache the loaded configuration
        self.loaded_configs[profile_name] = config.copy()
        
        self.logger.info(f"Successfully loaded profile '{profile_name}'")
        return config
    
    def list_available_profiles(self) -> List[str]:
        """
        List all available configuration profiles
        
        Returns:
            List of profile names (without .yaml extension)
        """
        profiles = []
        for yaml_file in self.config_dir.glob("*.yaml"):
            if yaml_file.name != "loader.py":  # Skip this file
                profiles.append(yaml_file.stem)
        return sorted(profiles)
    
    def get_profile_info(self, profile_name: str) -> Dict[str, Any]:
        """
        Get basic information about a profile without fully loading it
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Dictionary with profile metadata
        """
        profile_path = self.config_dir / f"{profile_name}.yaml"
        
        if not profile_path.exists():
            return {"error": f"Profile '{profile_name}' not found"}
        
        try:
            with open(profile_path, 'r') as file:
                raw_config = yaml.safe_load(file)
            
            return {
                "name": raw_config.get("profile_name", profile_name),
                "version": raw_config.get("profile_version", "unknown"),
                "description": raw_config.get("description", "No description available"),
                "extends": raw_config.get("extends", None),
                "file_path": str(profile_path)
            }
        except Exception as e:
            return {"error": f"Error reading profile: {e}"}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two dictionaries, with override values taking precedence
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _substitute_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute environment variables in string values
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                default_value = None
                
                # Handle default values: ${VAR:default}
                if ":" in env_var:
                    env_var, default_value = env_var.split(":", 1)
                
                return os.getenv(env_var, default_value or value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config)
    
    def _validate_configuration(self, config: Dict[str, Any], profile_name: str):
        """
        Validate the configuration for required fields and reasonable values
        
        Args:
            config: Configuration to validate
            profile_name: Name of the profile being validated
            
        Raises:
            ConfigurationError: If validation fails
        """
        # Check for required top-level fields
        required_fields = ["execution", "storage_tests", "network_tests"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Profile '{profile_name}' missing required field: {field}")
        
        # Validate execution configuration
        execution = config["execution"]
        if not isinstance(execution.get("max_parallel_tests"), int) or execution["max_parallel_tests"] < 1:
            raise ConfigurationError(f"Profile '{profile_name}': max_parallel_tests must be a positive integer")
        
        if not isinstance(execution.get("default_iterations"), int) or execution["default_iterations"] < 1:
            raise ConfigurationError(f"Profile '{profile_name}': default_iterations must be a positive integer")
        
        # Validate test focus
        test_focus = execution.get("test_focus", [])
        valid_focus = ["storage", "network"]
        for focus in test_focus:
            if focus not in valid_focus:
                raise ConfigurationError(f"Profile '{profile_name}': invalid test focus '{focus}'. Valid options: {valid_focus}")
        
        # Validate timeout values
        timeout_multiplier = execution.get("timeout_multiplier", 1.0)
        if not isinstance(timeout_multiplier, (int, float)) or timeout_multiplier <= 0:
            raise ConfigurationError(f"Profile '{profile_name}': timeout_multiplier must be a positive number")
        
        self.logger.debug(f"Configuration validation passed for profile '{profile_name}'")

def load_test_configuration(profile_name: str = "default", config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to load a test configuration
    
    Args:
        profile_name: Name of the profile to load
        config_dir: Optional custom configuration directory
        
    Returns:
        Loaded configuration dictionary
    """
    loader = TestConfigLoader(config_dir)
    return loader.load_profile(profile_name)

def main():
    """CLI interface for configuration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="K3s Testing Framework Configuration Loader")
    parser.add_argument("command", choices=["list", "info", "load", "validate"], 
                       help="Command to execute")
    parser.add_argument("--profile", "-p", default="default",
                       help="Profile name for info/load/validate commands")
    parser.add_argument("--config-dir", "-c", type=Path,
                       help="Custom configuration directory")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    loader = TestConfigLoader(args.config_dir)
    
    try:
        if args.command == "list":
            profiles = loader.list_available_profiles()
            print("Available configuration profiles:")
            for profile in profiles:
                info = loader.get_profile_info(profile)
                if "error" in info:
                    print(f"  {profile}: {info['error']}")
                else:
                    print(f"  {profile}: {info['description']}")
                    if info['extends']:
                        print(f"    Extends: {info['extends']}")
        
        elif args.command == "info":
            info = loader.get_profile_info(args.profile)
            if "error" in info:
                print(f"Error: {info['error']}")
                sys.exit(1)
            
            print(f"Profile Information for '{args.profile}':")
            print(f"  Name: {info['name']}")
            print(f"  Version: {info['version']}")
            print(f"  Description: {info['description']}")
            if info['extends']:
                print(f"  Extends: {info['extends']}")
            print(f"  File Path: {info['file_path']}")
        
        elif args.command == "load" or args.command == "validate":
            config = loader.load_profile(args.profile)
            if args.command == "load":
                import json
                print(json.dumps(config, indent=2, default=str))
            else:
                print(f"Configuration '{args.profile}' is valid!")
    
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()