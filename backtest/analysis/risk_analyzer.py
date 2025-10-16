# -*- coding: utf-8 -*-
"""
Risk Analyzer - Análise avançada de risco para backtesting
Complementa o PerformanceAnalyzer com métricas específicas de risco
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class RiskAnalyzer:
    """
    Analisador avançado de risco para backtesting
    Foca em métricas específicas de gestão de risco
    """
    
    def __init__(self):
        print("[RISK_ANALYZER] Inicializado")
    
    def analyze_risk_metrics(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict[str, Any]:
        """
        Análise completa de métricas de risco
        """
        
        if not trades or not equity_curve:
            return {}
        
        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)
        
        risk_metrics = {
            **self._calculate_var_metrics(trades_df),
            **self._calculate_tail_risk_metrics(trades_df),
            **self._calculate_concentration_risk(trades_df)
        }
        
        return risk_metrics
    
    def _calculate_var_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula Value at Risk (VaR) e Expected Shortfall
        """
        
        if trades_df.empty:
            return {}
        
        returns = trades_df['return_pct'].values
        
        # VaR em diferentes níveis de confiança
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        # Expected Shortfall (CVaR)
        es_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else 0
        es_99 = np.mean(returns[returns <= var_99]) if len(returns[returns <= var_99]) > 0 else 0
        
        return {
            'var_95_pct': round(var_95, 2),
            'var_99_pct': round(var_99, 2),
            'expected_shortfall_95_pct': round(es_95, 2),
            'expected_shortfall_99_pct': round(es_99, 2)
        }
    
    def _calculate_tail_risk_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Métricas de risco de cauda
        """
        
        if trades_df.empty:
            return {}
        
        returns = trades_df['return_pct'].values
        
        # Tail ratio
        percentile_95 = np.percentile(returns, 95)
        percentile_5 = np.percentile(returns, 5)
        tail_ratio = abs(percentile_95) / abs(percentile_5) if percentile_5 != 0 else 0
        
        return {
            'tail_ratio': round(tail_ratio, 2),
            'worst_trade_pct': round(np.min(returns), 2),
            'best_trade_pct': round(np.max(returns), 2)
        }
    
    def _calculate_concentration_risk(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Análise de concentração de risco
        """
        
        if trades_df.empty:
            return {}
        
        # Concentração temporal
        if 'entry_time' in trades_df.columns:
            trades_df['hour'] = pd.to_datetime(trades_df['entry_time'], unit='ms').dt.hour
            hourly_concentration = trades_df.groupby('hour').size()
            max_hourly_concentration = hourly_concentration.max() / len(trades_df) if len(trades_df) > 0 else 0
        else:
            max_hourly_concentration = 0
        
        return {
            'max_hourly_concentration_pct': round(max_hourly_concentration * 100, 2)
        }