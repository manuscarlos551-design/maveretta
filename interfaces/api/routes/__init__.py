# interfaces/api/routes/__init__.py
"""
Maveretta API Routes
Rotas da API para integração dos engines do Freqtrade
"""

from .backtest import router as backtest_router
from .hyperopt import router as hyperopt_router
from .risk import router as risk_router
from .logs import router as logs_router
from .rates import router as rates_router
from .strategies import router as strategies_router
from .cascade import router as cascade_router

__all__ = [
    'backtest_router', 
    'hyperopt_router', 
    'risk_router',
    'logs_router',
    'rates_router',
    'strategies_router',
    'cascade_router'
]