"""CatBoost model implementation."""

import numpy as np
from typing import Dict, Any, Optional
import logging

try:
    from catboost import CatBoostClassifier, Pool
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    logging.warning("CatBoost not installed. Install with: pip install catboost")

from .base_ml_model import BaseMLModel

logger = logging.getLogger(__name__)


class CatBoostModel(BaseMLModel):
    """
    CatBoost classifier for binary/multi-class classification.
    
    Features:
    - Automatic handling of categorical features
    - High accuracy
    - Feature importance
    - Early stopping
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not CATBOOST_AVAILABLE:
            raise ImportError("CatBoost not installed")
        
        # Default parameters
        params = {
            'iterations': 1000,
            'learning_rate': 0.05,
            'depth': 6,
            'loss_function': 'Logloss',
            'eval_metric': 'Accuracy',
            'random_seed': 42,
            'verbose': 100,
            'early_stopping_rounds': 50,
        }
        
        # Override with config
        freqai_config = config.get('freqai', {})
        model_params = freqai_config.get('model_params', {})
        if model_params:
            params.update(model_params)
        
        self.model = CatBoostClassifier(**params)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: Optional[np.ndarray] = None,
        y_valid: Optional[np.ndarray] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train CatBoost model.
        """
        logger.info(f"Training CatBoost with {len(X_train)} samples...")
        
        # Create pools
        train_pool = Pool(X_train, y_train)
        
        eval_set = None
        if X_valid is not None and y_valid is not None:
            eval_set = Pool(X_valid, y_valid)
        
        # Train model
        self.model.fit(
            train_pool,
            eval_set=eval_set,
            use_best_model=True if eval_set else False,
            plot=False
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
        
        y_pred = self.model.predict(X)
        
        return y_pred.astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        y_pred_proba = self.model.predict_proba(X)
        
        return y_pred_proba

    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        return self.model.get_feature_importance()

    def partial_fit(self, X: np.ndarray, y: np.ndarray):
        """
        Incremental learning (not directly supported by CatBoost).
        """
        logger.warning("CatBoost does not support true incremental learning. Retraining...")
        self.train(X, y)
