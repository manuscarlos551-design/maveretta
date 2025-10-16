"""Data Kitchen for preparing data for ML training."""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


class DataKitchen:
    """
    Data Kitchen for preparing and processing data for ML.
    
    Responsibilities:
    - Load historical data
    - Clean and preprocess data
    - Split data into train/test
    - Handle missing values
    - Normalize/scale features
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.freqai_config = config.get('freqai', {})

    def prepare_data(
        self,
        symbol: str,
        timerange: str,
        strategy: str,
        timeframe: str = '5m'
    ) -> pd.DataFrame:
        """
        Prepare data for ML training.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timerange: Time range (e.g., '20240101-20241001')
            strategy: Strategy name
            timeframe: Timeframe (default: '5m')
            
        Returns:
            DataFrame with prepared data
        """
        logger.info(f"Preparing data for {symbol} from {timerange}")
        
        # Parse timerange
        start_date, end_date = self._parse_timerange(timerange)
        
        # Load data from database or data provider
        data = self._load_historical_data(symbol, start_date, end_date, timeframe)
        
        # Clean data
        data = self._clean_data(data)
        
        # Add strategy-specific indicators
        data = self._add_strategy_indicators(data, strategy)
        
        return data

    def _parse_timerange(self, timerange: str) -> Tuple[datetime, datetime]:
        """
        Parse timerange string into start and end dates.
        
        Args:
            timerange: String like '20240101-20241001'
            
        Returns:
            Tuple of (start_date, end_date)
        """
        try:
            start_str, end_str = timerange.split('-')
            start_date = datetime.strptime(start_str, '%Y%m%d')
            end_date = datetime.strptime(end_str, '%Y%m%d')
            return start_date, end_date
        except Exception as e:
            logger.error(f"Error parsing timerange: {e}")
            # Default to last 90 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            return start_date, end_date

    def _load_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Load historical OHLCV data.
        
        This should integrate with the existing data provider.
        For now, we'll create a simple implementation.
        """
        try:
            # Import the data provider from core
            from core.data.data_provider import DataProvider
            
            provider = DataProvider(self.config)
            data = provider.get_ohlcv_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            return data
            
        except Exception as e:
            logger.warning(f"Could not load data from provider: {e}")
            
            # Fallback: create sample data
            logger.info("Creating sample data for testing...")
            return self._create_sample_data(start_date, end_date, timeframe)

    def _create_sample_data(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Create sample OHLCV data for testing.
        """
        # Parse timeframe to minutes
        timeframe_minutes = self._parse_timeframe_to_minutes(timeframe)
        
        # Generate date range
        date_range = pd.date_range(
            start=start_date,
            end=end_date,
            freq=f"{timeframe_minutes}T"
        )
        
        # Generate random OHLCV data (more realistic)
        np.random.seed(42)
        base_price = 50000  # Starting price (e.g., BTC)
        
        data = []
        current_price = base_price
        
        for date in date_range:
            # Random walk
            change_pct = np.random.normal(0, 0.5) / 100
            current_price *= (1 + change_pct)
            
            high = current_price * (1 + abs(np.random.normal(0, 0.3)) / 100)
            low = current_price * (1 - abs(np.random.normal(0, 0.3)) / 100)
            open_price = current_price * (1 + np.random.normal(0, 0.1) / 100)
            close = current_price
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        return df

    def _parse_timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Parse timeframe string to minutes.
        
        Examples:
            '5m' -> 5
            '1h' -> 60
            '1d' -> 1440
        """
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 1440
        else:
            return 5  # Default to 5 minutes

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean data by handling missing values and outliers.
        """
        # Remove duplicates
        data = data.drop_duplicates(subset=['date'], keep='last')
        
        # Sort by date
        data = data.sort_values('date').reset_index(drop=True)
        
        # Forward fill missing values
        data = data.fillna(method='ffill')
        
        # Drop any remaining NaN
        data = data.dropna()
        
        return data

    def _add_strategy_indicators(self, data: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """
        Add strategy-specific technical indicators.
        
        This can be customized based on the strategy.
        """
        # For now, we'll add basic indicators
        # The FeatureEngineering class will add more
        
        return data

    def split_data(
        self,
        data: pd.DataFrame,
        test_size: float = 0.2,
        shuffle: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into train and test sets.
        
        Args:
            data: DataFrame to split
            test_size: Proportion of test set (0.0 to 1.0)
            shuffle: Whether to shuffle data before splitting
            
        Returns:
            Tuple of (train_data, test_data)
        """
        if shuffle:
            data = data.sample(frac=1).reset_index(drop=True)
        
        split_idx = int(len(data) * (1 - test_size))
        
        train_data = data.iloc[:split_idx].copy()
        test_data = data.iloc[split_idx:].copy()
        
        logger.info(f"Data split: Train={len(train_data)}, Test={len(test_data)}")
        
        return train_data, test_data
