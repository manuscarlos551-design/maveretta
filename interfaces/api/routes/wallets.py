# interfaces/api/routes/wallets.py
"""
Wallet Routes - Gestão de carteiras e saldos
"""
import logging
import os
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import requests
import ccxt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Wallets"])

# Cache simples para cotações (evitar muitas requests)
_price_cache = {}
_cache_timestamp = 0
CACHE_TTL = 60  # 60 segundos

def _get_usd_brl_rate() -> float:
    """Obtém cotação USD/BRL via API pública"""
    global _price_cache, _cache_timestamp
    
    current_time = time.time()
    if 'usd_brl' in _price_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _price_cache['usd_brl']
    
    try:
        # Tentar CoinGecko primeiro
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        if coingecko_key:
            headers = {'x-cg-demo-api-key': coingecko_key}
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=usd&vs_currencies=brl',
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                rate = data.get('usd', {}).get('brl')
                if rate:
                    _price_cache['usd_brl'] = rate
                    _cache_timestamp = current_time
                    return rate
        
        # Fallback: API pública sem chave
        response = requests.get(
            'https://api.exchangerate-api.com/v4/latest/USD',
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            rate = data.get('rates', {}).get('BRL')
            if rate:
                _price_cache['usd_brl'] = rate
                _cache_timestamp = current_time
                return rate
        
        # Fallback final: taxa padrão
        return 5.50
        
    except Exception as e:
        logger.warning(f"Erro ao obter cotação USD/BRL: {e}")
        return 5.50

def _get_crypto_prices() -> Dict[str, float]:
    """Obtém preços de criptomoedas principais em USD"""
    global _price_cache, _cache_timestamp
    
    current_time = time.time()
    if 'crypto_prices' in _price_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _price_cache['crypto_prices']
    
    try:
        # Lista de moedas principais para conversão
        coins = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana']
        
        coingecko_key = os.getenv('COINGECKO_API_KEY')
        headers = {}
        if coingecko_key:
            headers = {'x-cg-demo-api-key': coingecko_key}
        
        response = requests.get(
            f'https://api.coingecko.com/api/v3/simple/price?ids={",".join(coins)}&vs_currencies=usd',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Mapear para símbolos conhecidos
            price_map = {}
            symbol_mapping = {
                'bitcoin': 'BTC',
                'ethereum': 'ETH', 
                'binancecoin': 'BNB',
                'cardano': 'ADA',
                'solana': 'SOL'
            }
            
            for coin_id, coin_data in data.items():
                if coin_id in symbol_mapping:
                    symbol = symbol_mapping[coin_id]
                    price_map[symbol] = coin_data.get('usd', 0)
            
            _price_cache['crypto_prices'] = price_map
            _cache_timestamp = current_time
            return price_map
        
        return {}
        
    except Exception as e:
        logger.warning(f"Erro ao obter preços de crypto: {e}")
        return {}

def _create_exchange_instance(exchange_id: str) -> ccxt.Exchange:
    """Cria instância da exchange (reuso do exchanges.py)"""
    exchange_configs = {
        'binance': {'class': ccxt.binance, 'api_key': 'BINANCE_API_KEY', 'secret': 'BINANCE_API_SECRET'},
        'kucoin': {'class': ccxt.kucoin, 'api_key': 'KUCOIN_API_KEY', 'secret': 'KUCOIN_API_SECRET', 'passphrase': 'KUCOIN_API_PASSPHRASE'},
        'bybit': {'class': ccxt.bybit, 'api_key': 'BYBIT_API_KEY', 'secret': 'BYBIT_API_SECRET'},
        'okx': {'class': ccxt.okx, 'api_key': 'OKX_API_KEY', 'secret': 'OKX_API_SECRET', 'passphrase': 'OKX_API_PASSPHRASE'}
    }
    
    if exchange_id not in exchange_configs:
        raise ValueError(f"Exchange {exchange_id} não suportada")
    
    config = exchange_configs[exchange_id]
    api_key = os.getenv(config['api_key'])
    secret = os.getenv(config['secret'])
    
    if not api_key or not secret:
        raise ValueError(f"Credenciais da {exchange_id} não configuradas")
    
    exchange_params = {
        'apiKey': api_key,
        'secret': secret,
        'sandbox': False,
        'enableRateLimit': True
    }
    
    if 'passphrase' in config:
        passphrase = os.getenv(config['passphrase'])
        if passphrase:
            exchange_params['password'] = passphrase
    
    return config['class'](exchange_params)

@router.get("/wallet/summary")
async def get_wallet_summary() -> Dict[str, Any]:
    """
    Resumo da carteira agregando todas as exchanges
    Converte tudo para USD e BRL
    """
    try:
        # Obter cotações
        usd_brl_rate = _get_usd_brl_rate()
        crypto_prices = _get_crypto_prices()
        
        exchanges_data = []
        total_usd = 0.0
        
        # Lista de exchanges para verificar
        supported_exchanges = ['binance', 'kucoin', 'bybit', 'okx']
        
        for exchange_id in supported_exchanges:
            try:
                exchange = _create_exchange_instance(exchange_id)
                
                # Obter saldos
                balance_data = await exchange.fetch_balance()
                
                exchange_usd = 0.0
                assets = {}
                
                for asset, balance in balance_data.items():
                    if not isinstance(balance, dict):
                        continue
                    
                    total_balance = balance.get('total', 0)
                    if total_balance <= 0:
                        continue
                    
                    # Converter para USD
                    asset_usd = 0.0
                    if asset == 'USDT' or asset == 'USD':
                        asset_usd = total_balance
                    elif asset in crypto_prices:
                        asset_usd = total_balance * crypto_prices[asset]
                    else:
                        # Para assets não conhecidos, tentar buscar preço via exchange
                        try:
                            if f"{asset}/USDT" in exchange.markets:
                                ticker = await exchange.fetch_ticker(f"{asset}/USDT")
                                asset_usd = total_balance * ticker['last']
                        except:
                            pass
                    
                    if asset_usd > 0.01:  # Só incluir se valor > $0.01
                        assets[asset] = {
                            'amount': total_balance,
                            'usd_value': asset_usd
                        }
                        exchange_usd += asset_usd
                
                if exchange_usd > 0:
                    exchanges_data.append({
                        'id': exchange_id,
                        'total_usd': exchange_usd,
                        'total_brl': exchange_usd * usd_brl_rate,
                        'assets': assets,
                        'status': 'connected'
                    })
                    total_usd += exchange_usd
                
            except Exception as e:
                logger.warning(f"Erro ao processar carteira da {exchange_id}: {e}")
                # Incluir exchange com erro na lista
                exchanges_data.append({
                    'id': exchange_id,
                    'total_usd': 0,
                    'total_brl': 0,
                    'assets': {},
                    'status': 'error',
                    'error': str(e)
                })
        
        # Verificar se temos chave para cotação
        has_price_api = bool(os.getenv('COINGECKO_API_KEY'))
        
        return {
            'total_usd': total_usd,
            'total_brl': total_usd * usd_brl_rate,
            'usd_brl_rate': usd_brl_rate,
            'by_exchange': exchanges_data,
            'price_source': 'coingecko' if has_price_api else 'fallback',
            'last_updated': time.time(),
            'warning': None if has_price_api else 'COINGECKO_API_KEY não configurado - usando cotações aproximadas'
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter resumo da carteira: {e}")
        
        # Retornar estrutura básica mesmo com erro
        return {
            'total_usd': 0,
            'total_brl': 0,
            'usd_brl_rate': 5.50,
            'by_exchange': [],
            'price_source': 'unavailable',
            'last_updated': time.time(),
            'error': str(e)
        }