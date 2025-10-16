"""FreqAI Interface - Main interface for ML training and predictions."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from .data_kitchen import DataKitchen
from .data_drawer import DataDrawer
from .feature_engineering import FeatureEngineering
from .base_models import LightGBMModel, XGBoostModel, CatBoostModel

logger = logging.getLogger(__name__)


class FreqAIInterface:
    """
    Main interface for FreqAI system.
    
    Features:
    - Automatic ML model training
    - Feature engineering
    - Model versioning
    - Backtesting with ML
    - Online learning
    - Model comparison
    """

    AVAILABLE_MODELS = {
        'LightGBMClassifier': LightGBMModel,
        'XGBoostClassifier': XGBoostModel,
        'CatBoostClassifier': CatBoostModel,
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.freqai_enabled = config.get('freqai', {}).get('enabled', False)
        
        # Initialize components
        self.data_kitchen = DataKitchen(config)
        self.data_drawer = DataDrawer(config)
        self.feature_engineering = FeatureEngineering(config)
        
        # Current model
        self.current_model = None
        self.current_model_name = None
        self.model_metadata = {}

    def train(
        self,
        strategy_name: str,
        symbol: str,
        timerange: str,
        model_name: str = 'LightGBMClassifier',
        timeframe: str = '5m',
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train an ML model for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading pair (e.g., 'BTC/USDT')
            timerange: Time range (e.g., '20240101-20241001')
            model_name: Model to train
            timeframe: Candle timeframe
            test_size: Test set proportion
            
        Returns:
            Dict with training results and metrics
        """
        logger.info(f"🎯 Starting ML training for {strategy_name} on {symbol}")
        logger.info(f"Model: {model_name}, Timeframe: {timeframe}, Timerange: {timerange}")
        
        # 1. Prepare data
        logger.info("📊 Step 1/6: Preparing data...")
        data = self.data_kitchen.prepare_data(
            symbol=symbol,
            timerange=timerange,
            strategy=strategy_name,
            timeframe=timeframe
        )
        
        if len(data) == 0:
            raise ValueError("No data available for training")
        
        logger.info(f"Loaded {len(data)} candles")
        
        # 2. Feature engineering
        logger.info("🔧 Step 2/6: Creating features...")
        features = self.feature_engineering.create_features(data, include_labels=True)
        
        X = features['X']
        y = features['y']
        feature_names = features['feature_names']
        
        logger.info(f"Created {len(feature_names)} features")
        
        # 3. Split data
        logger.info("✂️ Step 3/6: Splitting data...")
        X_train, X_test, y_train, y_test = self._split_data(X, y, test_size=test_size)
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # 4. Train model
        logger.info(f"🤖 Step 4/6: Training {model_name}...")
        
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model {model_name} not available. Choose from: {list(self.AVAILABLE_MODELS.keys())}")
        
        model_class = self.AVAILABLE_MODELS[model_name]
        model = model_class(self.config)
        
        # Use 20% of training data for validation during training
        val_split = int(len(X_train) * 0.8)
        X_train_fit = X_train[:val_split]
        y_train_fit = y_train[:val_split]
        X_val = X_train[val_split:]
        y_val = y_train[val_split:]
        
        train_metrics = model.train(
            X_train=X_train_fit,
            y_train=y_train_fit,
            X_valid=X_val,
            y_valid=y_val
        )
        
        # 5. Evaluate model
        logger.info("📈 Step 5/6: Evaluating model...")
        test_metrics = model.evaluate(X_test, y_test)
        
        logger.info(f"Test Accuracy: {test_metrics['accuracy']:.4f}")
        logger.info(f"Test F1 Score: {test_metrics['f1_score']:.4f}")
        
        # 6. Save model
        logger.info("💾 Step 6/6: Saving model...")
        model_path = self.data_drawer.save_model(
            model=model,
            strategy_name=strategy_name,
            symbol=symbol,
            metrics=test_metrics,
            model_name=model_name
        )
        
        # Update current model
        self.current_model = model
        self.current_model_name = model_name
        self.model_metadata = {
            'strategy': strategy_name,
            'symbol': symbol,
            'model_name': model_name,
            'timeframe': timeframe,
            'trained_at': datetime.now().isoformat(),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'num_features': len(feature_names),
            'feature_names': feature_names,
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'model_path': model_path
        }
        
        logger.info("✅ Training complete!")
        
        return self.model_metadata

    def predict(
        self,
        dataframe: pd.DataFrame,
        return_proba: bool = False
    ) -> np.ndarray:
        """
        Make predictions using trained model.
        
        Args:
            dataframe: DataFrame with OHLCV data
            return_proba: Return probabilities instead of labels
            
        Returns:
            Predictions array
        """
        if self.current_model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        # Feature engineering
        features = self.feature_engineering.create_features(dataframe, include_labels=False)
        X = features['X']
        
        # Predict
        if return_proba:
            predictions = self.current_model.predict_proba(X)
        else:
            predictions = self.current_model.predict(X)
        
        return predictions

    def load_model(
        self,
        strategy_name: str,
        symbol: str,
        model_path: Optional[str] = None
    ):
        """
        Load a trained model.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            model_path: Path to model file (optional, loads latest if not specified)
        """
        if model_path:
            self.current_model = self.data_drawer.load_model(model_path)
            metadata = self.data_drawer.get_model_metadata(model_path)
        else:
            self.current_model = self.data_drawer.load_latest_model(strategy_name, symbol)
            metadata = {}
        
        if self.current_model is None:
            raise ValueError(f"No model found for {strategy_name}/{symbol}")
        
        self.model_metadata = metadata
        logger.info(f"✅ Model loaded for {strategy_name}/{symbol}")

    def online_update(
        self,
        new_data: pd.DataFrame
    ):
        """
        Update model with new data (online learning).
        
        Args:
            new_data: DataFrame with new OHLCV data and labels
        """
        if self.current_model is None:
            raise ValueError("No model loaded")
        
        # Feature engineering
        features = self.feature_engineering.create_features(new_data, include_labels=True)
        X = features['X']
        y = features['y']
        
        # Update model
        self.current_model.partial_fit(X, y)
        
        logger.info(f"✅ Model updated with {len(X)} new samples")

    def compare_models(
        self,
        strategy_name: str,
        symbol: str,
        timerange: str,
        models: List[str] = None,
        timeframe: str = '5m'
    ) -> pd.DataFrame:
        """
        Compare performance of multiple models.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            timerange: Time range for training
            models: List of model names (None = all available)
            timeframe: Candle timeframe
            
        Returns:
            DataFrame with model comparison
        """
        if models is None:
            models = list(self.AVAILABLE_MODELS.keys())
        
        logger.info(f"🔬 Comparing {len(models)} models...")
        
        results = []
        
        for model_name in models:
            logger.info(f"\n--- Testing {model_name} ---")
            
            try:
                metrics = self.train(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    timerange=timerange,
                    model_name=model_name,
                    timeframe=timeframe
                )
                
                results.append({
                    'model': model_name,
                    'accuracy': metrics['test_metrics']['accuracy'],
                    'f1_score': metrics['test_metrics']['f1_score'],
                    'precision': metrics['test_metrics']['precision'],
                    'recall': metrics['test_metrics']['recall'],
                    'train_samples': metrics['train_samples'],
                    'num_features': metrics['num_features']
                })
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
                results.append({
                    'model': model_name,
                    'error': str(e)
                })
        
        comparison = pd.DataFrame(results)
        
        # Sort by F1 score (descending)
        if 'f1_score' in comparison.columns:
            comparison = comparison.sort_values('f1_score', ascending=False)
        
        logger.info("\n📊 Model Comparison:")
        print(comparison.to_string(index=False))
        
        return comparison

    def backtest_with_ml(
        self,
        strategy_name: str,
        symbol: str,
        timerange: str,
        timeframe: str = '5m'
    ) -> Dict[str, Any]:
        """
        Run backtest using ML predictions.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            timerange: Time range for backtesting
            timeframe: Candle timeframe
            
        Returns:
            Backtest results
        """
        if self.current_model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        logger.info(f"🔄 Running backtest with ML for {strategy_name} on {symbol}")
        
        # Prepare data
        data = self.data_kitchen.prepare_data(
            symbol=symbol,
            timerange=timerange,
            strategy=strategy_name,
            timeframe=timeframe
        )
        
        # Get predictions
        predictions = self.predict(data)
        predictions_proba = self.predict(data, return_proba=True)
        
        # Add predictions to dataframe
        data['ml_prediction'] = predictions
        if predictions_proba.ndim > 1:
            data['ml_confidence'] = predictions_proba[:, 1]
        else:
            data['ml_confidence'] = predictions_proba
        
        # TODO: Integrate with existing backtest runner
        # For now, return basic statistics
        results = {
            'symbol': symbol,
            'timerange': timerange,
            'total_signals': int(np.sum(predictions == 1)),
            'signal_rate': float(np.mean(predictions)),
            'avg_confidence': float(np.mean(data['ml_confidence'])),
            'data_points': len(data)
        }
        
        logger.info(f"✅ Backtest complete. Signals: {results['total_signals']}")
        
        return results

    def _split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into train and test sets (time-series split, no shuffle).
        """
        split_idx = int(len(X) * (1 - test_size))
        
        X_train = X[:split_idx]
        X_test = X[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]
        
        return X_train, X_test, y_train, y_test

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance from current model.
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            DataFrame with feature importance
        """
        if self.current_model is None:
            raise ValueError("No model loaded")
        
        importance = self.current_model.get_feature_importance()
        
        if importance is None:
            logger.warning("Model does not support feature importance")
            return pd.DataFrame()
        
        feature_names = self.model_metadata.get('feature_names', [])
        
        if isinstance(importance, dict):
            # XGBoost returns dict
            importance_df = pd.DataFrame([
                {'feature': k, 'importance': v}
                for k, v in importance.items()
            ])
        else:
            # LightGBM, CatBoost return array
            if len(feature_names) != len(importance):
                feature_names = [f'feature_{i}' for i in range(len(importance))]
            
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importance
            })
        
        importance_df = importance_df.sort_values('importance', ascending=False)
        
        return importance_df.head(top_n)
