#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Gateway REAL - Sistema de Trading Bot com Dados Reais
Substitui o ai-gateway-main.py com integração completa às 5 exchanges
SEM MOCKS - Apenas dados reais
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# Core imports
from core.exchanges.multi_exchange_manager import MultiExchangeManager
from core.slots.real_slot_manager import RealSlotManager
from core.agents.agent_orchestrator import AgentOrchestrator
from core.api.exchange_routes import router as exchange_router
from core.api.slot_routes import router as slot_router, set_slot_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title="AI Gateway - Real Trading Bot",
    description="API Gateway para Bot de Trading com Agentes IA - Dados Reais das 5 Exchanges",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== PROMETHEUS METRICS ====================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# ==================== GLOBAL MANAGERS ====================

exchange_manager: MultiExchangeManager = None
slot_manager: RealSlotManager = None
agent_orchestrator: AgentOrchestrator = None


def initialize_managers():
    """Inicializa managers globais"""
    global exchange_manager, slot_manager, agent_orchestrator
    
    try:
        # Inicializar Exchange Manager
        logger.info("🚀 Inicializando Exchange Manager...")
        exchange_manager = MultiExchangeManager()
        
        # Inicializar Slot Manager
        logger.info("🚀 Inicializando Slot Manager...")
        slot_manager = RealSlotManager(exchange_manager)
        
        # Configurar slot manager nas rotas
        set_slot_manager(slot_manager)
        
        # Inicializar Agent Orchestrator
        logger.info("🚀 Inicializando Agent Orchestrator...")
        agent_orchestrator = AgentOrchestrator(exchange_manager, slot_manager)
        
        logger.info("✅ Managers inicializados com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar managers: {e}")
        raise


# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware para coleta de métricas"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Coletar métricas
    method = request.method
    endpoint = request.url.path
    status = response.status_code
    
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response


# ==================== HEALTH & METRICS ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Verificar saúde dos managers
        exchange_health = exchange_manager.health_check() if exchange_manager else {}
        
        active_exchanges = list(exchange_health.keys()) if exchange_health else []
        online_exchanges = [
            ex for ex, data in exchange_health.items()
            if isinstance(data, dict) and data.get('status') == 'online'
        ]
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "components": {
                "exchange_manager": "initialized" if exchange_manager else "not_initialized",
                "slot_manager": "initialized" if slot_manager else "not_initialized"
            },
            "exchanges": {
                "total": len(active_exchanges),
                "online": len(online_exchanges),
                "list": online_exchanges
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": str(e)}
        )


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Gateway - Real Trading Bot",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "exchanges": "/v1/exchanges/*",
            "slots": "/v1/slots/*",
            "agents": "/v1/agents/*",
            "orchestration": "/v1/orchestration/*"
        }
    }


# ==================== ORCHESTRATION ENDPOINTS ====================

@app.get("/v1/orchestration/state")
async def get_orchestration_state():
    """Retorna estado completo da orquestração (compatibilidade com dashboard)"""
    try:
        # Buscar dados reais
        slots_data = slot_manager.get_all_slots() if slot_manager else []
        summary = slot_manager.get_summary() if slot_manager else {}
        
        # Buscar agentes IA
        ias = agent_orchestrator.get_agent_health() if agent_orchestrator else []
        
        # Buscar resumo dos agentes
        agent_summary = agent_orchestrator.get_summary() if agent_orchestrator else {}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "slots": slots_data,
            "ias": ias,
            "summary": summary,
            "agent_summary": agent_summary,
            "risk_controls": {
                "global_max_drawdown": 10.0,
                "global_max_position_size": 5.0
            },
            "wallet": {
                "total_usd": summary.get("total_current", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error getting orchestration state: {e}")
        return {
            "slots": [],
            "ias": [],
            "summary": {},
            "agent_summary": {},
            "risk_controls": {},
            "wallet": {}
        }


@app.get("/v1/ia/health")
async def get_ia_health():
    """Retorna status dos agentes IA (compatibilidade com dashboard)"""
    try:
        if not agent_orchestrator:
            return []
        
        return agent_orchestrator.get_agent_health()
    except Exception as e:
        logger.error(f"Error getting IA health: {e}")
        return []


@app.get("/v1/agents")
async def get_all_agents():
    """Retorna todos os agentes com detalhes"""
    try:
        if not agent_orchestrator:
            return {"agents": [], "count": 0}
        
        agents = agent_orchestrator.get_all_agents()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(agents),
            "agents": agents
        }
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/agents/summary")
async def get_agents_summary():
    """Retorna resumo dos agentes"""
    try:
        if not agent_orchestrator:
            return {}
        
        return agent_orchestrator.get_summary()
    except Exception as e:
        logger.error(f"Error getting agents summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/agents/{agent_id}/activate")
async def activate_agent(agent_id: str):
    """Ativa um agente"""
    try:
        if not agent_orchestrator:
            raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
        
        success = agent_orchestrator.activate_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return {
            "message": f"Agent {agent_id} activated",
            "agent_id": agent_id,
            "status": "active"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/agents/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str):
    """Desativa um agente"""
    try:
        if not agent_orchestrator:
            raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
        
        success = agent_orchestrator.deactivate_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return {
            "message": f"Agent {agent_id} deactivated",
            "agent_id": agent_id,
            "status": "inactive"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/orchestration/start")
async def start_orchestration():
    """Inicia a orquestração de agentes"""
    try:
        if not agent_orchestrator:
            raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
        
        agent_orchestrator.start()
        
        return {
            "message": "Orchestration started successfully",
            "status": "running"
        }
    except Exception as e:
        logger.error(f"Error starting orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/orchestration/stop")
async def stop_orchestration():
    """Para a orquestração de agentes"""
    try:
        if not agent_orchestrator:
            raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
        
        agent_orchestrator.stop()
        
        return {
            "message": "Orchestration stopped successfully",
            "status": "stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/wallet/details")
async def get_wallet_details():
    """Retorna detalhes das carteiras (compatibilidade com dashboard)"""
    try:
        if not exchange_manager:
            return []
        
        balances = exchange_manager.get_all_balances()
        
        wallet_list = []
        for exchange_name, balance_data in balances.items():
            if isinstance(balance_data, dict) and 'total_usd' in balance_data:
                wallet_list.append({
                    "exchange": exchange_name,
                    "balance_usd": balance_data['total_usd'],
                    "assets": balance_data.get('total', {}),
                    "last_update": balance_data.get('timestamp')
                })
        
        return wallet_list
    except Exception as e:
        logger.error(f"Error getting wallet details: {e}")
        return []


# ==================== INCLUDE ROUTERS ====================

app.include_router(exchange_router, prefix="/v1")
app.include_router(slot_router, prefix="/v1")


# ==================== STARTUP & SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Inicialização na startup"""
    logger.info("=" * 60)
    logger.info("🚀 AI GATEWAY - REAL TRADING BOT")
    logger.info("=" * 60)
    
    try:
        initialize_managers()
        logger.info("✅ Sistema inicializado com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup no shutdown"""
    logger.info("🛑 Shutting down AI Gateway...")
    
    # Parar orchestrator
    if agent_orchestrator:
        try:
            agent_orchestrator.stop()
            logger.info("✅ Agent Orchestrator parado")
        except Exception as e:
            logger.error(f"Erro ao parar orchestrator: {e}")
    
    # Fechar exchanges
    if exchange_manager:
        try:
            exchange_manager.close_all()
            logger.info("✅ Exchanges fechadas")
        except Exception as e:
            logger.error(f"Erro ao fechar exchanges: {e}")


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8080"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
