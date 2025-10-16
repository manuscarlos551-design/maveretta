# core/strategies/registry.py
"""
Strategy Registry - Catálogo Completo de Estratégias de Trading
Sistema centralizado com metadados e validações para todas as estratégias suportadas
"""

from typing import Dict, List, Any, Optional
from enum import Enum

class StrategyGroup(Enum):
    """Grupos de estratégias por perfil operacional"""
    SHORT_TERM = "short-term"
    TREND = "trend" 
    COUNTER_TREND = "counter-trend"
    MARKET_NEUTRAL = "market-neutral"
    RANGE = "range"
    AI = "ai"
    VOLATILITY = "volatility"
    FUNDING = "funding"
    MICROSTRUCTURE = "microstructure"
    EVENT = "event"
    INTRADAY = "intraday"

# Catálogo completo com 16 estratégias
STRATEGY_CATALOG = {
    "scalp": {
        "name": "Scalp",
        "group": StrategyGroup.SHORT_TERM.value,
        "description": "Operações de alta frequência com lucros pequenos e rápidos",
        "granularity": "1m",
        "min_data": "1d",
        "min_notional": 10,
        "risk_level": "high",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "50-200", "avg_hold_time": "1-5min"}
    },
    "momentum": {
        "name": "Momentum",
        "group": StrategyGroup.TREND.value,
        "description": "Segue tendências de preço com confirmação de momento",
        "granularity": "5m",
        "min_data": "7d",
        "min_notional": 50,
        "risk_level": "medium",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "10-30", "avg_hold_time": "30min-2h"}
    },
    "mean_reversion": {
        "name": "Mean Reversion",
        "group": StrategyGroup.COUNTER_TREND.value,
        "description": "Aposta no retorno à média após movimentos extremos",
        "granularity": "5m",
        "min_data": "14d",
        "min_notional": 50,
        "risk_level": "medium",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "5-15", "avg_hold_time": "1-6h"}
    },
    "breakout": {
        "name": "Breakout",
        "group": StrategyGroup.TREND.value,
        "description": "Detecta e segue rompimentos de níveis de suporte/resistência",
        "granularity": "15m",
        "min_data": "21d",
        "min_notional": 100,
        "risk_level": "high",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "3-10", "avg_hold_time": "2-8h"}
    },
    "trend_following": {
        "name": "Trend Following",
        "group": StrategyGroup.TREND.value,
        "description": "Segue tendências de longo prazo com filtros de ruído",
        "granularity": "1h",
        "min_data": "30d",
        "min_notional": 200,
        "risk_level": "low",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "1-5", "avg_hold_time": "6-24h"}
    },
    "arbitrage": {
        "name": "Arbitrage",
        "group": StrategyGroup.MARKET_NEUTRAL.value,
        "description": "Explora diferenças de preço entre exchanges ou instrumentos",
        "granularity": "1m",
        "min_data": "3d",
        "min_notional": 500,
        "risk_level": "low",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "20-100", "avg_hold_time": "1-10min"}
    },
    "grid": {
        "name": "Grid Trading",
        "group": StrategyGroup.RANGE.value,
        "description": "Ordens em grade para capturar oscilações em mercado lateral",
        "granularity": "5m",
        "min_data": "7d",
        "min_notional": 300,
        "risk_level": "medium",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "10-40", "avg_hold_time": "15min-4h"}
    },
    "pairs_trading": {
        "name": "Pairs Trading",
        "group": StrategyGroup.MARKET_NEUTRAL.value,
        "description": "Trading de pares correlacionados buscando convergência",
        "granularity": "15m",
        "min_data": "30d",
        "min_notional": 1000,
        "risk_level": "medium",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "2-8", "avg_hold_time": "4-48h"}
    },
    "ml_predictive": {
        "name": "ML Predictive",
        "group": StrategyGroup.AI.value,
        "description": "Previsões baseadas em machine learning e análise preditiva",
        "granularity": "15m",
        "min_data": "60d",
        "min_notional": 200,
        "risk_level": "high",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "5-20", "avg_hold_time": "1-12h"}
    },
    "volatility_breakout": {
        "name": "Volatility Breakout",
        "group": StrategyGroup.VOLATILITY.value,
        "description": "Detecta explosões de volatilidade para entradas direcionais",
        "granularity": "5m",
        "min_data": "14d",
        "min_notional": 150,
        "risk_level": "high",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "5-25", "avg_hold_time": "30min-4h"}
    },
    "mean_median": {
        "name": "Mean/Median",
        "group": StrategyGroup.COUNTER_TREND.value,
        "description": "Reversão baseada em desvios da média e mediana móvel",
        "granularity": "15m",
        "min_data": "21d",
        "min_notional": 100,
        "risk_level": "medium",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "3-12", "avg_hold_time": "2-8h"}
    },
    "carry": {
        "name": "Carry",
        "group": StrategyGroup.FUNDING.value,
        "description": "Estratégia de funding rate e carry trade em perpetuals",
        "granularity": "1h",
        "min_data": "7d",
        "min_notional": 1000,
        "risk_level": "low",
        "markets": ["futures"],
        "performance_target": {"daily_trades": "1-3", "avg_hold_time": "8-72h"}
    },
    "liquidity_sweep": {
        "name": "Liquidity Sweep",
        "group": StrategyGroup.MICROSTRUCTURE.value,
        "description": "Detecta e segue movimentos de varredura de liquidez",
        "granularity": "1m",
        "min_data": "5d",
        "min_notional": 200,
        "risk_level": "high",
        "markets": ["futures"],
        "performance_target": {"daily_trades": "15-50", "avg_hold_time": "5-30min"}
    },
    "orderbook_imbalance": {
        "name": "Orderbook Imbalance",
        "group": StrategyGroup.MICROSTRUCTURE.value,
        "description": "Analisa desequilíbrios no order book para previsão direcional",
        "granularity": "1m",
        "min_data": "3d",
        "min_notional": 100,
        "risk_level": "medium",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "20-80", "avg_hold_time": "2-15min"}
    },
    "news_sentiment": {
        "name": "News/Sentiment",
        "group": StrategyGroup.EVENT.value,
        "description": "Trading baseado em análise de notícias e sentiment do mercado",
        "granularity": "5m",
        "min_data": "7d",
        "min_notional": 300,
        "risk_level": "high",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "2-10", "avg_hold_time": "15min-6h"}
    },
    "reversion_intraday": {
        "name": "Intraday Reversion",
        "group": StrategyGroup.INTRADAY.value,
        "description": "Reversão intradiária com fechamento obrigatório no final do dia",
        "granularity": "15m",
        "min_data": "14d",
        "min_notional": 150,
        "risk_level": "medium",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "3-15", "avg_hold_time": "1-6h"}
    },
    "market_making": {
        "name": "Market Making",
        "group": StrategyGroup.MICROSTRUCTURE.value,
        "description": "Market making profissional com múltiplos níveis de ordens ao redor do spread",
        "granularity": "1m",
        "min_data": "3d",
        "min_notional": 500,
        "risk_level": "medium",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "100-500", "avg_hold_time": "1-10min"}
    },
    "grid_trading": {
        "name": "Grid Trading",
        "group": StrategyGroup.RANGE.value,
        "description": "Grid trading com distribuição inteligente de ordens em múltiplos níveis",
        "granularity": "15m",
        "min_data": "7d",
        "min_notional": 300,
        "risk_level": "medium",
        "markets": ["spot"],
        "performance_target": {"daily_trades": "10-40", "avg_hold_time": "30min-4h"}
    },
    "dca": {
        "name": "DCA (Dollar Cost Averaging)",
        "group": StrategyGroup.TREND.value,
        "description": "Acumulação gradual com pyramid trading para reduzir risco de timing",
        "granularity": "1h",
        "min_data": "14d",
        "min_notional": 200,
        "risk_level": "low",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "1-5", "avg_hold_time": "24-168h"}
    },
    "multi_timeframe": {
        "name": "Multi-Timeframe",
        "group": StrategyGroup.AI.value,
        "description": "Análise multi-timeframe com confirmação de sinais em múltiplos períodos",
        "granularity": "15m",
        "min_data": "30d",
        "min_notional": 200,
        "risk_level": "medium",
        "markets": ["spot", "futures"],
        "performance_target": {"daily_trades": "5-20", "avg_hold_time": "1-12h"}
    }
}

