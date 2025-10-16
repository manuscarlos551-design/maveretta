# interfaces/api/routes/cascade.py
"""
Cascade Management API Routes
Gerencia sistema de cascade entre slots
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from core.engine.cascade_orchestrator import get_cascade_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cascade", tags=["cascade"])


# ============================================================================
# MODELS
# ============================================================================

class SlotConfigUpdate(BaseModel):
    """Modelo para atualização de configuração de slot"""
    capital_base: Optional[float] = Field(None, description="Capital base do slot")
    cascade_target_pct: Optional[float] = Field(None, description="Meta percentual de lucro para cascade")
    cascade_enabled: Optional[bool] = Field(None, description="Se cascade está habilitado")
    active: Optional[bool] = Field(None, description="Se slot está ativo")


class CascadeStatusResponse(BaseModel):
    """Resposta com status do orquestrador"""
    running: bool
    check_interval_seconds: int
    total_slots: int
    active_slots: int
    total_cascades: int
    last_cascade: Optional[Dict[str, Any]] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status", response_model=CascadeStatusResponse)
async def get_cascade_status():
    """
    Retorna status do sistema de cascade
    
    Returns:
        Status completo do orquestrador
    """
    try:
        orchestrator = get_cascade_orchestrator()
        status = orchestrator.get_status()
        return status
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_cascade_config():
    """
    Retorna configuração completa da cadeia de slots
    
    Returns:
        Configuração de todos os slots
    """
    try:
        orchestrator = get_cascade_orchestrator()
        return {
            "cascade_chain": list(orchestrator.slots_config.values())
        }
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/{slot_id}")
async def update_slot_config(
    slot_id: str,
    updates: SlotConfigUpdate
):
    """
    Atualiza configuração de um slot específico
    
    Args:
        slot_id: ID do slot (ex: slot_1)
        updates: Campos a atualizar
        
    Returns:
        Confirmação da atualização
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        # Converter para dict removendo campos None
        updates_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not updates_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = orchestrator.update_slot_config(slot_id, updates_dict)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
        
        return {
            "success": True,
            "slot_id": slot_id,
            "updated_fields": list(updates_dict.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CASCADE_API] Error updating slot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_cascade_history(limit: int = 50):
    """
    Retorna histórico de cascades executados
    
    Args:
        limit: Número máximo de registros (padrão: 50)
        
    Returns:
        Lista com histórico de cascades
    """
    try:
        orchestrator = get_cascade_orchestrator()
        history = orchestrator.get_cascade_history(limit=limit)
        
        return {
            "total": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_cascade_orchestrator():
    """
    Inicia o orquestrador de cascade (se não estiver rodando)
    
    Returns:
        Confirmação de início
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        if orchestrator.running:
            return {
                "success": True,
                "message": "Cascade orchestrator already running"
            }
        
        orchestrator.start()
        
        return {
            "success": True,
            "message": "Cascade orchestrator started"
        }
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error starting orchestrator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_cascade_orchestrator():
    """
    Para o orquestrador de cascade
    
    Returns:
        Confirmação de parada
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        if not orchestrator.running:
            return {
                "success": True,
                "message": "Cascade orchestrator already stopped"
            }
        
        orchestrator.stop()
        
        return {
            "success": True,
            "message": "Cascade orchestrator stopped"
        }
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error stopping orchestrator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slots/{slot_id}")
async def get_slot_details(slot_id: str):
    """
    Retorna detalhes de um slot específico
    
    Args:
        slot_id: ID do slot
        
    Returns:
        Configuração e estado do slot
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        if slot_id not in orchestrator.slots_config:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
        
        slot = orchestrator.slots_config[slot_id]
        
        # Calcular progresso atual
        capital_base = slot.get('capital_base', 1000.0)
        capital_current = slot.get('capital_current', capital_base)
        pnl = capital_current - capital_base
        pnl_percentage = (pnl / capital_base * 100) if capital_base > 0 else 0
        cascade_target = slot.get('cascade_target_pct', 10.0)
        progress = min((pnl_percentage / cascade_target * 100), 100) if cascade_target > 0 else 0
        
        return {
            "slot": slot,
            "calculated": {
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "cascade_progress": progress,
                "ready_for_cascade": pnl_percentage >= cascade_target
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting slot details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slots/{slot_id}/simulate")
async def simulate_cascade(
    slot_id: str,
    profit_amount: float = Body(..., embed=True)
):
    """
    Simula execução de cascade (não executa de verdade)
    
    Args:
        slot_id: ID do slot
        profit_amount: Valor de lucro a simular
        
    Returns:
        Resultado da simulação
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        if slot_id not in orchestrator.slots_config:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
        
        slot = orchestrator.slots_config[slot_id]
        next_slot_id = slot.get('next_slot_id')
        
        if not next_slot_id:
            return {
                "can_cascade": False,
                "reason": "No next slot configured"
            }
        
        next_slot = orchestrator.slots_config.get(next_slot_id)
        
        if not next_slot:
            return {
                "can_cascade": False,
                "reason": f"Next slot {next_slot_id} not found"
            }
        
        # Simular transferência
        current_capital = slot.get('capital_current', slot['capital_base'])
        next_capital = next_slot.get('capital_current', next_slot['capital_base'])
        
        return {
            "can_cascade": True,
            "simulation": {
                "from_slot": slot_id,
                "to_slot": next_slot_id,
                "profit_to_transfer": profit_amount,
                "current_slot_capital_before": current_capital,
                "current_slot_capital_after": slot['capital_base'],
                "next_slot_capital_before": next_capital,
                "next_slot_capital_after": next_capital + profit_amount,
                "next_slot_will_activate": not next_slot.get('active', False),
                "next_slot_agent": next_slot.get('assigned_ia', 'N/A'),
                "next_slot_agent_will_activate": next_slot.get('ia_status') != 'ACTIVE'
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CASCADE_API] Error simulating cascade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/status")
async def get_agents_status():
    """
    Retorna status de todos os agentes IA vinculados aos slots
    
    Returns:
        Status de cada agente e seu slot correspondente
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        agents_status = {}
        
        for slot_id, slot in orchestrator.slots_config.items():
            agent_id = slot.get('assigned_ia')
            if agent_id:
                if agent_id not in agents_status:
                    agents_status[agent_id] = {
                        'agent_id': agent_id,
                        'group': slot.get('ia_group', 'N/A'),
                        'slots_assigned': [],
                        'active_slots': 0,
                        'inactive_slots': 0
                    }
                
                slot_info = {
                    'slot_id': slot_id,
                    'active': slot.get('active', False),
                    'ia_status': slot.get('ia_status', 'UNKNOWN'),
                    'capital_current': slot.get('capital_current', 0)
                }
                
                agents_status[agent_id]['slots_assigned'].append(slot_info)
                
                if slot.get('active', False):
                    agents_status[agent_id]['active_slots'] += 1
                else:
                    agents_status[agent_id]['inactive_slots'] += 1
        
        return {
            'agents': list(agents_status.values()),
            'summary': {
                'total_agents': len(agents_status),
                'agents_with_active_slots': sum(1 for a in agents_status.values() if a['active_slots'] > 0)
            }
        }
        
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting agents status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/slots")
async def get_agent_slots(agent_id: str):
    """
    Retorna todos os slots operados por um agente específico
    
    Args:
        agent_id: ID do agente (A1, A2, A3, A4, A5, A6)
        
    Returns:
        Lista de slots operados pelo agente
    """
    try:
        orchestrator = get_cascade_orchestrator()
        
        agent_slots = []
        
        for slot_id, slot in orchestrator.slots_config.items():
            if slot.get('assigned_ia') == agent_id:
                agent_slots.append({
                    'slot_id': slot_id,
                    'active': slot.get('active', False),
                    'ia_status': slot.get('ia_status', 'UNKNOWN'),
                    'capital_base': slot.get('capital_base', 0),
                    'capital_current': slot.get('capital_current', 0),
                    'pnl': slot.get('capital_current', 0) - slot.get('capital_base', 0),
                    'cascade_target_pct': slot.get('cascade_target_pct', 10.0),
                    'next_slot_id': slot.get('next_slot_id')
                })
        
        if not agent_slots:
            raise HTTPException(status_code=404, detail=f"No slots found for agent {agent_id}")
        
        return {
            'agent_id': agent_id,
            'group': agent_slots[0].get('ia_group', orchestrator.slots_config.get(agent_slots[0]['slot_id'], {}).get('ia_group', 'N/A')),
            'total_slots': len(agent_slots),
            'active_slots': sum(1 for s in agent_slots if s['active']),
            'slots': agent_slots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CASCADE_API] Error getting agent slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))
