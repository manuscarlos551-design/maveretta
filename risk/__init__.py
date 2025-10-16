"""
Risk Management Module
Mantém compatibilidade com sistema existente
"""

from .managers.risk_manager import RiskManager
from .protections.protection_manager import ProtectionManager

__all__ = ['RiskManager', 'ProtectionManager']