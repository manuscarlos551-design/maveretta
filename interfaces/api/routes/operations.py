# interfaces/api/routes/operations.py
"""
Operations Routes - Gerenciamento de operações (trades)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
import redis

from ..models.operation import Operation, OperationStatus, OperationSide

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["Operations"])

# MongoDB client
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["maveretta"]
operations_collection = db["operations"]


@router.get("", response_model=List[Operation])
async def get_operations(
    limit: int = Query(50, ge=1, le=500, description="Número máximo de operações"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    exchange: Optional[str] = Query(None, description="Filtrar por exchange"),
    symbol: Optional[str] = Query(None, description="Filtrar por par"),
    start_date: Optional[str] = Query(None, description="Data inicial (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Data final (ISO 8601)")
):
    """
    Lista operações do sistema
    
    Retorna todas as operações (trades) executadas pelo bot, com filtros opcionais.
    """
    try:
        # Construir query
        query = {}
        
        if status:
            # Validar status
            if status.lower() not in [s.value for s in OperationStatus]:
                raise HTTPException(400, f"Status inválido. Use um dos seguintes: {[s.value for s in OperationStatus]}")
            query["status"] = status.lower()
        
        if exchange:
            query["exchange"] = exchange.lower()
        
        if symbol:
            query["symbol"] = symbol.upper()
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    date_query["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(400, "Formato de data inicial inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).")
            if end_date:
                try:
                    date_query["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(400, "Formato de data final inválido. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).")
            query["opened_at"] = date_query
        
        # Buscar no MongoDB
        cursor = operations_collection.find(query).sort("opened_at", -1).skip(offset).limit(limit)
        operations = await cursor.to_list(length=limit)
        
        # Converter _id para string e datetime para ISO format
        serialized_operations = []
        for op in operations:
            op["_id"] = str(op["_id"])
            if isinstance(op.get("opened_at"), datetime):
                op["opened_at"] = op["opened_at"].isoformat() + "Z"
            if op.get("closed_at") and isinstance(op["closed_at"], datetime):
                op["closed_at"] = op["closed_at"].isoformat() + "Z"
            serialized_operations.append(op)
        
        return {"operations": serialized_operations, "total": len(serialized_operations)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{operation_id}", response_model=Operation)
async def get_operation_detail(operation_id: str):
    """
    Detalhes de uma operação específica
    """
    try:
        operation = await operations_collection.find_one({"id": operation_id})
        
        if not operation:
            raise HTTPException(status_code=404, detail="Operação não encontrada")
        
        # Serializar datetime para ISO format
        if isinstance(operation.get("opened_at"), datetime):
            operation["opened_at"] = operation["opened_at"].isoformat() + "Z"
        if operation.get("closed_at") and isinstance(operation["closed_at"], datetime):
            operation["closed_at"] = operation["closed_at"].isoformat() + "Z"
        
        return operation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching operation {operation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{operation_id}/close")
async def force_close_operation(operation_id: str):
    """
    Força o fechamento de uma operação aberta
    
    Envia comando para o bot fechar a posição imediatamente.
    """
    try:
        # Buscar operação
        operation = await operations_collection.find_one({"id": operation_id})
        
        if not operation:
            raise HTTPException(status_code=404, detail="Operação não encontrada")
        
        if operation["status"] != "open":
            return {
                "status": "warning",
                "message": f"Operação já está {operation['status']}"
            }
        
        # Enviar comando via Redis para fechar
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.publish("bot:commands", f"CLOSE_OPERATION:{operation_id}")
        
        logger.warning(f"Force close requested for operation {operation_id}")
        
        return {
            "status": "ok",
            "message": f"Comando de fechamento enviado para operação {operation_id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing operation {operation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_operations_summary():
    """
    Resumo estatístico das operações
    """
    try:
        # Total de operações
        total = await operations_collection.count_documents({})
        
        # Operações abertas
        open_ops = await operations_collection.count_documents({"status": "open"})
        
        # Operações fechadas
        closed_ops = await operations_collection.count_documents({"status": "closed"})
        
        # P&L total e métricas de trades vencedores/perdedores
        pipeline = [
            {"$match": {"status": "closed", "pnl": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": None,
                "total_pnl": {"$sum": "$pnl"},
                "avg_pnl": {"$avg": "$pnl"},
                "winning_trades": {
                    "$sum": {"$cond": [{"$gt": ["$pnl", 0]}, 1, 0]}
                },
                "losing_trades": {
                    "$sum": {"$cond": [{"$lt": ["$pnl", 0]}, 1, 0]}
                },
                "zero_pnl_trades": {
                    "$sum": {"$cond": [{"$eq": ["$pnl", 0]}, 1, 0]}
                }
            }}
        ]
        
        result = await operations_collection.aggregate(pipeline).to_list(1)
        stats = result[0] if result else {}
        
        winning_trades = stats.get("winning_trades", 0)
        losing_trades = stats.get("losing_trades", 0)
        zero_pnl_trades = stats.get("zero_pnl_trades", 0)
        
        total_closed_with_pnl = winning_trades + losing_trades + zero_pnl_trades
        
        win_rate = 0.0
        if total_closed_with_pnl > 0:
            win_rate = (winning_trades / total_closed_with_pnl) * 100
        
        return {
            "total_operations": total,
            "open": open_ops,
            "closed": closed_ops,
            "total_pnl": round(stats.get("total_pnl", 0), 2),
            "avg_pnl": round(stats.get("avg_pnl", 0), 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "zero_pnl_trades": zero_pnl_trades,
            "win_rate": round(win_rate, 2)
        }
    
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
