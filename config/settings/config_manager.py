# -*- coding: utf-8 -*-
"""
Config Manager - Gerenciamento centralizado de configurações
Mantém compatibilidade com .env e sistema existente
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv

# Carrega .env automaticamente
load_dotenv()


class ConfigManager:
    """
    Gerenciador centralizado de configurações
    Integra .env, YAML e configurações dinâmicas
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        # Carrega configurações em ordem de prioridade
        self._load_default_config()
        self._load_env_config()
        
        if config_path:
            self._load_file_config(config_path)
    
    def _load_default_config(self):
        """Carrega configurações padrão"""
        self.config = {
            # Core settings
            'engine': {
                'name': 'Bot AI Multi-Agent v2',
                'version': '2.0.0-modular'
            },
            
            # Health server
            'health_server': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8000
            },
            
            # Trading settings (compatibilidade com .env)
            'trading': {
                'symbol': 'BTC/USDT',
                'timeframe': '1m',
                'take_profit': 0.10,
                'stop_loss': 0.03,
                'trail_trigger': 0.06,
                'trail_distance': 0.05,
                'paper_mode': False
            },
            
            # Exchange settings
            'exchange': {
                'name': 'binance',
                'timeout': 20000,
                'rate_limit': True
            },
            
            # Risk management
            'risk': {
                'max_drawdown_pct': 8.0,
                'drawdown_reset_hours': 48,
                'symbol_block_duration_hours': 2,
                'session_max_daily_loss_pct': 3.0,
                'session_max_trades_per_hour': 8,
                'session_max_consecutive_losses': 3,
                'atr_periods': 21,
                'atr_multiplier': 1.5,
                'min_position_size_usdt': 5.0,
                'max_position_size_usdt': 2000.0
            },
            
            # AI settings
            'ai': {
                'gateway_url': 'http://ai-gateway:8080',
                'score_threshold': 0.70,
                'cache_ttl_seconds': 60,
                'multi_agent_enabled': True
            },
            
            # Multi-symbol trading
            'multi_symbol': {
                'enabled': True,
                'scan_interval_sec': 4,
                'candidates_per_scan': 6,
                'max_concurrent_positions': 3,
                'min_trade_interval_sec': 15,
                'max_exposure_pct': 15.0,
                'correlation_threshold': 0.8
            },
            
            # Notifications
            'notifications': {
                'enabled': True,
                'max_retries': 2,
                'timeout': 30,
                'telegram': {
                    'enabled': False,
                    'timeout': 10
                },
                'discord': {
                    'enabled': False,
                    'timeout': 10
                }
            },
            
            # Logging
            'logging': {
                'level': 'INFO',
                'max_history': 1000,
                'auto_cleanup_days': 30
            },
            
            # Plugins
            'plugins': {
                'enabled': True,
                'auto_discover': True,
                'directories': ['plugins/implementations']
            }
        }
    
    def _load_env_config(self):
        """Carrega configurações do .env - mantém compatibilidade total"""
        
        # Exchange
        if os.getenv('EXCHANGE'):
            self.config['exchange']['name'] = os.getenv('EXCHANGE').lower()
        
        # Trading
        trading_env_vars = {
            'SYMBOL': 'symbol',
            'TIMEFRAME': 'timeframe', 
            'TAKE_PROFIT': 'take_profit',
            'STOP_LOSS': 'stop_loss',
            'TRAIL_TRIGGER': 'trail_trigger',
            'TRAIL_DIST': 'trail_distance',
            'PAPER_MODE': 'paper_mode'
        }
        
        for env_var, config_key in trading_env_vars.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_key in ['take_profit', 'stop_loss', 'trail_trigger', 'trail_distance']:
                    self.config['trading'][config_key] = float(value)
                elif config_key == 'paper_mode':
                    self.config['trading'][config_key] = value.lower() == 'true'
                else:
                    self.config['trading'][config_key] = value
        
        # Risk management
        risk_env_vars = {
            'MAX_DRAWDOWN_PER_SYMBOL_PCT': 'max_drawdown_pct',
            'DRAWDOWN_RESET_HOURS': 'drawdown_reset_hours',
            'SYMBOL_BLOCK_DURATION_HOURS': 'symbol_block_duration_hours',
            'SESSION_MAX_DAILY_LOSS_PCT': 'session_max_daily_loss_pct',
            'SESSION_MAX_TRADES_PER_HOUR': 'session_max_trades_per_hour',
            'SESSION_MAX_CONSECUTIVE_LOSSES': 'session_max_consecutive_losses',
            'ATR_PERIODS': 'atr_periods',
            'ATR_MULTIPLIER': 'atr_multiplier',
            'MIN_POSITION_SIZE_USDT': 'min_position_size_usdt',
            'MAX_POSITION_SIZE_USDT': 'max_position_size_usdt'
        }
        
        for env_var, config_key in risk_env_vars.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_key in ['atr_periods', 'drawdown_reset_hours', 'symbol_block_duration_hours', 'session_max_trades_per_hour', 'session_max_consecutive_losses']:
                    self.config['risk'][config_key] = int(value)
                else:
                    self.config['risk'][config_key] = float(value)
        
        # AI
        if os.getenv('API_URL'):
            self.config['ai']['gateway_url'] = os.getenv('API_URL')
        if os.getenv('AI_SCORE_THRESHOLD'):
            self.config['ai']['score_threshold'] = float(os.getenv('AI_SCORE_THRESHOLD'))
        if os.getenv('AI_CACHE_TTL_SECONDS'):
            self.config['ai']['cache_ttl_seconds'] = int(os.getenv('AI_CACHE_TTL_SECONDS'))
        
        # Multi-symbol
        multi_symbol_env_vars = {
            'MULTI_SYMBOL_MODE': 'enabled',
            'SCAN_INTERVAL_SEC': 'scan_interval_sec',
            'CANDIDATES_PER_SCAN': 'candidates_per_scan',
            'MAX_CONCURRENT_POSITIONS': 'max_concurrent_positions',
            'MIN_TRADE_INTERVAL_SEC': 'min_trade_interval_sec',
            'MULTI_SYMBOL_MAX_EXPOSURE_PCT': 'max_exposure_pct',
            'CORRELATION_BLOCK_THRESHOLD': 'correlation_threshold'
        }
        
        for env_var, config_key in multi_symbol_env_vars.items():
            value = os.getenv(env_var)
            if value is not None:
                if config_key == 'enabled':
                    self.config['multi_symbol'][config_key] = value.lower() == 'true'
                elif config_key in ['scan_interval_sec', 'candidates_per_scan', 'max_concurrent_positions', 'min_trade_interval_sec']:
                    self.config['multi_symbol'][config_key] = int(value)
                else:
                    self.config['multi_symbol'][config_key] = float(value)
        
        # Notifications
        if os.getenv('NOTIFICATIONS_ENABLED'):
            self.config['notifications']['enabled'] = os.getenv('NOTIFICATIONS_ENABLED').lower() == 'true'
        
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.config['notifications']['telegram']['enabled'] = True
        
        if os.getenv('DISCORD_WEBHOOK_URL'):
            self.config['notifications']['discord']['enabled'] = True
    
    def _load_file_config(self, config_path: str):
        """Carrega configurações de arquivo YAML/JSON"""
        try:
            path = Path(config_path)
            
            if not path.exists():
                print(f"[CONFIG_MANAGER] Arquivo de config não encontrado: {config_path}")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    print(f"[CONFIG_MANAGER] Formato de arquivo não suportado: {path.suffix}")
                    return
            
            # Merge configurações (arquivo sobrescreve padrão)
            self._deep_merge(self.config, file_config)
            print(f"[CONFIG_MANAGER] Configurações carregadas de: {config_path}")
            
        except Exception as e:
            print(f"[CONFIG_MANAGER] Erro ao carregar config: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Merge profundo de dicionários"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna configuração completa"""
        return self.config.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém valor de configuração usando dot notation
        
        Args:
            key: Chave em formato 'section.subsection.key'
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Define valor de configuração usando dot notation
        
        Args:
            key: Chave em formato 'section.subsection.key'
            value: Valor a ser definido
        """
        keys = key.split('.')
        config = self.config
        
        # Navega até o último nível
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Define o valor
        config[keys[-1]] = value
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Obtém configurações de trading"""
        return self.config.get('trading', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Obtém configurações de risco"""
        return self.config.get('risk', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Obtém configurações de IA"""
        return self.config.get('ai', {})
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """Obtém configurações de exchange"""
        return self.config.get('exchange', {})
    
    def get_multi_symbol_config(self) -> Dict[str, Any]:
        """Obtém configurações multi-symbol"""
        return self.config.get('multi_symbol', {})
    
    def get_notifications_config(self) -> Dict[str, Any]:
        """Obtém configurações de notificações"""
        return self.config.get('notifications', {})
    
    def save_config(self, output_path: str, format: str = 'yaml'):
        """
        Salva configuração atual em arquivo
        
        Args:
            output_path: Caminho do arquivo de saída
            format: Formato do arquivo ('yaml' ou 'json')
        """
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(self.config, f, default_flow_style=False, ensure_ascii=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                else:
                    raise ValueError(f"Formato não suportado: {format}")
            
            print(f"[CONFIG_MANAGER] Configuração salva em: {output_path}")
            
        except Exception as e:
            print(f"[CONFIG_MANAGER] Erro ao salvar config: {e}")
    
    def reload_config(self):
        """Recarrega configurações"""
        self.config.clear()
        self._load_default_config()
        self._load_env_config()
        
        if self.config_path:
            self._load_file_config(self.config_path)
        
        print("[CONFIG_MANAGER] Configurações recarregadas")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador de config"""
        return {
            'config_loaded': bool(self.config),
            'config_path': self.config_path,
            'total_sections': len(self.config),
            'sections': list(self.config.keys()),
            'env_variables_detected': self._count_env_variables()
        }
    
    def _count_env_variables(self) -> int:
        """Conta variáveis de ambiente detectadas"""
        env_vars = [
            'EXCHANGE', 'SYMBOL', 'TIMEFRAME', 'TAKE_PROFIT', 'STOP_LOSS',
            'API_URL', 'AI_SCORE_THRESHOLD', 'MULTI_SYMBOL_MODE',
            'MAX_DRAWDOWN_PER_SYMBOL_PCT', 'SESSION_MAX_DAILY_LOSS_PCT'
        ]
        
        return sum(1 for var in env_vars if os.getenv(var) is not None)


# Instância global do config manager
_global_config_manager = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Obtém instância global do config manager"""
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_path)
    
    return _global_config_manager