"""
Automation Orchestrator - Infrastructure Discovery and Management System

This package provides comprehensive infrastructure discovery, asset management,
and dynamic Ansible inventory generation capabilities.
"""

__version__ = "1.0.0"
__author__ = "Homelab Infrastructure Team"

from .core.orchestrator import AutomationOrchestrator
from .core.config_manager import ConfigManager
from .core.logger import setup_logging

__all__ = ["AutomationOrchestrator", "ConfigManager", "setup_logging"]