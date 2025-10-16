# core/data/converters.py
"""
Maveretta Data Converters - Adaptação do Freqtrade para Maveretta
Conversão e limpeza de dados de trading integrado com sistema de slots
Origem: freqtrade/data/converter/converter.py
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MaverettaDataConverter:
    """
    Conversor de dados de trading para formato Maveretta
    Adaptado dos conversores do Freqtrade para sistema de slots
    """
    
    def __init__(self):
        """Inicializa o conversor"""
        self.supported_formats = ['json', 'csv', 'feather', 'parquet']
        logger.info("[DATA_CONVERTER] Initialized Maveretta Data Converter")
    
    def clean_ohlcv_dataframe(
        self,
        df: pd.DataFrame,
        timeframe: str,
        pair: str,
        *,
        fill_missing: bool = True,
        drop_incomplete: bool = True
    ) -> pd.DataFrame:
        """
        Limpa e valida DataFrame OHLCV
        
        Args:
            df: DataFrame OHLCV bruto
            timeframe: Timeframe dos dados
            pair: Par de trading
            fill_missing: Preencher valores faltantes
            drop_incomplete: Remover candles incompletos
            
        Returns:
            DataFrame limpo e validado
        """
        try:
            if df.empty:
                logger.warning(f"[DATA_CONVERTER] Empty dataframe for {pair}")
                return df
            
            logger.info(f"[DATA_CONVERTER] Cleaning {len(df)} candles for {pair} {timeframe}")
            
            # Garantir colunas obrigatórias
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"[DATA_CONVERTER] Missing required columns for {pair}: {missing_columns}")
                return pd.DataFrame()
            
            # Converter para tipos numéricos
            for col in required_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Garantir index de timestamp
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'timestamp' in df.columns:
                    df.set_index('timestamp', inplace=True)
                else:
                    logger.error(f"[DATA_CONVERTER] No timestamp index for {pair}")
                    return pd.DataFrame()
            
            # Ordenar por timestamp
            df = df.sort_index()
            
            # Validações básicas OHLCV
            df = self._validate_ohlcv_logic(df, pair)
            
            # Remover duplicatas
            df = df[~df.index.duplicated(keep='last')]
            
            # Preencher valores faltantes se solicitado
            if fill_missing:
                df = self._fill_missing_values(df, timeframe)
            
            # Remover candles incompletos (último candle se muito recente)
            if drop_incomplete:
                df = self._drop_incomplete_candles(df, timeframe)
            
            # Validações finais
            df = self._final_validations(df, pair)
            
            logger.info(f"[DATA_CONVERTER] Cleaned dataframe: {len(df)} valid candles for {pair}")
            return df
            
        except Exception as e:
            logger.error(f"[DATA_CONVERTER] Error cleaning dataframe for {pair}: {e}")
            return pd.DataFrame()
    
    def convert_trades_to_ohlcv(
        self,
        trades: List[Dict[str, Any]],
        timeframe: str,
        pair: str
    ) -> pd.DataFrame:
        """
        Converte lista de trades para formato OHLCV
        
        Args:
            trades: Lista de trades
            timeframe: Timeframe desejado
            pair: Par de trading
            
        Returns:
            DataFrame OHLCV
        """
        try:
            if not trades:
                logger.warning(f"[DATA_CONVERTER] No trades to convert for {pair}")
                return pd.DataFrame()
            
            logger.info(f"[DATA_CONVERTER] Converting {len(trades)} trades to OHLCV for {pair}")
            
            # Converter para DataFrame
            df_trades = pd.DataFrame(trades)
            
            # Validar colunas necessárias
            required_cols = ['timestamp', 'price', 'amount']
            if not all(col in df_trades.columns for col in required_cols):
                logger.error(f"[DATA_CONVERTER] Missing required trade columns for {pair}")
                return pd.DataFrame()
            
            # Converter timestamp para datetime
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
            df_trades.set_index('timestamp', inplace=True)
            
            # Converter tipos numéricos
            df_trades['price'] = pd.to_numeric(df_trades['price'], errors='coerce')
            df_trades['amount'] = pd.to_numeric(df_trades['amount'], errors='coerce')
            
            # Resamplear para o timeframe desejado
            timeframe_pandas = self._convert_timeframe_to_pandas(timeframe)
            
            ohlcv = df_trades['price'].resample(timeframe_pandas).agg({
                'open': 'first',
                'high': 'max', 
                'low': 'min',
                'close': 'last'
            })
            
            # Volume
            ohlcv['volume'] = df_trades['amount'].resample(timeframe_pandas).sum()
            
            # Remover períodos sem trades
            ohlcv = ohlcv.dropna()
            
            logger.info(f"[DATA_CONVERTER] Generated {len(ohlcv)} OHLCV candles from trades")
            return ohlcv
            
        except Exception as e:
            logger.error(f"[DATA_CONVERTER] Error converting trades to OHLCV for {pair}: {e}")
            return pd.DataFrame()
    
    def normalize_data_for_slot(
        self,
        df: pd.DataFrame,
        slot_id: str,
        pair: str,
        normalize_volume: bool = True,
        add_metadata: bool = True
    ) -> pd.DataFrame:
        """
        Normaliza dados para uso específico em slot
        
        Args:
            df: DataFrame de entrada
            slot_id: ID do slot
            pair: Par de trading
            normalize_volume: Normalizar volumes
            add_metadata: Adicionar metadados do slot
            
        Returns:
            DataFrame normalizado para o slot
        """
        try:
            if df.empty:
                return df
            
            df_normalized = df.copy()
            
            # Normalizar volumes se solicitado
            if normalize_volume and 'volume' in df_normalized.columns:
                volume_median = df_normalized['volume'].median()
                if volume_median > 0:
                    df_normalized['volume_normalized'] = df_normalized['volume'] / volume_median
            
            # Adicionar metadados do slot se solicitado
            if add_metadata:
                df_normalized['slot_id'] = slot_id
                df_normalized['pair'] = pair
                df_normalized['processing_time'] = datetime.now(timezone.utc)
            
            # Calcular returns
            df_normalized['returns'] = df_normalized['close'].pct_change()
            df_normalized['log_returns'] = np.log(df_normalized['close'] / df_normalized['close'].shift(1))
            
            # Calcular spread (para análise de liquidez)
            if 'high' in df_normalized.columns and 'low' in df_normalized.columns:
                df_normalized['spread'] = df_normalized['high'] - df_normalized['low']
                df_normalized['spread_pct'] = df_normalized['spread'] / df_normalized['close']
            
            logger.info(f"[DATA_CONVERTER] Normalized data for slot {slot_id}: {len(df_normalized)} records")
            return df_normalized
            
        except Exception as e:
            logger.error(f"[DATA_CONVERTER] Error normalizing data for slot {slot_id}: {e}")
            return df
    
    def convert_format(
        self,
        df: pd.DataFrame,
        from_format: str,
        to_format: str,
        output_path: Optional[str] = None
    ) -> Union[pd.DataFrame, bool]:
        """
        Converte DataFrame entre diferentes formatos
        
        Args:
            df: DataFrame de entrada
            from_format: Formato de origem
            to_format: Formato de destino
            output_path: Caminho para salvar (se aplicável)
            
        Returns:
            DataFrame convertido ou True se salvou em arquivo
        """
        try:
            if to_format not in self.supported_formats:
                raise ValueError(f"Unsupported format: {to_format}")
            
            logger.info(f"[DATA_CONVERTER] Converting from {from_format} to {to_format}")
            
            if to_format == 'csv':
                if output_path:
                    df.to_csv(output_path, index=True)
                    return True
                else:
                    return df.to_csv(index=True)
                    
            elif to_format == 'json':
                if output_path:
                    df.to_json(output_path, orient='index', date_format='iso')
                    return True
                else:
                    return df.to_json(orient='index', date_format='iso')
                    
            elif to_format == 'feather':
                if output_path:
                    # Reset index para feather (não suporta DatetimeIndex)
                    df_reset = df.reset_index()
                    df_reset.to_feather(output_path)
                    return True
                else:
                    return df.reset_index()
                    
            elif to_format == 'parquet':
                if output_path:
                    df.to_parquet(output_path, index=True)
                    return True
                else:
                    return df
            
            return df
            
        except Exception as e:
            logger.error(f"[DATA_CONVERTER] Error converting format: {e}")
            return df if not output_path else False
    
    def merge_multiple_sources(
        self,
        dataframes: Dict[str, pd.DataFrame],
        merge_strategy: str = 'outer',
        fill_method: str = 'ffill'
    ) -> pd.DataFrame:
        """
        Merge dados de múltiplas fontes
        
        Args:
            dataframes: Dict com nome da fonte como chave e DataFrame como valor
            merge_strategy: Estratégia de merge ('outer', 'inner', 'left')
            fill_method: Método para preencher dados faltantes
            
        Returns:
            DataFrame merged
        """
        try:
            if not dataframes:
                logger.warning("[DATA_CONVERTER] No dataframes to merge")
                return pd.DataFrame()
            
            logger.info(f"[DATA_CONVERTER] Merging {len(dataframes)} data sources")
            
            # Iniciar com o primeiro DataFrame
            sources = list(dataframes.keys())
            merged_df = dataframes[sources[0]].copy()
            
            # Adicionar sufixo da fonte
            merged_df.columns = [f"{col}_{sources[0]}" for col in merged_df.columns]
            
            # Merge com outras fontes
            for source in sources[1:]:
                df_source = dataframes[source].copy()
                df_source.columns = [f"{col}_{source}" for col in df_source.columns]
                
                merged_df = merged_df.join(df_source, how=merge_strategy)
            
            # Preencher valores faltantes
            if fill_method:
                merged_df = merged_df.fillna(method=fill_method)
            
            logger.info(f"[DATA_CONVERTER] Merged result: {len(merged_df)} records with {len(merged_df.columns)} columns")
            return merged_df
            
        except Exception as e:
            logger.error(f"[DATA_CONVERTER] Error merging data sources: {e}")
            return pd.DataFrame()
    
    def _validate_ohlcv_logic(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Valida lógica OHLCV (high >= low, close/open entre high/low)"""
        if df.empty:
            return df
        
        original_len = len(df)
        
        # Máscara de validação
        valid_mask = (
            (df['high'] >= df['low']) &
            (df['high'] >= df['open']) & 
            (df['high'] >= df['close']) &
            (df['low'] <= df['open']) &
            (df['low'] <= df['close']) &
            (df['volume'] >= 0)
        )
        
        df = df[valid_mask]
        
        if len(df) < original_len:
            logger.warning(f"[DATA_CONVERTER] Removed {original_len - len(df)} invalid OHLCV records for {pair}")
        
        return df
    
    def _fill_missing_values(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Preenche valores faltantes"""
        if df.empty:
            return df
        
        # Forward fill para preços
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')
        
        # Volume como zero se faltante
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0)
        
        return df
    
    def _drop_incomplete_candles(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Remove candles potencialmente incompletos"""
        if df.empty or len(df) <= 1:
            return df
        
        # Calcular intervalo esperado do timeframe
        timeframe_minutes = self._timeframe_to_minutes(timeframe)
        
        # Se último candle é muito recente, pode estar incompleto
        now = datetime.now(timezone.utc)
        if df.index[-1].tz_localize('UTC') > now - pd.Timedelta(minutes=timeframe_minutes):
            df = df.iloc[:-1]
        
        return df
    
    def _final_validations(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Validações finais dos dados"""
        if df.empty:
            return df
        
        # Remover outliers extremos (preços que variam mais de 50% entre candles)
        price_change = df['close'].pct_change().abs()
        outlier_mask = price_change < 0.5  # Máximo 50% de variação
        
        outliers_removed = (~outlier_mask).sum()
        if outliers_removed > 0:
            logger.warning(f"[DATA_CONVERTER] Removed {outliers_removed} outlier candles for {pair}")
            df = df[outlier_mask]
        
        return df
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Converte timeframe para minutos"""
        timeframe_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, 
            '12h': 720, '1d': 1440, '3d': 4320, '1w': 10080
        }
        return timeframe_map.get(timeframe, 60)
    
    def _convert_timeframe_to_pandas(self, timeframe: str) -> str:
        """Converte timeframe Maveretta para formato pandas resample"""
        timeframe_map = {
            '1m': '1Min', '5m': '5Min', '15m': '15Min', '30m': '30Min',
            '1h': '1H', '2h': '2H', '4h': '4H', '6h': '6H',
            '12h': '12H', '1d': '1D', '3d': '3D', '1w': '1W'
        }
        return timeframe_map.get(timeframe, '1H')

# Funções de conveniência
def clean_slot_ohlcv_data(df: pd.DataFrame, timeframe: str, pair: str, **kwargs) -> pd.DataFrame:
    """Função de conveniência para limpeza de dados OHLCV"""
    converter = MaverettaDataConverter()
    return converter.clean_ohlcv_dataframe(df, timeframe, pair, **kwargs)

def convert_trades_for_slot(trades: List[Dict], timeframe: str, pair: str) -> pd.DataFrame:
    """Função de conveniência para conversão de trades"""
    converter = MaverettaDataConverter()
    return converter.convert_trades_to_ohlcv(trades, timeframe, pair)