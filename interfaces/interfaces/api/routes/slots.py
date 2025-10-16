"""Slot management API routes."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from core.slots.slot_store import slot_store
from core.slots.slot_context import update_slot_stage

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/")
async def get_slots() -> List[Dict[str, Any]]:
    """Get all bot slots."""
    try:
        slots = slot_store.get_all_slots()
        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slot_id}")
async def get_slot(slot_id: str) -> Dict[str, Any]:
    """Get specific slot details."""
    slot = slot_store.get_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot


@router.post("/{slot_id}/strategy")
async def update_slot_strategy(slot_id: str, strategy_config: Dict[str, Any]) -> Dict[str, str]:
    """Update slot strategy configuration."""
    success = slot_store.update_slot_strategy(slot_id, strategy_config)
    if not success:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    return {"message": f"Strategy updated for slot {slot_id}", "status": "success"}
