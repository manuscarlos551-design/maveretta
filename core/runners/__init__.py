# core/runners/__init__.py
"""
Maveretta Runners Engine
Engines de execução robustos integrados com sistema de slots do Maveretta
Inclui backtesting, hyperopt, e relatórios baseados no Freqtrade
"""

from .backtest_runner import MaverettaBacktestRunner, run_slot_backtest
from .hyperopt_runner import MaverettaHyperoptRunner, optimize_slot_strategy
from .backtest_cache import MaverettaBacktestCache

__all__ = [
    'MaverettaBacktestRunner',
    'run_slot_backtest', 
    'MaverettaHyperoptRunner',
    'optimize_slot_strategy',
    'MaverettaBacktestCache'
]