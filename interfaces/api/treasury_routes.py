# interfaces/api/treasury_routes.py
"""
API Routes para Treasury Router
Sistema de cascata e roteamento de lucros
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from core.treasury import treasury_router

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/v1/treasury", tags=["treasury"])


# ========== MODELS ==========

class SettleTradeRequest(BaseModel):
    """Request para liquidar um trade"""
    slot_id: str
    net_pnl: float
    settlement_id: str
    trade_details: Optional[Dict[str, Any]] = None


class StandardResponse(BaseModel):
    """Response padrão"""
    status: str
    data: Optional[Any] = None
    message: Optional[str] = None


# ========== ENDPOINTS ==========

@router.get("/status", response_model=StandardResponse)
async def get_cascade_status():
    """
    Retorna status geral da cascata
    
    Returns:
        Status com todos os slots, capitalização, treasury balance
    """
    try:
        status = treasury_router.get_cascade_status()
        
        return StandardResponse(
            status="success",
            data=status
        )
    
    except Exception as e:
        logger.error(f"Error getting cascade status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots", response_model=StandardResponse)
async def get_all_slots():
    """
    Retorna estado de todos os slots
    
    Returns:
        Lista com estado detalhado de cada slot
    """
    try:
        slots = treasury_router.get_all_slots_state()
        
        return StandardResponse(
            status="success",
            data={
                "slots": slots,
                "total": len(slots)
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots/{slot_id}", response_model=StandardResponse)
async def get_slot_state(slot_id: str):
    """
    Retorna estado de um slot específico
    
    Args:
        slot_id: ID do slot (ex: slot_1)
    
    Returns:
        Estado detalhado do slot
    """
    try:
        slot_state = treasury_router.get_slot_state(slot_id)
        
        if not slot_state:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return StandardResponse(
            status="success",
            data=slot_state
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settle", response_model=StandardResponse)
async def settle_trade(request: SettleTradeRequest):
    """
    Liquida um trade e roteia lucros conforme cascata
    
    Args:
        request: Dados do settlement
    
    Returns:
        Resultado do settlement e roteamento
    """
    try:
        result = treasury_router.settle_trade(
            slot_id=request.slot_id,
            net_pnl=request.net_pnl,
            settlement_id=request.settlement_id,
            trade_details=request.trade_details
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return StandardResponse(
            status="success",
            data=result,
            message=f"Settlement processado: {request.settlement_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error settling trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=StandardResponse)
async def get_settlement_history(limit: int = 100):
    """
    Retorna histórico de settlements
    
    Args:
        limit: Número máximo de registros (padrão: 100)
    
    Returns:
        Lista de settlements recentes
    """
    try:
        history = treasury_router.get_settlement_history(limit)
        
        return StandardResponse(
            status="success",
            data={
                "settlements": history,
                "count": len(history)
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting settlement history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/next-target", response_model=StandardResponse)
async def get_next_target_slot():
    """
    Retorna próximo slot alvo para receber lucros
    
    Returns:
        ID e estado do próximo slot não capitalizado
    """
    try:
        next_slot = treasury_router.next_target_slot()
        
        if next_slot is None:
            return StandardResponse(
                status="success",
                data=None,
                message="Todos os slots estão capitalizados. Lucros vão para Treasury."
            )
        
        return StandardResponse(
            status="success",
            data=next_slot.to_dict()
        )
    
    except Exception as e:
        logger.error(f"Error getting next target slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sweep", response_model=StandardResponse)
async def force_sweep():
    """
    Força varredura de todos os slots
    Roteia qualquer excesso acima de VB
    
    Returns:
        Resultados da varredura
    """
    try:
        result = treasury_router.force_sweep_all_slots()
        
        return StandardResponse(
            status="success",
            data=result,
            message=f"Varredura concluída: {result['swept_slots']} slots processados"
        )
    
    except Exception as e:
        logger.error(f"Error forcing sweep: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/treasury", response_model=StandardResponse)
async def get_treasury_balance():
    """
    Retorna saldo da Tesouraria
    
    Returns:
        Saldo acumulado na tesouraria
    """
    try:
        balance = treasury_router.treasury_balance
        
        return StandardResponse(
            status="success",
            data={
                "treasury_balance": balance,
                "currency": "USD"
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting treasury balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=StandardResponse)
async def get_cascade_metrics():
    """
    Retorna métricas consolidadas da cascata
    
    Returns:
        Métricas agregadas de capitalização, lucros, etc.
    """
    try:
        status = treasury_router.get_cascade_status()
        history = treasury_router.get_settlement_history(1000)
        
        # Calcula métricas
        total_settlements = len(history)
        total_profit = sum(s['net_pnl'] for s in history if s['net_pnl'] > 0)
        total_loss = sum(abs(s['net_pnl']) for s in history if s['net_pnl'] < 0)
        net_pnl = total_profit - total_loss
        
        win_rate = 0.0
        if total_settlements > 0:
            winning_trades = len([s for s in history if s['net_pnl'] > 0])
            win_rate = (winning_trades / total_settlements) * 100
        
        metrics = {
            "cascade_completion_pct": status['cascade_completion_pct'],
            "capitalized_slots": status['capitalized_count'],
            "operating_slots": status['operating_count'],
            "treasury_balance": status['treasury_balance'],
            "total_capital_deployed": status['total_capital_deployed'],
            "total_settlements": total_settlements,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_pnl": net_pnl,
            "win_rate_pct": win_rate
        }
        
        return StandardResponse(
            status="success",
            data=metrics
        )
    
    except Exception as e:
        logger.error(f"Error getting cascade metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
