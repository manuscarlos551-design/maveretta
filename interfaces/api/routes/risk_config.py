# interfaces/api/routes/risk_config.py
"""
Risk Config Routes - Gerenciamento de configuração de risco
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/risk", tags=["Risk Management"])

# MongoDB client
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["maveretta"]
risk_config_collection = db["risk_config"]

# Default risk config
DEFAULT_RISK_CONFIG = {
    "max_exposure_pct": 50,
    "max_loss_per_trade_pct": 2.0,
    "max_daily_loss_pct": 5.0,
    "max_open_positions": 5,
    "trailing_stop_enabled": True,
    "trailing_stop_pct": 2.0,
    "min_confidence_pct": 70
}

@router.get("/config")
async def get_risk_config() -> Dict[str, Any]:
    """
    Retorna a configuração de risco atual
    """
    try:
        # Buscar config no MongoDB
        config = await risk_config_collection.find_one({"_id": "default"})

        if not config:
            # Se não existe, retorna default
            return DEFAULT_RISK_CONFIG

        # Remove _id do retorno
        config.pop("_id", None)

        return config

    except Exception as e:
        logger.error(f"Error fetching risk config: {e}")
        return DEFAULT_RISK_CONFIG

@router.post("/config")
async def save_risk_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Salva a nova configuração de risco
    """
    try:
        # Validar campos obrigatórios
        required_fields = [
            "max_exposure_pct", "max_loss_per_trade_pct",
            "max_daily_loss_pct", "max_open_positions",
            "trailing_stop_enabled", "trailing_stop_pct",
            "min_confidence_pct"
        ]

        for field in required_fields:
            if field not in config:
                raise HTTPException(400, f"Campo obrigatório ausente: {field}")

        # Adicionar timestamp
        config["updated_at"] = datetime.utcnow()
        config["_id"] = "default"

        # Salvar no MongoDB (upsert)
        await risk_config_collection.replace_one(
            {"_id": "default"},
            config,
            upsert=True
        )

        logger.info("Risk config saved successfully")

        return {
            "status": "ok",
            "message": "Configuração de risco salva com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving risk config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
