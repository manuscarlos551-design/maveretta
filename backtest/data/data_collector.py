# -*- coding: utf-8 -*-
"""
Data Collector - Coleta dados históricos de exchanges
Suporta múltiplas exchanges com rate limiting inteligente
"""

import ccxt
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


class DataCollector:
    """
    Coletor de dados históricos com suporte a múltiplas exchanges
    """
    
    def __init__(self):
        self.exchanges = {}
        self.rate_limits = {}
        
        # Configurações de coleta
        self.max_candles_per_request = {
            'binance': 1000,
            'okx': 100,
            'bybit': 200,
            'gateio': 1000,
            'kucoin': 1500
        }
        
        self.timeframe_limits = {
            '1m': 1440,    # 1 dia em minutos
            '5m': 288,     # 1 dia em 5min
            '15m': 96,     # 1 dia em 15min
            '1h': 24,      # 1 dia em horas
            '4h': 6,       # 1 dia em 4h
            '1d': 1        # 1 dia
        }
        
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """
        Inicializa exchanges disponíveis para coleta
        """
        
        # Binance (principal)
        if os.getenv("BINANCE_API_KEY"):
            try:
                self.exchanges['binance'] = ccxt.binance({
                    'apiKey': os.getenv("BINANCE_API_KEY"),
                    'secret': os.getenv("BINANCE_API_SECRET"),
                    'enableRateLimit': True,
                    'timeout': 20000,
                    'options': {'adjustForTimeDifference': True}
                })
                print("[DATA_COLLECTOR] ✅ Binance configurado")
            except Exception as e:
                print(f"[DATA_COLLECTOR] ⚠️  Binance: {e}")
        
        # Adiciona exchanges públicas para dados históricos (sem API key necessária)
        try:
            self.exchanges['binance_public'] = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 20000
            })
        except Exception:
            pass
        
        try:
            self.exchanges['okx_public'] = ccxt.okx({
                'enableRateLimit': True,
                'timeout': 15000
            })
        except Exception:
            pass
        
        print(f"[DATA_COLLECTOR] Exchanges disponíveis: {list(self.exchanges.keys())}")
    
    def collect_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        timeframe: str = '1m',
        exchange: str = 'binance'
    ) -> pd.DataFrame:
        """
        Coleta dados históricos de uma exchange
        """
        
        # Usa exchange pública se não tiver credenciais
        exchange_key = f"{exchange}_public" if f"{exchange}_public" in self.exchanges else exchange
        
        if exchange_key not in self.exchanges:
            raise ValueError(f"Exchange {exchange} não disponível")
        
        exchange_obj = self.exchanges[exchange_key]
        
        # Converte datas
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
        
        print(f"[DATA_COLLECTOR] Coletando {symbol} de {exchange} ({start_date} - {end_date})")
        
        all_candles = []
        current_ts = start_ts
        
        max_candles = self.max_candles_per_request.get(exchange, 500)
        
        while current_ts < end_ts:
            try:
                # Faz request
                candles = exchange_obj.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=current_ts, 
                    limit=max_candles
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Atualiza timestamp para próximo batch
                last_candle_ts = candles[-1][0]
                
                if last_candle_ts <= current_ts:
                    # Evita loop infinito
                    break
                
                current_ts = last_candle_ts + self._get_timeframe_ms(timeframe)
                
                print(f"[DATA_COLLECTOR] Coletadas {len(candles)} velas (total: {len(all_candles)})")
                
                # Rate limiting
                time.sleep(0.1)
                
                # Evita requests muito longos
                if len(all_candles) > 50000:
                    print("[DATA_COLLECTOR] ⚠️  Muitos dados, limitando coleta")
                    break
                
            except Exception as e:
                print(f"[DATA_COLLECTOR] ❌ Erro coletando dados: {e}")
                
                # Se for rate limit, aguarda mais
                if "rate limit" in str(e).lower() or "429" in str(e):
                    print("[DATA_COLLECTOR] ⏰ Rate limit - aguardando 60s")
                    time.sleep(60)
                    continue
                
                # Outros erros, para a coleta
                break
        
        if not all_candles:
            print(f"[DATA_COLLECTOR] ⚠️  Nenhum dado coletado para {symbol}")
            return pd.DataFrame()
        
        # Converte para DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Filtra por período solicitado
        df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]
        
        # Remove duplicatas
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        # Converte timestamp para datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        print(f"[DATA_COLLECTOR] ✅ Coletadas {len(df)} velas para {symbol}")
        return df
    
    def _get_timeframe_ms(self, timeframe: str) -> int:
        """
        Converte timeframe para milissegundos
        """
        timeframes = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        
        return timeframes.get(timeframe, 60 * 1000)
    
    def get_available_symbols(self, exchange: str = 'binance') -> List[str]:
        """
        Lista símbolos disponíveis em uma exchange
        """
        
        exchange_key = f"{exchange}_public" if f"{exchange}_public" in self.exchanges else exchange
        
        if exchange_key not in self.exchanges:
            return []
        
        try:
            exchange_obj = self.exchanges[exchange_key]
            markets = exchange_obj.load_markets()
            
            # Filtra apenas spot markets
            spot_symbols = [
                symbol for symbol, market in markets.items() 
                if market.get('type', '').lower() == 'spot' and market.get('active', True)
            ]
            
            return sorted(spot_symbols)
            
        except Exception as e:
            print(f"[DATA_COLLECTOR] ❌ Erro listando símbolos: {e}")
            return []
    
    def get_top_symbols_by_volume(self, exchange: str = 'binance', limit: int = 50) -> List[str]:
        """
        Retorna símbolos com maior volume
        """
        
        exchange_key = f"{exchange}_public" if f"{exchange}_public" in self.exchanges else exchange
        
        if exchange_key not in self.exchanges:
            return []
        
        try:
            exchange_obj = self.exchanges[exchange_key]
            
            # Obtém tickers 24h
            tickers = exchange_obj.fetch_tickers()
            
            # Filtra USDT pairs e ordena por volume
            usdt_tickers = {
                symbol: ticker for symbol, ticker in tickers.items() 
                if '/USDT' in symbol and ticker.get('quoteVolume', 0) > 0
            }
            
            # Ordena por volume
            sorted_symbols = sorted(
                usdt_tickers.keys(), 
                key=lambda x: usdt_tickers[x].get('quoteVolume', 0), 
                reverse=True
            )
            
            return sorted_symbols[:limit]
            
        except Exception as e:
            print(f"[DATA_COLLECTOR] ❌ Erro obtendo top símbolos: {e}")
            return []
    
    def test_data_quality(self, symbol: str, days_back: int = 7, exchange: str = 'binance') -> Dict[str, Any]:
        """
        Testa qualidade dos dados de um símbolo
        """
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            data = self.collect_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                '1h',
                exchange
            )
            
            if data.empty:
                return {'status': 'failed', 'reason': 'no_data'}
            
            # Análise de qualidade
            total_candles = len(data)
            null_values = data.isnull().sum().sum()
            zero_volumes = (data['volume'] == 0).sum()
            
            # Gaps temporais
            time_diffs = data['timestamp'].diff().dropna()
            expected_diff = 3600000  # 1h em ms
            gaps = (time_diffs > expected_diff * 1.5).sum()
            
            # Score de qualidade
            quality_score = 1.0
            if null_values > 0:
                quality_score -= 0.2
            if zero_volumes > total_candles * 0.1:  # Mais de 10% sem volume
                quality_score -= 0.3
            if gaps > total_candles * 0.05:  # Mais de 5% de gaps
                quality_score -= 0.2
            
            return {
                'status': 'success',
                'symbol': symbol,
                'total_candles': total_candles,
                'null_values': int(null_values),
                'zero_volumes': int(zero_volumes),
                'time_gaps': int(gaps),
                'quality_score': round(quality_score, 2),
                'recommendation': 'good' if quality_score >= 0.8 else 'fair' if quality_score >= 0.6 else 'poor'
            }
            
        except Exception as e:
            return {'status': 'failed', 'reason': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Status do coletor de dados
        """
        
        exchange_status = {}
        for name, exchange in self.exchanges.items():
            try:
                exchange.fetch_time()
                exchange_status[name] = 'connected'
            except Exception:
                exchange_status[name] = 'disconnected'
        
        return {
            'available_exchanges': list(self.exchanges.keys()),
            'exchange_status': exchange_status,
            'rate_limits_enabled': True
        }