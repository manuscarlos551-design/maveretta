#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slot API Routes - Endpoints para gerenciamento de slots de trading
Fornece controle completo sobre slots e posições
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Inicializar router
router = APIRouter(prefix="/slots", tags=["slots"])

# Instância global do slot manager (será injetada)
slot_manager = None


def set_slot_manager(manager):
    """Configura instância do slot manager"""
    global slot_manager
    slot_manager = manager


# ==================== MODELS ====================

class CreateSlotRequest(BaseModel):
    exchange: str
    capital_base: float
    strategy: str = "intelligent_agent"
    risk_config: Optional[Dict] = None


class OpenPositionRequest(BaseModel):
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class ClosePositionRequest(BaseModel):
    exit_price: float
    reason: str = "manual"


class UpdateRiskConfigRequest(BaseModel):
    risk_config: Dict


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_all_slots():
    """
    Retorna todos os slots
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        slots = slot_manager.get_all_slots()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(slots),
            "slots": slots
        }
    except Exception as e:
        logger.error(f"Erro ao buscar slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_slots():
    """
    Retorna apenas slots ativos
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        slots = slot_manager.get_active_slots()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(slots),
            "slots": slots
        }
    except Exception as e:
        logger.error(f"Erro ao buscar slots ativos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_slots_summary():
    """
    Retorna resumo geral de todos os slots
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        summary = slot_manager.get_summary()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            **summary
        }
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_slot(request: CreateSlotRequest):
    """
    Cria um novo slot de trading
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        slot_id = slot_manager.create_slot(
            exchange=request.exchange,
            capital_base=request.capital_base,
            strategy=request.strategy,
            risk_config=request.risk_config
        )
        
        slot = slot_manager.get_slot(slot_id)
        
        return {
            "message": "Slot criado com sucesso",
            "slot_id": slot_id,
            "slot": slot
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao criar slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slot_id}")
async def get_slot(slot_id: str):
    """
    Obtém informações de um slot específico
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        slot = slot_manager.get_slot(slot_id)
        
        if not slot:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return slot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slot_id}/activate")
async def activate_slot(slot_id: str):
    """
    Ativa um slot para trading
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        success = slot_manager.activate_slot(slot_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return {
            "message": f"Slot {slot_id} ativado com sucesso",
            "slot": slot_manager.get_slot(slot_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao ativar slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slot_id}/deactivate")
async def deactivate_slot(slot_id: str):
    """
    Desativa um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        success = slot_manager.deactivate_slot(slot_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return {
            "message": f"Slot {slot_id} desativado com sucesso",
            "slot": slot_manager.get_slot(slot_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao desativar slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slot_id}/assign-agent/{agent_id}")
async def assign_agent_to_slot(slot_id: str, agent_id: str):
    """
    Atribui um agente IA a um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        success = slot_manager.assign_agent(slot_id, agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return {
            "message": f"Agente {agent_id} atribuído ao slot {slot_id}",
            "slot": slot_manager.get_slot(slot_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atribuir agente ao slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slot_id}/positions")
async def get_slot_positions(
    slot_id: str,
    status: Optional[str] = Query(None, description="Filtrar por status (open, closed)")
):
    """
    Obtém posições de um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        positions = slot_manager.get_positions(slot_id, status)
        
        # Converter objetos SlotPosition para dict
        positions_dict = [
            {
                "position_id": p.position_id,
                "slot_id": p.slot_id,
                "symbol": p.symbol,
                "side": p.side,
                "size": p.size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "exit_price": p.exit_price,
                "stop_loss": p.stop_loss,
                "take_profit": p.take_profit,
                "status": p.status,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "unrealized_pnl": p.unrealized_pnl,
                "opened_at": p.opened_at.isoformat() if p.opened_at else None,
                "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                "close_reason": p.close_reason
            }
            for p in positions
        ]
        
        return {
            "slot_id": slot_id,
            "count": len(positions_dict),
            "positions": positions_dict
        }
    except Exception as e:
        logger.error(f"Erro ao buscar posições do slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slot_id}/positions")
async def open_position(slot_id: str, request: OpenPositionRequest):
    """
    Abre uma nova posição em um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        position_id = slot_manager.open_position(
            slot_id=slot_id,
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit
        )
        
        if not position_id:
            raise HTTPException(status_code=400, detail="Falha ao abrir posição - verifique logs")
        
        # Buscar posição criada
        positions = slot_manager.get_positions(slot_id, status="open")
        position = next((p for p in positions if p.position_id == position_id), None)
        
        return {
            "message": "Posição aberta com sucesso",
            "position_id": position_id,
            "position": {
                "position_id": position.position_id,
                "symbol": position.symbol,
                "side": position.side,
                "size": position.size,
                "entry_price": position.entry_price,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit
            } if position else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao abrir posição no slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slot_id}/positions/{position_id}/close")
async def close_position(slot_id: str, position_id: str, request: ClosePositionRequest):
    """
    Fecha uma posição
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        success = slot_manager.close_position(
            slot_id=slot_id,
            position_id=position_id,
            exit_price=request.exit_price,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao fechar posição - verifique logs")
        
        return {
            "message": "Posição fechada com sucesso",
            "position_id": position_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fechar posição {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slot_id}/metrics")
async def get_slot_metrics(slot_id: str):
    """
    Obtém métricas de desempenho de um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        metrics = slot_manager.get_metrics(slot_id)
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"Métricas não encontradas para slot {slot_id}")
        
        return {
            "slot_id": metrics.slot_id,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": metrics.win_rate,
            "total_pnl": metrics.total_pnl,
            "avg_win": metrics.avg_win,
            "avg_loss": metrics.avg_loss,
            "largest_win": metrics.largest_win,
            "largest_loss": metrics.largest_loss,
            "sharpe_ratio": metrics.sharpe_ratio
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar métricas do slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{slot_id}/risk-config")
async def update_risk_config(slot_id: str, request: UpdateRiskConfigRequest):
    """
    Atualiza configuração de risco de um slot
    """
    try:
        if slot_manager is None:
            raise HTTPException(status_code=503, detail="Slot manager not initialized")
        
        success = slot_manager.update_risk_config(slot_id, request.risk_config)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} não encontrado")
        
        return {
            "message": "Configuração de risco atualizada com sucesso",
            "slot": slot_manager.get_slot(slot_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar risk config do slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
