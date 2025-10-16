"""Base class for ML models."""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Optional
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)


class BaseMLModel(ABC):
    """
    Abstract base class for all ML models.
    
    All model implementations should inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.is_trained = False

    @abstractmethod
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: Optional[np.ndarray] = None,
        y_valid: Optional[np.ndarray] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_valid: Validation features (optional)
            y_valid: Validation labels (optional)
            **kwargs: Additional training parameters
            
        Returns:
            Dict with training metrics
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            X: Features
            
        Returns:
            Predictions (class labels)
        """
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities.
        
        Args:
            X: Features
            
        Returns:
            Class probabilities
        """
        pass

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model performance.
        
        Args:
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Dict with evaluation metrics
        """
        if not self.is_trained:
            raise ValueError("Model not trained! Call train() first.")
        
        y_pred = self.predict(X_test)
        y_pred_proba = self.predict_proba(X_test)
        
        metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)
        
        return metrics

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Calculate classification metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Predicted probabilities (optional)
            
        Returns:
            Dict with metrics
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'f1_score': f1_score(y_true, y_pred, average='weighted', zero_division=0),
            'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        # Add ROC AUC if probabilities available
        if y_pred_proba is not None:
            try:
                if y_pred_proba.ndim > 1 and y_pred_proba.shape[1] == 2:
                    # Binary classification
                    metrics['roc_auc'] = roc_auc_score(y_true, y_pred_proba[:, 1])
                else:
                    # Multi-class
                    metrics['roc_auc'] = roc_auc_score(
                        y_true, y_pred_proba, 
                        multi_class='ovr', average='weighted'
                    )
            except Exception:
                pass  # ROC AUC may not be computable in some cases
        
        return metrics

    def partial_fit(
        self,
        X: np.ndarray,
        y: np.ndarray
    ):
        """
        Incremental learning (online update).
        
        Default implementation re-trains the model.
        Override this method for models that support incremental learning.
        
        Args:
            X: New features
            y: New labels
        """
        # Default: retrain model
        # Subclasses can override for true incremental learning
        self.train(X, y)

    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        Get feature importance (if supported by model).
        
        Returns:
            Array of feature importances or None
        """
        return None

    def save(self, path: str):
        """
        Save model to disk.
        
        Args:
            path: Path to save model
        """
        import joblib
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str):
        """
        Load model from disk.
        
        Args:
            path: Path to model file
            
        Returns:
            Loaded model instance
        """
        import joblib
        return joblib.load(path)
