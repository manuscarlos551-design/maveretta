# -*- coding: utf-8 -*-
"""
AI Coordinator Refatorado - Mantém compatibilidade total
Integra com ai_orchestrator.py existente
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import do sistema existente para compatibilidade
try:
    from ai_orchestrator import AICoordinator as LegacyAICoordinator
except ImportError:
    LegacyAICoordinator = None


class AICoordinator:
    """
    Coordenador de IA modular
    Mantém 100% de compatibilidade com sistema existente
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Usa sistema existente se disponível
        self.legacy_coordinator = None
        if LegacyAICoordinator:
            try:
                self.legacy_coordinator = LegacyAICoordinator()
                print("[AI_COORDINATOR] Sistema legado integrado")
            except Exception as e:
                print(f"[AI_COORDINATOR] Erro ao integrar sistema legado: {e}")
        
        # Configurações próprias como backup
        self.data_dir = Path("data")
        self.policies_dir = Path("ai_policies")
        self.threshold = 0.70
        
        # Estado próprio
        self.current_regime = "neutral"
        self.agent_weights = {}
        
        self._initialize()
    
    def _initialize(self):
        """Inicializa o coordenador"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.policies_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[AI_COORDINATOR] Erro na inicialização: {e}")
    
    def allow(self, symbol: str) -> bool:
        """
        Função principal de decisão - compatível com sistema existente
        """
        try:
            # Usa sistema legado se disponível
            if self.legacy_coordinator:
                return self.legacy_coordinator.allow(symbol)
            
            # Implementação própria como backup
            return self._fallback_allow(symbol)
            
        except Exception as e:
            print(f"[AI_COORDINATOR] Erro em allow(): {e}")
            return False
    
    def _fallback_allow(self, symbol: str) -> bool:
        """Implementação de backup para allow()"""
        # Lógica simples de fallback
        allowed_symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]
        return symbol in allowed_symbols
    
    def decide_regime(self, closes: List[float]) -> str:
        """
        Decide o regime de trading - compatível com sistema existente
        """
        try:
            if self.legacy_coordinator:
                return self.legacy_coordinator.decide_regime(closes)
            
            # Fallback simples
            return self._fallback_decide_regime(closes)
            
        except Exception as e:
            print(f"[AI_COORDINATOR] Erro em decide_regime(): {e}")
            return "neutral"
    
    def _fallback_decide_regime(self, closes: List[float]) -> str:
        """Implementação de backup para decide_regime()"""
        if len(closes) < 20:
            return "neutral"
        
        # Análise simples de volatilidade
        recent_closes = closes[-20:]
        avg_price = sum(recent_closes) / len(recent_closes)
        price_std = (sum((p - avg_price) ** 2 for p in recent_closes) / len(recent_closes)) ** 0.5
        volatility = price_std / avg_price if avg_price > 0 else 0
        
        if volatility > 0.05:
            return "conservative"
        elif volatility < 0.02:
            return "aggressive"
        else:
            return "neutral"
    
    def regime_params(self, regime: str) -> Dict[str, Any]:
        """
        Retorna parâmetros do regime - compatível com sistema existente
        """
        try:
            if self.legacy_coordinator:
                return self.legacy_coordinator.regime_params(regime)
            
            # Parâmetros de fallback
            return self._get_fallback_params(regime)
            
        except Exception as e:
            print(f"[AI_COORDINATOR] Erro em regime_params(): {e}")
            return self._get_fallback_params("neutral")
    
    def _get_fallback_params(self, regime: str) -> Dict[str, Any]:
        """Parâmetros de fallback"""
        params = {
            "conservative": {
                "take_profit": 0.06,
                "stop_loss": 0.02,
                "trail_trigger": 0.04,
                "trail_distance": 0.02,
                "max_slots": 1,
                "position_size_multiplier": 0.5
            },
            "neutral": {
                "take_profit": 0.10,
                "stop_loss": 0.03,
                "trail_trigger": 0.06,
                "trail_distance": 0.05,
                "max_slots": 3,
                "position_size_multiplier": 1.0
            },
            "aggressive": {
                "take_profit": 0.15,
                "stop_loss": 0.04,
                "trail_trigger": 0.08,
                "trail_distance": 0.06,
                "max_slots": 3,
                "position_size_multiplier": 1.5
            }
        }
        
        return params.get(regime, params["neutral"])
    
    def get_current_regime(self) -> str:
        """Retorna o regime atual"""
        if self.legacy_coordinator:
            return self.legacy_coordinator.get_current_regime()
        return self.current_regime
    
    def get_agent_weights(self) -> Dict[str, float]:
        """Retorna os pesos atuais dos agentes"""
        if self.legacy_coordinator:
            return self.legacy_coordinator.get_agent_weights()
        
        # Pesos padrão
        return {
            "sentiment": 0.25,
            "technical": 0.35,
            "flow": 0.25,
            "risk": 0.15
        }
    
    def get_recent_decisions(self, limit: int = 200) -> List[Dict]:
        """Retorna decisões recentes da IA"""
        if self.legacy_coordinator:
            return self.legacy_coordinator.get_recent_decisions(limit)
        
        # Fallback: lista vazia
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do coordenador"""
        return {
            'legacy_integration': self.legacy_coordinator is not None,
            'current_regime': self.get_current_regime(),
            'agent_weights': self.get_agent_weights(),
            'threshold': self.threshold,
            'initialized': True
        }
    
    # Métodos adicionais para extensibilidade futura
    def update_agent_weights(self, weights: Dict[str, float]):
        """Atualiza pesos dos agentes"""
        if self.legacy_coordinator and hasattr(self.legacy_coordinator, 'update_agent_weights'):
            self.legacy_coordinator.update_agent_weights(weights)
        else:
            self.agent_weights.update(weights)
            print(f"[AI_COORDINATOR] Pesos atualizados: {weights}")
    
    def set_regime(self, regime: str):
        """Define regime manualmente"""
        if regime in ["conservative", "neutral", "aggressive"]:
            self.current_regime = regime
            print(f"[AI_COORDINATOR] Regime definido para: {regime}")
        else:
            print(f"[AI_COORDINATOR] Regime inválido: {regime}")
    
    def set_threshold(self, threshold: float):
        """Define threshold de decisão"""
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
            print(f"[AI_COORDINATOR] Threshold definido para: {threshold}")
        else:
            print(f"[AI_COORDINATOR] Threshold inválido: {threshold}")


# Funções de compatibilidade global
def get_ai_coordinator(config: Dict[str, Any] = None) -> AICoordinator:
    """Função global de compatibilidade"""
    return AICoordinator(config)