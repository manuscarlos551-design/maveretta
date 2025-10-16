# core/risk/__init__.py
"""
Maveretta Risk Management System - Proteções Avançadas
Integração das proteções robustas do Freqtrade com sistema de slots do Maveretta
"""

from .stoploss_guard import MaverettaStoplossGuard
from .drawdown_guard import MaverettaDrawdownGuard
from .cooldown_manager import MaverettaCooldownManager
from .protection_manager import MaverettaProtectionManager, create_protection_manager

__all__ = [
    'MaverettaStoplossGuard',
    'MaverettaDrawdownGuard', 
    'MaverettaCooldownManager',
    'MaverettaProtectionManager',
    'create_protection_manager'
]