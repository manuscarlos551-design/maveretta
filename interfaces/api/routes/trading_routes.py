# interfaces/api/routes/trading_routes.py
"""
Rotas API para Trading Engine, Agentes e Slots
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

# Imports do sistema
from core.trading_engine import trading_engine
from ai.agents.multi_agent_system import multi_agent_system
from core.slots.cascade_manager import cascade_manager
from core.slots.manager import slot_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["trading"])


# ============= MODELS =============

class MarketAnalysisRequest(BaseModel):
    """Request para análise de mercado"""
    symbol: str
    closes: List[float]
    volumes: Optional[List[float]] = []
    highs: Optional[List[float]] = []
    lows: Optional[List[float]] = []


class TradeRequest(BaseModel):
    """Request para executar trade"""
    symbol: str
    market_data: Dict[str, Any]
    slot_id: Optional[str] = None


class CreateSlotRequest(BaseModel):
    """Request para criar slot"""
    slot_id: str
    exchange: str
    total_capital: float
    strategy: Optional[str] = "default"


class RecordTradeResultRequest(BaseModel):
    """Request para registrar resultado de trade"""
    slot_id: str
    profit_loss: float


# ============= TRADING ENGINE ROUTES =============

@router.get("/trading/status")
async def get_trading_status():
    """Retorna status do trading engine"""
    try:
        stats = trading_engine.get_statistics()
        return {
            "status": "ok",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/start")
async def start_trading():
    """Inicia o trading engine"""
    try:
        trading_engine.start()
        return {
            "status": "ok",
            "message": "Trading engine iniciado"
        }
    except Exception as e:
        logger.error(f"Erro ao iniciar trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/stop")
async def stop_trading():
    """Para o trading engine"""
    try:
        trading_engine.stop()
        return {
            "status": "ok",
            "message": "Trading engine parado"
        }
    except Exception as e:
        logger.error(f"Erro ao parar trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/analyze")
async def analyze_market(request: MarketAnalysisRequest):
    """Analisa mercado usando multi-agent system"""
    try:
        market_data = {
            'closes': request.closes,
            'volumes': request.volumes or [],
            'highs': request.highs or [],
            'lows': request.lows or []
        }
        
        consensus = multi_agent_system.analyze_market_consensus(
            market_data,
            request.symbol
        )
        
        return {
            "status": "ok",
            "data": consensus
        }
    except Exception as e:
        logger.error(f"Erro na análise: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/execute")
async def execute_trade(request: TradeRequest, background_tasks: BackgroundTasks):
    """Executa trade completo (análise + execução)"""
    try:
        result = await trading_engine.analyze_and_trade(
            symbol=request.symbol,
            market_data=request.market_data,
            slot_id=request.slot_id
        )
        
        return {
            "status": "ok",
            "data": result
        }
    except Exception as e:
        logger.error(f"Erro ao executar trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/history")
async def get_trade_history(limit: int = 100):
    """Retorna histórico de trades"""
    try:
        history = trading_engine.get_trade_history(limit)
        return {
            "status": "ok",
            "data": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= AGENTS ROUTES =============

@router.get("/agents")
async def get_all_agents():
    """Retorna status de todos os agentes"""
    try:
        agents = multi_agent_system.get_all_agents_status()
        return {
            "status": "ok",
            "data": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Erro ao obter agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent_status(agent_id: str):
    """Retorna status de um agente específico"""
    try:
        agent = multi_agent_system.get_agent_status(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} não encontrado")
        
        return {
            "status": "ok",
            "data": agent
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/stats")
async def get_agents_statistics():
    """Retorna estatísticas dos agentes"""
    try:
        stats = multi_agent_system.get_statistics()
        return {
            "status": "ok",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/decisions/history")
async def get_decision_history(limit: int = 100):
    """Retorna histórico de decisões dos agentes"""
    try:
        history = multi_agent_system.get_decision_history(limit)
        return {
            "status": "ok",
            "data": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= SLOTS CASCADE ROUTES =============

@router.post("/slots/cascade/create")
async def create_cascade_slot(request: CreateSlotRequest):
    """Cria um novo slot em cascata"""
    try:
        success = cascade_manager.create_slot(
            slot_id=request.slot_id,
            exchange=request.exchange,
            total_capital=request.total_capital,
            strategy=request.strategy
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao criar slot (já existe?)")
        
        return {
            "status": "ok",
            "message": f"Slot {request.slot_id} criado com sucesso"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots/cascade")
async def get_all_cascade_slots():
    """Retorna todos os slots em cascata"""
    try:
        slots = cascade_manager.get_all_slots()
        return {
            "status": "ok",
            "data": slots,
            "count": len(slots)
        }
    except Exception as e:
        logger.error(f"Erro ao obter slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots/cascade/{slot_id}")
async def get_cascade_slot(slot_id: str):
    """Retorna um slot específico"""
    try:
        slot = cascade_manager.get_slot(slot_id)
        if not slot:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return {
            "status": "ok",
            "data": slot.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slots/cascade/record-trade")
async def record_trade_result(request: RecordTradeResultRequest):
    """Registra resultado de trade e avalia upgrade/downgrade do slot"""
    try:
        success = cascade_manager.record_trade_result(
            slot_id=request.slot_id,
            profit_loss=request.profit_loss
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {request.slot_id} não encontrado")
        
        # Obter slot atualizado
        slot = cascade_manager.get_slot(request.slot_id)
        
        return {
            "status": "ok",
            "message": "Trade registrado com sucesso",
            "slot": slot.to_dict() if slot else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots/cascade/stats")
async def get_cascade_statistics():
    """Retorna estatísticas globais dos slots em cascata"""
    try:
        stats = cascade_manager.get_global_statistics()
        return {
            "status": "ok",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= PAPER TRADES ROUTES =============

@router.get("/paper-trades")
async def get_paper_trades():
    """Retorna todos os paper trades abertos"""
    try:
        trades = slot_manager.get_open_paper_trades()
        return {
            "status": "ok",
            "data": trades,
            "count": len(trades)
        }
    except Exception as e:
        logger.error(f"Erro ao obter paper trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper-trades/{paper_id}")
async def get_paper_trade(paper_id: str):
    """Retorna um paper trade específico"""
    try:
        trade = slot_manager.get_paper_trade(paper_id)
        if not trade:
            raise HTTPException(status_code=404, detail=f"Paper trade {paper_id} não encontrado")
        
        return {
            "status": "ok",
            "data": trade
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter paper trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paper-trades/{paper_id}/close")
async def close_paper_trade(paper_id: str, close_price: float, reason: str = "manual"):
    """Fecha um paper trade"""
    try:
        success, message, trade_data = slot_manager.close_paper_trade(
            paper_id=paper_id,
            close_price=close_price,
            reason=reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "status": "ok",
            "message": message,
            "data": trade_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fechar paper trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= HEALTH & INFO =============

@router.get("/health")
async def health_check():
    """Health check da API de trading"""
    try:
        # Verificar componentes críticos
        agents_count = len(multi_agent_system.agents)
        slots_count = len(cascade_manager.slots)
        
        return {
            "status": "healthy",
            "components": {
                "trading_engine": trading_engine.is_running,
                "multi_agent_system": agents_count > 0,
                "cascade_manager": slots_count >= 0,
                "slot_manager": True
            },
            "counts": {
                "agents": agents_count,
                "slots": slots_count,
                "total_trades": trading_engine.total_trades
            }
        }
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
