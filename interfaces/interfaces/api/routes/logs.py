# interfaces/api/routes/logs.py
"""
Logs Routes - Consulta e exportação de logs do sistema
"""
import logging
import json
import csv
import io
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Logs"])


class LogExportRequest(BaseModel):
    """Request para exportação de logs"""
    collection: str = Field(..., description="Nome da coleção MongoDB")
    from_date: Optional[str] = Field(None, alias="from", description="Data início ISO 8601")
    to_date: Optional[str] = Field(None, alias="to", description="Data fim ISO 8601")
    format: str = Field("json", description="Formato de exportação: json ou csv")
    limit: int = Field(50000, ge=1, le=100000, description="Limite de documentos")


def _get_mongo_client():
    """Obtém cliente MongoDB"""
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
        db_name = os.getenv("MONGO_DB", "botai_trading")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        return client[db_name]
    except Exception as e:
        logger.error(f"Erro ao conectar MongoDB: {e}")
        return None


@router.post("/logs/export")
async def export_logs(request: LogExportRequest):
    """
    Exporta logs/auditoria do MongoDB em JSON ou CSV
    
    Coleções válidas:
    - system_logs
    - audit_logs
    - agent_decisions
    - agent_consensus
    - agent_dialogs
    """
    try:
        # Validar coleção
        valid_collections = [
            "system_logs", 
            "audit_logs", 
            "agent_decisions", 
            "agent_consensus", 
            "agent_dialogs"
        ]
        
        if request.collection not in valid_collections:
            return Response(
                content=json.dumps({
                    "error": "invalid_collection",
                    "details": f"Coleção deve ser uma de: {', '.join(valid_collections)}"
                }),
                media_type="application/json",
                status_code=200
            )
        
        # Conectar MongoDB
        db = _get_mongo_client()
        if not db:
            return Response(
                content=json.dumps({
                    "error": "database_unavailable",
                    "details": "Não foi possível conectar ao MongoDB"
                }),
                media_type="application/json",
                status_code=200
            )
        
        # Construir filtro de data
        query = {}
        if request.from_date or request.to_date:
            query["timestamp"] = {}
            if request.from_date:
                try:
                    from_dt = datetime.fromisoformat(request.from_date.replace('Z', '+00:00'))
                    query["timestamp"]["$gte"] = from_dt
                except ValueError:
                    return Response(
                        content=json.dumps({
                            "error": "invalid_date_format",
                            "details": "Data 'from' inválida. Use formato ISO 8601"
                        }),
                        media_type="application/json",
                        status_code=200
                    )
            
            if request.to_date:
                try:
                    to_dt = datetime.fromisoformat(request.to_date.replace('Z', '+00:00'))
                    query["timestamp"]["$lte"] = to_dt
                except ValueError:
                    return Response(
                        content=json.dumps({
                            "error": "invalid_date_format",
                            "details": "Data 'to' inválida. Use formato ISO 8601"
                        }),
                        media_type="application/json",
                        status_code=200
                    )
        
        # Buscar dados
        try:
            collection = db[request.collection]
            cursor = collection.find(query).sort("timestamp", -1).limit(request.limit)
            documents = list(cursor)
            
            # Converter ObjectId para string
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                # Converter datetime para ISO string
                for key, value in doc.items():
                    if isinstance(value, datetime):
                        doc[key] = value.isoformat()
            
            # Retornar no formato solicitado
            if request.format.lower() == "csv":
                if not documents:
                    return Response(
                        content="",
                        media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={request.collection}.csv"}
                    )
                
                # Gerar CSV
                output = io.StringIO()
                if documents:
                    keys = documents[0].keys()
                    writer = csv.DictWriter(output, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(documents)
                
                csv_content = output.getvalue()
                return Response(
                    content=csv_content,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename={request.collection}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    }
                )
            else:
                # Retornar JSON
                return Response(
                    content=json.dumps({
                        "collection": request.collection,
                        "count": len(documents),
                        "data": documents,
                        "exported_at": datetime.now().isoformat()
                    }, indent=2),
                    media_type="application/json"
                )
        
        except PyMongoError as e:
            logger.error(f"Erro ao buscar dados do MongoDB: {e}")
            return Response(
                content=json.dumps({
                    "error": "query_failed",
                    "details": str(e)
                }),
                media_type="application/json",
                status_code=200
            )
    
    except Exception as e:
        logger.error(f"Erro na exportação de logs: {e}")
        return Response(
            content=json.dumps({
                "error": "export_failed",
                "details": str(e)
            }),
            media_type="application/json",
            status_code=200
        )
