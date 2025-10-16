# interfaces/web/api_client_extensions.py
"""
Extensões do API Client para novos endpoints de estratégias e monitoramento
Adiciona novos métodos sem modificar o cliente principal
"""

import os
import logging
from typing import Dict, Any, Optional, List
from api_client import _client, _u

logger = logging.getLogger(__name__)

class APIClientExtensions:
    """Extensões do cliente API para novos endpoints"""
    
    def __init__(self, base_client):
        self.client = base_client
    
    # ===== MÉTODOS DE ESTRATÉGIAS =====
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """Lista catálogo completo de estratégias - nunca lança exception"""
        try:
            result = self.client._request("GET", _u("/strategies"))
            if isinstance(result, dict) and "strategies" in result:
                return result["strategies"]
            elif isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_strategy_details(self, strategy_id: str) -> Dict[str, Any]:
        """Obtém detalhes de uma estratégia específica - nunca lança exception"""
        try:
            result = self.client._request("GET", _u(f"/strategies/{strategy_id}"))
            return result if result else {}
        except Exception:
            return {}
    
    def set_slot_strategy(self, slot_id: str, mode: str, strategy_id: Optional[str] = None, reason: str = "API request") -> Dict[str, Any]:
        """Define estratégia para slot (auto/manual) - nunca lança exception"""
        try:
            payload = {
                "mode": mode,
                "reason": reason
            }
            
            if mode == "manual" and strategy_id:
                payload["strategy_id"] = strategy_id
            
            result = self.client._request("POST", _u(f"/slots/{slot_id}/strategy"), json=payload)
            return result if result else {"success": False, "error": "Falha na comunicação"}
        except Exception:
            return {"success": False, "error": "Falha na comunicação"}
    
    # ===== MÉTODOS DE MONITORAMENTO DAS IAs =====
    
    def get_ias_health_extended(self) -> Dict[str, Any]:
        """Health das IAs com métricas estendidas - nunca lança exception"""
        try:
            result = self.client._request("GET", _u("/ias/health"))
            return result if result else {"ias": [], "summary": {}}
        except Exception:
            return {"ias": [], "summary": {}}
    
    def get_decisions(self, slot_id: Optional[str] = None, ia_id: Optional[str] = None, since: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
        """Feed de decisões das IAs - nunca lança exception"""
        try:
            params = {"limit": limit}
            
            if slot_id:
                params["slot_id"] = slot_id
            if ia_id:
                params["ia_id"] = ia_id
            if since:
                params["since"] = since
            
            result = self.client._request("GET", _u("/decisions"), params=params)
            return result if result else {"decisions": [], "pagination": {}}
        except Exception:
            return {"decisions": [], "pagination": {}}
    
    # ===== MÉTODOS DE ORQUESTRAÇÃO =====
    
    def get_orchestration_state_extended(self) -> Dict[str, Any]:
        """Estado completo da orquestração - nunca lança exception"""
        try:
            result = self.client._request("GET", _u("/orchestration/state"))
            if not result:
                # Retorna contrato fixo vazio
                return {
                    "leader_id": None,
                    "ias": [],
                    "slots": [],
                    "wallet": {},
                    "risk_controls": {},
                    "recent_events": [],
                    "system_stats": {}
                }
            return result
        except Exception:
            return {
                "leader_id": None,
                "ias": [],
                "slots": [],
                "wallet": {},
                "risk_controls": {},
                "recent_events": [],
                "system_stats": {}
            }
    
    # ===== MÉTODOS DE FAILOVER =====
    
    def get_failover_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema de failover - nunca lança exception"""
        try:
            result = self.client._request("GET", _u("/failover/stats"))
            return result if result else {"enabled": False, "stats": {}}
        except Exception:
            return {"enabled": False, "stats": {}}
    
    def test_failover(self, slot_id: str) -> Dict[str, Any]:
        """Teste de failover para slot - nunca lança exception"""
        try:
            result = self.client._request("POST", _u("/failover/test"), params={"slot_id": slot_id})
            return result if result else {"success": False, "error": "Falha no teste"}
        except Exception:
            return {"success": False, "error": "Falha na comunicação"}

# Instância global das extensões
_extensions = APIClientExtensions(_client)

# ===== FUNÇÕES DE INTERFACE (backward compatibility) =====

def list_strategies() -> List[Dict[str, Any]]:
    """Lista catálogo completo de estratégias"""
    return _extensions.list_strategies()

def get_strategy_details(strategy_id: str) -> Dict[str, Any]:
    """Obtém detalhes de uma estratégia específica"""
    return _extensions.get_strategy_details(strategy_id)

def set_slot_strategy(slot_id: str, mode: str, strategy_id: Optional[str] = None, reason: str = "API request") -> Dict[str, Any]:
    """Define estratégia para slot (auto/manual)"""
    return _extensions.set_slot_strategy(slot_id, mode, strategy_id, reason)

def get_ias_health_extended() -> Dict[str, Any]:
    """Health das IAs com métricas estendidas"""
    return _extensions.get_ias_health_extended()

def get_decisions(slot_id: Optional[str] = None, ia_id: Optional[str] = None, since: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
    """Feed de decisões das IAs"""
    return _extensions.get_decisions(slot_id, ia_id, since, limit)

def get_orchestration_state_extended() -> Dict[str, Any]:
    """Estado completo da orquestração"""
    return _extensions.get_orchestration_state_extended()

def get_failover_stats() -> Dict[str, Any]:
    """Estatísticas do sistema de failover"""
    return _extensions.get_failover_stats()

def test_failover(slot_id: str) -> Dict[str, Any]:
    """Teste de failover para slot"""
    return _extensions.test_failover(slot_id)

# ===== INICIALIZAÇÃO =====

def init_api_extensions():
    """Inicializa extensões do API client"""
    logger.info("🚀 Extensões do API Client inicializadas")

# Inicialização automática
init_api_extensions()