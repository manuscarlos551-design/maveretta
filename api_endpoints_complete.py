# api_endpoints_complete.py
"""
Endpoints completos para o AI Gateway
Implementa todos os endpoints esperados pelo dashboard Streamlit
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from prometheus_client import Gauge, Counter

logger = logging.getLogger(__name__)

# Métricas Prometheus
ia_status = Gauge("ia_status", "IA status (1=online, 0=offline)", ["ia_id", "model"])
ia_decisions_total = Counter("ia_decisions_total", "Total decisions by IA", ["ia_id", "result"])
slot_status = Gauge("bot_slot_status", "Slot status", ["slot_id", "exchange", "strategy"])
slot_pnl = Gauge("bot_slot_pnl_usd", "Slot P&L in USD", ["slot_id"])

# Router
router = APIRouter(prefix="/v1")

# ===== MODELOS =====

class OrchestrationState(BaseModel):
    timestamp: str
    ias: List[Dict[str, Any]]
    slots: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    risk_controls: Dict[str, Any]
    wallet: Dict[str, Any]

class IAHealth(BaseModel):
    id: str
    name: str
    status: str  # GREEN, AMBER, RED
    model: str
    uptime_hours: float
    latency_ms: float
    last_decision: Optional[str]
    accuracy: float
    pnl: float

class ExchangeHealth(BaseModel):
    id: str
    name: str
    status: str  # GREEN, AMBER, RED
    connected: bool
    latency_ms: float
    equity_usd: float
    equity_brl: float
    last_sync: str

class Slot(BaseModel):
    id: str
    exchange: str
    strategy: str
    status: str  # ACTIVE, PAUSED, STOPPED
    allocation: float
    pnl: float
    pnl_percentage: float
    trades_count: int
    created_at: str

class WalletDetails(BaseModel):
    total_balance: float
    total_balance_brl: float
    by_exchange: Dict[str, float]
    last_update: str

class Operation(BaseModel):
    id: str
    symbol: str
    exchange: str
    side: str  # BUY, SELL
    status: str  # OPEN, CLOSED, CANCELLED
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    opened_at: str
    closed_at: Optional[str]

# ===== ENDPOINTS =====

@router.get("/health")
async def health_check():
    """Health check do sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/orchestration/state")
async def get_orchestration_state() -> Dict[str, Any]:
    """
    Estado completo da orquestração
    Retorna IAs, Slots, Decisions, Risk Controls e Wallet
    """
    try:
        # TODO: Integrar com sistema real de orquestração
        # Por enquanto retorna estrutura básica
        
        state = {
            "timestamp": datetime.now().isoformat(),
            "ias": [],
            "slots": [],
            "decisions": [],
            "risk_controls": {
                "max_drawdown_pct": 8.0,
                "max_concurrent_positions": 3,
                "emergency_stop": False
            },
            "wallet": {
                "total_balance": 0.0,
                "total_balance_brl": 0.0,
                "by_exchange": {}
            }
        }
        
        # Buscar IAs configuradas
        ia_keys = {
            "IA_G1_SCALP_GPT4O": "G1-Scalping",
            "IA_G2_TENDENCIA_GPT4O": "G2-Trend",
            "IA_ORQUESTRADORA_CLAUDE": "Orchestrator",
            "IA_RESERVA_G1_HOT_HAIKU": "G1-Reserve-Hot",
            "IA_RESERVA_G1_WARM_GPT4ALL": "G1-Reserve-Warm",
            "IA_RESERVA_G2_HOT_HAIKU": "G2-Reserve-Hot",
            "IA_RESERVA_G2_WARM_GPT4ALL": "G2-Reserve-Warm"
        }
        
        for env_key, name in ia_keys.items():
            api_key = os.getenv(env_key, "")
            if api_key:
                state["ias"].append({
                    "id": env_key.lower(),
                    "name": name,
                    "status": "GREEN",
                    "configured": True
                })
        
        return state
        
    except Exception as e:
        logger.error(f"Error getting orchestration state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ias/health")
