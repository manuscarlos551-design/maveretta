# core/strategies/strategy_selector.py
"""
Strategy Selector - Seleção Inteligente de Estratégias
Permite seleção manual (humano) ou automática (IA)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from . import STRATEGY_REGISTRY, get_strategy
from .registry import (
    list_strategies as list_strategy_metadata,
    get_strategy as get_strategy_metadata,
    validate_strategy_for_slot,
    get_recommended_strategies_for_slot
)

logger = logging.getLogger(__name__)


class StrategySelector:
    """
    Seletor de Estratégias - Interface entre Humano/IA e Estratégias
    
    Funcionalidades:
    - Seleção manual de estratégia por humano
    - Seleção automática por agente IA
    - Validação de compatibilidade slot-estratégia
    - Recomendações baseadas em contexto
    - Histórico de performance por estratégia
    """
    
    def __init__(self, slot_manager=None):
        self.slot_manager = slot_manager
        self.strategy_performance = {}  # Histórico de performance
        logger.info("✅ StrategySelector inicializado")
    
    def list_available_strategies(self) -> List[Dict[str, Any]]:
        """
        Lista todas as estratégias disponíveis com metadados
        """
        return list_strategy_metadata()
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas de uma estratégia
        """
        return get_strategy_metadata(strategy_id)
    
    def validate_strategy_for_slot(self, strategy_id: str, slot_id: str) -> Dict[str, Any]:
        """
        Valida se estratégia é compatível com slot
        """
        if not self.slot_manager:
            return {"valid": False, "reason": "Slot manager não disponível"}
        
        slot = self.slot_manager.get_slot(slot_id)
        if not slot:
            return {"valid": False, "reason": f"Slot {slot_id} não encontrado"}
        
        slot_config = {
            "capital": slot.get("capital_base", 0),
            "market_type": slot.get("market_type", "spot"),
            "exchange": slot.get("exchange", "")
        }
        
        return validate_strategy_for_slot(strategy_id, slot_config)
    
    def get_recommendations(self, slot_id: str, market_conditions: Optional[Dict] = None) -> List[str]:
        """
        Recomenda estratégias para um slot baseado em:
        - Configuração do slot
        - Condições de mercado
        - Performance histórica
        """
        if not self.slot_manager:
            return []
        
        slot = self.slot_manager.get_slot(slot_id)
        if not slot:
            return []
        
        slot_config = {
            "capital": slot.get("capital_base", 0),
            "market_type": slot.get("market_type", "spot"),
            "exchange": slot.get("exchange", "")
        }
        
        # Recomendações base
        recommendations = get_recommended_strategies_for_slot(slot_id, slot_config)
        
        # Filtrar por condições de mercado se fornecidas
        if market_conditions:
            recommendations = self._filter_by_market_conditions(
                recommendations, 
                market_conditions
            )
        
        # Ordenar por performance histórica
        recommendations = self._sort_by_performance(recommendations, slot_id)
        
        return recommendations[:5]  # Top 5
    
    def select_strategy_manual(self, slot_id: str, strategy_id: str) -> Dict[str, Any]:
        """
        Seleção MANUAL de estratégia por humano
        """
        # Validar estratégia existe
        if strategy_id not in STRATEGY_REGISTRY:
            return {
                "success": False,
                "error": f"Estratégia '{strategy_id}' não encontrada"
            }
        
        # Validar compatibilidade
        validation = self.validate_strategy_for_slot(strategy_id, slot_id)
        if not validation.get("valid", False):
            return {
                "success": False,
                "error": validation.get("reason", "Estratégia incompatível")
            }
        
        # Aplicar estratégia ao slot
        if self.slot_manager:
            slot = self.slot_manager.get_slot(slot_id)
            if slot:
                slot["strategy"] = strategy_id
                slot["strategy_mode"] = "manual"
                slot["strategy_changed_at"] = datetime.utcnow().isoformat()
                slot["strategy_changed_by"] = "human"
                
                logger.info(f"✅ Estratégia '{strategy_id}' aplicada manualmente ao slot {slot_id}")
                
                return {
                    "success": True,
                    "slot_id": slot_id,
                    "strategy": strategy_id,
                    "mode": "manual"
                }
        
        return {"success": False, "error": "Falha ao aplicar estratégia"}
    
    def select_strategy_auto(self, slot_id: str, agent_id: str, market_data: Dict) -> Dict[str, Any]:
        """
        Seleção AUTOMÁTICA de estratégia por agente IA
        """
        # Obter recomendações baseadas em mercado
        market_conditions = self._analyze_market_conditions(market_data)
        recommendations = self.get_recommendations(slot_id, market_conditions)
        
        if not recommendations:
            return {
                "success": False,
                "error": "Nenhuma estratégia recomendada para condições atuais"
            }
        
        # IA escolhe melhor estratégia (primeira da lista = melhor score)
        selected_strategy = recommendations[0]
        
        # Aplicar estratégia ao slot
        if self.slot_manager:
            slot = self.slot_manager.get_slot(slot_id)
            if slot:
                slot["strategy"] = selected_strategy
                slot["strategy_mode"] = "auto"
                slot["strategy_changed_at"] = datetime.utcnow().isoformat()
                slot["strategy_changed_by"] = agent_id
                slot["market_conditions_at_selection"] = market_conditions
                
                logger.info(f"🤖 Estratégia '{selected_strategy}' selecionada automaticamente pelo agente {agent_id} para slot {slot_id}")
                
                return {
                    "success": True,
                    "slot_id": slot_id,
                    "strategy": selected_strategy,
                    "mode": "auto",
                    "agent_id": agent_id,
                    "alternatives": recommendations[1:],
                    "market_conditions": market_conditions
                }
        
        return {"success": False, "error": "Falha ao aplicar estratégia"}
    
    def update_performance(self, slot_id: str, strategy_id: str, performance_data: Dict):
        """
        Atualiza histórico de performance de uma estratégia
        """
        key = f"{slot_id}_{strategy_id}"
        
        if key not in self.strategy_performance:
            self.strategy_performance[key] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "win_rate": 0,
                "last_updated": None
            }
        
        perf = self.strategy_performance[key]
        perf["total_trades"] += performance_data.get("trades", 0)
        perf["winning_trades"] += performance_data.get("wins", 0)
        perf["losing_trades"] += performance_data.get("losses", 0)
        perf["total_pnl"] += performance_data.get("pnl", 0)
        
        if perf["total_trades"] > 0:
            perf["avg_pnl"] = perf["total_pnl"] / perf["total_trades"]
            perf["win_rate"] = (perf["winning_trades"] / perf["total_trades"]) * 100
        
        perf["last_updated"] = datetime.utcnow().isoformat()
    
    def get_strategy_performance(self, slot_id: str, strategy_id: str) -> Optional[Dict]:
        """
        Obtém histórico de performance de uma estratégia em um slot
        """
        key = f"{slot_id}_{strategy_id}"
        return self.strategy_performance.get(key)
    
    def _analyze_market_conditions(self, market_data: Dict) -> Dict[str, Any]:
        """
        Analisa condições de mercado para seleção de estratégia
        """
        conditions = {
            "trend": "sideways",
            "volatility": "medium",
            "volume": "normal",
            "regime": "range"
        }
        
        # Análise simplificada
        if "price_change_24h" in market_data:
            change = market_data["price_change_24h"]
            if change > 3:
                conditions["trend"] = "strong_up"
                conditions["regime"] = "trending"
            elif change < -3:
                conditions["trend"] = "strong_down"
                conditions["regime"] = "trending"
            elif abs(change) < 1:
                conditions["trend"] = "sideways"
                conditions["regime"] = "range"
        
        if "volatility" in market_data:
            vol = market_data["volatility"]
            if vol > 2.0:
                conditions["volatility"] = "high"
            elif vol < 0.5:
                conditions["volatility"] = "low"
        
        return conditions
    
    def _filter_by_market_conditions(self, strategies: List[str], conditions: Dict) -> List[str]:
        """
        Filtra estratégias baseado em condições de mercado
        """
        regime = conditions.get("regime", "range")
        volatility = conditions.get("volatility", "medium")
        
        # Preferências por regime
        if regime == "trending":
            # Prefere estratégias de tendência
            preferred = ['trend_following', 'swing_trading', 'breakout']
        elif regime == "range":
            # Prefere estratégias de range
            preferred = ['grid', 'mean_reversion', 'market_making']
        else:
            preferred = strategies
        
        # Volatilidade alta: evitar scalping/hft
        if volatility == "high":
            avoid = ['scalping', 'hft']
            strategies = [s for s in strategies if s not in avoid]
        
        # Reorganizar com preferências primeiro
        filtered = [s for s in preferred if s in strategies]
        filtered.extend([s for s in strategies if s not in filtered])
        
        return filtered
    
    def _sort_by_performance(self, strategies: List[str], slot_id: str) -> List[str]:
        """
        Ordena estratégias por performance histórica
        """
        performance_scores = []
        
        for strategy_id in strategies:
            perf = self.get_strategy_performance(slot_id, strategy_id)
            if perf and perf["total_trades"] > 5:  # Mínimo de trades para considerar
                # Score composto: win_rate * avg_pnl
                score = perf["win_rate"] * abs(perf["avg_pnl"])
            else:
                score = 0  # Sem histórico = score neutro
            
            performance_scores.append((strategy_id, score))
        
        # Ordenar por score decrescente
        performance_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [s[0] for s in performance_scores]
