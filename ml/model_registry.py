"""Model Registry for managing trained ML models."""

import json
import joblib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


class ModelRegistry:
    """
    Registry for managing trained ML models.
    
    Features:
    - Save and load models
    - Version control
    - Model metadata tracking
    - Performance metrics storage
    """

    def __init__(self, base_path: str = "models"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.base_path / "registry.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """Load registry metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save registry metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def register_model(
        self,
        model_name: str,
        strategy_name: str,
        symbol: str,
        model_path: str,
        metrics: Dict[str, float],
        hyperparameters: Dict[str, Any] = None
    ) -> str:
        """
        Register a trained model in the registry.
        
        Args:
            model_name: Name of the model (e.g., 'LightGBMClassifier')
            strategy_name: Strategy name
            symbol: Trading pair symbol
            model_path: Path where model is saved
            metrics: Performance metrics
            hyperparameters: Model hyperparameters
            
        Returns:
            Model ID
        """
        model_id = f"{strategy_name}_{symbol}_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.metadata[model_id] = {
            'model_name': model_name,
            'strategy_name': strategy_name,
            'symbol': symbol,
            'model_path': model_path,
            'metrics': metrics,
            'hyperparameters': hyperparameters or {},
            'created_at': datetime.now().isoformat(),
            'version': len([k for k in self.metadata.keys() if k.startswith(f"{strategy_name}_{symbol}_{model_name}")]) + 1
        }
        
        self._save_metadata()
        print(f"✅ Model registered: {model_id}")
        
        return model_id

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get model information by ID."""
        return self.metadata.get(model_id)

    def get_latest_model(
        self,
        strategy_name: str,
        symbol: str,
        model_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get the latest model for a strategy and symbol.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            model_name: Optional model name filter
            
        Returns:
            Model metadata dict or None
        """
        matching_models = []
        
        for model_id, info in self.metadata.items():
            if info['strategy_name'] == strategy_name and info['symbol'] == symbol:
                if model_name is None or info['model_name'] == model_name:
                    matching_models.append((model_id, info))
        
        if not matching_models:
            return None
        
        # Sort by creation date
        matching_models.sort(key=lambda x: x[1]['created_at'], reverse=True)
        
        model_id, info = matching_models[0]
        return {'model_id': model_id, **info}

    def list_models(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        List all registered models with optional filters.
        
        Args:
            strategy_name: Filter by strategy
            symbol: Filter by symbol
            
        Returns:
            List of model metadata
        """
        models = []
        
        for model_id, info in self.metadata.items():
            if strategy_name and info['strategy_name'] != strategy_name:
                continue
            if symbol and info['symbol'] != symbol:
                continue
            
            models.append({'model_id': model_id, **info})
        
        # Sort by creation date
        models.sort(key=lambda x: x['created_at'], reverse=True)
        
        return models

    def compare_models(
        self,
        strategy_name: str,
        symbol: str,
        metric: str = 'accuracy'
    ) -> pd.DataFrame:
        """
        Compare models for a strategy and symbol.
        
        Args:
            strategy_name: Strategy name
            symbol: Trading pair
            metric: Metric to sort by
            
        Returns:
            DataFrame with model comparison
        """
        models = self.list_models(strategy_name=strategy_name, symbol=symbol)
        
        if not models:
            return pd.DataFrame()
        
        comparison = []
        for model in models:
            comparison.append({
                'model_id': model['model_id'],
                'model_name': model['model_name'],
                'version': model['version'],
                'created_at': model['created_at'],
                **model['metrics']
            })
        
        df = pd.DataFrame(comparison)
        
        if metric in df.columns:
            df = df.sort_values(by=metric, ascending=False)
        
        return df

    def delete_model(self, model_id: str):
        """
        Delete a model from registry.
        
        Args:
            model_id: Model ID to delete
        """
        if model_id in self.metadata:
            model_info = self.metadata[model_id]
            model_path = Path(model_info['model_path'])
            
            # Delete model file
            if model_path.exists():
                model_path.unlink()
            
            # Remove from metadata
            del self.metadata[model_id]
            self._save_metadata()
            
            print(f"✅ Model deleted: {model_id}")
        else:
            print(f"⚠️ Model not found: {model_id}")