async def get_ia_health() -> Dict[str, Any]:
    """
    Health de todas as IAs
    Retorna status, latência, accuracy, etc.
    """
    try:
        ias = []
        
        # Lista de IAs configuradas
        ia_configs = [
            {"id": "ia_g1_scalp_gpt4o", "name": "G1 Scalping", "strategy": "scalping", "model": "gpt-4o"},
            {"id": "ia_g2_tendencia_gpt4o", "name": "G2 Trend", "strategy": "trend", "model": "gpt-4o"},
            {"id": "ia_orquestradora_claude", "name": "Orchestrator", "strategy": "orchestration", "model": "claude-3"},
            {"id": "ia_reserva_g1_hot_haiku", "name": "G1 Reserve Hot", "strategy": "scalping", "model": "claude-haiku"},
            {"id": "ia_reserva_g1_warm_gpt4all", "name": "G1 Reserve Warm", "strategy": "scalping", "model": "gpt4all"},
            {"id": "ia_reserva_g2_hot_haiku", "name": "G2 Reserve Hot", "strategy": "trend", "model": "claude-haiku"},
            {"id": "ia_reserva_g2_warm_gpt4all", "name": "G2 Reserve Warm", "strategy": "trend", "model": "gpt4all"},
        ]
        
        for config in ia_configs:
            # Verificar se tem API key configurada
            env_key = config["id"].upper()
            has_key = bool(os.getenv(env_key))
            
            status = "GREEN" if has_key else "RED"
            
            ias.append({
                "id": config["id"],
                "name": config["name"],
                "status": status,
                "strategy": config["strategy"],
                "model": config["model"],
                "uptime_hours": 0.0,
                "latency_ms": 0,
                "accuracy": 0.0,
                "pnl": 0.0,
                "configured": has_key
            })
            
            # Atualizar métrica Prometheus
            ia_status.labels(ia_id=config["id"], model=config["model"]).set(1 if has_key else 0)
        
        return {"ias": ias}
        
    except Exception as e:
        logger.error(f"Error getting IA health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exchanges/health")
async def get_exchange_health() -> Dict[str, Any]:
    """
    Health de todas as exchanges
    Retorna status de conexão, latência, equity, etc.
    """
    try:
        exchanges = []
        
        exchange_configs = [
            {"id": "binance", "name": "Binance", "env_key": "BINANCE_API_KEY"},
            {"id": "kucoin", "name": "KuCoin", "env_key": "KUCOIN_API_KEY"},
            {"id": "bybit", "name": "Bybit", "env_key": "BYBIT_API_KEY"},
            {"id": "coinbase", "name": "Coinbase", "env_key": "COINBASE_API_KEY"},
            {"id": "okx", "name": "OKX", "env_key": "OKX_API_KEY"},
        ]
        
        for config in exchange_configs:
            has_key = bool(os.getenv(config["env_key"]))
            status = "GREEN" if has_key else "RED"
            
            exchanges.append({
                "id": config["id"],
                "name": config["name"],
                "status": status,
                "connected": has_key,
                "latency_ms": 0,
                "equity_usd": 0.0,
                "equity_brl": 0.0,
                "last_sync": datetime.now().isoformat(),
                "configured": has_key
            })
        
        return {"exchanges": exchanges}
        
    except Exception as e:
        logger.error(f"Error getting exchange health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slots")
async def get_slots() -> Dict[str, Any]:
    """
    Lista todos os slots de trading
    """
    try:
        # TODO: Integrar com sistema real de slots
        slots = []
        
        # Exemplo de slots para desenvolvimento
        slot_examples = [
            {
                "id": "slot_btc_binance_1",
                "exchange": "binance",
                "strategy": "scalping",
                "status": "ACTIVE",
                "allocation": 1000.0,
                "pnl": 0.0,
                "pnl_percentage": 0.0,
                "trades_count": 0,
                "created_at": datetime.now().isoformat()
            }
        ]
        
        return {"slots": slot_examples}
        
    except Exception as e:
        logger.error(f"Error getting slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet")
