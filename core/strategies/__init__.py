"""
Strategy Management Module - Todas as Estratégias Disponíveis
"""
from .strategy_manager import StrategyManager
from .base_strategy import BaseStrategy

# Estratégias Existentes
from .example_strategy import ExampleStrategy
from .dca_strategy import DCAStrategy
from .grid_trading_strategy import GridTradingStrategy
from .market_making_strategy import MarketMakingStrategy
from .multi_timeframe_strategy import MultiTimeframeStrategy

# Novas Estratégias Implementadas
from .day_trading_strategy import DayTradingStrategy
from .swing_trading_strategy import SwingTradingStrategy
from .trend_following_strategy import TrendFollowingStrategy
from .scalping_strategy import ScalpingStrategy
from .arbitrage_strategy import ArbitrageStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .breakout_strategy import BreakoutStrategy
from .fading_strategy import FadingStrategy
from .pair_trading_strategy import PairTradingStrategy
from .hft_strategy import HFTStrategy
from .convergence_strategy import ConvergenceStrategy
from .index_basket_strategy import IndexBasketStrategy
from .ml_rl_strategy import MLRLStrategy

# Registry de todas as estratégias disponíveis
STRATEGY_REGISTRY = {
    # Estratégias Existentes
    'example': ExampleStrategy,
    'dca': DCAStrategy,
    'grid': GridTradingStrategy,
    'market_making': MarketMakingStrategy,
    'multi_timeframe': MultiTimeframeStrategy,
    
    # Novas Estratégias
    'day_trading': DayTradingStrategy,
    'swing_trading': SwingTradingStrategy,
    'trend_following': TrendFollowingStrategy,
    'scalping': ScalpingStrategy,
    'arbitrage': ArbitrageStrategy,
    'mean_reversion': MeanReversionStrategy,
    'breakout': BreakoutStrategy,
    'fading': FadingStrategy,
    'pair_trading': PairTradingStrategy,
    'hft': HFTStrategy,
    'convergence': ConvergenceStrategy,
    'index_basket': IndexBasketStrategy,
    'ml_rl': MLRLStrategy,
}

def get_strategy(strategy_name: str, config: dict = None):
    """Factory function para criar instância de estratégia"""
    strategy_class = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy_class:
        raise ValueError(f"Estratégia '{strategy_name}' não encontrada. Disponíveis: {list(STRATEGY_REGISTRY.keys())}")
    return strategy_class(config=config)

def list_strategies():
    """Lista todas as estratégias disponíveis"""
    return list(STRATEGY_REGISTRY.keys())

__all__ = [
    'StrategyManager',
    'BaseStrategy',
    'STRATEGY_REGISTRY',
    'get_strategy',
    'list_strategies',
    # Estratégias individuais
    'ExampleStrategy',
    'DCAStrategy',
    'GridTradingStrategy',
    'MarketMakingStrategy',
    'MultiTimeframeStrategy',
    'DayTradingStrategy',
    'SwingTradingStrategy',
    'TrendFollowingStrategy',
    'ScalpingStrategy',
    'ArbitrageStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'FadingStrategy',
    'PairTradingStrategy',
    'HFTStrategy',
    'ConvergenceStrategy',
    'IndexBasketStrategy',
    'MLRLStrategy',
]
