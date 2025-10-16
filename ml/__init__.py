"""Machine Learning module for Maveretta Trading Bot.

This module provides ML capabilities including:
- FreqAI interface for automated ML training
- Feature engineering
- Model registry and versioning
- Multiple ML models (LightGBM, XGBoost, CatBoost, PyTorch)
- Online learning
- Backtesting with ML predictions
"""

from .model_registry import ModelRegistry

__version__ = "1.0.0"
__all__ = ['ModelRegistry']
