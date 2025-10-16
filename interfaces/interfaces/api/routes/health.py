# interfaces/api/routes/health.py
"""
Health Check Routes - Sistema de saúde do Maveretta Bot
Verifica conectividade com serviços essenciais
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import redis
import pymongo
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check completo do sistema
    Verifica Redis, MongoDB e serviços core
    """
    try:
        start_time = time.time()
        
        health_status = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "response_time_ms": 0
        }
        
        # Verificar Redis
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
            health_status["services"]["redis"] = {
                "status": "ok",
                "url": redis_url.split('@')[-1] if '@' in redis_url else redis_url
            }
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            health_status["services"]["redis"] = {
                "status": "down", 
                "error": str(e)
            }
        
        # Verificar MongoDB
        try:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/botai_trading")
            mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
            mongo_client.server_info()
            health_status["services"]["mongodb"] = {
                "status": "ok",
                "database": os.getenv("MONGO_DATABASE", "botai_trading")
            }
        except Exception as e:
            logger.warning(f"MongoDB health check failed: {e}")
            health_status["services"]["mongodb"] = {
                "status": "down",
                "error": str(e)
            }
        
        # Verificar se algum serviço está down
        services_down = [svc for svc, data in health_status["services"].items() 
                        if data["status"] == "down"]
        
        if services_down:
            health_status["status"] = "degraded"
            health_status["degraded_services"] = services_down
        
        # Tempo de resposta
        health_status["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check critical error: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")