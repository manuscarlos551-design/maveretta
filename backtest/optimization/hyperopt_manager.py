# -*- coding: utf-8 -*-
"""
Hyperopt Manager - Sistema de otimização com Optuna
Otimização automática de parâmetros de estratégia
"""

import optuna
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import json
import sqlite3
from pathlib import Path

from ..engine.backtest_engine import BacktestEngine


class HyperoptManager:
    """
    Gerenciador de hyperoptimization usando Optuna
    Otimiza parâmetros de estratégia automaticamente
    """
    
    def __init__(self, study_name: str = None, storage_path: str = "data/optuna_studies.db"):
        self.study_name = study_name or f"backtest_study_{int(datetime.now().timestamp())}"
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Storage SQLite para persistência
        self.storage_url = f"sqlite:///{self.storage_path}"
        
        # Engine de backtesting
        self.backtest_engine = BacktestEngine()
        
        # Configurações de otimização
        self.optimization_config = {
            'n_trials': 100,
            'timeout': 3600,  # 1 hora
            'sampler': 'TPE',  # Tree-structured Parzen Estimator
            'direction': 'maximize'  # Maximiza Sharpe ratio por padrão
        }
        
        print(f"[HYPEROPT_MANAGER] Inicializado - Study: {self.study_name}")
    
    def optimize_strategy(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        parameter_space: Dict[str, Any] = None,
        optimization_metric: str = 'sharpe_ratio',
        n_trials: int = 100
    ) -> Dict[str, Any]:
        """
        Otimiza parâmetros de estratégia usando Optuna
        """
        
        print(f"[HYPEROPT_MANAGER] 🎯 Iniciando otimização para {symbol}")
        print(f"[HYPEROPT_MANAGER] Período: {start_date} - {end_date}")
        print(f"[HYPEROPT_MANAGER] Trials: {n_trials}")
        print(f"[HYPEROPT_MANAGER] Métrica: {optimization_metric}")
        
        # Define espaço de parâmetros se não fornecido
        if parameter_space is None:
            parameter_space = self._get_default_parameter_space()
        
        # Cria study
        study = optuna.create_study(
            study_name=f"{self.study_name}_{symbol.replace('/', '_')}",
            storage=self.storage_url,
            load_if_exists=True,
            direction='maximize' if optimization_metric in ['sharpe_ratio', 'total_return', 'win_rate'] else 'minimize'
        )
        
        # Define função objetivo
        def objective(trial):
            return self._objective_function(
                trial, symbol, start_date, end_date, 
                parameter_space, optimization_metric
            )
        
        # Executa otimização
        try:
            study.optimize(objective, n_trials=n_trials, timeout=3600)
            
            # Compila resultados
            results = {
                'study_name': study.study_name,
                'best_params': study.best_params,
                'best_value': study.best_value,
                'n_trials': len(study.trials),
                'optimization_metric': optimization_metric,
                'optimization_history': self._get_optimization_history(study),
                'parameter_importance': optuna.importance.get_param_importances(study),
                'symbol': symbol,
                'period': f"{start_date} - {end_date}"
            }
            
            print(f"[HYPEROPT_MANAGER] ✅ Otimização concluída!")
            print(f"[HYPEROPT_MANAGER] Melhor {optimization_metric}: {study.best_value:.4f}")
            print(f"[HYPEROPT_MANAGER] Melhores parâmetros: {study.best_params}")
            
            return results
            
        except Exception as e:
            print(f"[HYPEROPT_MANAGER] ❌ Erro na otimização: {e}")
            raise
    
    def _objective_function(
        self,
        trial,
        symbol: str,
        start_date: str,
        end_date: str,
        parameter_space: Dict[str, Any],
        metric: str
    ) -> float:
        """
        Função objetivo para otimização
        """
        
        # Sugere parâmetros baseado no espaço definido
        params = {}
        
        for param_name, param_config in parameter_space.items():
            param_type = param_config['type']
            
            if param_type == 'float':
                params[param_name] = trial.suggest_float(
                    param_name,
                    param_config['min'],
                    param_config['max'],
                    step=param_config.get('step', None)
                )
            elif param_type == 'int':
                params[param_name] = trial.suggest_int(
                    param_name,
                    param_config['min'],
                    param_config['max']
                )
            elif param_type == 'categorical':
                params[param_name] = trial.suggest_categorical(
                    param_name,
                    param_config['choices']
                )
        
        try:
            # Executa backtest com parâmetros sugeridos
            backtest_results = self.backtest_engine.run_backtest(
                symbol, start_date, end_date, params
            )
            
            # Extrai métrica objetivo
            performance = backtest_results['performance_metrics']
            
            metric_value = performance.get(metric, 0.0)
            
            # Adiciona penalizações se necessário
            penalty = 0.0
            
            # Penaliza se muito poucos trades
            if performance.get('total_trades', 0) < 10:
                penalty += 0.1
            
            # Penaliza drawdown muito alto
            if performance.get('max_drawdown_pct', 0) > 20:
                penalty += 0.2
            
            final_score = metric_value - penalty
            
            # Log do trial
            trial_info = f"Trial {trial.number}: {metric}={metric_value:.4f} (penalty={penalty:.4f})"
            print(f"[HYPEROPT_MANAGER] {trial_info}")
            
            return final_score
            
        except Exception as e:
            print(f"[HYPEROPT_MANAGER] ❌ Erro no trial {trial.number}: {e}")
            # Retorna valor muito baixo para trials com erro
            return -999.0
    
    def _get_default_parameter_space(self) -> Dict[str, Any]:
        """
        Espaço de parâmetros padrão baseado no sistema existente
        """
        return {
            'risk_per_trade': {
                'type': 'float',
                'min': 0.005,
                'max': 0.05,
                'step': 0.005
            },
            'take_profit': {
                'type': 'float',
                'min': 0.05,
                'max': 0.25,
                'step': 0.01
            },
            'stop_loss': {
                'type': 'float',
                'min': 0.01,
                'max': 0.08,
                'step': 0.005
            },
            'ai_threshold': {
                'type': 'float',
                'min': 0.60,
                'max': 0.90,
                'step': 0.05
            },
            'max_trades_per_day': {
                'type': 'int',
                'min': 5,
                'max': 20
            }
        }
    
    def _get_optimization_history(self, study) -> List[Dict]:
        """
        Extrai histórico de otimização
        """
        history = []
        
        for trial in study.trials:
            history.append({
                'trial_number': trial.number,
                'value': trial.value,
                'params': trial.params,
                'state': trial.state.name,
                'duration': trial.duration.total_seconds() if trial.duration else None
            })
        
        return history
    
    def run_walk_forward_optimization(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        optimization_window_days: int = 30,
        test_window_days: int = 7,
        n_trials_per_window: int = 50
    ) -> Dict[str, Any]:
        """
        Executa otimização walk-forward
        """
        
        print(f"[HYPEROPT_MANAGER] 🔄 Walk-Forward Optimization iniciado")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        results = []
        current_date = start_dt
        
        while current_date < end_dt:
            # Janela de otimização
            opt_start = current_date
            opt_end = current_date + timedelta(days=optimization_window_days)
            
            # Janela de teste
            test_start = opt_end
            test_end = opt_end + timedelta(days=test_window_days)
            
            if test_end > end_dt:
                break
            
            print(f"[HYPEROPT_MANAGER] Otimizando: {opt_start.date()} - {opt_end.date()}")
            
            # Otimiza na janela de otimização
            opt_results = self.optimize_strategy(
                symbol,
                opt_start.strftime("%Y-%m-%d"),
                opt_end.strftime("%Y-%m-%d"),
                n_trials=n_trials_per_window
            )
            
            # Testa com parâmetros otimizados
            print(f"[HYPEROPT_MANAGER] Testando: {test_start.date()} - {test_end.date()}")
            
            test_results = self.backtest_engine.run_backtest(
                symbol,
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d"),
                opt_results['best_params']
            )
            
            results.append({
                'optimization_period': f"{opt_start.date()} - {opt_end.date()}",
                'test_period': f"{test_start.date()} - {test_end.date()}",
                'best_params': opt_results['best_params'],
                'optimization_score': opt_results['best_value'],
                'test_performance': test_results['performance_metrics']
            })
            
            current_date = test_end
        
        # Calcula métricas agregadas
        aggregate_metrics = self._calculate_wf_aggregate_metrics(results)
        
        walk_forward_results = {
            'results': results,
            'aggregate_metrics': aggregate_metrics,
            'total_periods': len(results),
            'symbol': symbol,
            'full_period': f"{start_date} - {end_date}"
        }
        
        print(f"[HYPEROPT_MANAGER] ✅ Walk-Forward concluído: {len(results)} períodos")
        return walk_forward_results
    
    def _calculate_wf_aggregate_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Calcula métricas agregadas do walk-forward
        """
        
        if not results:
            return {}
        
        # Extrai métricas de teste
        test_returns = []
        test_sharpe_ratios = []
        test_win_rates = []
        test_max_drawdowns = []
        
        for result in results:
            perf = result['test_performance']
            test_returns.append(perf.get('total_return_pct', 0))
            test_sharpe_ratios.append(perf.get('sharpe_ratio', 0))
            test_win_rates.append(perf.get('win_rate', 0))
            test_max_drawdowns.append(perf.get('max_drawdown_pct', 0))
        
        return {
            'avg_return_pct': np.mean(test_returns),
            'std_return_pct': np.std(test_returns),
            'avg_sharpe_ratio': np.mean(test_sharpe_ratios),
            'avg_win_rate': np.mean(test_win_rates),
            'avg_max_drawdown_pct': np.mean(test_max_drawdowns),
            'consistency_score': len([r for r in test_returns if r > 0]) / len(test_returns),
            'total_periods': len(results)
        }
    
    def get_study_statistics(self, study_name: str = None) -> Dict[str, Any]:
        """
        Obtém estatísticas de um study
        """
        
        study_name = study_name or self.study_name
        
        try:
            study = optuna.load_study(
                study_name=study_name,
                storage=self.storage_url
            )
            
            trials_df = study.trials_dataframe()
            
            return {
                'study_name': study_name,
                'n_trials': len(study.trials),
                'best_value': study.best_value,
                'best_params': study.best_params,
                'trials_summary': {
                    'complete': len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
                    'failed': len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
                    'pruned': len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])
                },
                'value_statistics': {
                    'mean': trials_df['value'].mean() if not trials_df.empty else 0,
                    'std': trials_df['value'].std() if not trials_df.empty else 0,
                    'min': trials_df['value'].min() if not trials_df.empty else 0,
                    'max': trials_df['value'].max() if not trials_df.empty else 0
                }
            }
            
        except Exception as e:
            print(f"[HYPEROPT_MANAGER] ❌ Erro obtendo estatísticas: {e}")
            return {}
    
    def list_studies(self) -> List[str]:
        """
        Lista todos os studies disponíveis
        """
        try:
            studies = optuna.get_all_study_summaries(storage=self.storage_url)
            return [study.study_name for study in studies]
        except Exception as e:
            print(f"[HYPEROPT_MANAGER] ❌ Erro listando studies: {e}")
            return []
    
    def delete_study(self, study_name: str) -> bool:
        """
        Deleta um study
        """
        try:
            optuna.delete_study(study_name=study_name, storage=self.storage_url)
            print(f"[HYPEROPT_MANAGER] ✅ Study {study_name} deletado")
            return True
        except Exception as e:
            print(f"[HYPEROPT_MANAGER] ❌ Erro deletando study: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Status do gerenciador de hyperopt
        """
        return {
            'current_study': self.study_name,
            'storage_path': str(self.storage_path),
            'available_studies': self.list_studies(),
            'optimization_config': self.optimization_config
        }