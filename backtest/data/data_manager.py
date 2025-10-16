# -*- coding: utf-8 -*-
"""
Data Manager - Gerenciamento de dados históricos
Coleta automática de dados de múltiplas exchanges
"""

import pandas as pd
import numpy as np
import ccxt
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .data_collector import DataCollector


class DataManager:
    """
    Gerenciador de dados históricos para backtesting
    Coleta automática com cache inteligente
    """
    
    def __init__(self, cache_dir: str = "data/backtest_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.collector = DataCollector()
        
        # Configurações de cache
        self.cache_expiry_hours = 24  # Cache válido por 24h
        self.max_cache_size_mb = 500  # Máximo 500MB de cache
        
        print(f"[DATA_MANAGER] Inicializado com cache em {self.cache_dir}")
    
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        timeframe: str = '1m',
        exchange: str = 'binance'
    ) -> pd.DataFrame:
        """
        Obtém dados históricos com cache inteligente
        """
        
        # Gera chave de cache
        cache_key = self._generate_cache_key(symbol, start_date, end_date, timeframe, exchange)
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        # Verifica cache
        if self._is_cache_valid(cache_file):
            print(f"[DATA_MANAGER] 📋 Cache hit para {symbol} {timeframe}")
            return pd.read_parquet(cache_file)
        
        print(f"[DATA_MANAGER] 🔄 Coletando dados {symbol} ({start_date} - {end_date})")
        
        try:
            # Coleta dados novos
            data = self.collector.collect_data(symbol, start_date, end_date, timeframe, exchange)
            
            if not data.empty:
                # Valida e limpa dados
                data = self._validate_and_clean_data(data)
                
                # Salva no cache
                data.to_parquet(cache_file, compression='snappy')
                print(f"[DATA_MANAGER] ✅ Dados salvos no cache: {len(data)} registros")
            
            return data
            
        except Exception as e:
            print(f"[DATA_MANAGER] ❌ Erro coletando dados: {e}")
            return pd.DataFrame()
    
    def _generate_cache_key(self, symbol: str, start_date: str, end_date: str, 
                           timeframe: str, exchange: str) -> str:
        """
        Gera chave única para cache
        """
        # Remove caracteres especiais do símbolo
        clean_symbol = symbol.replace('/', '_').replace('-', '_')
        return f"{exchange}_{clean_symbol}_{timeframe}_{start_date}_{end_date}"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Verifica se cache é válido
        """
        if not cache_file.exists():
            return False
        
        # Verifica idade do arquivo
        file_age = time.time() - cache_file.stat().st_mtime
        max_age = self.cache_expiry_hours * 3600
        
        if file_age > max_age:
            print(f"[DATA_MANAGER] ⏰ Cache expirado: {cache_file.name}")
            return False
        
        return True
    
    def _validate_and_clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Valida e limpa dados históricos
        """
        
        # Verifica colunas obrigatórias
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
        
        # Remove valores nulos
        initial_len = len(data)
        data = data.dropna()
        
        if len(data) < initial_len:
            print(f"[DATA_MANAGER] 🧹 Removidos {initial_len - len(data)} registros com NaN")
        
        # Valida preços (não podem ser zero ou negativos)
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            invalid_prices = (data[col] <= 0).sum()
            if invalid_prices > 0:
                data = data[data[col] > 0]
                print(f"[DATA_MANAGER] 🧹 Removidos {invalid_prices} preços inválidos em {col}")
        
        # Valida OHLC lógica
        invalid_ohlc = (
            (data['high'] < data['low']) |
            (data['high'] < data['open']) |
            (data['high'] < data['close']) |
            (data['low'] > data['open']) |
            (data['low'] > data['close'])
        ).sum()
        
        if invalid_ohlc > 0:
            # Remove velas com OHLC inválido
            valid_mask = (
                (data['high'] >= data['low']) &
                (data['high'] >= data['open']) &
                (data['high'] >= data['close']) &
                (data['low'] <= data['open']) &
                (data['low'] <= data['close'])
            )
            data = data[valid_mask]
            print(f"[DATA_MANAGER] 🧹 Removidas {invalid_ohlc} velas com OHLC inválido")
        
        # Ordena por timestamp se existe
        if 'timestamp' in data.columns:
            data = data.sort_values('timestamp')
        
        # Reset index
        data = data.reset_index(drop=True)
        
        print(f"[DATA_MANAGER] ✅ Dados validados: {len(data)} registros limpos")
        return data
    
    def get_multiple_symbols_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        timeframe: str = '1m'
    ) -> Dict[str, pd.DataFrame]:
        """
        Obtém dados para múltiplos símbolos
        """
        
        results = {}
        
        for symbol in symbols:
            print(f"[DATA_MANAGER] 📊 Coletando {symbol}...")
            try:
                data = self.get_historical_data(symbol, start_date, end_date, timeframe)
                if not data.empty:
                    results[symbol] = data
                else:
                    print(f"[DATA_MANAGER] ⚠️  Nenhum dado para {symbol}")
            except Exception as e:
                print(f"[DATA_MANAGER] ❌ Erro em {symbol}: {e}")
                continue
        
        print(f"[DATA_MANAGER] ✅ Coletados dados para {len(results)}/{len(symbols)} símbolos")
        return results
    
    def update_data(
        self, 
        symbol: str, 
        exchange: str = 'binance',
        timeframe: str = '1m',
        days_back: int = 30
    ) -> bool:
        """
        Atualiza dados recentes de um símbolo
        """
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            data = self.collector.collect_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                timeframe,
                exchange
            )
            
            if not data.empty:
                # Invalida cache existente forçando nova coleta
                cache_key = self._generate_cache_key(
                    symbol, 
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d"), 
                    timeframe, 
                    exchange
                )
                cache_file = self.cache_dir / f"{cache_key}.parquet"
                
                if cache_file.exists():
                    cache_file.unlink()
                
                print(f"[DATA_MANAGER] ✅ Dados atualizados para {symbol}")
                return True
            
        except Exception as e:
            print(f"[DATA_MANAGER] ❌ Erro atualizando {symbol}: {e}")
            return False
    
    def cleanup_cache(self, max_age_days: int = 7) -> Dict[str, Any]:
        """
        Limpa cache antigo
        """
        
        cleanup_stats = {
            'files_removed': 0,
            'space_freed_mb': 0,
            'files_kept': 0
        }
        
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        for cache_file in self.cache_dir.glob("*.parquet"):
            file_mtime = cache_file.stat().st_mtime
            
            if file_mtime < cutoff_time:
                file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                cache_file.unlink()
                
                cleanup_stats['files_removed'] += 1
                cleanup_stats['space_freed_mb'] += file_size_mb
            else:
                cleanup_stats['files_kept'] += 1
        
        print(f"[DATA_MANAGER] 🧹 Cache limpo: {cleanup_stats['files_removed']} arquivos removidos")
        return cleanup_stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Estatísticas do cache
        """
        
        cache_files = list(self.cache_dir.glob("*.parquet"))
        total_size_mb = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)
        
        # Símbolos únicos no cache
        symbols = set()
        for cache_file in cache_files:
            parts = cache_file.stem.split('_')
            if len(parts) >= 2:
                symbols.add(parts[1])  # Assume formato: exchange_symbol_timeframe_start_end
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': round(total_size_mb, 2),
            'unique_symbols': len(symbols),
            'symbols': list(symbols),
            'cache_dir': str(self.cache_dir)
        }
    
    def export_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        output_format: str = 'csv'
    ) -> str:
        """
        Exporta dados para arquivo
        """
        
        data = self.get_historical_data(symbol, start_date, end_date)
        
        if data.empty:
            raise ValueError(f"Nenhum dado para exportar: {symbol}")
        
        # Nome do arquivo
        clean_symbol = symbol.replace('/', '_')
        filename = f"{clean_symbol}_{start_date}_{end_date}.{output_format}"
        filepath = self.cache_dir / filename
        
        # Exporta
        if output_format.lower() == 'csv':
            data.to_csv(filepath, index=False)
        elif output_format.lower() == 'parquet':
            data.to_parquet(filepath)
        elif output_format.lower() == 'json':
            data.to_json(filepath, orient='records', indent=2)
        else:
            raise ValueError(f"Formato não suportado: {output_format}")
        
        print(f"[DATA_MANAGER] ✅ Dados exportados: {filepath}")
        return str(filepath)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Status do gerenciador de dados
        """
        cache_stats = self.get_cache_stats()
        
        return {
            'cache_enabled': True,
            'cache_expiry_hours': self.cache_expiry_hours,
            'collector_status': self.collector.get_status(),
            'cache_stats': cache_stats
        }