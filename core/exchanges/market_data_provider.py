"""
Provider de Dados de Mercado
Busca dados em tempo real das exchanges via CCXT
"""
import ccxt
import os
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache de exchanges
_exchanges = {}

def get_exchange(exchange_name: str):
    """Obtém instância do CCXT para a exchange"""
    if exchange_name not in _exchanges:
        try:
            exchange_class = getattr(ccxt, exchange_name.lower())
            
            config = {
                "apiKey": os.getenv(f"{exchange_name.upper()}_API_KEY"),
                "secret": os.getenv(f"{exchange_name.upper()}_API_SECRET"),
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            }
            
            # Configurações específicas por exchange
            if exchange_name.lower() == "kucoin":
                config["password"] = os.getenv("KUCOIN_API_PASSPHRASE", "")
            elif exchange_name.lower() == "okx":
                config["password"] = os.getenv("OKX_API_PASSPHRASE", "")
            
            _exchanges[exchange_name] = exchange_class(config)
            logger.info(f"✅ Exchange {exchange_name} conectada")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar {exchange_name}: {e}")
            return None
    
    return _exchanges[exchange_name]


async def get_market_data(symbols: List[str], exchange_name: str = "binance") -> Dict[str, Any]:
    """
    Busca dados de mercado para uma lista de símbolos
    
    Args:
        symbols: Lista de símbolos (ex: ["BTC/USDT", "ETH/USDT"])
        exchange_name: Nome da exchange (padrão: binance)
    
    Returns:
        Dict com dados de mercado por símbolo
    """
    try:
        exchange = get_exchange(exchange_name)
        
        if not exchange:
            logger.error(f"❌ Exchange {exchange_name} não disponível")
            return {}
        
        market_data = {}
        
        for symbol in symbols:
            try:
                # Busca ticker (preço atual, volume, etc)
                ticker = exchange.fetch_ticker(symbol)
                
                # Busca order book (bid/ask)
                order_book = exchange.fetch_order_book(symbol, limit=10)
                
                # Busca trades recentes
                trades = exchange.fetch_trades(symbol, limit=50)
                
                # Busca OHLCV (candles) - últimas 100 velas de 1m
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
                
                market_data[symbol] = {
                    "symbol": symbol,
                    "exchange": exchange_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "price": ticker.get("last"),
                    "bid": ticker.get("bid"),
                    "ask": ticker.get("ask"),
                    "volume_24h": ticker.get("quoteVolume"),
                    "high_24h": ticker.get("high"),
                    "low_24h": ticker.get("low"),
                    "change_24h_pct": ticker.get("percentage"),
                    "order_book": {
                        "bids": order_book.get("bids", [])[:5],  # Top 5 bids
                        "asks": order_book.get("asks", [])[:5]   # Top 5 asks
                    },
                    "recent_trades": [
                        {
                            "price": t.get("price"),
                            "amount": t.get("amount"),
                            "side": t.get("side"),
                            "timestamp": t.get("timestamp")
                        }
                        for t in trades[:10]  # Últimos 10 trades
                    ],
                    "ohlcv": ohlcv  # [[timestamp, open, high, low, close, volume], ...]
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar dados de {symbol}: {e}")
                continue
        
        logger.info(f"📊 Dados de mercado obtidos para {len(market_data)} símbolos")
        return market_data
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados de mercado: {e}")
        return {}


async def get_total_equity() -> float:
    """
    Calcula equity total somando saldos de todas as exchanges
    
    Returns:
        Equity total em USD
    """
    try:
        total_equity = 0.0
        
        exchanges_to_check = ["binance", "kucoin", "bybit", "coinbase", "okx"]
        
        for exchange_name in exchanges_to_check:
            try:
                exchange = get_exchange(exchange_name)
                
                if not exchange:
                    continue
                
                balance = exchange.fetch_balance()
                
                # Soma USDT/USD livres
                if "USDT" in balance.get("free", {}):
                    total_equity += balance["free"]["USDT"]
                if "USD" in balance.get("free", {}):
                    total_equity += balance["free"]["USD"]
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar balance de {exchange_name}: {e}")
                continue
        
        logger.info(f"💰 Equity total: ${total_equity:.2f}")
        return total_equity
        
    except Exception as e:
        logger.error(f"❌ Erro ao calcular equity: {e}")
        return 0.0


def test_all_exchanges():
    """Testa conectividade com todas as exchanges"""
    exchanges_to_test = ["binance", "kucoin", "bybit", "coinbase", "okx"]
    
    results = {}
    
    for exchange_name in exchanges_to_test:
        try:
            exchange = get_exchange(exchange_name)
            
            if exchange:
                # Tenta buscar ticker de BTC
                ticker = exchange.fetch_ticker("BTC/USDT")
                results[exchange_name] = {
                    "status": "✅ Connected",
                    "btc_price": ticker.get("last")
                }
            else:
                results[exchange_name] = {
                    "status": "❌ Failed",
                    "error": "Could not initialize"
                }
                
        except Exception as e:
            results[exchange_name] = {
                "status": "❌ Failed",
                "error": str(e)
            }
    
    # Print results
    print("\n🔍 TESTE DE CONECTIVIDADE COM EXCHANGES\n")
    for exchange_name, result in results.items():
        status = result["status"]
        print(f"{exchange_name.upper()}: {status}")
        if "btc_price" in result:
            print(f"  BTC Price: ${result['btc_price']:.2f}")
        elif "error" in result:
            print(f"  Error: {result['error']}")
    
    return results
