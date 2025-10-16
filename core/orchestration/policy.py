# core/orchestration/policy.py
"""
Strategy Selection Policy - Motor de Seleção Automática de Estratégias
Escolhe estratégias baseado em regime de mercado, saúde das IAs e histórico
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from core.strategies.registry import get_strategy, get_recommended_strategies_for_slot, STRATEGY_CATALOG

class MarketRegime:
    """Classificação de regime de mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"

class StrategySelectionPolicy:
    """Motor de política para seleção automática de estratégias"""
    
    def __init__(self):
        self.regime_strategy_mapping = {
            MarketRegime.TRENDING_UP: ["momentum", "trend_following", "breakout"],
            MarketRegime.TRENDING_DOWN: ["momentum", "trend_following", "liquidity_sweep"],
            MarketRegime.SIDEWAYS: ["mean_reversion", "grid", "arbitrage", "pairs_trading"],
            MarketRegime.HIGH_VOLATILITY: ["volatility_breakout", "scalp", "news_sentiment"],
            MarketRegime.LOW_VOLATILITY: ["carry", "grid", "mean_median"],
            MarketRegime.BREAKOUT: ["breakout", "momentum", "volatility_breakout"],
            MarketRegime.UNKNOWN: ["momentum", "mean_reversion"]  # Safe defaults
        }
        
        self.ia_group_preferences = {
            "G1": ["scalp", "momentum", "orderbook_imbalance", "liquidity_sweep"],
            "G2": ["trend_following", "ml_predictive", "pairs_trading", "carry"]
        }
    
    def choose_strategy_auto(
        self, 
        slot: Dict[str, Any], 
        market_snapshot: Dict[str, Any], 
        ia_health: List[Dict[str, Any]], 
        history: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Escolhe estratégia automaticamente baseado em múltiplos critérios
        
        Returns:
            {
                "strategy": "momentum",
                "reason": "Trending market with high IA health",
                "confidence": 0.85,
                "fallback_strategies": ["breakout", "trend_following"]
            }
        """
        slot_id = slot.get("id", "unknown")
        slot_config = slot.get("config", {})
        
        # 1. Detectar regime de mercado
        market_regime = self._detect_market_regime(market_snapshot)
        
        # 2. Avaliar saúde das IAs
        ia_health_score = self._calculate_ia_health_score(ia_health, slot)
        
        # 3. Analisar histórico de performance
        historical_performance = self._analyze_historical_performance(history, slot_id)
        
        # 4. Obter estratégias candidatas
        candidate_strategies = self._get_candidate_strategies(
            slot, market_regime, ia_health, historical_performance
        )
        
        # 5. Scoring e seleção final
        scored_strategies = self._score_strategies(
            candidate_strategies, market_regime, ia_health_score, historical_performance
        )
        
        if not scored_strategies:
            # Fallback seguro
            return {
                "strategy": "momentum",
                "reason": "Fallback strategy - no suitable candidates found",
                "confidence": 0.3,
                "fallback_strategies": ["mean_reversion", "grid"]
            }
        
        # Melhor estratégia
        best_strategy = scored_strategies[0]
        fallback_strategies = [s["strategy"] for s in scored_strategies[1:3]]
        
        return {
            "strategy": best_strategy["strategy"],
            "reason": best_strategy["reason"],
            "confidence": best_strategy["score"],
            "fallback_strategies": fallback_strategies,
            "market_regime": market_regime,
            "ia_health_score": ia_health_score,
            "timestamp": datetime.now().isoformat()
        }
    
    def _detect_market_regime(self, market_snapshot: Dict[str, Any]) -> str:
        """Detecta regime atual do mercado"""
        if not market_snapshot:
            return MarketRegime.UNKNOWN
        
        try:
            # Indicadores básicos do snapshot
            volatility = market_snapshot.get("volatility", 0)
            trend_score = market_snapshot.get("trend_score", 0)
            price_change_24h = market_snapshot.get("price_change_24h", 0)
            volume_ratio = market_snapshot.get("volume_ratio", 1.0)
            
            # Classificação por volatilidade
            if volatility > 0.05:  # >5% volatilidade
                if abs(price_change_24h) > 0.1:  # >10% mudança
                    return MarketRegime.BREAKOUT
                return MarketRegime.HIGH_VOLATILITY
            elif volatility < 0.02:  # <2% volatilidade
                return MarketRegime.LOW_VOLATILITY
            
            # Classificação por tendência
            if trend_score > 0.6:
                return MarketRegime.TRENDING_UP if price_change_24h > 0 else MarketRegime.TRENDING_DOWN
            elif trend_score < -0.6:
                return MarketRegime.TRENDING_DOWN if price_change_24h < 0 else MarketRegime.TRENDING_UP
            else:
                return MarketRegime.SIDEWAYS
                
        except Exception as e:
            print(f"[POLICY] Erro ao detectar regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _calculate_ia_health_score(self, ia_health: List[Dict[str, Any]], slot: Dict[str, Any]) -> float:
        """Calcula score de saúde das IAs relevantes para o slot"""
        if not ia_health:
            return 0.3  # Score baixo sem dados
        
        relevant_ias = []
        slot_group = self._get_slot_group(slot.get("id", ""))
        
        # Filtra IAs relevantes para o grupo do slot
        for ia in ia_health:
            ia_id = ia.get("id", "")
            if slot_group in ia_id or "leader" in ia_id.lower() or "orchestrator" in ia_id.lower():
                relevant_ias.append(ia)
        
        if not relevant_ias:
            relevant_ias = ia_health  # Fallback para todas as IAs
        
        # Calcula score baseado em status, latência e accuracy
        total_score = 0
        for ia in relevant_ias:
            ia_score = 0
            
            # Status (50% do peso)
            status = ia.get("status", "RED")
            if status == "GREEN":
                ia_score += 0.5
            elif status == "AMBER":
                ia_score += 0.25
            
            # Latência (25% do peso)
            latency_ms = ia.get("latency_ms", 1000)
            if latency_ms < 100:
                ia_score += 0.25
            elif latency_ms < 500:
                ia_score += 0.15
            elif latency_ms < 1000:
                ia_score += 0.05
            
            # Accuracy (25% do peso)
            accuracy = ia.get("accuracy", 0)
            ia_score += (accuracy / 100) * 0.25
            
            total_score += ia_score
        
        return min(total_score / len(relevant_ias), 1.0) if relevant_ias else 0.3
    
    def _get_slot_group(self, slot_id: str) -> str:
        """Determina grupo (G1/G2) baseado no ID do slot"""
        try:
            import re
            numbers = re.findall(r'\d+', str(slot_id))
            if numbers:
                return "G1" if int(numbers[0]) % 2 == 1 else "G2"
        except:
            pass
        return "G1"  # Default
    
    def _analyze_historical_performance(self, history: Optional[Dict[str, Any]], slot_id: str) -> Dict[str, Any]:
        """Analisa performance histórica de estratégias no slot"""
        if not history:
            return {"top_performers": [], "avg_performance": {}}
        
        slot_history = history.get("slots", {}).get(slot_id, {})
        strategy_performance = slot_history.get("strategy_performance", {})
        
        # Ordena estratégias por performance (ROI, win rate, Sharpe ratio)
        performance_scores = []
        
        for strategy_id, perf in strategy_performance.items():
            roi = perf.get("roi_30d", 0)
            win_rate = perf.get("win_rate", 0)
            sharpe = perf.get("sharpe_ratio", 0)
            
            # Score composto
            score = (roi * 0.4) + (win_rate * 0.3) + (sharpe * 0.3)
            
            performance_scores.append({
                "strategy": strategy_id,
                "score": score,
                "roi": roi,
                "win_rate": win_rate,
                "sharpe": sharpe
            })
        
        # Ordena por score decrescente
        performance_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "top_performers": [p["strategy"] for p in performance_scores[:3]],
            "avg_performance": {p["strategy"]: p["score"] for p in performance_scores}
        }
    
    def _get_candidate_strategies(
        self, 
        slot: Dict[str, Any], 
        market_regime: str, 
        ia_health: List[Dict[str, Any]], 
        historical_performance: Dict[str, Any]
    ) -> List[str]:
        """Obtém lista de estratégias candidatas baseada nos critérios"""
        candidates = set()
        
        # 1. Estratégias por regime de mercado
        regime_strategies = self.regime_strategy_mapping.get(market_regime, [])
        candidates.update(regime_strategies)
        
        # 2. Estratégias recomendadas para o slot
        slot_recommendations = get_recommended_strategies_for_slot(
            slot.get("id", ""), slot.get("config", {})
        )
        candidates.update(slot_recommendations)
        
        # 3. Top performers históricos
        top_performers = historical_performance.get("top_performers", [])
        candidates.update(top_performers)
        
        # 4. Estratégias baseadas no grupo da IA
        slot_group = self._get_slot_group(slot.get("id", ""))
        group_preferences = self.ia_group_preferences.get(slot_group, [])
        candidates.update(group_preferences)
        
        # Filtra apenas estratégias válidas
        valid_candidates = []
        for strategy_id in candidates:
            if strategy_id in STRATEGY_CATALOG:
                valid_candidates.append(strategy_id)
        
        return valid_candidates if valid_candidates else ["momentum", "mean_reversion"]
    
    def _score_strategies(
        self, 
        candidates: List[str], 
        market_regime: str, 
        ia_health_score: float, 
        historical_performance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aplica scoring nas estratégias candidatas"""
        scored_strategies = []
        
        for strategy_id in candidates:
            strategy_config = get_strategy(strategy_id)
            if not strategy_config:
                continue
            
            score = 0
            reasons = []
            
            # 1. Compatibilidade com regime (40% do peso)
            regime_strategies = self.regime_strategy_mapping.get(market_regime, [])
            if strategy_id in regime_strategies:
                score += 0.4
                reasons.append(f"Compatible with {market_regime} regime")
            
            # 2. Adequação ao nível de risco baseado na saúde da IA (30% do peso)
            strategy_risk = strategy_config.get("risk_level", "medium")
            if ia_health_score > 0.8:  # IAs saudáveis podem arriscar mais
                if strategy_risk == "high":
                    score += 0.3
                    reasons.append("High-risk strategy with healthy IAs")
                elif strategy_risk == "medium":
                    score += 0.25
            elif ia_health_score > 0.5:  # IAs médias preferem risco médio
                if strategy_risk == "medium":
                    score += 0.3
                    reasons.append("Medium-risk strategy with stable IAs")
                elif strategy_risk == "low":
                    score += 0.2
            else:  # IAs com problemas preferem baixo risco
                if strategy_risk == "low":
                    score += 0.3
                    reasons.append("Low-risk strategy for unstable IAs")
            
            # 3. Performance histórica (30% do peso)
            avg_performance = historical_performance.get("avg_performance", {})
            if strategy_id in avg_performance:
                historical_score = avg_performance[strategy_id]
                score += historical_score * 0.3
                if historical_score > 0:
                    reasons.append(f"Positive historical performance ({historical_score:.2f})")
            
            # Ajuste por diversificação (evita repetir a mesma estratégia)
            # Este ajuste seria implementado considerando estratégias ativas em outros slots
            
            scored_strategies.append({
                "strategy": strategy_id,
                "score": min(score, 1.0),
                "reason": "; ".join(reasons) if reasons else f"Standard selection for {market_regime}"
            })
        
        # Ordena por score decrescente
        scored_strategies.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_strategies

def choose_strategy_auto(
    slot: Dict[str, Any], 
    market_snapshot: Dict[str, Any], 
    ia_health: List[Dict[str, Any]], 
    history: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Função wrapper para seleção automática de estratégia"""
    policy = StrategySelectionPolicy()
    return policy.choose_strategy_auto(slot, market_snapshot, ia_health, history)