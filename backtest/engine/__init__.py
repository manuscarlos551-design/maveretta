# -*- coding: utf-8 -*-
"""
Backtest Engine Package
Core do sistema de backtesting
"""

from .backtest_engine import BacktestEngine
from .strategy_runner import StrategyRunner

__all__ = ['BacktestEngine', 'StrategyRunner']