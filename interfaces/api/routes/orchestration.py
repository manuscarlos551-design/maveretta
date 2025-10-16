# interfaces/api/routes/orchestration.py
"""
Orchestration Routes - Estado da orquestração do sistema
Inclui controles de operação: start/stop/pause/emergency
"""
import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Orchestration"])

# Modelo para alteração de modo
class ModeRequest(BaseModel):
    mode: str  # "auto", "manual", "simulation"

def _get_redis_client():
    """Obtém cliente Redis"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Erro ao conectar Redis: {e}")
        return None

@router.get("/orchestration/state")
async def get_orchestration_state() -> Dict[str, Any]:
    """
    Estado completo da orquestração
    """
    try:
        redis_client = _get_redis_client()
        
        # Estado base
        orchestration_state = {
            "leader": None,
            "leader_id": "IA_ORQUESTRADORA_CLAUDE",
            "slots": [],
            "cascade": {
                "enabled": True,
                "target_pct": 10.0,
                "queue": []
            },
            "orchestrator": {
                "status": "RUNNING",
                "leader_id": "IA_ORQUESTRADORA_CLAUDE",
                "last_decision": None,
                "decision_count": 0
            },
            "active_strategies": {},
            "risk_controls": {
                "emergency_stop": False,
                "global_protection": False,
                "max_drawdown_reached": False
            },
            "performance": {
                "total_pnl": 0,
                "daily_pnl": 0,
                "winning_slots": 0,
                "losing_slots": 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if redis_client:
            try:
                # Estado do líder
                leader_key = "orchestration:leader"
                leader_data = redis_client.get(leader_key)
                if leader_data:
                    leader_info = json.loads(leader_data)
                    orchestration_state["leader"] = leader_info
                    orchestration_state["leader_id"] = leader_info.get("id", "IA_ORQUESTRADORA_CLAUDE")
                
                # Estado dos slots
                slots_key = "orchestration:slots"
                slots_data = redis_client.get(slots_key)
                if slots_data:
                    slots_info = json.loads(slots_data)
                    orchestration_state["slots"] = slots_info
                
                # Estado da cascata
                cascade_key = "orchestration:cascade"
                cascade_data = redis_client.get(cascade_key)
                if cascade_data:
                    cascade_info = json.loads(cascade_data)
                    orchestration_state["cascade"].update(cascade_info)
                
                # Controles de risco globais
                risk_key = "orchestration:risk_controls"
                risk_data = redis_client.get(risk_key)
                if risk_data:
                    risk_info = json.loads(risk_data)
                    orchestration_state["risk_controls"].update(risk_info)
                
                # Performance agregada
                perf_key = "orchestration:performance"
                perf_data = redis_client.get(perf_key)
                if perf_data:
                    perf_info = json.loads(perf_data)
                    orchestration_state["performance"].update(perf_info)
                
            except Exception as e:
                logger.warning(f"Erro ao ler dados de orquestração do Redis: {e}")
        
        return orchestration_state
        
    except Exception as e:
        logger.error(f"Erro ao obter estado de orquestração: {e}")
        # Retorna estado mínimo funcional
        return {
            "leader": {"id": "IA_ORQUESTRADORA_CLAUDE", "status": "UNKNOWN"},
            "leader_id": "IA_ORQUESTRADORA_CLAUDE", 
            "slots": [],
            "cascade": {"enabled": True, "target_pct": 10.0, "queue": []},
            "orchestrator": {"status": "ERROR", "leader_id": "IA_ORQUESTRADORA_CLAUDE"},
            "active_strategies": {},
            "risk_controls": {"emergency_stop": False, "global_protection": False},
            "performance": {"total_pnl": 0, "daily_pnl": 0},
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/decisions/feed")
async def get_decisions_feed() -> Dict[str, Any]:
    """
    Feed de decisões das IAs
    """
    try:
        redis_client = _get_redis_client()
        decisions = []
        
        if redis_client:
            try:
                # Buscar decisões recentes de todas as IAs
                decisions_key = "decisions:feed"
                decisions_data = redis_client.lrange(decisions_key, 0, 49)  # Últimas 50
                
                for decision_str in decisions_data:
                    try:
                        decision = json.loads(decision_str)
                        decisions.append(decision)
                    except:
                        continue
                
            except Exception as e:
                logger.warning(f"Erro ao obter feed de decisões: {e}")
        
        return {
            "decisions": decisions,
            "total": len(decisions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro no feed de decisões: {e}")
        return {
            "decisions": [],
            "total": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/orchestration/stream")
async def orchestration_stream():
    """
    Server-Sent Events (SSE) stream para eventos de orquestração em tempo real
    
    Publica eventos como:
    - agent_started / agent_stopped
    - consensus_started / consensus_proposals / consensus_challenges / consensus_decision
    - risk_blocked
    """
    async def event_generator():
        """Gera eventos SSE"""
        try:
            # Importa EventsBus do módulo de eventos
            from core.orchestrator.events import event_publisher
            
            # Envia ping inicial
            yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Loop de eventos
            last_event_id = 0
            while True:
                try:
                    # Busca novos eventos do EventsBus
                    events = event_publisher.get_recent_events(since_id=last_event_id, limit=10)
                    
                    for event in events:
                        event_type = event.get('type', 'unknown')
                        event_id = event.get('id', last_event_id + 1)
                        event_data = json.dumps(event)
                        
                        # Envia evento SSE
                        yield f"id: {event_id}\nevent: {event_type}\ndata: {event_data}\n\n"
                        
                        last_event_id = max(last_event_id, event_id)
                    
                    # Envia ping periódico a cada 15s se não houver eventos
                    if not events:
                        yield f"event: ping\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                    
                    # Aguarda antes de buscar novamente
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Erro no event generator: {e}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Erro fatal no event generator: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Desabilita buffering no nginx
        }
    )

@router.get("/orchestration/agents")
async def get_orchestration_agents() -> Dict[str, Any]:
    """
    Lista todos os agentes e seus estados
    """
    try:
        from core.orchestrator.engine import agent_engine
        
        agents = agent_engine.list_agents()
        stats = agent_engine.get_stats()
        
        return {
            "agents": agents,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao buscar agentes: {e}")
        return {
            "agents": {},
            "stats": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/orchestration/agents/{agent_id}/start")
async def start_agent(agent_id: str) -> Dict[str, Any]:
    """
    Inicia um agente específico
    """
    try:
        from core.orchestrator.engine import agent_engine
        
        success, message = agent_engine.start_agent(agent_id)
        
        return {
            "success": success,
            "message": message,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao iniciar agente {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/agents/{agent_id}/stop")
async def stop_agent(agent_id: str) -> Dict[str, Any]:
    """
    Para um agente específico
    """
    try:
        from core.orchestrator.engine import agent_engine
        
        success, message = agent_engine.stop_agent(agent_id)
        
        return {
            "success": success,
            "message": message,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao parar agente {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/agents/{agent_id}/mode")
async def set_agent_mode(agent_id: str, mode: str) -> Dict[str, Any]:
    """
    Define o modo de execução de um agente (shadow/paper/live)
    """
    try:
        from core.orchestrator.engine import agent_engine
        
        success, message = agent_engine.set_mode(agent_id, mode)
        
        return {
            "success": success,
            "message": message,
            "agent_id": agent_id,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao definir modo do agente {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestration/consensus/force")
async def force_consensus(
    symbol: Optional[str] = None, 
    agents: Optional[List[str]] = None, 
    timeframe: str = "5m",
    symbols: Optional[List[str]] = None,
    reason: str = "manual"
) -> Dict[str, Any]:
    """
    Força uma rodada de consenso manual
    
    Aceita payload opcional:
    {
        "symbols": ["BTC/USDT", "ETH/USDT"],  # Lista de símbolos (ou symbol único)
        "agents": ["IA_ALPHA", "IA_BETA"],    # Agentes participantes (opcional)
        "timeframe": "5m",                     # Timeframe (padrão 5m)
        "reason": "manual"                     # Razão do consenso forçado
    }
    """
    try:
        from core.orchestrator.engine import agent_engine
        
        # Suportar tanto symbol único quanto symbols array
        target_symbols = symbols if symbols else ([symbol] if symbol else ["BTC/USDT"])
        
        results = []
        for sym in target_symbols:
            result = agent_engine.run_consensus_round(
                symbol=sym,
                participating_agents=agents or [],
                timeframe=timeframe
            )
            result["reason"] = reason
            results.append(result)
        
        return {
            "success": True,
            "consensus_rounds": results,
            "total": len(results),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao forçar consenso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orchestration/consensus/recent")
async def get_recent_consensus(limit: int = 50) -> Dict[str, Any]:
    """
    Obtém rodadas de consenso recentes
    """
    try:
        from core.orchestrator.events import get_recent_consensus_rounds
        
        consensus_rounds = get_recent_consensus_rounds(limit=limit)
        
        return {
            "consensus_rounds": consensus_rounds,
            "total": len(consensus_rounds),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao buscar consensos recentes: {e}")
        return {
            "consensus_rounds": [],
            "total": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# CONTROLES DE OPERAÇÃO - FASE 3 IMPLEMENTATION
# =============================================================================

@router.post("/v1/orchestration/start")
async def start_orchestration():
    """
    Inicia o bot de trading
    
    Envia comando via Redis para bot_runner_modular.py
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível")
        
        # Verifica se já está rodando
        current_state = redis_client.get("bot:state")
        if current_state == "running":
            return {"status": "warning", "message": "Bot já está rodando"}
        
        # Envia comando START
        redis_client.publish("bot:commands", "START")
        redis_client.set("bot:state", "running")
        
        logger.info("Bot started via API")
        return {
            "status": "ok",
            "message": "Bot iniciado com sucesso",
            "state": "running"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/orchestration/stop")
async def stop_orchestration():
    """
    Para o bot (fecha todas as posições abertas e para)
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível")
        
        current_state = redis_client.get("bot:state")
        if current_state == "stopped":
            return {"status": "warning", "message": "Bot já está parado"}
        
        # Envia comando STOP (fecha posições)
        redis_client.publish("bot:commands", "STOP")
        redis_client.set("bot:state", "stopping")
        
        logger.warning("Bot stopping - closing all positions")
        return {
            "status": "ok",
            "message": "Bot parando - fechando todas as posições",
            "state": "stopping"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/orchestration/pause")
async def pause_orchestration():
    """
    Pausa o bot (mantém posições abertas, não abre novas)
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível")
        
        current_state = redis_client.get("bot:state")
        if current_state == "paused":
            return {"status": "warning", "message": "Bot já está pausado"}
        
        # Envia comando PAUSE
        redis_client.publish("bot:commands", "PAUSE")
        redis_client.set("bot:state", "paused")
        
        logger.info("Bot paused - no new positions")
        return {
            "status": "ok",
            "message": "Bot pausado - não abrirá novas posições",
            "state": "paused"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/orchestration/emergency-stop")
async def emergency_stop():
    """
    EMERGENCY STOP - Fecha tudo imediatamente a mercado
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível")
        
        # Envia comando EMERGENCY_STOP
        redis_client.publish("bot:commands", "EMERGENCY_STOP")
        redis_client.set("bot:state", "emergency_stopped")
        redis_client.set("bot:emergency", "true")
        
        logger.critical("EMERGENCY STOP ACTIVATED")
        return {
            "status": "ok",
            "message": "🚨 EMERGENCY STOP - Fechando todas as posições IMEDIATAMENTE",
            "state": "emergency_stopped"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/orchestration/mode")
async def set_mode(request: ModeRequest):
    """
    Altera o modo de operação
    
    Modos:
    - auto: Totalmente automático
    - manual: Apenas com aprovação humana
    - simulation: Modo simulação (paper trading)
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis não disponível")
        
        valid_modes = ["auto", "manual", "simulation"]
        if request.mode not in valid_modes:
            raise HTTPException(400, f"Modo inválido. Use: {valid_modes}")
        
        # Salva modo no Redis
        redis_client.set("bot:mode", request.mode)
        redis_client.publish("bot:commands", f"MODE:{request.mode}")
        
        logger.info(f"Mode changed to: {request.mode}")
        return {
            "status": "ok",
            "message": f"Modo alterado para: {request.mode}",
            "mode": request.mode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/orchestration/status")
async def get_status():
    """
    Retorna o status atual do bot
    """
    try:
        redis_client = _get_redis_client()
        if not redis_client:
            return {
                "state": "unknown",
                "mode": "unknown",
                "emergency": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        state = redis_client.get("bot:state") or "unknown"
        mode = redis_client.get("bot:mode") or "auto"
        emergency = redis_client.get("bot:emergency") == "true"
        
        return {
            "state": state,
            "mode": mode,
            "emergency": emergency,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))