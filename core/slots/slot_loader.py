"""
Carregador de Slots - Lê configuração de slots do JSON
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SLOT_CONFIG_PATH = Path("/app/data/slot_config.json")

class SlotLoader:
    """Carrega e gerencia configuração de slots"""
    
    def __init__(self):
        self.slots = []
        self._load_slots()
    
    def _load_slots(self):
        """Carrega slots do arquivo JSON"""
        try:
            if not SLOT_CONFIG_PATH.exists():
                logger.warning(f"⚠️ Arquivo de slots não encontrado: {SLOT_CONFIG_PATH}")
                return
            
            with open(SLOT_CONFIG_PATH, 'r') as f:
                data = json.load(f)
            
            slots_data = data.get("slots", {})
            
            for slot_id, slot_info in slots_data.items():
                if slot_info.get("active"):
                    self.slots.append({
                        "id": f"slot_{slot_id}",
                        "symbol": slot_info.get("symbol"),
                        "strategy": slot_info.get("strategy", "default"),
                        "status": "ACTIVE" if slot_info.get("active") else "INACTIVE",
                        "allocation": 0.0,  # Será preenchido dinamicamente
                        "pnl": 0.0,
                        "pnl_percentage": 0.0,
                        "exchange": "binance"  # Default
                    })
            
            logger.info(f"✅ Carregados {len(self.slots)} slots ativos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar slots: {e}")
            self.slots = []
    
    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Retorna todos os slots"""
        return self.slots
    
    def get_active_slots(self) -> List[Dict[str, Any]]:
        """Retorna apenas slots ativos"""
        return [slot for slot in self.slots if slot["status"] == "ACTIVE"]
    
    def get_slot_by_id(self, slot_id: str) -> Dict[str, Any]:
        """Retorna slot específico por ID"""
        for slot in self.slots:
            if slot["id"] == slot_id:
                return slot
        return None


# Instância global
_slot_loader = None

def get_slot_loader():
    """Obtém instância global do loader"""
    global _slot_loader
    if _slot_loader is None:
        _slot_loader = SlotLoader()
    return _slot_loader

def get_all_slots() -> List[Dict[str, Any]]:
    """Obtém todos os slots"""
    return get_slot_loader().get_all_slots()

def get_active_slots() -> List[Dict[str, Any]]:
    """Obtém slots ativos"""
    return get_slot_loader().get_active_slots()
