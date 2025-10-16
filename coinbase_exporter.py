#!/usr/bin/env python3
"""
Maveretta Bot - Coinbase Exporter
Real-time exporter for Coinbase Advanced Trade market data
Exposes Prometheus metrics on port 8003
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import ccxt
from prometheus_client import start_http_server, Gauge, Counter, Info, MetricsHandler
from http.server import HTTPServer
import threading
import json

# ================================
# CONFIGURATION
# ================================

# Support both legacy and normalized variable names
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY") or os.getenv("COINBASE_KEY", "")
COINBASE_PRIVATE_KEY = os.getenv("COINBASE_PRIVATE_KEY_PEM") or os.getenv("COINBASE_SECRET", "")
METRICS_PORT = int(os.getenv("COINBASE_METRICS_PORT", "8003"))
QUOTE_FIAT = os.getenv("QUOTE_FIAT", "BRL")

# ================================
# LOGGING SETUP
# ================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# PROMETHEUS METRICS
# ================================

# Equity metrics
coinbase_equity_usdt = Gauge('coinbase_equity_usdt', 'Total equity in USDT')
coinbase_equity_brl = Gauge('coinbase_equity_brl', 'Total equity in BRL')

# Connection metrics
coinbase_connection_status = Gauge('coinbase_connection_status', 'Coinbase connection status (1=connected, 0=disconnected)')
coinbase_exporter_up = Gauge('coinbase_exporter_up', 'Exporter status (1=up, 0=down)', ['exchange'])
coinbase_api_calls_total = Counter('coinbase_api_calls_total', 'Total API calls made', ['endpoint'])
coinbase_latency_seconds = Gauge('coinbase_latency_seconds', 'E2E latency in seconds')

# Info metrics
coinbase_exporter_info = Info('coinbase_exporter_info', 'Coinbase exporter information')

# Config error metric
exchange_config_error = Gauge('exchange_config_error', 'Configuration error indicator', ['exchange', 'reason'])

# ================================
# COINBASE CLIENT
# ================================

class CoinbaseExporter:
    def __init__(self):
        self.exchange = None
        self.running = False
        self.connection_status = False
        
        # Set exporter info
        coinbase_exporter_info.info({
            'version': '1.0.0',
            'exchange': 'Coinbase',
            'quote_fiat': QUOTE_FIAT
        })
        
        # Initialize metrics
        coinbase_exporter_up.labels(exchange="Coinbase").set(0)
        
        # Initialize exchange client
        self._init_exchange()
        
    def _init_exchange(self):
        """Initialize CCXT exchange client"""
        try:
            if not COINBASE_API_KEY or not COINBASE_PRIVATE_KEY:
                logger.warning("Coinbase API credentials not provided")
                exchange_config_error.labels(exchange="coinbase", reason="missing_credentials").set(1)
                coinbase_exporter_up.labels(exchange="Coinbase").set(0)
                return
            else:
                exchange_config_error.labels(exchange="coinbase", reason="missing_credentials").set(0)
                
            self.exchange = ccxt.coinbase({
                'apiKey': COINBASE_API_KEY,
                'secret': COINBASE_PRIVATE_KEY,
                'enableRateLimit': True,
            })
            logger.info("Coinbase exchange client initialized successfully")
            
            # Test connection
            try:
                self.exchange.fetch_balance()
                logger.info("Coinbase API credentials validated successfully")
                self.connection_status = True
                coinbase_connection_status.set(1)
                coinbase_exporter_up.labels(exchange="Coinbase").set(1)
            except Exception as e:
                logger.error(f"Failed to validate Coinbase API credentials: {e}")
                self.connection_status = False
                coinbase_connection_status.set(0)
                
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase exchange client: {e}")
            self.exchange = None
    
    async def start(self):
        """Start the exporter"""
        logger.info("Starting Coinbase Exporter...")
        self.running = True
        
        # Start background task
        await self._equity_updater()
    
    async def _equity_updater(self):
        """Update equity metrics periodically"""
        while self.running:
            try:
                if self.exchange and COINBASE_API_KEY and COINBASE_PRIVATE_KEY:
                    await self._update_equity_metrics()
                else:
                    logger.debug("Skipping equity update: Exchange not initialized or no API keys.")
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error updating equity metrics: {e}")
                await asyncio.sleep(60)
    
    async def _update_equity_metrics(self):
        """Calculate and update equity metrics"""
        try:
            start_time = time.time()
            
            # Fetch account balance
            balance = self.exchange.fetch_balance()
            total_usdt = 0.0
            
            # Collect all assets and their USDT values
            for asset, amounts in balance['total'].items():
                if amounts and float(amounts) > 0:
                    if asset in ['USDT', 'USDC', 'USD']:
                        total_usdt += float(amounts)
                    else:
                        try:
                            ticker_symbol = f"{asset}/USDT"
                            ticker = self.exchange.fetch_ticker(ticker_symbol)
                            price = float(ticker['last'])
                            total_usdt += float(amounts) * price
                            coinbase_api_calls_total.labels(endpoint='ticker').inc()
                        except Exception:
                            # Try with USD pair if USDT fails
                            try:
                                ticker_symbol = f"{asset}/USD"
                                ticker = self.exchange.fetch_ticker(ticker_symbol)
                                price = float(ticker['last'])
                                total_usdt += float(amounts) * price
                                coinbase_api_calls_total.labels(endpoint='ticker').inc()
                            except Exception as e:
                                logger.debug(f"Could not convert {asset} to USD/USDT: {e}")
                                continue
            
            # Update USDT equity
            coinbase_equity_usdt.set(total_usdt)
            
            # Convert to BRL if needed
            if QUOTE_FIAT.upper() == "BRL":
                brl_rate = await self._get_usd_brl_rate()
                total_brl = total_usdt * brl_rate
                coinbase_equity_brl.set(total_brl)
            
            # Update latency
            latency = time.time() - start_time
            coinbase_latency_seconds.set(latency)
            
            logger.info(f"Coinbase equity updated: {total_usdt:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Failed to update Coinbase equity: {e}")
            coinbase_connection_status.set(0)
            coinbase_exporter_up.labels(exchange="Coinbase").set(0)
    
    async def _get_usd_brl_rate(self):
        """Get USD to BRL exchange rate"""
        try:
            import requests
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD", 
                timeout=10
            )
            data = response.json()
            return data['rates']['BRL']
        except Exception as e:
            logger.warning(f"Failed to fetch USD/BRL rate: {e}")
            return 5.0  # Fallback rate

# ================================
# HEALTH ENDPOINT
# ================================

_exporter_instance = None

class CombinedHandler(MetricsHandler):
    """HTTP handler for both metrics and health checks"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if _exporter_instance and _exporter_instance.connection_status:
                response = {
                    'status': 'ok',
                    'exchange': 'Coinbase'
                }
            else:
                response = {
                    'status': 'degraded',
                    'reason': 'connection_failed',
                    'exchange': 'Coinbase'
                }
            
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/metrics':
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

# ================================
# MAIN
# ================================

async def main():
    """Main entry point"""
    global _exporter_instance
    
    logger.info(f"Starting Coinbase Exporter on port {METRICS_PORT}")
    
    # Create exporter instance
    exporter = CoinbaseExporter()
    _exporter_instance = exporter
    
    # Start combined HTTP server
    server = HTTPServer(('0.0.0.0', METRICS_PORT), CombinedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"HTTP server started on port {METRICS_PORT} (/metrics and /health)")
    
    # Start exporter
    await exporter.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Coinbase Exporter stopped by user")
    except Exception as e:
        logger.error(f"Coinbase Exporter error: {e}")
        sys.exit(1)