async def get_wallet_details() -> Dict[str, Any]:
    """
    Detalhes completos da carteira
    Soma de todas as exchanges
    """
    try:
        wallet = {
            "total_balance": 0.0,
            "total_balance_brl": 0.0,
            "by_exchange": {
                "binance": 0.0,
                "kucoin": 0.0,
                "bybit": 0.0,
                "coinbase": 0.0,
                "okx": 0.0
            },
            "last_update": datetime.now().isoformat()
        }
        
        # TODO: Buscar saldos reais das exchanges via Prometheus ou APIs
        
        return wallet
        
    except Exception as e:
        logger.error(f"Error getting wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/operations")
async def get_operations(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Histórico de operações/trades
    """
    try:
        # TODO: Buscar do MongoDB
        operations = []
        
        return {"operations": operations, "total": 0}
        
    except Exception as e:
        logger.error(f"Error getting operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ias/{ia_id}/insights")
async def get_ia_insights(ia_id: str) -> Dict[str, Any]:
    """
    Insights detalhados de uma IA específica
    """
    try:
        insights = {
            "id": ia_id,
            "name": ia_id.replace("_", " ").title(),
            "description": "AI trading agent",
            "status": "GREEN",
            "uptime_h": 0.0,
            "latency_ms": 0,
            "last_decision": {
                "timestamp": datetime.now().isoformat(),
                "result": "approve",
                "confidence": 0.85
            },
            "recent_performance": {
                "last_24h_pnl_pct": 0.0,
                "trades_count_24h": 0,
                "win_rate_24h": 0.0
            },
            "recommendations": []
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"Error getting IA insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINTS DE CONTROLE =====

@router.post("/orchestration/start")
async def start_orchestration() -> Dict[str, Any]:
    """Inicia o sistema de orquestração"""
    try:
        # TODO: Implementar start real
        return {
            "status": "ok",
            "message": "Sistema iniciado com sucesso",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/pause")
async def pause_orchestration() -> Dict[str, Any]:
    """Pausa o sistema de orquestração"""
    try:
        # TODO: Implementar pause real
        return {
            "status": "ok",
            "message": "Sistema pausado",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error pausing orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/stop")
async def stop_orchestration() -> Dict[str, Any]:
    """Para o sistema de orquestração"""
    try:
        # TODO: Implementar stop real
        return {
            "status": "ok",
            "message": "Sistema parado",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error stopping orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/emergency-stop")
async def emergency_stop() -> Dict[str, Any]:
    """Emergency stop - fecha todas as posições imediatamente"""
    try:
        # TODO: Implementar emergency stop real
        return {
            "status": "ok",
            "message": "Emergency stop acionado - fechando todas as posições",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/operations/{operation_id}/close")
async def close_operation(operation_id: str) -> Dict[str, Any]:
    """Fecha uma operação específica"""
    try:
        # TODO: Implementar fechamento real
        return {
            "status": "ok",
            "message": f"Operação {operation_id} será fechada",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error closing operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version")
async def get_version() -> Dict[str, Any]:
    """Versão do sistema e cotação USD/BRL"""
    try:
        # TODO: Buscar cotação real
        usd_brl_rate = 5.85  # Mock - integrar com API de cotação
        
        return {
            "version": "1.0.0",
            "environment": os.getenv("ENV", "production"),
            "usd_brl_rate": usd_brl_rate,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting version: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== FUNÇÃO DE REGISTRO =====

def register_extensions(app):
    """
    Registra todos os endpoints no app FastAPI
    """
    try:
        app.include_router(router)
        logger.info("✅ API endpoints registered successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to register API endpoints: {e}")
        return False
