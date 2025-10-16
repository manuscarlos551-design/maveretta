# -*- coding: utf-8 -*-
"""
Multi-Agent Coordinator Refatorado
Integra com ai_multi.py existente
"""

from typing import Dict, Tuple, List, Any

# Import do sistema existente para compatibilidade
try:
    from ai_multi import AICoordinator as LegacyMultiAgent
except ImportError:
    LegacyMultiAgent = None


class MultiAgentCoordinator:
    """
    Coordenador Multi-Agente modular
    Mantém compatibilidade com sistema existente
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Usa sistema existente se disponível
        self.legacy_multi_agent = None
        if LegacyMultiAgent:
            try:
                self.legacy_multi_agent = LegacyMultiAgent()
                print("[MULTI_AGENT] Sistema legado integrado")
            except Exception as e:
                print(f"[MULTI_AGENT] Erro ao integrar sistema legado: {e}")
        
        # Configurações próprias
        self.group_weights = {
            "G1": {"A1": 0.25, "A2": 0.25, "A3": 0.25, "A4": 0.0833, "A5": 0.0833, "A6": 0.0834},
            "G2": {"A4": 0.25, "A5": 0.25, "A6": 0.25, "A1": 0.0833, "A2": 0.0833, "A3": 0.0834}
        }
        
        self.threshold = 0.70
    
    def allow_and_regime(self, symbol: str, closes: List[float], group_id: str) -> Tuple[bool, str]:
        """
        Método principal: decide se permite entrada e qual regime aplicar
        Compatível com sistema existente
        """
        try:
            # Usa sistema legado se disponível
            if self.legacy_multi_agent:
                return self.legacy_multi_agent.allow_and_regime(symbol, closes, group_id)
            
            # Implementação de fallback
            return self._fallback_allow_and_regime(symbol, closes, group_id)
            
        except Exception as e:
            print(f"[MULTI_AGENT] Erro em allow_and_regime: {e}")
            return False, "conservative"
    
    def _fallback_allow_and_regime(self, symbol: str, closes: List[float], group_id: str) -> Tuple[bool, str]:
        """Implementação de fallback para allow_and_regime"""
        # Lógica simples de fallback
        allowed_symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]
        allow = symbol in allowed_symbols
        
        # Regime baseado em volatilidade simples
        if len(closes) >= 10:
            recent = closes[-10:]
            avg = sum(recent) / len(recent)
            variance = sum((p - avg) ** 2 for p in recent) / len(recent)
            volatility = (variance ** 0.5) / avg if avg > 0 else 0
            
            if volatility > 0.03:
                regime = "conservative"
            elif volatility < 0.01:
                regime = "aggressive"
            else:
                regime = "neutral"
        else:
            regime = "neutral"
        
        return allow, regime
    
    def get_regime_params(self, regime: str) -> Dict[str, float]:
        """Retorna parâmetros do regime - compatível com sistema existente"""
        try:
            if self.legacy_multi_agent:
                return self.legacy_multi_agent.get_regime_params(regime)
            
            # Parâmetros de fallback
            return self._get_fallback_regime_params(regime)
            
        except Exception as e:
            print(f"[MULTI_AGENT] Erro em get_regime_params: {e}")
            return self._get_fallback_regime_params("neutral")
    
    def _get_fallback_regime_params(self, regime: str) -> Dict[str, float]:
        """Parâmetros de fallback para regimes"""
        params = {
            "conservative": {
                "take_profit": 0.06,
                "stop_loss": 0.02,
                "trail_trigger": 0.04,
                "trail_distance": 0.02
            },
            "neutral": {
                "take_profit": 0.10,
                "stop_loss": 0.03,
                "trail_trigger": 0.06,
                "trail_distance": 0.05
            },
            "aggressive": {
                "take_profit": 0.15,
                "stop_loss": 0.04,
                "trail_trigger": 0.08,
                "trail_distance": 0.06
            }
        }
        
        return params.get(regime, params["neutral"])
    
    def get_group_weights(self, group_id: str) -> Dict[str, float]:
        """Retorna pesos dos agentes para um grupo - compatível com sistema existente"""
        try:
            if self.legacy_multi_agent:
                return self.legacy_multi_agent.get_group_weights(group_id)
            
            return self.group_weights.get(group_id, self.group_weights["G1"])
            
        except Exception as e:
            print(f"[MULTI_AGENT] Erro em get_group_weights: {e}")
            return self.group_weights["G1"]
    
    def get_recent_decisions(self, limit: int = 100) -> List[Dict]:
        """Retorna decisões recentes do log - compatível com sistema existente"""
        try:
            if self.legacy_multi_agent:
                return self.legacy_multi_agent.get_recent_decisions(limit)
            
            return []  # Fallback: lista vazia
            
        except Exception as e:
            print(f"[MULTI_AGENT] Erro em get_recent_decisions: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do coordenador multi-agente"""
        return {
            'legacy_integration': self.legacy_multi_agent is not None,
            'group_weights': self.group_weights,
            'threshold': self.threshold,
            'groups_configured': list(self.group_weights.keys()),
            'agents_per_group': {
                group: list(weights.keys()) 
                for group, weights in self.group_weights.items()
            }
        }
    
    # Métodos para extensibilidade futura
    def update_group_weights(self, group_id: str, weights: Dict[str, float]):
        """Atualiza pesos de um grupo"""
        if group_id in self.group_weights:
            self.group_weights[group_id].update(weights)
            print(f"[MULTI_AGENT] Pesos do grupo {group_id} atualizados: {weights}")
        else:
            print(f"[MULTI_AGENT] Grupo {group_id} não encontrado")
    
    def add_group(self, group_id: str, weights: Dict[str, float]):
        """Adiciona novo grupo de agentes"""
        self.group_weights[group_id] = weights
        print(f"[MULTI_AGENT] Grupo {group_id} adicionado com pesos: {weights}")
    
    def set_threshold(self, threshold: float):
        """Define threshold global"""
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
            print(f"[MULTI_AGENT] Threshold definido para: {threshold}")
        else:
            print(f"[MULTI_AGENT] Threshold inválido: {threshold}")


# Função de compatibilidade global
def get_multi_agent_coordinator(config: Dict[str, Any] = None) -> MultiAgentCoordinator:
    """Função global de compatibilidade"""
    return MultiAgentCoordinator(config)