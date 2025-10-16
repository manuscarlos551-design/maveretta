"""Data Drawer for model storage and versioning."""

import joblib
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataDrawer:
    """
    Data Drawer for saving and loading ML models.
    
    Responsibilities:
    - Save trained models
    - Load models for prediction
    - Manage model versions
    - Store model metadata
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models_dir = Path(config.get('models_path', 'models'))
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        model: Any,
        strategy_name: str,
        symbol: str,
        metrics: Dict[str, float],
        model_name: str = None
    ) -> str:
        """
        Save a trained model to disk.
        
        Args:
            model: Trained model object
            strategy_name: Strategy name
            symbol: Trading pair
            metrics: Performance metrics
            model_name: Optional custom model name
            
        Returns:
            Path to saved model
        """
        # Create model directory
        symbol_clean = symbol.replace('/', '_')
        model_dir = self.models_dir / strategy_name / symbol_clean
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate model filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if model_name:
            filename = f"{model_name}_{timestamp}.pkl"
        else:
            filename = f"model_{timestamp}.pkl"
        
        model_path = model_dir / filename
        
        # Save model
        joblib.dump(model, model_path)
        
        # Save metadata
        metadata = {
            'strategy_name': strategy_name,
            'symbol': symbol,
            'model_name': model_name or 'unknown',
            'model_type': type(model).__name__,
            'saved_at': timestamp,
            'metrics': metrics,
            'model_path': str(model_path)
        }
        
        metadata_path = model_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Model saved: {model_path}")
        
        return str(model_path)

    def load_model(self, model_path: str) -> Any:
        """
        Load a model from disk.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Loaded model object
        """
        model_path = Path(model_path)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        model = joblib.load(model_path)
        
        logger.info(f"✅ Model loaded: {model_path}")
        
        return model

    def load_latest_model(
        self,
        strategy_name: str,
        symbol: str
    ) -> Optional[Any]:
        """
        Load the latest model for a strategy and symbol.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            
        Returns:
            Loaded model or None if not found
        """
        symbol_clean = symbol.replace('/', '_')
        model_dir = self.models_dir / strategy_name / symbol_clean
        
        if not model_dir.exists():
            logger.warning(f"No models found for {strategy_name}/{symbol}")
            return None
        
        # Find latest model
        model_files = list(model_dir.glob('*.pkl'))
        
        if not model_files:
            logger.warning(f"No model files found in {model_dir}")
            return None
        
        # Sort by modification time
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
        
        return self.load_model(str(latest_model))

    def get_model_metadata(self, model_path: str) -> Optional[Dict]:
        """
        Get metadata for a saved model.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Metadata dict or None
        """
        metadata_path = Path(model_path).with_suffix('.json')
        
        if not metadata_path.exists():
            logger.warning(f"Metadata not found: {metadata_path}")
            return None
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return metadata

    def list_models(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> list:
        """
        List all saved models.
        
        Args:
            strategy_name: Filter by strategy (optional)
            symbol: Filter by symbol (optional)
            
        Returns:
            List of model paths
        """
        if strategy_name and symbol:
            symbol_clean = symbol.replace('/', '_')
            search_dir = self.models_dir / strategy_name / symbol_clean
        elif strategy_name:
            search_dir = self.models_dir / strategy_name
        else:
            search_dir = self.models_dir
        
        if not search_dir.exists():
            return []
        
        model_files = list(search_dir.rglob('*.pkl'))
        return [str(p) for p in model_files]

    def delete_model(self, model_path: str):
        """
        Delete a saved model and its metadata.
        
        Args:
            model_path: Path to model file
        """
        model_path = Path(model_path)
        metadata_path = model_path.with_suffix('.json')
        
        # Delete model file
        if model_path.exists():
            model_path.unlink()
            logger.info(f"✅ Model deleted: {model_path}")
        
        # Delete metadata
        if metadata_path.exists():
            metadata_path.unlink()
            logger.info(f"✅ Metadata deleted: {metadata_path}")
