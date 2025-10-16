"""XGBoost model implementation."""

import numpy as np
from typing import Dict, Any, Optional
import logging

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not installed. Install with: pip install xgboost")

from .base_ml_model import BaseMLModel

logger = logging.getLogger(__name__)


class XGBoostModel(BaseMLModel):
    """
    XGBoost classifier for binary/multi-class classification.
    
    Features:
    - High performance
    - Feature importance
    - Early stopping
    - GPU support
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not installed")
        
        # Default parameters
        self.params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.9,
            'min_child_weight': 1,
            'verbosity': 1,
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
        Train XGBoost model.
        """
        logger.info(f"Training XGBoost with {len(X_train)} samples...")
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        evals = [(dtrain, 'train')]
        
        if X_valid is not None and y_valid is not None:
            dvalid = xgb.DMatrix(X_valid, label=y_valid)
            evals.append((dvalid, 'valid'))
        
        # Train model
        evals_result = {}
        
        self.model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=evals,
            early_stopping_rounds=early_stopping_rounds if X_valid is not None else None,
            evals_result=evals_result,
            verbose_eval=100
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
        
        dtest = xgb.DMatrix(X)
        y_pred_proba = self.model.predict(dtest)
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        return y_pred

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        dtest = xgb.DMatrix(X)
        y_pred_proba = self.model.predict(dtest)
        
        # Convert to 2D array for binary classification
        if y_pred_proba.ndim == 1:
            y_pred_proba = np.column_stack([1 - y_pred_proba, y_pred_proba])
        
        return y_pred_proba

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance.
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")
        
        return self.model.get_score(importance_type='gain')

    def partial_fit(self, X: np.ndarray, y: np.ndarray):
        """
        Incremental learning.
        """
        if not self.is_trained:
            # First training
            self.train(X, y)
        else:
            # Continue training
            dnew = xgb.DMatrix(X, label=y)
            
            self.model = xgb.train(
                self.params,
                dnew,
                num_boost_round=100,
                xgb_model=self.model
            )
            
            logger.info(f"Model updated with {len(X)} new samples")
