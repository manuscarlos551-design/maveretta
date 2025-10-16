#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugin Registry - Sistema de Registro e Gerenciamento de Plugins
Bot AI Multi-Agente
"""

import os
import logging
import importlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..base.plugin_interface import IPlugin

logger = logging.getLogger(__name__)

class PluginRegistry:
    """
    Registro central de plugins do sistema
    """
    
    def __init__(self):
        """Inicializa o registry de plugins"""
        self.plugins: Dict[str, IPlugin] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
        
        logger.info("🔌 Plugin Registry initialized")
    
    def discover_plugins(self, plugin_dir: str = None) -> List[str]:
        """
        Descobre plugins disponíveis no diretório
        
        Args:
            plugin_dir: Diretório de plugins (padrão: /app/plugins)
            
        Returns:
            Lista de nomes de plugins descobertos
        """
        
        if plugin_dir is None:
            plugin_dir = "/app/plugins"
        
        discovered_plugins = []
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return discovered_plugins
        
        # Buscar por arquivos Python (exceto __init__.py e base/)
        for py_file in plugin_path.glob("*.py"):
            if py_file.name.startswith("__") or py_file.name == "base":
                continue
            
            plugin_name = py_file.stem
            discovered_plugins.append(plugin_name)
            logger.info(f"📦 Discovered plugin: {plugin_name}")
        
        logger.info(f"✅ Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins
    
    def load_plugin(self, plugin_name: str, plugin_dir: str = None) -> bool:
        """
        Carrega um plugin específico
        
        Args:
            plugin_name: Nome do plugin
            plugin_dir: Diretório de plugins
            
        Returns:
            True se carregado com sucesso
        """
        
        try:
            if plugin_dir is None:
                plugin_dir = "/app/plugins"
            
            # Import dinâmico do módulo do plugin
            module_path = f"plugins.{plugin_name}"
            
            try:
                plugin_module = importlib.import_module(module_path)
            except ImportError as e:
                logger.error(f"Failed to import plugin {plugin_name}: {e}")
                return False
            
            # Buscar classe do plugin no módulo
            plugin_instance = None
            
            # Convenções de nomeação de plugins
            possible_names = [
                f"{plugin_name}_plugin",  # ex: rate_limiter_plugin
                f"{self._camel_case(plugin_name)}Plugin",  # ex: RateLimiterPlugin
                "plugin_instance"  # instância global
            ]
            
            for attr_name in possible_names:
                if hasattr(plugin_module, attr_name):
                    attr = getattr(plugin_module, attr_name)
                    
                    # Verificar se é instância de IPlugin
                    if isinstance(attr, IPlugin):
                        plugin_instance = attr
                        break
            
            if plugin_instance is None:
                logger.error(f"No IPlugin instance found in {plugin_name}")
                return False
            
            # Registrar plugin
            self.plugins[plugin_name] = plugin_instance
            logger.info(f"✅ Loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def _camel_case(self, snake_str: str) -> str:
        """Converte snake_case para CamelCase"""
        components = snake_str.split('_')
        return ''.join(word.capitalize() for word in components)
    
    def initialize_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicializa um plugin específico
        
        Args:
            plugin_name: Nome do plugin
            config: Configuração específica do plugin
            
        Returns:
            True se inicializado com sucesso
        """
        
        try:
            if plugin_name not in self.plugins:
                logger.error(f"Plugin {plugin_name} not loaded")
                return False
            
            plugin = self.plugins[plugin_name]
            
            # Usar configuração específica ou padrão
            plugin_config = config or self.plugin_configs.get(plugin_name, {})
            
            # Inicializar plugin
            success = plugin.initialize(plugin_config)
            
            if success:
                logger.info(f"✅ Initialized plugin: {plugin_name}")
            else:
                logger.error(f"❌ Failed to initialize plugin: {plugin_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_name}: {e}")
            return False
    
    def initialize_all_plugins(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Inicializa todos os plugins carregados
        
        Args:
            configs: Configurações por plugin
            
        Returns:
            Dict com status de inicialização por plugin
        """
        
        results = {}
        
        if configs:
            self.plugin_configs.update(configs)
        
        for plugin_name in self.plugins.keys():
            config = self.plugin_configs.get(plugin_name)
            results[plugin_name] = self.initialize_plugin(plugin_name, config)
        
        successful = sum(results.values())
        total = len(results)
        
        logger.info(f"📊 Plugin initialization: {successful}/{total} successful")
        
        if successful == total:
            self.initialized = True
        
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """
        Obtém instância de um plugin
        
        Args:
            plugin_name: Nome do plugin
            
        Returns:
            Instância do plugin ou None
        """
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        Lista todos os plugins carregados com informações
        
        Returns:
            Lista de informações dos plugins
        """
        
        plugin_list = []
        
        for plugin_name, plugin in self.plugins.items():
            try:
                info = plugin.get_info()
                info["loaded"] = True
                info["status"] = "active" if hasattr(plugin, 'enabled') and plugin.enabled else "inactive"
                plugin_list.append(info)
                
            except Exception as e:
                plugin_list.append({
                    "name": plugin_name,
                    "loaded": True,
                    "status": "error",
                    "error": str(e)
                })
        
        return plugin_list
    
    def execute_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """
        Executa um plugin específico
        
        Args:
            plugin_name: Nome do plugin
            
        Returns:
            Resultado da execução
        """
        
        try:
            if plugin_name not in self.plugins:
                return {
                    "error": f"Plugin {plugin_name} not found",
                    "success": False
                }
            
            plugin = self.plugins[plugin_name]
            result = plugin.execute()
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_name}: {e}")
            return {
                "error": str(e),
                "success": False,
                "plugin": plugin_name
            }
    
    def execute_all_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Executa todos os plugins
        
        Returns:
            Resultados da execução por plugin
        """
        
        results = {}
        
        for plugin_name in self.plugins.keys():
            results[plugin_name] = self.execute_plugin(plugin_name)
        
        return results
    
    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Faz shutdown de um plugin específico
        
        Args:
            plugin_name: Nome do plugin
            
        Returns:
            True se shutdown bem-sucedido
        """
        
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not found for shutdown")
                return False
            
            plugin = self.plugins[plugin_name]
            success = plugin.shutdown()
            
            if success:
                logger.info(f"🛑 Plugin {plugin_name} shutdown completed")
            else:
                logger.error(f"❌ Plugin {plugin_name} shutdown failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_name}: {e}")
            return False
    
    def shutdown_all_plugins(self) -> Dict[str, bool]:
        """
        Faz shutdown de todos os plugins
        
        Returns:
            Resultados do shutdown por plugin
        """
        
        results = {}
        
        for plugin_name in self.plugins.keys():
            results[plugin_name] = self.shutdown_plugin(plugin_name)
        
        successful = sum(results.values())
        total = len(results)
        
        logger.info(f"🛑 Plugin shutdown: {successful}/{total} successful")
        return results
    
    def auto_setup(self, plugin_dir: str = None, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Setup automático: descobre, carrega e inicializa todos os plugins
        
        Args:
            plugin_dir: Diretório de plugins
            configs: Configurações por plugin
            
        Returns:
            True se setup bem-sucedido
        """
        
        try:
            # Descobrir plugins
            discovered = self.discover_plugins(plugin_dir)
            
            if not discovered:
                logger.warning("No plugins discovered")
                return True  # Não é erro se não há plugins
            
            # Carregar plugins
            loaded_count = 0
            for plugin_name in discovered:
                if self.load_plugin(plugin_name, plugin_dir):
                    loaded_count += 1
            
            logger.info(f"📦 Loaded {loaded_count}/{len(discovered)} plugins")
            
            # Inicializar plugins
            if self.plugins:
                results = self.initialize_all_plugins(configs)
                successful = sum(results.values())
                
                if successful > 0:
                    logger.info(f"🚀 Plugin system ready: {successful} plugins active")
                    return True
                else:
                    logger.warning("No plugins successfully initialized")
                    return False
            else:
                logger.warning("No plugins loaded")
                return False
                
        except Exception as e:
            logger.error(f"Auto setup error: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do sistema de plugins
        
        Returns:
            Status detalhado do sistema
        """
        
        plugin_list = self.list_plugins()
        active_plugins = [p for p in plugin_list if p.get("status") == "active"]
        error_plugins = [p for p in plugin_list if p.get("status") == "error"]
        
        return {
            "initialized": self.initialized,
            "total_plugins": len(self.plugins),
            "active_plugins": len(active_plugins),
            "error_plugins": len(error_plugins),
            "plugins": plugin_list,
            "registry_status": "healthy" if len(active_plugins) > 0 else "degraded"
        }

# Instância global do registry
plugin_registry = PluginRegistry()

# Utilitários de conveniência
def get_plugin_registry() -> PluginRegistry:
    """Retorna instância do registry"""
    return plugin_registry

def setup_all_plugins(plugin_dir: str = None, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    """Setup automático de todos os plugins"""
    return plugin_registry.auto_setup(plugin_dir, configs)

def get_plugin(plugin_name: str) -> Optional[IPlugin]:
    """Obtém instância de plugin"""
    return plugin_registry.get_plugin(plugin_name)