# interfaces/api/routes/rates.py
"""
Rates Routes - Cotações de moedas em tempo real
"""
import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
import requests
import redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Rates"])

# Configuração Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = 300  # 5 minutos
CACHE_KEY = "rates:usdbrl"


def _get_redis_client():
    """Obtém cliente Redis"""
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis não disponível: {e}")
        return None


def _fetch_rate_from_api() -> Optional[Dict[str, Any]]:
    """Busca cotação da API externa"""
    try:
        # Tentar exchangerate.host (API gratuita, sem key necessária)
        url = "https://api.exchangerate.host/latest?base=USD&symbols=BRL"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "rates" in data and "BRL" in data["rates"]:
                rate = data["rates"]["BRL"]
                return {
                    "pair": "USD/BRL",
                    "rate": float(rate),
                    "ts": datetime.now().isoformat(),
                    "stale": False,
                    "source": "exchangerate.host"
                }
        
        logger.warning(f"API exchangerate.host retornou status {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar cotação da API: {e}")
    
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar cotação: {e}")
    
    return None


@router.get("/rates/usdbrl")
async def get_usdbrl_rate():
    """
    Retorna cotação USD→BRL em tempo real
    
    Comportamento:
    1. Tenta cache Redis (TTL 5min)
    2. Se cache vazio, consulta exchangerate.host
    3. Se API falhar, retorna último valor do cache com flag stale=true
    4. Se nada disponível, retorna erro
    
    Resposta:
    {
        "pair": "USD/BRL",
        "rate": 5.12,
        "ts": "2025-10-11T23:00:00Z",
        "stale": false
    }
    """
    redis_client = _get_redis_client()
    
    # 1. Tentar cache
    if redis_client:
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                cache_data = json.loads(cached)
                cache_age = datetime.now() - datetime.fromisoformat(cache_data["ts"])
                
                # Se cache ainda válido (< 5min), retornar
                if cache_age < timedelta(seconds=CACHE_TTL):
                    logger.info("Retornando cotação do cache Redis (válido)")
                    return cache_data
                
                logger.info("Cache Redis expirado, buscando nova cotação")
        except Exception as e:
            logger.warning(f"Erro ao ler cache Redis: {e}")
    
    # 2. Buscar da API
    fresh_data = _fetch_rate_from_api()
    
    if fresh_data:
        # Salvar no cache
        if redis_client:
            try:
                redis_client.setex(
                    CACHE_KEY,
                    CACHE_TTL,
                    json.dumps(fresh_data)
                )
                logger.info("Cotação atualizada e salva no cache")
            except Exception as e:
                logger.warning(f"Erro ao salvar no cache Redis: {e}")
        
        return fresh_data
    
    # 3. Se API falhou, tentar retornar cache stale
    if redis_client:
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                cache_data = json.loads(cached)
                cache_data["stale"] = True
                logger.warning("API falhou, retornando cotação stale do cache")
                return cache_data
        except Exception as e:
            logger.error(f"Erro ao ler cache stale: {e}")
    
    # 4. Nada disponível
    logger.error("Nenhuma cotação disponível (API e cache falharam)")
    return {
        "error": "rate_unavailable",
        "details": "Não foi possível obter cotação USD/BRL (API e cache indisponíveis)",
        "pair": "USD/BRL",
        "ts": datetime.now().isoformat()
    }
