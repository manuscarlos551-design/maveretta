# interfaces/api/routes/exchanges.py
"""
Exchange Routes - Gerenciamento de Exchanges
"""
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path
import ccxt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Exchanges"])

# Configuração de exchanges suportadas
SUPPORTED_EXCHANGES = {
    'binance': {
        'class': ccxt.binance,
        'api_key_env': 'BINANCE_API_KEY', 
        'secret_env': 'BINANCE_API_SECRET',
        'testnet_env': 'BINANCE_TESTNET'
    },
    'kucoin': {
        'class': ccxt.kucoin,
        'api_key_env': 'KUCOIN_API_KEY',
        'secret_env': 'KUCOIN_API_SECRET', 
        'passphrase_env': 'KUCOIN_API_PASSPHRASE'
    },
    'bybit': {
        'class': ccxt.bybit,
        'api_key_env': 'BYBIT_API_KEY',
        'secret_env': 'BYBIT_API_SECRET',
        'testnet_env': 'BYBIT_TESTNET'
    },
    'okx': {
        'class': ccxt.okx,
        'api_key_env': 'OKX_API_KEY', 
        'secret_env': 'OKX_API_SECRET',
        'passphrase_env': 'OKX_API_PASSPHRASE'
    }
}

def _create_exchange_instance(exchange_id: str) -> ccxt.Exchange:
    """Cria instância da exchange com credenciais das envs"""
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Exchange {exchange_id} não suportada")
    
    config = SUPPORTED_EXCHANGES[exchange_id]
    api_key = os.getenv(config['api_key_env'])
    secret = os.getenv(config['secret_env'])
    
    if not api_key or not secret:
        raise ValueError(f"Credenciais da {exchange_id} não configuradas")
    
    exchange_params = {
        'apiKey': api_key,
        'secret': secret,
        'sandbox': False,
        'enableRateLimit': True
    }
    
    # Adicionar passphrase se necessário
    if 'passphrase_env' in config:
        passphrase = os.getenv(config['passphrase_env'])
        if passphrase:
            exchange_params['password'] = passphrase
    
    # Verificar testnet
    if 'testnet_env' in config:
        testnet = os.getenv(config['testnet_env'], 'false').lower() == 'true'
        exchange_params['sandbox'] = testnet
    
    return config['class'](exchange_params)

@router.get("/exchanges")
async def get_exchanges() -> Dict[str, Any]:
    """
    Lista exchanges habilitadas com status
    """
    try:
        exchanges_info = []
        
        for exchange_id in SUPPORTED_EXCHANGES.keys():
            try:
                # Verificar se tem credenciais
                config = SUPPORTED_EXCHANGES[exchange_id]
                api_key = os.getenv(config['api_key_env'])
                secret = os.getenv(config['secret_env'])
                
                if not api_key or not secret:
                    exchanges_info.append({
                        "id": exchange_id,
                        "status": "RED",
                        "error": "Credenciais não configuradas",
                        "account_mode": "unknown"
                    })
                    continue
                
                # Tentar conectar
                exchange = _create_exchange_instance(exchange_id)
                start_time = time.time()
                
                # Teste básico de conectividade
                await exchange.load_markets()
                latency_ms = int((time.time() - start_time) * 1000)
                
                exchanges_info.append({
                    "id": exchange_id,
                    "status": "GREEN",
                    "latency_ms": latency_ms,
                    "account_mode": "sandbox" if exchange.sandbox else "live"
                })
                
            except Exception as e:
                logger.warning(f"Erro ao verificar exchange {exchange_id}: {e}")
                exchanges_info.append({
                    "id": exchange_id,
                    "status": "RED", 
                    "error": str(e),
                    "account_mode": "unknown"
                })
        
        return {"exchanges": exchanges_info}
        
    except Exception as e:
        logger.error(f"Erro ao listar exchanges: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar exchanges: {str(e)}")

@router.get("/exchanges/{exchange_id}/status")
async def get_exchange_status(exchange_id: str = Path(..., description="ID da exchange")) -> Dict[str, Any]:
    """
    Status detalhado de uma exchange específica
    """
    try:
        if exchange_id not in SUPPORTED_EXCHANGES:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} não suportada")
        
        exchange = _create_exchange_instance(exchange_id)
        
        # Carregar mercados
        markets = await exchange.load_markets()
        
        # Obter saldos (se possível)
        balances = {}
        try:
            balance_data = await exchange.fetch_balance()
            balances = {
                asset: {
                    "free": balance["free"],
                    "used": balance["used"], 
                    "total": balance["total"]
                }
                for asset, balance in balance_data.items()
                if isinstance(balance, dict) and balance.get("total", 0) > 0
            }
        except Exception as e:
            logger.warning(f"Não foi possível obter saldos da {exchange_id}: {e}")
        
        # Informações de rate limit
        rate_limits = {}
        if hasattr(exchange, 'rateLimit'):
            rate_limits = {
                "rate_limit_ms": exchange.rateLimit,
                "enable_rate_limit": exchange.enableRateLimit
            }
        
        # Símbolos principais
        main_symbols = []
        if markets:
            # Pegar alguns símbolos principais
            for symbol in ["BTC/USDT", "ETH/USDT", "BNB/USDT"]:
                if symbol in markets:
                    main_symbols.append(symbol)
        
        return {
            "id": exchange_id,
            "status": "GREEN",
            "balances": balances,
            "symbols": main_symbols[:10],  # Limitar para não sobrecarregar
            "total_markets": len(markets) if markets else 0,
            "rate_limits": rate_limits,
            "account_mode": "sandbox" if exchange.sandbox else "live",
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao obter status da exchange {exchange_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter status: {str(e)}")