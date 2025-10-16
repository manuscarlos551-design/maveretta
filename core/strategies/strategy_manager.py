# -*- coding: utf-8 -*-
"""
Strategy Manager - Gerenciador de estratégias modular
Integra com sistema de estratégias existente
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Type

# Compatibilidade com sistema existente
try:
    from strategies.loader import load_active_strategy
except ImportError:
    load_active_strategy = None


class StrategyManager:
    """
    Gerenciador modular de estratégias
    Mantém compatibilidade com sistema existente
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategies = {}
        self.active_strategy = None
        
        # Integração com sistema existente
        self._load_legacy_strategy()
    
    def _load_legacy_strategy(self):
        """Carrega estratégia do sistema existente"""
        try:
            if load_active_strategy:
                legacy_strategy = load_active_strategy()
                if legacy_strategy:
                    self.active_strategy = legacy_strategy
                    print("[STRATEGY_MANAGER] Estratégia legacy carregada")
        except Exception as e:
            print(f"[STRATEGY_MANAGER] Erro ao carregar estratégia legacy: {e}")
    
    def register_strategy(self, name: str, strategy_class: Type, config: Dict[str, Any] = None):
        """Registra uma nova estratégia"""
        try:
            strategy_config = config or {}
            strategy_instance = strategy_class(strategy_config)
            
            self.strategies[name] = {
                'class': strategy_class,
                'instance': strategy_instance,
                'config': strategy_config
            }
            
            print(f"[STRATEGY_MANAGER] Estratégia '{name}' registrada")
            
        except Exception as e:
            print(f"[STRATEGY_MANAGER] Erro ao registrar estratégia '{name}': {e}")
    
    def activate_strategy(self, name: str) -> bool:
        """Ativa uma estratégia registrada"""
        if name in self.strategies:
            self.active_strategy = self.strategies[name]['instance']
            print(f"[STRATEGY_MANAGER] Estratégia '{name}' ativada")
            return True
        
        print(f"[STRATEGY_MANAGER] Estratégia '{name}' não encontrada")
        return False
    
    def get_active_strategy(self):
        """Retorna estratégia ativa (compatibilidade)"""
        return self.active_strategy
    
    def list_strategies(self) -> List[str]:
        """Lista estratégias disponíveis"""
        return list(self.strategies.keys())
    
    def get_strategy_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de uma estratégia"""
        if name in self.strategies:
            strategy = self.strategies[name]
            return {
                'name': name,
                'class': strategy['class'].__name__,
                'config': strategy['config'],
                'active': strategy['instance'] == self.active_strategy
            }
        return None
    
    def reload_strategy(self, name: str) -> bool:
        """Recarrega uma estratégia"""
        if name in self.strategies:
            try:
                strategy_info = self.strategies[name]
                new_instance = strategy_info['class'](strategy_info['config'])
                
                # Atualiza instância
                self.strategies[name]['instance'] = new_instance
                
                # Se era a ativa, atualiza referência
                if strategy_info['instance'] == self.active_strategy:
                    self.active_strategy = new_instance
                
                print(f"[STRATEGY_MANAGER] Estratégia '{name}' recarregada")
                return True
                
            except Exception as e:
                print(f"[STRATEGY_MANAGER] Erro ao recarregar '{name}': {e}")
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador"""
        return {
            'registered_strategies': len(self.strategies),
            'active_strategy': self.active_strategy.__class__.__name__ if self.active_strategy else None,
            'legacy_integration': load_active_strategy is not None,
            'strategies': [
                {
                    'name': name,
                    'active': info['instance'] == self.active_strategy
                }
                for name, info in self.strategies.items()
            ]
        }