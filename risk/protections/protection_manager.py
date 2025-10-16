# -*- coding: utf-8 -*-
"""
Protection Manager - Sistema modular de proteções
Extensão das proteções existentes
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class BaseProtection(ABC):
    """Interface base para proteções"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Avalia se a proteção deve ser ativada"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna nome da proteção"""
        pass


class MaxDrawdownProtection(BaseProtection):
    """Proteção por máximo drawdown"""
    
    def get_name(self) -> str:
        return "max_drawdown"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        current_price = context.get('current_price')
        risk_manager = context.get('risk_manager')
        
        if not all([symbol, current_price, risk_manager]):
            return {'triggered': False, 'reason': 'insufficient_data'}
        
        blocked = risk_manager.check_drawdown_block(symbol, current_price)
        
        return {
            'triggered': blocked,
            'reason': f'drawdown_limit_exceeded' if blocked else 'within_limits',
            'symbol': symbol,
            'protection': self.get_name()
        }


class ConsecutiveLossProtection(BaseProtection):
    """Proteção por perdas consecutivas"""
    
    def get_name(self) -> str:
        return "consecutive_loss"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        risk_manager = context.get('risk_manager')
        max_losses = self.config.get('max_consecutive_losses', 3)
        
        if not risk_manager:
            return {'triggered': False, 'reason': 'no_risk_manager'}
        
        session_state = risk_manager.get_session_state()
        consecutive_losses = session_state.get('consecutive_losses', 0)
        
        triggered = consecutive_losses >= max_losses
        
        return {
            'triggered': triggered,
            'reason': f'{consecutive_losses}_consecutive_losses' if triggered else 'within_limits',
            'consecutive_losses': consecutive_losses,
            'max_allowed': max_losses,
            'protection': self.get_name()
        }


class DailyLossProtection(BaseProtection):
    """Proteção por perda diária"""
    
    def get_name(self) -> str:
        return "daily_loss"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        current_equity = context.get('current_equity')
        risk_manager = context.get('risk_manager')
        
        if not all([current_equity, risk_manager]):
            return {'triggered': False, 'reason': 'insufficient_data'}
        
        triggered = risk_manager.check_daily_loss_limit(current_equity)
        
        return {
            'triggered': triggered,
            'reason': 'daily_loss_limit_exceeded' if triggered else 'within_limits',
            'current_equity': current_equity,
            'protection': self.get_name()
        }


class TradeFrequencyProtection(BaseProtection):
    """Proteção por frequência de trades"""
    
    def get_name(self) -> str:
        return "trade_frequency"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        risk_manager = context.get('risk_manager')
        
        if not risk_manager:
            return {'triggered': False, 'reason': 'no_risk_manager'}
        
        triggered = risk_manager.check_trade_frequency_limit()
        
        return {
            'triggered': triggered,
            'reason': 'frequency_limit_exceeded' if triggered else 'within_limits',
            'protection': self.get_name()
        }


class SessionPauseProtection(BaseProtection):
    """Proteção por pausa de sessão"""
    
    def get_name(self) -> str:
        return "session_pause"
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        risk_manager = context.get('risk_manager')
        
        if not risk_manager:
            return {'triggered': False, 'reason': 'no_risk_manager'}
        
        triggered = risk_manager.check_session_pause()
        
        return {
            'triggered': triggered,
            'reason': 'session_paused' if triggered else 'session_active',
            'protection': self.get_name()
        }


class ProtectionManager:
    """
    Gerenciador modular de proteções
    Integra com sistema de risco existente
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.protections: List[BaseProtection] = []
        
        self._initialize_default_protections()
    
    def _initialize_default_protections(self):
        """Inicializa proteções padrão"""
        default_protections = [
            MaxDrawdownProtection(self.config),
            ConsecutiveLossProtection(self.config),
            DailyLossProtection(self.config),
            TradeFrequencyProtection(self.config),
            SessionPauseProtection(self.config)
        ]
        
        for protection in default_protections:
            if protection.enabled:
                self.protections.append(protection)
        
        print(f"[PROTECTION_MANAGER] {len(self.protections)} proteções ativas")
    
    def add_protection(self, protection: BaseProtection):
        """Adiciona proteção customizada"""
        if protection not in self.protections:
            self.protections.append(protection)
            print(f"[PROTECTION_MANAGER] Proteção '{protection.get_name()}' adicionada")
    
    def remove_protection(self, protection_name: str):
        """Remove proteção por nome"""
        self.protections = [p for p in self.protections if p.get_name() != protection_name]
        print(f"[PROTECTION_MANAGER] Proteção '{protection_name}' removida")
    
    def evaluate_all_protections(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avalia todas as proteções ativas
        Retorna resultado agregado
        """
        results = []
        any_triggered = False
        
        for protection in self.protections:
            try:
                result = protection.evaluate(context)
                results.append(result)
                
                if result.get('triggered', False):
                    any_triggered = True
                    
            except Exception as e:
                print(f"[PROTECTION_MANAGER] Erro em {protection.get_name()}: {e}")
                results.append({
                    'triggered': False,
                    'reason': f'evaluation_error: {e}',
                    'protection': protection.get_name()
                })
        
        # Resultado agregado
        return {
            'any_protection_triggered': any_triggered,
            'total_protections': len(self.protections),
            'triggered_protections': [r for r in results if r.get('triggered', False)],
            'all_results': results
        }
    
    def should_block_trade(self, context: Dict[str, Any]) -> bool:
        """
        Verifica se trade deve ser bloqueado
        Wrapper simples para uso no bot principal
        """
        result = self.evaluate_all_protections(context)
        return result['any_protection_triggered']
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Retorna status das proteções"""
        return {
            'total_protections': len(self.protections),
            'active_protections': [p.get_name() for p in self.protections],
            'protection_configs': {
                p.get_name(): p.config for p in self.protections
            }
        }
    
    def get_triggered_protections_summary(self, context: Dict[str, Any]) -> List[str]:
        """Retorna resumo das proteções ativadas"""
        result = self.evaluate_all_protections(context)
        
        return [
            f"{r['protection']}: {r['reason']}" 
            for r in result['triggered_protections']
        ]