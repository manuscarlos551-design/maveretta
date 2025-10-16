"""
Configuration Management Module
Sistema centralizado de configurações
"""

from .settings.config_manager import ConfigManager
from .plugins.plugin_config import PluginConfigManager

__all__ = ['ConfigManager', 'PluginConfigManager']