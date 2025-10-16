# backtest/analysis/quant_metrics.py
"""
Quantitative Metrics - Métricas quantitativas avançadas
Adaptado de Catalyst/Zipline e Freqtrade Hyperopt loss functions
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class QuantitativeMetrics:
    """
    Métricas quantitativas profissionais para análise de trading
    
    Inclui:
    - Sharpe Ratio
    - Sortino Ratio  
    - Calmar Ratio
    - Information Ratio
    - Omega Ratio
    - Tail Ratio
    - Value at Risk (VaR)
    - Conditional Value at Risk (CVaR)
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Args:
            risk_free_rate: Taxa livre de risco anual (padrão 2%)
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = 365  # Crypto 24/7
        
        logger.info("QuantitativeMetrics initialized")
    
    def calculate_all_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Calcula todas as métricas quantitativas
        
        Args:
            returns: Série de retornos
            benchmark_returns: Retornos do benchmark (opcional)
        
        Returns:
            Dicionário com todas as métricas
        """
        metrics = {}
        
        # Métricas de risco-retorno
        metrics['sharpe_ratio'] = self.sharpe_ratio(returns)
        metrics['sortino_ratio'] = self.sortino_ratio(returns)
        metrics['calmar_ratio'] = self.calmar_ratio(returns)
        
        # Métricas de risco
        metrics['max_drawdown'] = self.max_drawdown(returns)
        metrics['volatility'] = self.volatility(returns)
        metrics['downside_deviation'] = self.downside_deviation(returns)
        
        # Métricas avançadas
        metrics['omega_ratio'] = self.omega_ratio(returns)
        metrics['tail_ratio'] = self.tail_ratio(returns)
        metrics['var_95'] = self.value_at_risk(returns, confidence=0.95)
        metrics['cvar_95'] = self.conditional_value_at_risk(returns, confidence=0.95)
        
        # Métricas de distribuição
        metrics['skewness'] = self.skewness(returns)
        metrics['kurtosis'] = self.kurtosis(returns)
        
        # Métricas vs benchmark
        if benchmark_returns is not None:
            metrics['information_ratio'] = self.information_ratio(returns, benchmark_returns)
            metrics['alpha'] = self.alpha(returns, benchmark_returns)
            metrics['beta'] = self.beta(returns, benchmark_returns)
        
        return metrics
    
    def sharpe_ratio(self, returns: pd.Series, periods: int = None) -> float:
        """
        Sharpe Ratio - Retorno ajustado pelo risco
        
        Sharpe = (Return - RiskFreeRate) / Volatility
        
        Args:
            returns: Série de retornos
            periods: Períodos por ano (default: trading_days_per_year)
        
        Returns:
            Sharpe ratio anualizado
        """
        if len(returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        # Anualiza retornos e volatilidade
        mean_return = returns.mean() * periods
        std_return = returns.std() * np.sqrt(periods)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return - self.risk_free_rate) / std_return
        
        return sharpe
    
    def sortino_ratio(self, returns: pd.Series, periods: int = None, target_return: float = 0) -> float:
        """
        Sortino Ratio - Similar ao Sharpe mas penaliza apenas downside volatility
        
        Sortino = (Return - Target) / DownsideDeviation
        
        Args:
            returns: Série de retornos
            periods: Períodos por ano
            target_return: Retorno alvo (default: 0)
        
        Returns:
            Sortino ratio anualizado
        """
        if len(returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        # Calcula downside deviation
        downside_returns = returns[returns < target_return]
        downside_std = downside_returns.std() * np.sqrt(periods)
        
        if downside_std == 0:
            return 0.0
        
        mean_return = returns.mean() * periods
        sortino = (mean_return - target_return) / downside_std
        
        return sortino
    
    def calmar_ratio(self, returns: pd.Series, periods: int = None) -> float:
        """
        Calmar Ratio - Retorno anual dividido pelo max drawdown
        
        Calmar = AnnualReturn / MaxDrawdown
        
        Args:
            returns: Série de retornos
            periods: Períodos por ano
        
        Returns:
            Calmar ratio
        """
        if len(returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        # Retorno anualizado
        annual_return = returns.mean() * periods
        
        # Max drawdown
        max_dd = abs(self.max_drawdown(returns))
        
        if max_dd == 0:
            return 0.0
        
        calmar = annual_return / max_dd
        
        return calmar
    
    def information_ratio(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """
        Information Ratio - Excess return vs benchmark ajustado pelo tracking error
        
        IR = (Return - Benchmark) / TrackingError
        
        Args:
            returns: Série de retornos da estratégia
            benchmark_returns: Série de retornos do benchmark
        
        Returns:
            Information ratio
        """
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0
        
        # Alinha séries
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) == 0:
            return 0.0
        
        strategy_returns = aligned.iloc[:, 0]
        bench_returns = aligned.iloc[:, 1]
        
        # Excess returns
        excess_returns = strategy_returns - bench_returns
        
        # Tracking error
        tracking_error = excess_returns.std()
        
        if tracking_error == 0:
            return 0.0
        
        ir = excess_returns.mean() / tracking_error
        
        return ir
    
    def omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> float:
        """
        Omega Ratio - Probabilidade de ganhos vs perdas acima de um threshold
        
        Args:
            returns: Série de retornos
            threshold: Threshold de retorno (default: 0)
        
        Returns:
            Omega ratio
        """
        if len(returns) == 0:
            return 0.0
        
        # Gains e losses relativos ao threshold
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns < threshold]
        
        if len(losses) == 0 or losses.sum() == 0:
            return np.inf if len(gains) > 0 else 0.0
        
        omega = gains.sum() / losses.sum()
        
        return omega
    
    def tail_ratio(self, returns: pd.Series) -> float:
        """
        Tail Ratio - Razão entre 95th percentile e 5th percentile
        
        Mede assimetria das caudas da distribuição
        
        Args:
            returns: Série de retornos
        
        Returns:
            Tail ratio
        """
        if len(returns) == 0:
            return 0.0
        
        percentile_95 = np.percentile(returns, 95)
        percentile_5 = np.percentile(returns, 5)
        
        if percentile_5 >= 0:
            return 0.0
        
        tail_ratio = abs(percentile_95 / percentile_5)
        
        return tail_ratio
    
    def value_at_risk(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Value at Risk (VaR) - Perda máxima esperada com X% de confiança
        
        Args:
            returns: Série de retornos
            confidence: Nível de confiança (default: 0.95 = 95%)
        
        Returns:
            VaR (valor positivo representa perda)
        """
        if len(returns) == 0:
            return 0.0
        
        var = -np.percentile(returns, (1 - confidence) * 100)
        
        return var
    
    def conditional_value_at_risk(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Conditional Value at Risk (CVaR / Expected Shortfall)
        
        Perda média quando VaR é excedido
        
        Args:
            returns: Série de retornos
            confidence: Nível de confiança
        
        Returns:
            CVaR (valor positivo representa perda)
        """
        if len(returns) == 0:
            return 0.0
        
        var = self.value_at_risk(returns, confidence)
        cvar = -returns[returns <= -var].mean()
        
        return cvar if not np.isnan(cvar) else var
    
    def max_drawdown(self, returns: pd.Series) -> float:
        """
        Maximum Drawdown - Maior queda do pico ao vale
        
        Args:
            returns: Série de retornos
        
        Returns:
            Max drawdown (valor negativo)
        """
        if len(returns) == 0:
            return 0.0
        
        # Calcula equity curve cumulativa
        cumulative = (1 + returns).cumprod()
        
        # Running maximum
        running_max = cumulative.expanding().max()
        
        # Drawdown
        drawdown = (cumulative - running_max) / running_max
        
        max_dd = drawdown.min()
        
        return max_dd
    
    def volatility(self, returns: pd.Series, periods: int = None) -> float:
        """
        Volatilidade anualizada
        
        Args:
            returns: Série de retornos
            periods: Períodos por ano
        
        Returns:
            Volatilidade anualizada
        """
        if len(returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        vol = returns.std() * np.sqrt(periods)
        
        return vol
    
    def downside_deviation(self, returns: pd.Series, target: float = 0, periods: int = None) -> float:
        """
        Downside Deviation - Desvio padrão dos retornos negativos
        
        Args:
            returns: Série de retornos
            target: Retorno alvo
            periods: Períodos por ano
        
        Returns:
            Downside deviation anualizada
        """
        if len(returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        downside_returns = returns[returns < target]
        downside_dev = downside_returns.std() * np.sqrt(periods)
        
        return downside_dev
    
    def skewness(self, returns: pd.Series) -> float:
        """
        Skewness - Assimetria da distribuição de retornos
        
        Args:
            returns: Série de retornos
        
        Returns:
            Skewness
        """
        if len(returns) < 3:
            return 0.0
        
        return returns.skew()
    
    def kurtosis(self, returns: pd.Series) -> float:
        """
        Kurtosis - Curtose da distribuição (fat tails)
        
        Args:
            returns: Série de retornos
        
        Returns:
            Excess kurtosis
        """
        if len(returns) < 4:
            return 0.0
        
        return returns.kurtosis()
    
    def alpha(self, returns: pd.Series, benchmark_returns: pd.Series, periods: int = None) -> float:
        """
        Alpha - Excess return vs benchmark (CAPM)
        
        Args:
            returns: Série de retornos da estratégia
            benchmark_returns: Série de retornos do benchmark
            periods: Períodos por ano
        
        Returns:
            Alpha anualizado
        """
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0
        
        if periods is None:
            periods = self.trading_days_per_year
        
        # Alinha séries
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0
        
        strategy_returns = aligned.iloc[:, 0]
        bench_returns = aligned.iloc[:, 1]
        
        # Calcula beta
        beta = self.beta(strategy_returns, bench_returns)
        
        # Alpha = Return - (RiskFree + Beta * (BenchmarkReturn - RiskFree))
        strategy_return = strategy_returns.mean() * periods
        benchmark_return = bench_returns.mean() * periods
        
        alpha = strategy_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))
        
        return alpha
    
    def beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """
        Beta - Sensibilidade ao benchmark
        
        Args:
            returns: Série de retornos da estratégia
            benchmark_returns: Série de retornos do benchmark
        
        Returns:
            Beta
        """
        if len(returns) == 0 or len(benchmark_returns) == 0:
            return 0.0
        
        # Alinha séries
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0
        
        strategy_returns = aligned.iloc[:, 0]
        bench_returns = aligned.iloc[:, 1]
        
        # Covariância / Variância
        covariance = np.cov(strategy_returns, bench_returns)[0, 1]
        benchmark_variance = bench_returns.var()
        
        if benchmark_variance == 0:
            return 0.0
        
        beta = covariance / benchmark_variance
        
        return beta
