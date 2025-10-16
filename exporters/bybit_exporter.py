#!/usr/bin/env python3
"""
Maveretta Bot - Bybit Exporter
Real-time exporter for Bybit market data
Exposes Prometheus metrics on port 8002
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
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY") or os.getenv("BYBIT_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET") or os.getenv("BYBIT_SECRET", "")
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
METRICS_PORT = int(os.getenv("BYBIT_METRICS_PORT", "8002"))
QUOTE_FIAT = os.getenv("QUOTE_FIAT", "BRL")

# ================================
# LOGGING SETUP
# ================================

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# PROMETHEUS METRICS
# ================================

# Equity metrics
bybit_equity_usdt = Gauge('bybit_equity_usdt', 'Total equity in USDT')
bybit_equity_brl = Gauge('bybit_equity_brl', 'Total equity in BRL')

# Connection metrics
bybit_connection_status = Gauge('bybit_connection_status', 'Bybit connection status (1=connected, 0=disconnected)')
bybit_exporter_up = Gauge('bybit_exporter_up', 'Exporter status (1=up, 0=down)', ['exchange'])
bybit_api_calls_total = Counter('bybit_api_calls_total', 'Total API calls made', ['endpoint'])
bybit_latency_seconds = Gauge('bybit_latency_seconds', 'E2E latency in seconds')

# Info metrics
bybit_exporter_info = Info('bybit_exporter_info', 'Bybit exporter information')

# Config error metric
exchange_config_error = Gauge('exchange_config_error', 'Configuration error indicator', ['exchange', 'reason'])

# API timeout metric
bybit_api_timeout = Gauge('bybit_api_timeout', 'API timeout indicator', ['exchange'])

# ================================
# BYBIT CLIENT
# ================================

class BybitExporter:
    def __init__(self):
        self.exchange = None
        self.running = False
        self.connection_status = False
        self.cache = {}
        self.cache_ttl = 10  # 10 seconds cache
        
        # Set exporter info
        bybit_exporter_info.info({
            'version': '1.0.0',
            'exchange': 'Bybit',
            'testnet': str(BYBIT_TESTNET),
            'quote_fiat': QUOTE_FIAT
        })
        
        # Initialize metrics
        bybit_exporter_up.labels(exchange="Bybit").set(0)
        bybit_api_timeout.labels(exchange="bybit").set(0)
        
        # Initialize exchange client
        self._init_exchange()
        
    def _init_exchange(self):
        """Initialize CCXT exchange client"""
        try:
            if not BYBIT_API_KEY or not BYBIT_API_SECRET:
                logger.warning("Bybit API credentials not provided")
                exchange_config_error.labels(exchange="bybit", reason="missing_credentials").set(1)
                bybit_exporter_up.labels(exchange="Bybit").set(0)
                return
            else:
                exchange_config_error.labels(exchange="bybit", reason="missing_credentials").set(0)
                
            self.exchange = ccxt.bybit({
                'apiKey': BYBIT_API_KEY,
                'secret': BYBIT_API_SECRET,
                'enableRateLimit': True,
                'timeout': 8000,  # 8 seconds timeout
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            if BYBIT_TESTNET:
                self.exchange.set_sandbox_mode(True)
                logger.info("Bybit testnet mode enabled")
            
            logger.info("Bybit exchange client initialized successfully")
            
            # Test connection
            try:
                self.exchange.fetch_balance()
                logger.info("Bybit API credentials validated successfully")
                self.connection_status = True
                bybit_connection_status.set(1)
                bybit_exporter_up.labels(exchange="Bybit").set(1)
            except Exception as e:
                logger.error(f"Failed to validate Bybit API credentials: {e}")
                self.connection_status = False
                bybit_connection_status.set(0)
                
        except Exception as e:
            logger.error(f"Failed to initialize Bybit exchange client: {e}")
            self.exchange = None
    
    async def start(self):
        """Start the exporter"""
        logger.info("Starting Bybit Exporter...")
        self.running = True
        
        # Start background task
        await self._equity_updater()
    
    async def _equity_updater(self):
        """Update equity metrics periodically"""
        while self.running:
            try:
                if self.exchange and BYBIT_API_KEY and BYBIT_API_SECRET:
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
            
            # Check cache first
            cache_key = 'balance'
            if cache_key in self.cache:
                cached_time, cached_data = self.cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    total_usdt = cached_data
                    bybit_equity_usdt.set(total_usdt)
                    return
            
            # Fetch account balance with timeout handling
            try:
                balance = self.exchange.fetch_balance()
                bybit_api_timeout.labels(exchange="bybit").set(0)
            except Exception as e:
                logger.error(f"API timeout: {e}")
                bybit_api_timeout.labels(exchange="bybit").set(1)
                raise
            
            total_usdt = 0.0
            
            # Collect all assets and their USDT values
            for asset, amounts in balance['total'].items():
                if amounts and float(amounts) > 0:
                    if asset in ['USDT', 'USDC']:
                        total_usdt += float(amounts)
                    else:
                        try:
                            ticker_symbol = f"{asset}/USDT"
                            ticker = self.exchange.fetch_ticker(ticker_symbol)
                            price = float(ticker['last'])
                            total_usdt += float(amounts) * price
                            bybit_api_calls_total.labels(endpoint='ticker').inc()
                        except Exception as e:
                            logger.debug(f"Could not convert {asset} to USDT: {e}")
                            continue
            
            # Update USDT equity
            bybit_equity_usdt.set(total_usdt)
            
            # Cache the result
            self.cache[cache_key] = (time.time(), total_usdt)
            
            # Convert to BRL if needed
            if QUOTE_FIAT.upper() == "BRL":
                brl_rate = await self._get_usd_brl_rate()
                total_brl = total_usdt * brl_rate
                bybit_equity_brl.set(total_brl)
            
            # Update latency
            latency = time.time() - start_time
            bybit_latency_seconds.set(latency)
            
            logger.info(f"Bybit equity updated: {total_usdt:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Failed to update Bybit equity: {e}")
            bybit_connection_status.set(0)
            bybit_exporter_up.labels(exchange="Bybit").set(0)
    
    async def _get_usd_brl_rate(self):
        """Get USD to BRL exchange rate"""
        try:
            import requests
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD", 
                timeout=8
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
                    'exchange': 'Bybit'
                }
            else:
                response = {
                    'status': 'degraded',
                    'reason': 'connection_failed',
                    'exchange': 'Bybit'
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
    
    logger.info(f"Starting Bybit Exporter on port {METRICS_PORT}")
    
    # Create exporter instance
    exporter = BybitExporter()
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
        logger.info("Bybit Exporter stopped by user")
    except Exception as e:
        logger.error(f"Bybit Exporter error: {e}")
        sys.exit(1)
