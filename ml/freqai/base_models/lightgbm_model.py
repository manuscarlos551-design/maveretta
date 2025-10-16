"""LightGBM model implementation."""

import numpy as np
from typing import Dict, Any, Optional
import logging

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logging.warning("LightGBM not installed. Install with: pip install lightgbm")

from .base_ml_model import BaseMLModel

logger = logging.getLogger(__name__)


class LightGBMModel(BaseMLModel):
    """
    LightGBM classifier for binary/multi-class classification.
    
    Features:
    - Fast training
    - Good performance
    - Feature importance
    - Early stopping
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not LIGHTGBM_AVAILABLE:
            raise ImportError("LightGBM not installed")
        
        # Default parameters
        self.params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'force_col_wise': True,
        }
        
        # Override with config
        freqai_config = config.get('freqai', {})
        model_params = freqai_config.get('model_params', {})
        if model_params:
            self.params.update(model_params)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: Optional[np.ndarray] = None,
        y_valid: Optional[np.ndarray] = None,
        num_boost_round: int = 1000,
        early_stopping_rounds: int = 50
    ) -> Dict[str, Any]:
        """
        Train LightGBM model.
        """
        logger.info(f"Training LightGBM with {len(X_train)} samples...")
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        
        valid_sets = [train_data]
        valid_names = ['train']
        
        if X_valid is not None and y_valid is not None:
            valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
            valid_sets.append(valid_data)
            valid_names.append('valid')
        
        # Train model
        callbacks = [
            lgb.log_evaluation(period=100),
        ]
        
        if early_stopping_rounds and X_valid is not None:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))
        
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )
        
        self.is_trained = True
        
        # Calculate training metrics
        y_pred = self.predict(X_train)
        y_pred_proba = self.predict_proba(X_train)
        metrics = self._calculate_metrics(y_train, y_pred, y_pred_proba)
        
        logger.info(f"Training complete. Accuracy: {metrics['accuracy']:.4f}")
        
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class labels.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        y_pred_proba = self.model.predict(X)
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        return y_pred

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        y_pred_proba = self.model.predict(X)
        
        # Convert to 2D array for binary classification
        if y_pred_proba.ndim == 1:
            y_pred_proba = np.column_stack([1 - y_pred_proba, y_pred_proba])
        
        return y_pred_proba

    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        return self.model.feature_importance(importance_type='gain')

    def partial_fit(self, X: np.ndarray, y: np.ndarray):
        """
        Incremental learning.
        """
        if not self.is_trained:
            # First training
            self.train(X, y)
        else:
            # Continue training
            new_data = lgb.Dataset(X, label=y)
            
            self.model = lgb.train(
                self.params,
                new_data,
                num_boost_round=100,
                init_model=self.model
            )
            
            logger.info(f"Model updated with {len(X)} new samples")
