#!/usr/bin/env python3
"""
Maveretta Bot - Kucoin Exporter
Real-time exporter for Kucoin market data
Exposes Prometheus metrics on port 8001
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import ccxt
from prometheus_client import start_http_server, Gauge, Counter, Info
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json

# ================================
# CONFIGURATION
# ================================

# Support both legacy and normalized variable names
KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY") or os.getenv("KUCOIN_KEY", "")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET") or os.getenv("KUCOIN_SECRET", "")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE", "")
METRICS_PORT = int(os.getenv("KUCOIN_METRICS_PORT", "8001"))
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
kucoin_equity_usdt = Gauge('kucoin_equity_usdt', 'Total equity in USDT')
kucoin_equity_brl = Gauge('kucoin_equity_brl', 'Total equity in BRL')

# Connection metrics
kucoin_connection_status = Gauge('kucoin_connection_status', 'Kucoin connection status (1=connected, 0=disconnected)')
kucoin_exporter_up = Gauge('kucoin_exporter_up', 'Exporter status (1=up, 0=down)', ['exchange'])
kucoin_api_calls_total = Counter('kucoin_api_calls_total', 'Total API calls made', ['endpoint'])
kucoin_latency_seconds = Gauge('kucoin_latency_seconds', 'E2E latency in seconds')

# Info metrics
kucoin_exporter_info = Info('kucoin_exporter_info', 'Kucoin exporter information')

# Config error metric
exchange_config_error = Gauge('exchange_config_error', 'Configuration error indicator', ['exchange', 'reason'])

# API timeout metric
kucoin_api_timeout = Gauge('kucoin_api_timeout', 'API timeout indicator', ['exchange'])

# ================================
# KUCOIN CLIENT
# ================================

class KucoinExporter:
    def __init__(self):
        self.exchange = None
        self.running = False
        self.connection_status = False
        self.cache = {}
        self.cache_ttl = 10  # 10 seconds cache
        
        # Set exporter info
        kucoin_exporter_info.info({
            'version': '1.0.0',
            'exchange': 'Kucoin',
            'quote_fiat': QUOTE_FIAT
        })
        
        # Initialize metrics
        kucoin_exporter_up.labels(exchange="Kucoin").set(0)
        kucoin_api_timeout.labels(exchange="kucoin").set(0)
        
        # Initialize exchange client
        self._init_exchange()
        
    def _init_exchange(self):
        """Initialize CCXT exchange client"""
        try:
            if not KUCOIN_API_KEY or not KUCOIN_API_SECRET:
                logger.warning("Kucoin API credentials not provided")
                exchange_config_error.labels(exchange="kucoin", reason="missing_credentials").set(1)
                return
            
            if not KUCOIN_API_PASSPHRASE:
                logger.warning("Kucoin API passphrase not provided - exporter will run in degraded mode")
                self.connection_status = False
                kucoin_connection_status.set(0)
                kucoin_exporter_up.labels(exchange="Kucoin").set(0)
                exchange_config_error.labels(exchange="kucoin", reason="missing_passphrase").set(1)
                return
            else:
                exchange_config_error.labels(exchange="kucoin", reason="missing_passphrase").set(0)
                
            self.exchange = ccxt.kucoin({
                'apiKey': KUCOIN_API_KEY,
                'secret': KUCOIN_API_SECRET,
                'password': KUCOIN_API_PASSPHRASE,
                'enableRateLimit': True,
                'timeout': 8000,  # 8 seconds timeout
            })
            logger.info("Kucoin exchange client initialized successfully")
            
            # Test connection
            try:
                self.exchange.fetch_balance()
                logger.info("Kucoin API credentials validated successfully")
                self.connection_status = True
                kucoin_connection_status.set(1)
                kucoin_exporter_up.labels(exchange="Kucoin").set(1)
            except Exception as e:
                logger.error(f"Failed to validate Kucoin API credentials: {e}")
                self.connection_status = False
                kucoin_connection_status.set(0)
                
        except Exception as e:
            logger.error(f"Failed to initialize Kucoin exchange client: {e}")
            self.exchange = None
    
    async def start(self):
        """Start the exporter"""
        logger.info("Starting Kucoin Exporter...")
        self.running = True
        
        # Start background task
        await self._equity_updater()
    
    async def _equity_updater(self):
        """Update equity metrics periodically"""
        while self.running:
            try:
                if self.exchange and KUCOIN_API_KEY and KUCOIN_API_SECRET:
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
                    if asset in ['USDT', 'USDC']:
                        total_usdt += float(amounts)
                    else:
                        try:
                            ticker_symbol = f"{asset}/USDT"
                            ticker = self.exchange.fetch_ticker(ticker_symbol)
                            price = float(ticker['last'])
                            total_usdt += float(amounts) * price
                            kucoin_api_calls_total.labels(endpoint='ticker').inc()
                        except Exception as e:
                            logger.debug(f"Could not convert {asset} to USDT: {e}")
                            continue
            
            # Update USDT equity
            kucoin_equity_usdt.set(total_usdt)
            
            # Convert to BRL if needed
            if QUOTE_FIAT.upper() == "BRL":
                brl_rate = await self._get_usd_brl_rate()
                total_brl = total_usdt * brl_rate
                kucoin_equity_brl.set(total_brl)
            
            # Update latency
            latency = time.time() - start_time
            kucoin_latency_seconds.set(latency)
            
            logger.info(f"Kucoin equity updated: {total_usdt:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Failed to update Kucoin equity: {e}")
            kucoin_connection_status.set(0)
            kucoin_exporter_up.labels(exchange="Kucoin").set(0)
    
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

from prometheus_client import MetricsHandler

class CombinedHandler(MetricsHandler):
    """HTTP handler for both metrics and health checks"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Check if passphrase is missing
            if not KUCOIN_API_PASSPHRASE:
                response = {
                    'status': 'degraded',
                    'reason': 'missing_passphrase',
                    'exchange': 'Kucoin'
                }
            elif _exporter_instance and _exporter_instance.connection_status:
                response = {
                    'status': 'ok',
                    'exchange': 'Kucoin'
                }
            else:
                response = {
                    'status': 'degraded',
                    'reason': 'connection_failed',
                    'exchange': 'Kucoin'
                }
            
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/metrics':
            # Delegate to parent MetricsHandler
            super().do_GET()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

# ================================
# MAIN
# ================================

async def main():
    """Main entry point"""
    global _exporter_instance
    
    logger.info(f"Starting Kucoin Exporter on port {METRICS_PORT}")
    
    # Create exporter instance
    exporter = KucoinExporter()
    _exporter_instance = exporter
    
    # Start combined HTTP server (metrics + health)
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
        logger.info("Kucoin Exporter stopped by user")
    except Exception as e:
        logger.error(f"Kucoin Exporter error: {e}")
        sys.exit(1)
