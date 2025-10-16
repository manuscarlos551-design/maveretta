#!/usr/bin/env python3
"""
Maveretta Bot - Binance Spot Exporter
Real-time WebSocket exporter for Binance Spot market data
Exposes Prometheus metrics on port 8000
"""

import os
import sys
import time
import json
import asyncio
import logging
import websockets
import threading
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

import requests
from prometheus_client import start_http_server, Gauge, Counter, Info, MetricsHandler
from http.server import HTTPServer
import ccxt

# ================================
# CONFIGURATION
# ================================

# Support both legacy and normalized variable names
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET", "")
BINANCE_MARKET = os.getenv("BINANCE_MARKET", "spot")
BINANCE_SYMBOLS_ENV = os.getenv("BINANCE_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,MATICUSDT,DOTUSDT,TRXUSDT,LTCUSDT,AVAXUSDT,LINKUSDT,ATOMUSDT,UNIUSDT,XLMUSDT,FILUSDT,APTUSDT,OPUSDT,SUIUSDT")
QUOTE_FIAT = os.getenv("QUOTE_FIAT", "BRL")

# Parse symbols
BINANCE_SYMBOLS = [s.strip() for s in BINANCE_SYMBOLS_ENV.split(",") if s.strip()]

# Metrics port
METRICS_PORT = int(os.getenv("METRICS_PORT", "8000"))

# WebSocket configuration
BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream?streams="

RECONNECT_DELAY = 5  # seconds
HEARTBEAT_INTERVAL = 30  # seconds
REST_FALLBACK_INTERVAL = 10  # seconds

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

# Price metrics
binance_last_price = Gauge('binance_last_price', 'Last price for symbol', ['symbol'])
binance_best_bid = Gauge('binance_best_bid', 'Best bid price for symbol', ['symbol'])
binance_best_ask = Gauge('binance_best_ask', 'Best ask price for symbol', ['symbol'])
binance_volume_24h = Gauge('binance_volume_24h', '24h volume for symbol', ['symbol'])

# Equity metrics
binance_equity_usdt = Gauge('binance_equity_usdt', 'Total equity in USDT')
binance_equity_brl = Gauge('binance_equity_brl', 'Total equity in BRL')

# Bot metrics (placeholders - will be populated from real bot data)
bot_slots_active = Gauge('bot_slots_active', 'Number of active bot slots')
bot_cycles_completed_total = Counter('bot_cycles_completed_total', 'Total completed cycles')

# Risk metrics
risk_atr_14 = Gauge('risk_atr_14', 'ATR 14 periods for symbol', ['symbol'])

# Connection metrics
binance_connection_status = Gauge('binance_connection_status', 'Binance connection status (1=connected, 0=disconnected)')
binance_exporter_up = Gauge('binance_exporter_up', 'Exporter status (1=up, 0=down)', ['exchange'])
binance_websocket_messages_total = Counter('binance_websocket_messages_total', 'Total WebSocket messages received')
binance_api_calls_total = Counter('binance_api_calls_total', 'Total API calls made', ['endpoint'])
binance_latency_seconds = Gauge('binance_latency_seconds', 'E2E latency in seconds', ['symbol'])

# Info metrics
binance_exporter_info = Info('binance_exporter_info', 'Binance exporter information')

# Config error metric
exchange_config_error = Gauge('exchange_config_error', 'Configuration error indicator', ['exchange', 'reason'])

# ================================
# BINANCE CLIENT
# ================================

