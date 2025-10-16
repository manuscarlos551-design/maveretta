"""Slot storage and persistence for Maveretta Bot."""
from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime, timezone


class SlotStore:
    """In-memory slot storage with basic persistence."""
    
    def __init__(self):
        self._slots: Dict[str, Dict[str, Any]] = {}
        self._load_slots()
    
    def _load_slots(self):
        """Load slots from storage (placeholder)."""
        # Initialize with demo slots
        for i in range(1, 5):
            slot_id = f"slot_{i}"
            self._slots[slot_id] = {
                "slot_id": slot_id,
                "status": "active" if i <= 2 else "inactive",
                "base_amount": 100.0 * i,
                "min_amount": 10.0,
                "strategy": f"strategy_{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "trades": [],
                "pnl": (i - 2) * 50.0,
                "exposure": i * 25.0,
                "cascade_level": i - 1
            }
    
    def get_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Get slot by ID."""
        return self._slots.get(slot_id)
    
    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Get all slots."""
        return list(self._slots.values())
    
    def save_slot(self, slot_data: Dict[str, Any]) -> bool:
        """Save slot data."""
        slot_id = slot_data.get("slot_id")
        if slot_id:
            self._slots[slot_id] = slot_data
            return True
        return False
    
    def update_slot_strategy(self, slot_id: str, strategy_config: Dict[str, Any]) -> bool:
        """Update slot strategy configuration."""
        if slot_id in self._slots:
            self._slots[slot_id].update({
                "strategy": strategy_config.get("strategy", "default"),
                "last_updated": datetime.now(timezone.utc).isoformat()
            })
            return True
        return False
    
    def delete_slot(self, slot_id: str) -> bool:
        """Delete slot."""
        if slot_id in self._slots:
            del self._slots[slot_id]
            return True
        return False


# Global slot store instance
slot_store = SlotStore()
