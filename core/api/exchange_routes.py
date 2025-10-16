#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exchange API Routes - Endpoints para gerenciamento de exchanges
Fornece dados reais das 5 exchanges conectadas
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.exchanges.multi_exchange_manager import MultiExchangeManager

logger = logging.getLogger(__name__)

# Inicializar router
router = APIRouter(prefix="/exchanges", tags=["exchanges"])

# Instância global do exchange manager
exchange_manager = None


def get_exchange_manager() -> MultiExchangeManager:
    """Retorna instância singleton do exchange manager"""
    global exchange_manager
    if exchange_manager is None:
        exchange_manager = MultiExchangeManager()
    return exchange_manager


@router.get("/health")
async def get_exchanges_health():
    """
    Verifica saúde de todas as exchanges
    
    Returns:
        Dict com status de cada exchange
    """
    try:
        manager = get_exchange_manager()
        health = manager.health_check()
        
        # Adicionar resumo
        total = len(health)
        online = sum(1 for v in health.values() if v.get('status') == 'online')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": total,
                "online": online,
                "offline": total - online
            },
            "exchanges": health
        }
    except Exception as e:
        logger.error(f"Erro ao buscar health das exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_exchanges():
    """
    Lista exchanges ativas (com credenciais configuradas)
    
    Returns:
        Lista de nomes de exchanges ativas
    """
    try:
        manager = get_exchange_manager()
        active = manager.get_active_exchanges()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(active),
            "exchanges": active
        }
    except Exception as e:
        logger.error(f"Erro ao buscar exchanges ativas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances")
async def get_all_balances():
    """
    Obtém saldos de todas as exchanges ativas
    
    Returns:
        Dict com saldos de cada exchange
    """
    try:
        manager = get_exchange_manager()
        balances = manager.get_all_balances()
        
        # Calcular total geral
        total_usd = sum(
            b.get('total_usd', 0) 
            for b in balances.values() 
            if isinstance(b, dict) and 'total_usd' in b
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_usd": round(total_usd, 2),
            "exchanges": balances
        }
    except Exception as e:
        logger.error(f"Erro ao buscar saldos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{exchange_name}/balance")
async def get_exchange_balance(exchange_name: str):
    """
    Obtém saldo de uma exchange específica
    
    Args:
        exchange_name: Nome da exchange (binance, kucoin, bybit, coinbase, okx)
    """
    try:
        manager = get_exchange_manager()
        balance = manager.get_balance(exchange_name.lower())
        
        if 'error' in balance:
            raise HTTPException(status_code=400, detail=balance['error'])
        
        return balance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar saldo de {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{exchange_name}/ticker/{symbol}")
async def get_ticker(exchange_name: str, symbol: str):
    """
    Obtém ticker de um símbolo em uma exchange
    
    Args:
        exchange_name: Nome da exchange
        symbol: Símbolo (ex: BTC/USDT)
    """
    try:
        manager = get_exchange_manager()
        ticker = manager.get_ticker(exchange_name.lower(), symbol)
        
        if 'error' in ticker:
            raise HTTPException(status_code=400, detail=ticker['error'])
        
        return ticker
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar ticker {symbol} de {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{exchange_name}/markets")
async def get_markets(exchange_name: str):
    """
    Lista mercados disponíveis em uma exchange
    
    Args:
        exchange_name: Nome da exchange
    """
    try:
        manager = get_exchange_manager()
        markets = manager.get_markets(exchange_name.lower())
        
        return {
            "exchange": exchange_name.lower(),
            "count": len(markets),
            "markets": markets
        }
    except Exception as e:
        logger.error(f"Erro ao buscar mercados de {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{exchange_name}/orders")
async def get_open_orders(
    exchange_name: str,
    symbol: Optional[str] = Query(None, description="Filtrar por símbolo")
):
    """
    Obtém ordens abertas de uma exchange
    
    Args:
        exchange_name: Nome da exchange
        symbol: Símbolo opcional para filtrar
    """
    try:
        manager = get_exchange_manager()
        orders = manager.get_open_orders(exchange_name.lower(), symbol)
        
        return {
            "exchange": exchange_name.lower(),
            "symbol": symbol,
            "count": len(orders),
            "orders": orders
        }
    except Exception as e:
        logger.error(f"Erro ao buscar ordens de {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{exchange_name}/order")
async def create_order(
    exchange_name: str,
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: Optional[float] = None
):
    """
    Cria uma ordem em uma exchange
    
    Args:
        exchange_name: Nome da exchange
        symbol: Par de trading (ex: BTC/USDT)
        side: 'buy' ou 'sell'
        order_type: 'market' ou 'limit'
        amount: Quantidade
        price: Preço (obrigatório para limit orders)
    """
    try:
        # Validações
        if side not in ['buy', 'sell']:
            raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")
        
        if order_type not in ['market', 'limit']:
            raise HTTPException(status_code=400, detail="Order type must be 'market' or 'limit'")
        
        if order_type == 'limit' and price is None:
            raise HTTPException(status_code=400, detail="Price is required for limit orders")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        manager = get_exchange_manager()
        result = manager.create_order(
            exchange_name.lower(),
            symbol,
            order_type,
            side,
            amount,
            price
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar ordem em {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{exchange_name}/order/{order_id}")
async def cancel_order(
    exchange_name: str,
    order_id: str,
    symbol: str = Query(..., description="Símbolo da ordem")
):
    """
    Cancela uma ordem específica
    
    Args:
        exchange_name: Nome da exchange
        order_id: ID da ordem
        symbol: Símbolo da ordem
    """
    try:
        manager = get_exchange_manager()
        result = manager.cancel_order(exchange_name.lower(), order_id, symbol)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar ordem em {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
