#!/usr/bin/env python3
"""
Maveretta Bot - OKX Exporter
Real-time exporter for OKX market data
Exposes Prometheus metrics on port 8004
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
OKX_API_KEY = os.getenv("OKX_API_KEY") or os.getenv("OKX_KEY", "")
OKX_API_SECRET = os.getenv("OKX_API_SECRET") or os.getenv("OKX_SECRET", "")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE", "")
OKX_SIMULATED = os.getenv("OKX_SIMULATED", "false").lower() == "true"
METRICS_PORT = int(os.getenv("OKX_METRICS_PORT", "8004"))
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
okx_equity_usdt = Gauge('okx_equity_usdt', 'Total equity in USDT')
okx_equity_brl = Gauge('okx_equity_brl', 'Total equity in BRL')

# Connection metrics
okx_connection_status = Gauge('okx_connection_status', 'OKX connection status (1=connected, 0=disconnected)')
okx_exporter_up = Gauge('okx_exporter_up', 'Exporter status (1=up, 0=down)', ['exchange'])
okx_api_calls_total = Counter('okx_api_calls_total', 'Total API calls made', ['endpoint'])
okx_latency_seconds = Gauge('okx_latency_seconds', 'E2E latency in seconds')

# Info metrics
okx_exporter_info = Info('okx_exporter_info', 'OKX exporter information')

# Config error metric
exchange_config_error = Gauge('exchange_config_error', 'Configuration error indicator', ['exchange', 'reason'])

# ================================
# OKX CLIENT
# ================================

class OKXExporter:
    def __init__(self):
        self.exchange = None
        self.running = False
        self.connection_status = False
        
        # Set exporter info
        okx_exporter_info.info({
            'version': '1.0.0',
            'exchange': 'OKX',
            'simulated': str(OKX_SIMULATED),
            'quote_fiat': QUOTE_FIAT
        })
        
        # Initialize metrics
        okx_exporter_up.labels(exchange="OKX").set(0)
        
        # Initialize exchange client
        self._init_exchange()
        
    def _init_exchange(self):
        """Initialize CCXT exchange client"""
        try:
            if not OKX_API_KEY or not OKX_API_SECRET:
                logger.warning("OKX API credentials not provided")
                exchange_config_error.labels(exchange="okx", reason="missing_credentials").set(1)
                return
            else:
                exchange_config_error.labels(exchange="okx", reason="missing_credentials").set(0)
            
            if not OKX_API_PASSPHRASE:
                logger.warning("OKX API passphrase not provided - exporter will run in degraded mode")
                self.connection_status = False
                okx_connection_status.set(0)
                okx_exporter_up.labels(exchange="OKX").set(0)
                exchange_config_error.labels(exchange="okx", reason="missing_passphrase").set(1)
                return
            else:
                exchange_config_error.labels(exchange="okx", reason="missing_passphrase").set(0)
                
            self.exchange = ccxt.okx({
                'apiKey': OKX_API_KEY,
                'secret': OKX_API_SECRET,
                'password': OKX_API_PASSPHRASE,
                'enableRateLimit': True,
            })
            
            if OKX_SIMULATED:
                self.exchange.set_sandbox_mode(True)
                logger.info("OKX simulated trading mode enabled")
            
            logger.info("OKX exchange client initialized successfully")
            
            # Test connection
            try:
                self.exchange.fetch_balance()
                logger.info("OKX API credentials validated successfully")
                self.connection_status = True
                okx_connection_status.set(1)
                okx_exporter_up.labels(exchange="OKX").set(1)
            except Exception as e:
                logger.error(f"Failed to validate OKX API credentials: {e}")
                self.connection_status = False
                okx_connection_status.set(0)
                
        except Exception as e:
            logger.error(f"Failed to initialize OKX exchange client: {e}")
            self.exchange = None
    
    async def start(self):
        """Start the exporter"""
        logger.info("Starting OKX Exporter...")
        self.running = True
        
        # Start background task
        await self._equity_updater()
    
    async def _equity_updater(self):
        """Update equity metrics periodically"""
        while self.running:
            try:
                if self.exchange and OKX_API_KEY and OKX_API_SECRET:
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
                            okx_api_calls_total.labels(endpoint='ticker').inc()
                        except Exception as e:
                            logger.debug(f"Could not convert {asset} to USDT: {e}")
                            continue
            
            # Update USDT equity
            okx_equity_usdt.set(total_usdt)
            
            # Convert to BRL if needed
            if QUOTE_FIAT.upper() == "BRL":
                brl_rate = await self._get_usd_brl_rate()
                total_brl = total_usdt * brl_rate
                okx_equity_brl.set(total_brl)
            
            # Update latency
            latency = time.time() - start_time
            okx_latency_seconds.set(latency)
            
            logger.info(f"OKX equity updated: {total_usdt:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Failed to update OKX equity: {e}")
            okx_connection_status.set(0)
            okx_exporter_up.labels(exchange="OKX").set(0)
    
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
            
            if not OKX_API_PASSPHRASE:
                response = {
                    'status': 'degraded',
                    'reason': 'missing_passphrase',
                    'exchange': 'OKX'
                }
            elif _exporter_instance and _exporter_instance.connection_status:
                response = {
                    'status': 'ok',
                    'exchange': 'OKX'
                }
            else:
                response = {
                    'status': 'degraded',
                    'reason': 'connection_failed',
                    'exchange': 'OKX'
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
    
    logger.info(f"Starting OKX Exporter on port {METRICS_PORT}")
    
    # Create exporter instance
    exporter = OKXExporter()
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
        logger.info("OKX Exporter stopped by user")
    except Exception as e:
        logger.error(f"OKX Exporter error: {e}")
        sys.exit(1)
