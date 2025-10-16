"""
Parameter Optimizer Module
Provides parameter optimization functionality for trading strategies
"""

import logging
from typing import Dict, Any, List, Tuple
import optuna
import numpy as np

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """
    Handles parameter optimization for trading strategies using Optuna
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.study = None
        
    def create_study(self, study_name: str = "strategy_optimization"):
        """Create optimization study"""
        try:
            self.study = optuna.create_study(
                direction="maximize",
                study_name=study_name
            )
            logger.info(f"Created optimization study: {study_name}")
        except Exception as e:
            logger.error(f"Error creating study: {e}")
            
    def optimize_parameters(self, 
                          objective_func, 
                          n_trials: int = 100,
                          timeout: int = None) -> Dict[str, Any]:
        """
        Run parameter optimization
        
        Args:
            objective_func: Function to optimize
            n_trials: Number of optimization trials
            timeout: Timeout in seconds
            
        Returns:
            Dict with best parameters and results
        """
        if not self.study:
            self.create_study()
            
        try:
            self.study.optimize(
                objective_func,
                n_trials=n_trials,
                timeout=timeout
            )
            
            best_params = self.study.best_params
            best_value = self.study.best_value
            
            logger.info(f"Optimization completed. Best value: {best_value}")
            
            return {
                "best_params": best_params,
                "best_value": best_value,
                "n_trials": len(self.study.trials)
            }
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
            return {}
            
    def suggest_parameters(self, trial) -> Dict[str, Any]:
        """Suggest parameters for optimization trial"""
        params = {}
        
        # Example parameter ranges - adjust based on your strategy
        params['risk_per_trade'] = trial.suggest_float('risk_per_trade', 0.001, 0.02)
        params['take_profit'] = trial.suggest_float('take_profit', 0.01, 0.20)
        params['stop_loss'] = trial.suggest_float('stop_loss', 0.005, 0.10)
        
        return params
        
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization trial history"""
        if not self.study:
            return []
            
        trials = []
        for trial in self.study.trials:
            trials.append({
                "number": trial.number,
                "value": trial.value,
                "params": trial.params,
                "state": trial.state.name
            })
            
        return trials

# Factory function for easy import
def create_optimizer(config: Dict[str, Any] = None) -> ParameterOptimizer:
    """Factory function to create parameter optimizer"""
    return ParameterOptimizer(config)