def list_strategies() -> List[Dict[str, Any]]:
    """Retorna lista completa de estratégias em formato JSON-ready"""
    strategies = []
    
    for strategy_id, config in STRATEGY_CATALOG.items():
        strategy_info = {
            "id": strategy_id,
            **config
        }
        strategies.append(strategy_info)
    
    return strategies

def get_strategy(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Retorna configuração de uma estratégia específica"""
    if strategy_id in STRATEGY_CATALOG:
        return {
            "id": strategy_id,
            **STRATEGY_CATALOG[strategy_id]
        }
    return None

def validate_strategy_for_slot(strategy_id: str, slot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Valida se estratégia é compatível com configuração do slot"""
    strategy = get_strategy(strategy_id)
    
    if not strategy:
        return {"valid": False, "reason": f"Estratégia '{strategy_id}' não encontrada"}
    
    # Validação de notional mínimo
    slot_capital = slot_config.get("capital", 0)
    min_notional = strategy.get("min_notional", 0)
    
    if slot_capital < min_notional:
        return {
            "valid": False, 
            "reason": f"Capital do slot (${slot_capital}) menor que mínimo requerido (${min_notional})"
        }
    
    # Validação de mercado
    slot_market_type = slot_config.get("market_type", "spot")
    supported_markets = strategy.get("markets", ["spot"])
    
    if slot_market_type not in supported_markets:
        return {
            "valid": False,
            "reason": f"Tipo de mercado '{slot_market_type}' não suportado pela estratégia"
        }
    
    return {"valid": True, "reason": "Estratégia válida para o slot"}

def get_strategies_by_group(group: str) -> List[Dict[str, Any]]:
    """Retorna estratégias filtradas por grupo"""
    strategies = []
    
    for strategy_id, config in STRATEGY_CATALOG.items():
        if config.get("group") == group:
            strategies.append({
                "id": strategy_id,
                **config
            })
    
    return strategies

def get_strategy_groups() -> List[Dict[str, Any]]:
    """Retorna lista de grupos de estratégias disponíveis"""
    groups = {}
    
    for config in STRATEGY_CATALOG.values():
        group = config.get("group")
        if group not in groups:
            groups[group] = {
                "id": group,
                "name": group.replace("-", " ").title(),
                "strategies": []
            }
        groups[group]["strategies"].append(config["name"])
    
    return list(groups.values())

def get_recommended_strategies_for_slot(slot_id: str, slot_config: Dict[str, Any]) -> List[str]:
    """Retorna estratégias recomendadas baseadas na configuração do slot"""
    recommendations = []
    
    # Determina se slot é ímpar (G1 - curto prazo) ou par (G2 - longo prazo)
    try:
        import re
        numbers = re.findall(r'\d+', str(slot_id))
        is_odd = int(numbers[0]) % 2 == 1 if numbers else True
    except:
        is_odd = True
    
    if is_odd:
        # G1: Estratégias de curto prazo
        preferred_groups = [StrategyGroup.SHORT_TERM.value, StrategyGroup.MICROSTRUCTURE.value, StrategyGroup.VOLATILITY.value]
    else:
        # G2: Estratégias de longo prazo  
        preferred_groups = [StrategyGroup.TREND.value, StrategyGroup.AI.value, StrategyGroup.MARKET_NEUTRAL.value]
    
    # Filtra estratégias por grupo preferido
    for strategy_id, config in STRATEGY_CATALOG.items():
        if config.get("group") in preferred_groups:
            validation = validate_strategy_for_slot(strategy_id, slot_config)
            if validation.get("valid", False):
                recommendations.append(strategy_id)
    
    # Se nenhuma recomendação específica, inclui estratégias universais
    if not recommendations:
        universal_strategies = ["momentum", "mean_reversion", "grid"]
        for strategy_id in universal_strategies:
            validation = validate_strategy_for_slot(strategy_id, slot_config)
            if validation.get("valid", False):
                recommendations.append(strategy_id)
    
    return recommendations[:5]  # Máximo 5 recomendações

# Cache para performance
_strategy_cache = {}

def get_strategy_cached(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Versão cached do get_strategy"""
    if strategy_id not in _strategy_cache:
        _strategy_cache[strategy_id] = get_strategy(strategy_id)
    return _strategy_cache[strategy_id]