class BinanceExporter:
    def __init__(self):
        self.exchange = None
        self.websocket = None
        self.running = False
        self.last_prices = {}
        self.last_tickers = {}
        self.connection_status = False
        
        # Set exporter info
        binance_exporter_info.info({
            'version': '1.0.0',
            'symbols': ','.join(BINANCE_SYMBOLS),
            'market': BINANCE_MARKET,
            'quote_fiat': QUOTE_FIAT
        })
        
        # Initialize metrics
        binance_exporter_up.labels(exchange="Binance").set(0)  # Start as down until connected
        
        # Initialize exchange client
        self._init_exchange()
        
    def _init_exchange(self):
        """Initialize CCXT exchange client"""
        try:
            # Check for missing credentials
            if not BINANCE_API_KEY or not BINANCE_API_SECRET:
                logger.warning("Binance API credentials not provided")
                exchange_config_error.labels(exchange="binance", reason="missing_credentials").set(1)
                binance_exporter_up.labels(exchange="Binance").set(0)
                return
            else:
                exchange_config_error.labels(exchange="binance", reason="missing_credentials").set(0)
            
            self.exchange = ccxt.binance({
                'apiKey': BINANCE_API_KEY,
                'secret': BINANCE_API_SECRET,
                'sandbox': False,  # Production
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            logger.info("Exchange client initialized successfully")
            
            # Test connection
            try:
                self.exchange.fetch_balance()
                logger.info("API credentials validated successfully")
            except Exception as e:
                logger.warning(f"Failed to validate API credentials: {e}. Equity calculations might not be available.")
                exchange_config_error.labels(exchange="binance", reason="invalid_credentials").set(1)
                
        except Exception as e:
            logger.error(f"Failed to initialize exchange client: {e}")
            self.exchange = None
            exchange_config_error.labels(exchange="binance", reason="init_failed").set(1)
    
    async def start(self):
        """Start the exporter"""
        logger.info("Starting Binance Spot Exporter...")
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._websocket_handler()),
            asyncio.create_task(self._equity_updater()),
            asyncio.create_task(self._bot_metrics_updater()),
            asyncio.create_task(self._rest_fallback_handler()),
            asyncio.create_task(self._heartbeat_handler())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Exporter error: {e}")
        finally:
            self.running = False
            logger.info("Exporter tasks finished.")
    
    async def _websocket_handler(self):
        """Handle WebSocket connection and messages"""
        while self.running:
            try:
                # Create streams for all symbols
                streams = []
                for symbol in BINANCE_SYMBOLS:
                    symbol_lower = symbol.lower()
                    # We are interested in ticker and bookTicker for price and volume
                    streams.extend([
                        f"{symbol_lower}@ticker",
                        f"{symbol_lower}@bookTicker"
                    ])
                
                if not streams:
                    logger.warning("No symbols configured, skipping WebSocket connection.")
                    await asyncio.sleep(10)
                    continue
                    
                stream_names = "/".join(streams)
                ws_url = f"{BINANCE_WS_BASE}{stream_names}"
                
                logger.info(f"Connecting to WebSocket: {len(streams)} streams for {len(BINANCE_SYMBOLS)} symbols")
                
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    self.connection_status = True
                    binance_connection_status.set(1)
                    binance_exporter_up.labels(exchange="Binance").set(1)
                    logger.info("WebSocket connected successfully")
                    
                    async for message in websocket:
                        if not self.running:
                            break
                            
                        try:
                            data = json.loads(message)
                            await self._process_websocket_message(data)
                            binance_websocket_messages_total.inc()
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse WebSocket message: {e}. Message: {message[:100]}...")
                        except Exception as e:
                            logger.error(f"Error processing WebSocket message: {e}. Data: {data}")
                            
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.connection_status = False
                binance_connection_status.set(0)
                binance_exporter_up.labels(exchange="Binance").set(0)
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connection_status = False
                binance_connection_status.set(0)
                binance_exporter_up.labels(exchange="Binance").set(0)
                
            if self.running:
                logger.info(f"Reconnecting to WebSocket in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)
    
    async def _process_websocket_message(self, data):
        """Process incoming WebSocket message"""
        if isinstance(data, dict) and 'stream' in data:
            stream = data['stream']
            payload = data['data']
            
            # Process ticker data
            if '@ticker' in stream:
                symbol = payload['s']
                if symbol in BINANCE_SYMBOLS:
                    # Record latency
                    event_time = int(payload['E']) / 1000  # Convert to seconds
                    current_time = time.time()
                    latency = current_time - event_time
                    binance_latency_seconds.labels(symbol=symbol).set(latency)
                    
                    # Update price and volume metrics
                    last_price = float(payload['c'])
                    volume_24h = float(payload['v'])
                    
                    binance_last_price.labels(symbol=symbol).set(last_price)
                    binance_volume_24h.labels(symbol=symbol).set(volume_24h)
                    
                    self.last_prices[symbol] = last_price
                    self.last_tickers[symbol] = payload
            
            # Process book ticker data
            elif '@bookTicker' in stream:
                symbol = payload['s']
                if symbol in BINANCE_SYMBOLS:
                    best_bid = float(payload['b']) if payload['b'] else 0
                    best_ask = float(payload['a']) if payload['a'] else 0
                    
                    binance_best_bid.labels(symbol=symbol).set(best_bid)
                    binance_best_ask.labels(symbol=symbol).set(best_ask)
    
    async def _equity_updater(self):
        """Update equity metrics periodically"""
        while self.running:
            try:
                if self.exchange and BINANCE_API_KEY and BINANCE_API_SECRET:
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
            # Fetch account balance
            balance = self.exchange.fetch_balance()
            total_usdt = 0.0
            
            # Collect all assets and their USDT values
            assets_to_convert = {}
            for asset, amounts in balance['total'].items():
                if amounts and float(amounts) > 0:
                    if asset in ['USDT', 'USDC', 'BUSD', 'FDUSD']:
                        # Stablecoins are already in USDT value
                        total_usdt += float(amounts)
                    else:
                        assets_to_convert[asset] = float(amounts)
            
            # Convert other assets to USDT
            for asset, amount in assets_to_convert.items():
                try:
                    ticker_symbol = f"{asset}/USDT"
                    if ticker_symbol.replace('/', '') in self.last_prices:
                        price = self.last_prices[ticker_symbol.replace('/', '')]
                        total_usdt += amount * price
                    else:
                        # Fallback to API call if price not available from WebSocket
                        try:
                            ticker = self.exchange.fetch_ticker(ticker_symbol)
                            price = float(ticker['last'])
                            total_usdt += amount * price
                            binance_api_calls_total.labels(endpoint='ticker').inc()
                        except Exception as api_e:
                            logger.warning(f"Could not fetch ticker for {ticker_symbol} via REST: {api_e}")
                except Exception as conversion_e:
                    logger.warning(f"Could not convert {asset} to USDT: {conversion_e}")
                    continue # Skip this asset if conversion fails
            
            # Update USDT equity
            binance_equity_usdt.set(total_usdt)
            
            # Convert to BRL if QUOTE_FIAT is BRL
            if QUOTE_FIAT.upper() == "BRL":
                brl_rate = await self._get_usd_brl_rate()
                total_brl = total_usdt * brl_rate
                binance_equity_brl.set(total_brl)
            
            logger.info(f"Equity updated: {total_usdt:.2f} USDT")
            if QUOTE_FIAT.upper() == "BRL":
                logger.info(f"Equity updated: {total_brl:.2f} BRL")
            
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching balance: {e}. Check API keys.")
            # Resetting exchange might be too aggressive, just log and skip
        except Exception as e:
            logger.error(f"Failed to update equity: {e}")
    
    async def _get_usd_brl_rate(self):
        """Get USD to BRL exchange rate"""
        try:
            # Prefer using Binance's USDT/BRL if available and in symbols
            if 'USDTBRL' in BINANCE_SYMBOLS or 'USDT/BRL' in BINANCE_SYMBOLS:
                try:
                    ticker = self.exchange.fetch_ticker('USDT/BRL')
                    rate = float(ticker['last'])
                    binance_api_calls_total.labels(endpoint='usdtbrl_ticker').inc()
                    logger.debug(f"Using Binance USDT/BRL rate: {rate}")
                    return rate
                except Exception as binance_rate_e:
                    logger.warning(f"Failed to fetch USDT/BRL from Binance: {binance_rate_e}")
            
            # Fallback to external API
            logger.debug("Falling back to external API for USD/BRL rate.")
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD", 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                rate = data['rates'].get('BRL', 0.0)
                if rate == 0.0:
                    logger.warning("BRL rate not found in exchangerate-api response.")
                return rate
            else:
                logger.warning(f"exchangerate-api request failed with status {response.status_code}. Response: {response.text}")
                return 0.0 # Indicate failure or use a sensible default if absolutely necessary
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error getting USD/BRL rate: {e}")
            return 0.0
        except Exception as e:
            logger.warning(f"Unexpected error getting USD/BRL rate: {e}")
            return 0.0
    
    async def _bot_metrics_updater(self):
        """Update bot-specific metrics from internal sources"""
        while self.running:
            try:
                # Try to read bot data from state files
                await self._update_bot_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error updating bot metrics: {e}")
                await asyncio.sleep(30)
    
    async def _update_bot_metrics(self):
        """Update bot metrics from data files"""
        try:
            # Try to read from state.json if it exists in a common location
            state_path = "/app/data/state.json" # Common path in Docker containers
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = json.load(f)
                
                # Update active slots
                slots = state.get('slots', [])
                active_slots = sum(1 for slot in slots if slot.get('enabled_runtime', False))
                bot_slots_active.set(active_slots)
                
                # Update total cycles (cumulative counter)
                # This assumes state.json contains a cumulative count of cycles
                # If it's a per-slot count, we need to sum them.
                total_cycles_in_state = 0
                for slot in slots:
                    total_cycles_in_state += slot.get('cycles_completed', 0)
                
                # Prometheus Counter is cumulative. We can only increment.
                # To avoid issues with restarting exporter and losing counter value,
                # it's better to rely on Prometheus's persistent storage or a separate file.
                # For simplicity here, we'll try to ensure it increments correctly.
                # A more robust approach would be to store the last known value.
                current_counter_value = bot_cycles_completed_total._value._value
                if total_cycles_in_state > current_counter_value:
                    bot_cycles_completed_total.inc(total_cycles_in_state - current_counter_value)
            
            # Calculate ATR for available symbols
            await self._update_atr_metrics()
            
        except FileNotFoundError:
            # state.json not found, ignore
            pass
        except Exception as e:
            logger.warning(f"Failed to update bot metrics from state.json: {e}")
    
    async def _update_atr_metrics(self):
        """Calculate and update ATR metrics"""
        try:
            if not self.exchange:
                return
                
            # Calculate ATR for a selection of symbols to avoid excessive API calls
            # Prioritize symbols present in BINANCE_SYMBOLS
            symbols_for_atr = [s for s in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'] if s in BINANCE_SYMBOLS]
            
            for symbol in symbols_for_atr:
                try:
                    # Fetch OHLCV data for ATR calculation (e.g., 1-hour candles)
                    # Fetch enough data points for the period (e.g., 20 for 14-period ATR)
                    ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=20)
                    if len(ohlcv) >= 14: # Ensure we have enough data for the calculation
                        atr = self._calculate_atr(ohlcv, period=14)
                        if atr > 0: # Only set if calculation is successful
                            risk_atr_14.labels(symbol=symbol).set(atr)
                        binance_api_calls_total.labels(endpoint='ohlcv').inc()
                except ccxt.NetworkError as e:
                    logger.warning(f"Network error fetching OHLCV for {symbol}: {e}")
                except ccxt.ExchangeError as e:
                    logger.warning(f"Exchange error fetching OHLCV for {symbol}: {e}")
                except Exception as e:
                    logger.warning(f"Failed to calculate ATR for {symbol}: {e}")
                        
        except Exception as e:
            logger.error(f"Error updating ATR metrics: {e}")
    
    def _calculate_atr(self, ohlcv_data, period=14):
        """Calculate Average True Range (ATR) using the given OHLCV data"""
        if len(ohlcv_data) < period + 1:
            return 0.0
        
        true_ranges = []
        # Iterate from the second data point to compare with the previous one
        for i in range(1, len(ohlcv_data)):
            high = ohlcv_data[i][2]
            low = ohlcv_data[i][3]
            prev_close = ohlcv_data[i-1][4] # Closing price of the previous candle
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # Calculate the ATR using a Simple Moving Average (SMA) for the specified period
        if len(true_ranges) >= period:
            # Take the last 'period' true ranges
            return sum(true_ranges[-period:]) / period
        elif true_ranges: # If we have some true ranges but not enough for the full period
            return sum(true_ranges) / len(true_ranges)
        else: # No true ranges calculated
            return 0.0
    
    async def _rest_fallback_handler(self):
        """REST API fallback when WebSocket is down"""
        while self.running:
            try:
                if not self.connection_status and self.exchange:
                    logger.info("WebSocket down, using REST fallback to fetch market data...")
                    await self._fetch_rest_data()
                await asyncio.sleep(REST_FALLBACK_INTERVAL)
            except Exception as e:
                logger.error(f"REST fallback error: {e}")
                await asyncio.sleep(REST_FALLBACK_INTERVAL)
    
    async def _fetch_rest_data(self):
        """Fetch data via REST API as fallback for a subset of symbols"""
        # Limit the number of symbols to fetch via REST to avoid hitting rate limits
        symbols_to_fetch = BINANCE_SYMBOLS[:5] 
        if not symbols_to_fetch:
            return

        try:
            logger.debug(f"Fetching {len(symbols_to_fetch)} symbols via REST...")
            # Fetch tickers for multiple symbols at once if possible, or individually
            # ccxt's fetch_tickers can be used for bulk, but individual calls are simpler here
            for symbol in symbols_to_fetch:
                try:
                    ticker = self.exchange.fetch_ticker(symbol)
                    
                    binance_last_price.labels(symbol=symbol).set(float(ticker['last']))
                    binance_best_bid.labels(symbol=symbol).set(float(ticker['bid']) if ticker.get('bid') else 0)
                    binance_best_ask.labels(symbol=symbol).set(float(ticker['ask']) if ticker.get('ask') else 0)
                    # Use 'baseVolume' for the volume of the base currency (e.g., BTC in BTCUSDT)
                    binance_volume_24h.labels(symbol=symbol).set(float(ticker['baseVolume']) if ticker.get('baseVolume') else 0)
                    
                    binance_api_calls_total.labels(endpoint='ticker_rest').inc()
                    
                except ccxt.NetworkError as e:
                    logger.warning(f"Network error fetching {symbol} via REST: {e}")
                except ccxt.ExchangeError as e:
                    logger.warning(f"Exchange error fetching {symbol} via REST: {e}")
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol} via REST: {e}")
                    
        except Exception as e:
            logger.error(f"REST fallback fetch error: {e}")
    
    async def _heartbeat_handler(self):
        """Send periodic heartbeat logs to indicate status"""
        while self.running:
            try:
                status = "CONNECTED" if self.connection_status else "DISCONNECTED"
                # Count how many symbols have recent price data
                active_symbols_count = sum(1 for s in BINANCE_SYMBOLS if s in self.last_prices)
                logger.info(f"Heartbeat: Binance WS Status={status}, Active Symbols={active_symbols_count}/{len(BINANCE_SYMBOLS)}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)

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
            
            response = {
                'status': 'ok',
                'exchange': 'Binance'
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
# MAIN FUNCTION
# ================================

async def main():
    """Main function to start the exporter"""
    global _exporter_instance
    
    logger.info("=" * 50)
    logger.info("Maveretta Bot - Binance Spot Exporter")
    logger.info("=" * 50)
    logger.info(f"Symbols configured: {len(BINANCE_SYMBOLS)}")
    if BINANCE_SYMBOLS:
        logger.info(f"First 5 symbols: {', '.join(BINANCE_SYMBOLS[:5])}...")
    logger.info(f"Market type: {BINANCE_MARKET}")
    logger.info(f"Quote Currency for Equity: {QUOTE_FIAT}")
    logger.info(f"Prometheus Metrics Port: {METRICS_PORT}")
    logger.info("=" * 50)
    
    # Create the Binance exporter instance
    exporter = BinanceExporter()
    _exporter_instance = exporter
    
    # Start combined HTTP server in a separate thread
    try:
        server = HTTPServer(('0.0.0.0', METRICS_PORT), CombinedHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"HTTP server started on port {METRICS_PORT} (/metrics and /health)")
    except Exception as e:
        logger.error(f"Failed to start HTTP server on port {METRICS_PORT}: {e}")
        sys.exit(1)
    
    try:
        await exporter.start()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping exporter...")
    except Exception as e:
        logger.error(f"An unhandled error occurred in the exporter: {e}")
        sys.exit(1)
    finally:
        logger.info("Maveretta Binance Spot Exporter stopped.")

if __name__ == "__main__":
    # Check for required libraries and prompt for installation if missing
    try:
        import websockets
        import ccxt
        from prometheus_client import start_http_server, Gauge, Counter, Info
        import requests
    except ImportError as e:
        logger.error(f"Missing required package: {e.name}")
        logger.error("Please install the required packages by running:")
        logger.error("pip install websockets ccxt prometheus-client requests")
        sys.exit(1)
    
    # Run the main asynchronous function
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"An error occurred during asyncio execution: {e}")
        sys.exit(1)