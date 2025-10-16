from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from bson import ObjectId

# Importar cliente MongoDB
from core.db.db_client import db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Alerts"])

@router.get("/alerts")
async def get_alerts(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista alertas do sistema
    """
    try:
        query = {}
        if status:
            query["status"] = status
        if severity:
            query["severity"] = severity
        
        alerts = await db_client.db.alerts.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        for alert in alerts:
            alert["id"] = str(alert["_id"])
            if "_id" in alert: del alert["_id"]
            if "timestamp" in alert and isinstance(alert["timestamp"], datetime):
                alert["timestamp"] = alert["timestamp"].isoformat() + "Z"

        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    """
    Reconhece um alerta, alterando seu status para 'acknowledged'.
    """
    try:
        update_result = await db_client.db.alerts.update_one(
            {"_id": ObjectId(alert_id), "status": "active"},
            {"$set": {"status": "acknowledged", "acknowledged_at": datetime.utcnow()}}
        )
        
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Alerta não encontrado ou já reconhecido/resolvido")
        
        logger.info(f"Alerta {alert_id} reconhecido via API")
        return {"status": "ok", "message": f"Alerta {alert_id} reconhecido com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao reconhecer alerta {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str) -> Dict[str, Any]:
    """
    Deleta um alerta do sistema.
    """
    try:
        delete_result = await db_client.db.alerts.delete_one({"_id": ObjectId(alert_id)})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Alerta não encontrado")
        
        logger.info(f"Alerta {alert_id} deletado via API")
        return {"status": "ok", "message": f"Alerta {alert_id} deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar alerta {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

