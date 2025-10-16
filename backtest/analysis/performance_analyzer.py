# -*- coding: utf-8 -*-
"""
Performance Analyzer - Análise avançada de performance
Métricas completas de backtesting compatível com Freqtrade
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import math


class PerformanceAnalyzer:
    """
    Analisador avançado de performance para backtesting
    Métricas compatíveis com padrões da indústria
    """
    
    def __init__(self):
        # Configurações
        self.risk_free_rate = 0.02  # 2% ao ano
        self.trading_days_per_year = 365  # Crypto trade 24/7
        
        print("[PERFORMANCE_ANALYZER] Inicializado com métricas avançadas")
    
    def calculate_metrics(
        self, 
        trades: List[Dict], 
        equity_curve: List[Dict], 
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Calcula métricas completas de performance
        """
        
        if not trades or not equity_curve:
            return self._empty_metrics()
        
        # Converte para DataFrames para facilitar cálculos
        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)
        
        # Métricas básicas
        basic_metrics = self._calculate_basic_metrics(trades_df, equity_df, initial_capital)
        
        # Métricas de risco
        risk_metrics = self._calculate_risk_metrics(trades_df, equity_df, initial_capital)
        
        # Métricas de drawdown
        drawdown_metrics = self._calculate_drawdown_metrics(equity_df)
        
        # Métricas de distribuição
        distribution_metrics = self._calculate_distribution_metrics(trades_df)
        
        # Métricas de tempo
        time_metrics = self._calculate_time_metrics(trades_df)
        
        # Combina todas as métricas
        all_metrics = {
            **basic_metrics,
            **risk_metrics,
            **drawdown_metrics,
            **distribution_metrics,
            **time_metrics
        }
        
        print(f"[PERFORMANCE_ANALYZER] ✅ Métricas calculadas - {len(trades)} trades analisados")
        return all_metrics
    
    def _calculate_basic_metrics(self, trades_df: pd.DataFrame, equity_df: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        """
        Métricas básicas de trading
        """
        
        total_trades = len(trades_df)
        if total_trades == 0:
            return {}
        
        # PnL
        total_pnl = trades_df['net_pnl'].sum()
        final_capital = initial_capital + total_pnl
        
        # Returns
        total_return = (final_capital - initial_capital) / initial_capital
        total_return_pct = total_return * 100
        
        # Win/Loss
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Average trades
        avg_win = winning_trades['net_pnl'].mean() if win_count > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if loss_count > 0 else 0
        
        # Profit factor
        gross_profit = winning_trades['net_pnl'].sum() if win_count > 0 else 0
        gross_loss = abs(losing_trades['net_pnl'].sum()) if loss_count > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': round(win_rate, 4),
            'total_pnl': round(total_pnl, 2),
            'total_return': round(total_return, 4),
            'total_return_pct': round(total_return_pct, 2),
            'initial_capital': initial_capital,
            'final_capital': round(final_capital, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2)
        }
    
    def _calculate_risk_metrics(self, trades_df: pd.DataFrame, equity_df: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        """
        Métricas de risco
        """
        
        if equity_df.empty:
            return {}
        
        # Calcula retornos diários
        equity_values = equity_df['equity'].values
        daily_returns = np.diff(equity_values) / equity_values[:-1]
        
        # Remove valores infinitos/NaN
        daily_returns = daily_returns[np.isfinite(daily_returns)]
        
        if len(daily_returns) == 0:
            return {'sharpe_ratio': 0, 'sortino_ratio': 0, 'calmar_ratio': 0}
        
        # Sharpe Ratio
        excess_returns = daily_returns - (self.risk_free_rate / self.trading_days_per_year)
        sharpe_ratio = np.mean(excess_returns) / np.std(daily_returns) * np.sqrt(self.trading_days_per_year) if np.std(daily_returns) > 0 else 0
        
        # Sortino Ratio
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0
        sortino_ratio = np.mean(excess_returns) / downside_deviation * np.sqrt(self.trading_days_per_year) if downside_deviation > 0 else 0
        
        # Volatilidade anualizada
        volatility = np.std(daily_returns) * np.sqrt(self.trading_days_per_year)
        
        return {
            'sharpe_ratio': round(sharpe_ratio, 4),
            'sortino_ratio': round(sortino_ratio, 4),
            'volatility': round(volatility, 4),
            'daily_returns_mean': round(np.mean(daily_returns), 6),
            'daily_returns_std': round(np.std(daily_returns), 6)
        }
    
    def _calculate_drawdown_metrics(self, equity_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Métricas de drawdown
        """
        
        if equity_df.empty:
            return {}
        
        equity_values = equity_df['equity'].values
        
        # Calcula drawdown
        peak = np.maximum.accumulate(equity_values)
        drawdown = (equity_values - peak) / peak
        
        # Max drawdown
        max_drawdown = np.min(drawdown)
        max_drawdown_pct = max_drawdown * 100
        
        # Calcula duração do drawdown
        drawdown_periods = []
        in_drawdown = False
        start_period = 0
        
        for i, dd in enumerate(drawdown):
            if dd < -0.001 and not in_drawdown:  # Inicia drawdown (>0.1%)
                in_drawdown = True
                start_period = i
            elif dd >= -0.001 and in_drawdown:  # Termina drawdown
                in_drawdown = False
                drawdown_periods.append(i - start_period)
        
        # Se ainda está em drawdown
        if in_drawdown:
            drawdown_periods.append(len(drawdown) - start_period)
        
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        avg_drawdown_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        
        # Calmar Ratio (Return anualizado / Max Drawdown)
        total_return_pct = (equity_values[-1] - equity_values[0]) / equity_values[0] * 100
        calmar_ratio = abs(total_return_pct / max_drawdown_pct) if max_drawdown_pct != 0 else 0
        
        return {
            'max_drawdown': round(max_drawdown, 4),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'max_drawdown_duration': max_drawdown_duration,
            'avg_drawdown_duration': round(avg_drawdown_duration, 1),
            'calmar_ratio': round(calmar_ratio, 4),
            'total_drawdown_periods': len(drawdown_periods)
        }
    
    def _calculate_distribution_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Métricas de distribuição dos trades
        """
        
        if trades_df.empty:
            return {}
        
        returns = trades_df['return_pct'].values
        
        # Estatísticas descritivas
        mean_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        
        # Skewness e Kurtosis
        skewness = self._calculate_skewness(returns)
        kurtosis = self._calculate_kurtosis(returns)
        
        # Percentis
        percentiles = np.percentile(returns, [5, 25, 75, 95])
        
        # Maior sequência de wins/losses
        max_consecutive_wins = self._calculate_max_consecutive(trades_df, 'win')
        max_consecutive_losses = self._calculate_max_consecutive(trades_df, 'loss')
        
        return {
            'mean_return_pct': round(mean_return, 2),
            'median_return_pct': round(median_return, 2),
            'std_return_pct': round(std_return, 2),
            'skewness': round(skewness, 4),
            'kurtosis': round(kurtosis, 4),
            'return_5th_percentile': round(percentiles[0], 2),
            'return_25th_percentile': round(percentiles[1], 2),
            'return_75th_percentile': round(percentiles[2], 2),
            'return_95th_percentile': round(percentiles[3], 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }
    
    def _calculate_time_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Métricas relacionadas ao tempo
        """
        
        if trades_df.empty or 'entry_time' not in trades_df.columns:
            return {}
        
        # Duração dos trades (assumindo timestamp em ms)
        durations = []
        for _, trade in trades_df.iterrows():
            if pd.notna(trade['entry_time']) and pd.notna(trade['exit_time']):
                duration_ms = trade['exit_time'] - trade['entry_time']
                duration_minutes = duration_ms / (1000 * 60)  # Converte para minutos
                durations.append(duration_minutes)
        
        if not durations:
            return {}
        
        avg_trade_duration = np.mean(durations)
        median_trade_duration = np.median(durations)
        min_trade_duration = np.min(durations)
        max_trade_duration = np.max(durations)
        
        # Distribuição por período do dia (se possível)
        time_distribution = self._analyze_time_distribution(trades_df)
        
        return {
            'avg_trade_duration_minutes': round(avg_trade_duration, 1),
            'median_trade_duration_minutes': round(median_trade_duration, 1),
            'min_trade_duration_minutes': round(min_trade_duration, 1),
            'max_trade_duration_minutes': round(max_trade_duration, 1),
            **time_distribution
        }
    
    def _calculate_skewness(self, data: np.array) -> float:
        """
        Calcula skewness dos dados
        """
        if len(data) < 3:
            return 0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
        
        skew = np.mean(((data - mean) / std) ** 3)
        return skew
    
    def _calculate_kurtosis(self, data: np.array) -> float:
        """
        Calcula kurtosis dos dados
        """
        if len(data) < 4:
            return 0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
        
        kurt = np.mean(((data - mean) / std) ** 4) - 3  # Excess kurtosis
        return kurt
    
    def _calculate_max_consecutive(self, trades_df: pd.DataFrame, result_type: str) -> int:
        """
        Calcula máxima sequência consecutiva de wins ou losses
        """
        if result_type == 'win':
            results = (trades_df['net_pnl'] > 0).astype(int)
        else:
            results = (trades_df['net_pnl'] < 0).astype(int)
        
        max_consecutive = 0
        current_consecutive = 0
        
        for result in results:
            if result == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _analyze_time_distribution(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analisa distribuição temporal dos trades
        """
        # Implementação básica - pode ser expandida
        return {
            'trades_per_day_avg': round(len(trades_df) / max(1, (trades_df['exit_time'].max() - trades_df['entry_time'].min()) / (1000 * 60 * 60 * 24)), 2) if 'exit_time' in trades_df.columns else 0
        }
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas vazias quando não há dados
        """
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'total_return_pct': 0,
            'sharpe_ratio': 0,
            'max_drawdown_pct': 0,
            'profit_factor': 0
        }
    
    def generate_performance_report(self, metrics: Dict[str, Any]) -> str:
        """
        Gera relatório textual de performance
        """
        
        if not metrics or metrics.get('total_trades', 0) == 0:
            return "❌ Nenhum dado de performance disponível"
        
        report = []
        report.append("📊 RELATÓRIO DE PERFORMANCE")
        report.append("=" * 50)
        report.append("")
        
        # Métricas básicas
        report.append("📈 MÉTRICAS BÁSICAS")
        report.append(f"  Total de Trades: {metrics.get('total_trades', 0)}")
        report.append(f"  Taxa de Acerto: {metrics.get('win_rate', 0):.2%}")
        report.append(f"  Retorno Total: {metrics.get('total_return_pct', 0):.2f}%")
        report.append(f"  PnL Total: ${metrics.get('total_pnl', 0):.2f}")
        report.append(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        report.append("")
        
        # Métricas de risco
        report.append("⚠️ MÉTRICAS DE RISCO")
        report.append(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
        report.append(f"  Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}")
        report.append(f"  Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}")
        report.append(f"  Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
        report.append(f"  Volatilidade: {metrics.get('volatility', 0):.2%}")
        report.append("")
        
        # Classificação da estratégia
        classification = self._classify_strategy(metrics)
        report.append(f"🎯 CLASSIFICAÇÃO: {classification}")
        report.append("")
        
        return "\n".join(report)
    
    def _classify_strategy(self, metrics: Dict[str, Any]) -> str:
        """
        Classifica a estratégia baseado nas métricas
        """
        
        sharpe = metrics.get('sharpe_ratio', 0)
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        max_dd = abs(metrics.get('max_drawdown_pct', 100))
        
        score = 0
        
        # Scoring baseado em métricas
        if sharpe > 1.5:
            score += 3
        elif sharpe > 1.0:
            score += 2
        elif sharpe > 0.5:
            score += 1
        
        if win_rate > 0.6:
            score += 2
        elif win_rate > 0.5:
            score += 1
        
        if profit_factor > 1.5:
            score += 2
        elif profit_factor > 1.2:
            score += 1
        
        if max_dd < 5:
            score += 2
        elif max_dd < 10:
            score += 1
        
        # Classificação final
        if score >= 8:
            return "🟢 EXCELENTE"
        elif score >= 6:
            return "🟡 BOM"
        elif score >= 4:
            return "🟠 REGULAR"
        else:
            return "🔴 RUIM"