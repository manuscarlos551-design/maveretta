"""Feature Engineering for ML models."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

try:
    import ta
except ImportError:
    ta = None
    logging.warning("ta library not installed. Some indicators may not be available.")


logger = logging.getLogger(__name__)


class FeatureEngineering:
    """
    Automated feature engineering for trading strategies.
    
    Creates features from OHLCV data:
    - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - Price-based features
    - Volume features
    - Temporal features
    - Volatility features
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.freqai_config = config.get('freqai', {})
        self.feature_params = self.freqai_config.get('feature_params', {})

    def create_features(
        self,
        dataframe: pd.DataFrame,
        include_labels: bool = True
    ) -> Dict[str, Any]:
        """
        Create features from OHLCV data.
        
        Args:
            dataframe: DataFrame with OHLCV data
            include_labels: Whether to create labels (y)
            
        Returns:
            Dict with X (features), y (labels), feature_names, dataframe
        """
        logger.info("Creating features...")
        
        df = dataframe.copy()
        
        # Add technical indicators
        df = self._add_technical_indicators(df)
        
        # Add price features
        df = self._add_price_features(df)
        
        # Add volume features
        df = self._add_volume_features(df)
        
        # Add temporal features
        df = self._add_temporal_features(df)
        
        # Add volatility features
        df = self._add_volatility_features(df)
        
        # Add momentum features
        df = self._add_momentum_features(df)
        
        # Drop NaN values created by indicators
        df = df.dropna()
        
        # Create labels if requested
        y = None
        if include_labels:
            if 'signal' in df.columns:
                y = df['signal'].values
            else:
                # Create default labels: 1 if next candle is up, 0 otherwise
                df['future_return'] = df['close'].shift(-1) / df['close'] - 1
                y = (df['future_return'] > 0).astype(int).values
                df = df[:-1]  # Remove last row (no future data)
        
        # Select feature columns
        feature_cols = self._select_feature_columns(df)
        
        # Extract features
        X = df[feature_cols].values
        
        logger.info(f"Created {len(feature_cols)} features from {len(df)} samples")
        
        return {
            'X': X,
            'y': y,
            'feature_names': feature_cols,
            'dataframe': df
        }

    def _select_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Select feature columns from dataframe.
        """
        # Exclude non-feature columns
        exclude_cols = {'date', 'open', 'high', 'low', 'close', 'volume', 'signal', 'future_return'}
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        return feature_cols

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators using ta library.
        """
        if ta is None:
            logger.warning("ta library not available, skipping technical indicators")
            return df
        
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            df['rsi_7'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
            df['rsi_21'] = ta.momentum.RSIIndicator(df['close'], window=21).rsi()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            df['bb_pct'] = bb.bollinger_pband()
            
            # EMAs
            for period in [9, 21, 50, 100, 200]:
                df[f'ema_{period}'] = ta.trend.EMAIndicator(
                    df['close'], window=period
                ).ema_indicator()
            
            # SMAs
            for period in [10, 20, 50, 100]:
                df[f'sma_{period}'] = ta.trend.SMAIndicator(
                    df['close'], window=period
                ).sma_indicator()
            
            # ADX
            df['adx'] = ta.trend.ADXIndicator(
                df['high'], df['low'], df['close']
            ).adx()
            
            # ATR
            df['atr'] = ta.volatility.AverageTrueRange(
                df['high'], df['low'], df['close']
            ).average_true_range()
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(
                df['high'], df['low'], df['close']
            )
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # CCI
            df['cci'] = ta.trend.CCIIndicator(
                df['high'], df['low'], df['close']
            ).cci()
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
        
        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price-based features.
        """
        # Returns
        for period in [1, 2, 3, 5, 10, 20]:
            df[f'returns_{period}'] = df['close'].pct_change(period)
        
        # High-Low spread
        df['hl_spread'] = (df['high'] - df['low']) / df['close']
        df['hl_spread_pct'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Close position within candle
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        
        # Price distance from EMA (if EMA exists)
        if 'ema_21' in df.columns:
            df['price_distance_ema21'] = (df['close'] - df['ema_21']) / df['ema_21']
        
        # Price momentum
        df['price_momentum_3'] = df['close'] / df['close'].shift(3) - 1
        df['price_momentum_5'] = df['close'] / df['close'].shift(5) - 1
        
        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volume-based features.
        """
        # Volume SMA
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_sma_50'] = df['volume'].rolling(window=50).mean()
        
        # Volume ratio
        df['volume_ratio'] = df['volume'] / (df['volume_sma_20'] + 1e-10)
        
        # Volume change
        df['volume_change'] = df['volume'].pct_change()
        
        # On-Balance Volume (OBV) approximation
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        
        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add temporal features (hour, day of week, etc.).
        """
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['hour'] = df['date'].dt.hour
            df['day_of_week'] = df['date'].dt.dayofweek
            df['day_of_month'] = df['date'].dt.day
            df['month'] = df['date'].dt.month
            
            # Cyclical encoding
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volatility features.
        """
        # Rolling volatility
        for period in [5, 10, 20, 50]:
            df[f'volatility_{period}'] = df['returns_1'].rolling(
                window=period
            ).std()
        
        # Realized volatility
        df['realized_vol_20'] = np.sqrt((df['returns_1'] ** 2).rolling(20).sum())
        
        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add momentum features.
        """
        # Rate of change
        for period in [5, 10, 20]:
            df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / 
                                    df['close'].shift(period)) * 100
        
        # Moving average crossovers
        if 'ema_9' in df.columns and 'ema_21' in df.columns:
            df['ema_cross_9_21'] = (df['ema_9'] > df['ema_21']).astype(int)
        
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            df['sma_cross_20_50'] = (df['sma_20'] > df['sma_50']).astype(int)
        
        return df
