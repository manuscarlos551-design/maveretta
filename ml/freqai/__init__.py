"""FreqAI module for automated ML training and predictions.

This module provides:
- FreqAI interface for training and predictions
- Feature engineering
- Data kitchen for data preparation
- Data drawer for model storage
- Multiple ML models
"""

from .freqai_interface import FreqAIInterface
from .feature_engineering import FeatureEngineering

__all__ = ['FreqAIInterface', 'FeatureEngineering']
