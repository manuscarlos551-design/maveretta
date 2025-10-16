# -*- coding: utf-8 -*-
"""
Backtest Package - Etapa 3: Advanced Backtesting Engine
Sistema completo de backtesting com hyperoptimization
"""

from .engine.backtest_engine import BacktestEngine
from .data.data_manager import DataManager
from .optimization.hyperopt_manager import HyperoptManager
from .analysis.performance_analyzer import PerformanceAnalyzer

__all__ = [
    'BacktestEngine',
    'DataManager', 
    'HyperoptManager',
    'PerformanceAnalyzer'
]