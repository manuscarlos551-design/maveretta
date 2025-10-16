# -*- coding: utf-8 -*-
"""
Plugin Configuration Manager
Gerenciamento de configurações específicas para plugins
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class PluginConfigManager:
    """
    Gerenciador de configurações para plugins
    """
    
    def __init__(self, config_dir: str = "config/plugins"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._load_all_plugin_configs()
    
    def _load_all_plugin_configs(self):
        """Carrega todas as configurações de plugins"""
        for config_file in self.config_dir.glob("*.yaml"):
            plugin_name = config_file.stem
            self._load_plugin_config(plugin_name)
        
        for config_file in self.config_dir.glob("*.json"):
            plugin_name = config_file.stem
            if plugin_name not in self.plugin_configs:
                self._load_plugin_config(plugin_name, format='json')
    
    def _load_plugin_config(self, plugin_name: str, format: str = 'yaml'):
        """Carrega configuração de plugin específico"""
        try:
            if format == 'yaml':
                config_path = self.config_dir / f"{plugin_name}.yaml"
            else:
                config_path = self.config_dir / f"{plugin_name}.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    if format == 'yaml':
                        config = yaml.safe_load(f)
                    else:
                        config = json.load(f)
                
                self.plugin_configs[plugin_name] = config
                print(f"[PLUGIN_CONFIG] Configuração carregada para plugin '{plugin_name}'")
            
        except Exception as e:
            print(f"[PLUGIN_CONFIG] Erro ao carregar config do plugin '{plugin_name}': {e}")
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        Obtém configuração de um plugin
        
        Args:
            plugin_name: Nome do plugin
            
        Returns:
            Dicionário de configuração do plugin
        """
        return self.plugin_configs.get(plugin_name, {})
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """
        Define configuração de um plugin
        
        Args:
            plugin_name: Nome do plugin
            config: Configuração do plugin
        """
        self.plugin_configs[plugin_name] = config
        print(f"[PLUGIN_CONFIG] Configuração definida para plugin '{plugin_name}'")
    
    def save_plugin_config(self, plugin_name: str, format: str = 'yaml'):
        """
        Salva configuração de plugin em arquivo
        
        Args:
            plugin_name: Nome do plugin
            format: Formato do arquivo ('yaml' ou 'json')
        """
        if plugin_name not in self.plugin_configs:
            print(f"[PLUGIN_CONFIG] Plugin '{plugin_name}' não tem configuração para salvar")
            return
        
        try:
            if format == 'yaml':
                config_path = self.config_dir / f"{plugin_name}.yaml"
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.plugin_configs[plugin_name], f, 
                            default_flow_style=False, ensure_ascii=False, indent=2)
            else:
                config_path = self.config_dir / f"{plugin_name}.json"
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.plugin_configs[plugin_name], f, 
                            ensure_ascii=False, indent=2)
            
            print(f"[PLUGIN_CONFIG] Configuração do plugin '{plugin_name}' salva em {config_path}")
            
        except Exception as e:
            print(f"[PLUGIN_CONFIG] Erro ao salvar config do plugin '{plugin_name}': {e}")
    
    def update_plugin_config(self, plugin_name: str, updates: Dict[str, Any]):
        """
        Atualiza configuração de plugin parcialmente
        
        Args:
            plugin_name: Nome do plugin
            updates: Atualizações a serem aplicadas
        """
        if plugin_name not in self.plugin_configs:
            self.plugin_configs[plugin_name] = {}
        
        self.plugin_configs[plugin_name].update(updates)
        print(f"[PLUGIN_CONFIG] Configuração do plugin '{plugin_name}' atualizada")
    
    def remove_plugin_config(self, plugin_name: str):
        """Remove configuração de plugin"""
        if plugin_name in self.plugin_configs:
            del self.plugin_configs[plugin_name]
            print(f"[PLUGIN_CONFIG] Configuração do plugin '{plugin_name}' removida")
    
    def get_all_plugin_configs(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todas as configurações de plugins"""
        return self.plugin_configs.copy()
    
    def get_plugins_list(self) -> list:
        """Retorna lista de plugins com configuração"""
        return list(self.plugin_configs.keys())
    
    def create_default_config(self, plugin_name: str, plugin_type: str = 'generic') -> Dict[str, Any]:
        """
        Cria configuração padrão para um plugin
        
        Args:
            plugin_name: Nome do plugin
            plugin_type: Tipo do plugin (strategy, exchange, risk, ai)
            
        Returns:
            Configuração padrão criada
        """
        default_configs = {
            'strategy': {
                'enabled': True,
                'parameters': {
                    'take_profit': 0.10,
                    'stop_loss': 0.03,
                    'trail_trigger': 0.06,
                    'trail_distance': 0.05
                },
                'risk_settings': {
                    'max_position_size': 1000.0,
                    'max_daily_trades': 10
                }
            },
            'exchange': {
                'enabled': True,
                'timeout': 20000,
                'rate_limit': True,
                'retry_count': 3,
                'credentials': {
                    'api_key': '',
                    'api_secret': '',
                    'sandbox': False
                }
            },
            'risk': {
                'enabled': True,
                'max_drawdown': 0.10,
                'max_consecutive_losses': 3,
                'cooldown_period': 300
            },
            'ai': {
                'enabled': True,
                'threshold': 0.70,
                'model_settings': {
                    'confidence_threshold': 0.60,
                    'update_frequency': 300
                }
            },
            'generic': {
                'enabled': True,
                'settings': {}
            }
        }
        
        config = default_configs.get(plugin_type, default_configs['generic'])
        config['plugin_name'] = plugin_name
        config['plugin_type'] = plugin_type
        
        self.set_plugin_config(plugin_name, config)
        return config
    
    def validate_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        Valida configuração de plugin
        
        Args:
            plugin_name: Nome do plugin
            
        Returns:
            Resultado da validação
        """
        config = self.get_plugin_config(plugin_name)
        
        if not config:
            return {
                'valid': False,
                'errors': ['Plugin configuration not found'],
                'warnings': []
            }
        
        errors = []
        warnings = []
        
        # Validações básicas
        if 'enabled' not in config:
            warnings.append('Missing "enabled" field, defaulting to True')
        
        if 'plugin_name' not in config:
            warnings.append('Missing "plugin_name" field')
        
        if 'plugin_type' not in config:
            warnings.append('Missing "plugin_type" field')
        
        # Validações específicas por tipo
        plugin_type = config.get('plugin_type', 'generic')
        
        if plugin_type == 'strategy':
            if 'parameters' not in config:
                errors.append('Strategy plugin missing "parameters" section')
        
        elif plugin_type == 'exchange':
            if 'credentials' in config:
                creds = config['credentials']
                if not creds.get('api_key'):
                    warnings.append('Missing API key in credentials')
                if not creds.get('api_secret'):
                    warnings.append('Missing API secret in credentials')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador de configurações de plugins"""
        return {
            'config_dir': str(self.config_dir),
            'total_plugins': len(self.plugin_configs),
            'plugins_with_config': list(self.plugin_configs.keys()),
            'config_files_found': len(list(self.config_dir.glob("*.yaml"))) + len(list(self.config_dir.glob("*.json")))
        }