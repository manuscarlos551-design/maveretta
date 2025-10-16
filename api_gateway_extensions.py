# api_gateway_extensions.py
"""
Extensões do AI Gateway para suporte completo ao sistema de estratégias e monitoramento
Adiciona novos endpoints sem modificar o gateway principal
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Query, Path
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge

# Imports dos novos módulos
from core.strategies.registry import list_strategies, get_strategy, validate_strategy_for_slot
from core.orchestration.policy import choose_strategy_auto
from core.orchestration.failover import process_automatic_failovers, get_failover_statistics

# Logger
logger = logging.getLogger(__name__)

# Métricas Prometheus para telemetria das IAs
ia_heartbeat = Gauge(
    "maveretta_ia_heartbeat",
    "IA heartbeat status (1=online, 0=offline)",
    ["ia_id", "group"]
)

ia_latency_ms = Gauge(
    "maveretta_ia_latency_ms", 
    "IA response latency in milliseconds",
    ["ia_id", "group"]
)

decisions_total = Counter(
    "maveretta_decisions_total",
    "Total number of IA decisions",
    ["ia_id", "result", "slot_id"]
)

decision_time_ms = Histogram(
    "maveretta_decision_time_ms",
    "IA decision processing time",
    ["ia_id", "slot_id"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000]
)

ia_confidence_avg = Gauge(
    "maveretta_ia_confidence_avg",
    "Average IA confidence score",
    ["ia_id", "slot_id"]
)

slot_pnl_pct = Gauge(
    "maveretta_slot_pnl_pct",
    "Slot P&L percentage",
    ["slot_id", "exchange", "strategy"]
)

failover_total = Counter(
    "maveretta_failover_total",
    "Total number of failovers",
    ["group", "trigger_reason"]
)

cascade_total = Counter(
    "maveretta_cascade_total",
    "Total number of cascade transfers",
    ["from_slot", "to_slot"]
)

# Modelos Pydantic para requests
class StrategyChangeRequest(BaseModel):
    mode: str  # "auto" ou "manual"
    strategy_id: Optional[str] = None
    reason: Optional[str] = "API request"

class DecisionEntry(BaseModel):
    timestamp: float
    ia_id: str
    slot_id: str
    result: str  # "approve", "reject", "defer"
    confidence: float
    latency_ms: float
    reason: str
    strategy_used: Optional[str] = None

# Router para novos endpoints
router = APIRouter(prefix="/v1")

# ===== ENDPOINTS DE ESTRATÉGIAS =====

@router.get("/strategies")
async def get_strategies_catalog():
    """Retorna catálogo completo de estratégias disponíveis"""
    try:
        strategies = list_strategies()
        
        return {
            "strategies": strategies,
            "total_count": len(strategies),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao listar estratégias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}")
async def get_strategy_details(strategy_id: str = Path(...)):
    """Retorna detalhes de uma estratégia específica"""
    try:
        strategy = get_strategy(strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Estratégia '{strategy_id}' não encontrada")
        
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter estratégia {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slots/{slot_id}/strategy")
async def set_slot_strategy(
    slot_id: str = Path(...),
    request: StrategyChangeRequest = None
):
    """Define estratégia para um slot (auto ou manual)"""
    try:
        if not request:
            raise HTTPException(status_code=400, detail="Request body obrigatório")
        
        # Validação básica
        if request.mode not in ["auto", "manual"]:
            raise HTTPException(status_code=400, detail="Modo deve ser 'auto' ou 'manual'")
        
        if request.mode == "manual" and not request.strategy_id:
            raise HTTPException(status_code=400, detail="strategy_id obrigatório para modo manual")
        
        # Simula configuração do slot (em implementação real viria do banco)
        slot_config = {
            "id": slot_id,
            "capital": 1000,  # Default
            "market_type": "spot"
        }
        
        # Para modo manual, valida estratégia
        if request.mode == "manual":
            strategy = get_strategy(request.strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail=f"Estratégia '{request.strategy_id}' não encontrada")
            
            # Valida compatibilidade
            validation = validate_strategy_for_slot(request.strategy_id, slot_config)
            if not validation.get("valid", False):
                raise HTTPException(status_code=400, detail=validation.get("reason"))
            
            selected_strategy = request.strategy_id
            selection_reason = request.reason or "Manual selection"
            
        else:
            # Modo automático - usa política de seleção
            
            # Mock de dados para política (em implementação real viria de fontes reais)
            market_snapshot = {
                "volatility": 0.03,
                "trend_score": 0.5,
                "price_change_24h": 0.02,
                "volume_ratio": 1.2
            }
            
            ia_health = [
                {"id": "ia_g1_1", "status": "GREEN", "latency_ms": 150, "accuracy": 75},
                {"id": "ia_g2_1", "status": "GREEN", "latency_ms": 200, "accuracy": 80}
            ]
            
            # Chama política de seleção
            policy_result = choose_strategy_auto(slot_config, market_snapshot, ia_health)
            selected_strategy = policy_result["strategy"]
            selection_reason = policy_result["reason"]
        
        # Registra mudança (simulado - em implementação real atualizaria banco)
        change_event = {
            "event_type": "STRATEGY_CHANGED",
            "slot_id": slot_id,
            "old_strategy": "unknown",  # Em implementação real viria do estado atual
            "new_strategy": selected_strategy,
            "mode": request.mode,
            "reason": selection_reason,
            "forced_by": "api_user",  # Em implementação real viria da autenticação
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Estratégia alterada para slot {slot_id}: {selected_strategy} (modo: {request.mode})")
        
        return {
            "success": True,
            "slot_id": slot_id,
            "strategy": selected_strategy,
            "mode": request.mode,
            "reason": selection_reason,
            "event": change_event,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao definir estratégia para slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINTS DE MONITORAMENTO DAS IAs =====

@router.get("/ias/health")
async def get_ias_health_extended():
    """Health das IAs com métricas estendidas para monitoramento"""
    try:
        # Em implementação real, estes dados viriam do sistema de IAs
        # Aqui simulamos dados realistas baseados na estrutura do sistema
        
        current_time = time.time()
        
        ias_health = [
            {
                "id": "ia_g1_scalp_gpt4o",
                "name": "G1 Scalp",
                "group": "G1",
                "status": "GREEN",
                "last_heartbeat": current_time - 15,  # 15s atrás
                "latency_ms": 150,
                "decisions_last_1h": 45,
                "avg_confidence": 78.5,
                "uptime_pct": 99.2,
                "accuracy": 76.3,
                "assigned_slots": ["slot_1", "slot_3"],
                "current_strategy": "scalp"
            },
            {
                "id": "ia_g2_tendencia_gpt4o", 
                "name": "G2 Tendência",
                "group": "G2",
                "status": "GREEN",
                "last_heartbeat": current_time - 8,  # 8s atrás
                "latency_ms": 220,
                "decisions_last_1h": 28,
                "avg_confidence": 82.1,
                "uptime_pct": 98.7,
                "accuracy": 79.8,
                "assigned_slots": ["slot_2", "slot_4"],
                "current_strategy": "trend_following"
            },
            {
                "id": "ia_orquestradora_claude",
                "name": "Orquestradora",
                "group": "LEADER",
                "status": "GREEN", 
                "last_heartbeat": current_time - 5,  # 5s atrás
                "latency_ms": 95,
                "decisions_last_1h": 12,
                "avg_confidence": 85.7,
                "uptime_pct": 99.8,
                "accuracy": 88.2,
                "assigned_slots": [],
                "current_strategy": "orchestration"
            },
            {
                "id": "ia_reserva_g1_haiku",
                "name": "Reserva G1",
                "group": "G1",
                "status": "AMBER",
                "last_heartbeat": current_time - 45,  # 45s atrás (high)
                "latency_ms": 890,
                "decisions_last_1h": 8,
                "avg_confidence": 65.2,
                "uptime_pct": 94.1,
                "accuracy": 68.5,
                "assigned_slots": [],
                "current_strategy": "standby"
            }
        ]
        
        # Atualiza métricas Prometheus
        for ia in ias_health:
            ia_id = ia["id"]
            group = ia["group"]
            
            # Heartbeat status
            heartbeat_status = 1 if ia["status"] == "GREEN" else 0
            ia_heartbeat.labels(ia_id=ia_id, group=group).set(heartbeat_status)
            
            # Latency
            ia_latency_ms.labels(ia_id=ia_id, group=group).set(ia["latency_ms"])
            
            # Confidence
            if ia["assigned_slots"]:
                for slot_id in ia["assigned_slots"]:
                    ia_confidence_avg.labels(ia_id=ia_id, slot_id=slot_id).set(ia["avg_confidence"])
        
        return {
            "ias": ias_health,
            "summary": {
                "total": len(ias_health),
                "green": len([ia for ia in ias_health if ia["status"] == "GREEN"]),
                "amber": len([ia for ia in ias_health if ia["status"] == "AMBER"]),
                "red": len([ia for ia in ias_health if ia["status"] == "RED"]),
                "avg_latency_ms": sum(ia["latency_ms"] for ia in ias_health) / len(ias_health),
                "total_decisions_1h": sum(ia["decisions_last_1h"] for ia in ias_health)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter health das IAs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/decisions")
async def get_decisions_feed(
    slot_id: Optional[str] = Query(None, description="Filtrar por slot"),
    ia_id: Optional[str] = Query(None, description="Filtrar por IA"),
    since: Optional[int] = Query(None, description="Timestamp desde quando buscar"),
    limit: int = Query(50, ge=1, le=500, description="Limite de resultados")
):
    """Feed de decisões das IAs com filtros"""
    try:
        current_time = time.time()
        
        # Simula decisões recentes (em implementação real viria do banco de dados)
        mock_decisions = []
        
        # Gera decisões dos últimos 60 minutos
        for i in range(100):
            decision_time = current_time - (i * 36)  # Uma decisão a cada 36 segundos
            
            decision = {
                "id": f"decision_{int(decision_time)}_{i}",
                "timestamp": decision_time,
                "datetime": datetime.fromtimestamp(decision_time).isoformat(),
                "ia_id": ["ia_g1_scalp_gpt4o", "ia_g2_tendencia_gpt4o", "ia_orquestradora_claude"][i % 3],
                "slot_id": [f"slot_{j}" for j in range(1, 5)][i % 4],
                "result": ["approve", "reject", "defer"][i % 3],
                "confidence": round(60 + (i % 40), 1),
                "latency_ms": 100 + (i % 400),
                "reason": [
                    "Market conditions favorable",
                    "High volatility detected", 
                    "Trend confirmation needed",
                    "Risk limits approached",
                    "Strategy alignment positive"
                ][i % 5],
                "strategy_used": ["scalp", "momentum", "trend_following"][i % 3],
                "market_data": {
                    "price": 50000 + (i % 1000),
                    "volume": 1000000 + (i % 500000)
                }
            }
            
            mock_decisions.append(decision)
        
        # Aplica filtros
        filtered_decisions = mock_decisions
        
        if slot_id:
            filtered_decisions = [d for d in filtered_decisions if d["slot_id"] == slot_id]
        
        if ia_id:
            filtered_decisions = [d for d in filtered_decisions if d["ia_id"] == ia_id]
        
        if since:
            filtered_decisions = [d for d in filtered_decisions if d["timestamp"] >= since]
        
        # Ordena por timestamp decrescente e aplica limite
        filtered_decisions.sort(key=lambda x: x["timestamp"], reverse=True)
        filtered_decisions = filtered_decisions[:limit]
        
        # Atualiza métricas Prometheus para as decisões
        for decision in filtered_decisions[:10]:  # Apenas as 10 mais recentes para evitar spam
            decisions_total.labels(
                ia_id=decision["ia_id"],
                result=decision["result"],
                slot_id=decision["slot_id"]
            ).inc()
            
            decision_time_ms.labels(
                ia_id=decision["ia_id"],
                slot_id=decision["slot_id"]
            ).observe(decision["latency_ms"])
        
        return {
            "decisions": filtered_decisions,
            "pagination": {
                "total_found": len(filtered_decisions),
                "limit": limit,
                "has_more": len([d for d in mock_decisions if (not since or d["timestamp"] >= since)]) > limit
            },
            "filters": {
                "slot_id": slot_id,
                "ia_id": ia_id,
                "since": since
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter feed de decisões: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINTS DE ORQUESTRAÇÃO =====

@router.get("/orchestration/state")
async def get_orchestration_state_extended():
    """Estado completo da orquestração com dados realistas"""
    try:
        current_time = time.time()
        
        # Simula estado completo do sistema
        orchestration_state = {
            "leader_id": "ia_orquestradora_claude",
            "active_slots": 4,
            "total_slots": 6,
            
            "ias": [
                {
                    "id": "ia_g1_scalp_gpt4o",
                    "name": "G1 Scalp",
                    "group": "G1", 
                    "status": "GREEN",
                    "assigned_slots": ["slot_1", "slot_3"],
                    "last_decision": current_time - 30
                },
                {
                    "id": "ia_g2_tendencia_gpt4o",
                    "name": "G2 Tendência", 
                    "group": "G2",
                    "status": "GREEN",
                    "assigned_slots": ["slot_2", "slot_4"],
                    "last_decision": current_time - 45
                },
                {
                    "id": "ia_orquestradora_claude",
                    "name": "Líder Orquestradora",
                    "group": "LEADER",
                    "status": "GREEN",
                    "assigned_slots": [],
                    "last_decision": current_time - 15
                }
            ],
            
            "slots": [
                {
                    "id": "slot_1",
                    "exchange": "binance",
                    "symbol": "BTC/USDT",
                    "status": "ACTIVE",
                    "strategy": "scalp",
                    "strategy_mode": "auto",
                    "strategy_since_ts": current_time - 1800,
                    "assigned_ia": "ia_g1_scalp_gpt4o",
                    "capital_base": 1000,
                    "capital_current": 1085.50,
                    "pnl": 85.50,
                    "pnl_percentage": 8.55,
                    "cascade_target": 10.0,
                    "next_slot": "slot_2",
                    "last_trade": {
                        "symbol": "BTC/USDT",
                        "side": "BUY",
                        "price": 50150,
                        "timestamp": current_time - 300
                    }
                },
                {
                    "id": "slot_2", 
                    "exchange": "binance",
                    "symbol": "ETH/USDT",
                    "status": "ACTIVE",
                    "strategy": "trend_following",
                    "strategy_mode": "manual",
                    "strategy_since_ts": current_time - 3600,
                    "assigned_ia": "ia_g2_tendencia_gpt4o",
                    "capital_base": 1000,
                    "capital_current": 1045.20,
                    "pnl": 45.20,
                    "pnl_percentage": 4.52,
                    "cascade_target": 10.0,
                    "next_slot": "slot_3",
                    "last_trade": {
                        "symbol": "ETH/USDT",
                        "side": "SELL", 
                        "price": 3280,
                        "timestamp": current_time - 600
                    }
                },
                {
                    "id": "slot_3",
                    "exchange": "kucoin",
                    "symbol": "ADA/USDT", 
                    "status": "PAUSED",
                    "strategy": "momentum",
                    "strategy_mode": "auto",
                    "strategy_since_ts": current_time - 2400,
                    "assigned_ia": "ia_g1_scalp_gpt4o",
                    "capital_base": 500,
                    "capital_current": 485.30,
                    "pnl": -14.70,
                    "pnl_percentage": -2.94,
                    "cascade_target": 10.0,
                    "next_slot": "slot_4",
                    "last_trade": None
                },
                {
                    "id": "slot_4",
                    "exchange": "bybit",
                    "symbol": "SOL/USDT",
                    "status": "STOPPED", 
                    "strategy": "grid",
                    "strategy_mode": "manual",
                    "strategy_since_ts": current_time - 7200,
                    "assigned_ia": None,
                    "capital_base": 750,
                    "capital_current": 750,
                    "pnl": 0,
                    "pnl_percentage": 0,
                    "cascade_target": 10.0,
                    "next_slot": None,
                    "last_trade": None
                }
            ],
            
            "wallet": {
                "total_balance": 3366.00,
                "total_pnl": 116.00,
                "total_pnl_pct": 3.57,
                "per_exchange": [
                    {"exchange": "binance", "balance": 2130.70},
                    {"exchange": "kucoin", "balance": 485.30},
                    {"exchange": "bybit", "balance": 750.00}
                ]
            },
            
            "risk_controls": {
                "max_drawdown_limit": 8.0,
                "current_drawdown": 0.87,
                "daily_loss_limit": 5.0,
                "current_daily_loss": 0.44,
                "total_exposure": 2870.50,
                "max_exposure": 4000.00
            },
            
            "recent_events": [
                {
                    "type": "STRATEGY_CHANGED",
                    "slot_id": "slot_1",
                    "details": "Auto selection: scalp → momentum",
                    "timestamp": current_time - 900
                },
                {
                    "type": "TRADE_EXECUTED", 
                    "slot_id": "slot_2",
                    "details": "ETH/USDT SELL @ 3280",
                    "timestamp": current_time - 600
                }
            ],
            
            "system_stats": {
                "uptime_hours": 24.5,
                "total_trades_today": 67,
                "avg_decision_latency_ms": 185,
                "failover_events_24h": 0
            },
            
            "timestamp": datetime.now().isoformat()
        }
        
        # Atualiza métricas Prometheus de slots
        for slot in orchestration_state["slots"]:
            slot_pnl_pct.labels(
                slot_id=slot["id"],
                exchange=slot["exchange"],
                strategy=slot["strategy"]
            ).set(slot["pnl_percentage"])
        
        return orchestration_state
        
    except Exception as e:
        logger.error(f"Erro ao obter estado da orquestração: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINTS DE FAILOVER =====

@router.get("/failover/stats")
async def get_failover_statistics_endpoint():
    """Estatísticas do sistema de failover"""
    try:
        stats = get_failover_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/failover/test")
async def test_failover(slot_id: str = Query(..., description="ID do slot para testar failover")):
    """Testa failover manual para um slot (desenvolvimento/debug)"""
    try:
        # Simula teste de failover
        current_time = time.time()
        
        test_result = {
            "test_id": f"failover_test_{int(current_time)}",
            "slot_id": slot_id,
            "simulated_failure": {
                "failed_ia": "ia_g1_scalp_gpt4o",
                "trigger": "manual_test",
                "detected_at": current_time
            },
            "failover_executed": {
                "substitute_ia": "ia_reserva_g1_haiku",
                "handoff_completed": True,
                "context_preserved": True,
                "duration_ms": 45.2
            },
            "success": True,
            "message": "Failover test completed successfully",
            "timestamp": datetime.now().isoformat()
        }
        
        # Atualiza métrica
        failover_total.labels(group="G1", trigger_reason="manual_test").inc()
        
        logger.info(f"Teste de failover executado para slot {slot_id}")
        
        return test_result
        
    except Exception as e:
        logger.error(f"Erro no teste de failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Função para registrar as extensões no app principal
def register_extensions(app):
    """Registra as extensões no app FastAPI principal"""
    app.include_router(router)
    logger.info("✅ Extensões da API registradas com sucesso")