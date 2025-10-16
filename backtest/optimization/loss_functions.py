# backtest/optimization/loss_functions.py
"""
Loss Functions para Hyperopt - Adaptado de Freqtrade
Funções objetivo especializadas para otimização de estratégias
"""

import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class HyperoptLossFunctions:
    """
    Funções de loss para hyperoptimization
    
    Baseado em Freqtrade loss functions:
    - Sharpe Ratio
    - Sortino Ratio
    - Calmar Ratio
    - Max Drawdown
    - Profit-Drawdown Ratio
    - Multi-Metric
    """
    
    @staticmethod
    def sharpe_ratio_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza para Sharpe Ratio
        
        Sharpe = (Return - RiskFree) / Volatility
        Quanto maior, melhor (multiplicamos por -1 para minimizar)
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (negativo do Sharpe Ratio)
        """
        sharpe = results.get('sharpe_ratio', 0)
        
        # Penaliza se muito poucos trades
        num_trades = results.get('total_trades', 0)
        if num_trades < 10:
            sharpe *= 0.5  # Penalidade de 50%
        
        # Retorna negativo para minimização
        return -sharpe
    
    @staticmethod
    def sortino_ratio_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza para Sortino Ratio
        
        Sortino penaliza apenas downside volatility
        Melhor para estratégias assimétricas
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (negativo do Sortino Ratio)
        """
        sortino = results.get('sortino_ratio', 0)
        
        # Penaliza drawdown excessivo
        max_dd = abs(results.get('max_drawdown', 0))
        if max_dd > 0.3:  # Mais de 30% drawdown
            sortino *= 0.7  # Penalidade de 30%
        
        return -sortino
    
    @staticmethod
    def calmar_ratio_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza para Calmar Ratio
        
        Calmar = AnnualReturn / MaxDrawdown
        Excelente para estratégias de longo prazo
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (negativo do Calmar Ratio)
        """
        calmar = results.get('calmar_ratio', 0)
        
        # Requer retorno positivo
        total_return = results.get('total_return_pct', 0)
        if total_return <= 0:
            return 999999  # Penalidade máxima
        
        return -calmar
    
    @staticmethod
    def max_drawdown_loss(results: Dict[str, Any]) -> float:
        """
        Minimiza Max Drawdown
        
        Foca em proteção de capital
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (Max Drawdown absoluto)
        """
        max_dd = abs(results.get('max_drawdown', 0))
        
        # Penaliza se retorno total for negativo
        total_return = results.get('total_return_pct', 0)
        if total_return < 0:
            max_dd += 1.0  # Adiciona 100% ao drawdown
        
        return max_dd
    
    @staticmethod
    def profit_drawdown_ratio_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza relação Profit/Drawdown
        
        Balanço entre retorno e risco de drawdown
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value
        """
        total_profit = results.get('total_return_pct', 0)
        max_dd = abs(results.get('max_drawdown', 0))
        
        # Evita divisão por zero
        if max_dd == 0:
            max_dd = 0.01
        
        # Profit/Drawdown ratio
        ratio = total_profit / max_dd
        
        # Penaliza win rate muito baixa
        win_rate = results.get('win_rate', 0)
        if win_rate < 0.3:  # Menos de 30%
            ratio *= 0.5
        
        return -ratio
    
    @staticmethod
    def multi_metric_loss(results: Dict[str, Any], weights: Dict[str, float] = None) -> float:
        """
        Otimização multi-objetivo com pesos customizáveis
        
        Combina múltiplas métricas em score único
        
        Args:
            results: Dicionário com resultados do backtest
            weights: Pesos para cada métrica
        
        Returns:
            Loss value (score combinado negativo)
        """
        # Pesos padrão
        if weights is None:
            weights = {
                'sharpe_ratio': 0.3,
                'total_return': 0.3,
                'win_rate': 0.2,
                'max_drawdown': 0.2  # Este será penalizado
            }
        
        # Normaliza métricas
        sharpe = results.get('sharpe_ratio', 0)
        sharpe_normalized = max(0, min(5, sharpe)) / 5  # Normaliza entre 0-5
        
        total_return = results.get('total_return_pct', 0) / 100
        return_normalized = max(-1, min(2, total_return)) / 2  # Normaliza entre -100% e 200%
        
        win_rate = results.get('win_rate', 0)
        
        max_dd = abs(results.get('max_drawdown', 0))
        dd_normalized = 1 - min(1, max_dd)  # Inverte para que menor drawdown seja melhor
        
        # Calcula score ponderado
        score = (
            sharpe_normalized * weights.get('sharpe_ratio', 0.3) +
            return_normalized * weights.get('total_return', 0.3) +
            win_rate * weights.get('win_rate', 0.2) +
            dd_normalized * weights.get('max_drawdown', 0.2)
        )
        
        # Penalidades
        num_trades = results.get('total_trades', 0)
        if num_trades < 20:
            score *= 0.7  # Poucos trades
        
        if max_dd > 0.5:
            score *= 0.5  # Drawdown muito alto
        
        return -score
    
    @staticmethod
    def expectancy_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza para Expectancy (Expected Value por trade)
        
        Expectancy = (WinRate * AvgWin) - (LossRate * AvgLoss)
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (negativo da expectancy)
        """
        win_rate = results.get('win_rate', 0)
        avg_win = results.get('avg_win', 0)
        avg_loss = abs(results.get('avg_loss', 0))
        
        loss_rate = 1 - win_rate
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        # Penaliza se profit factor for muito baixo
        profit_factor = results.get('profit_factor', 0)
        if profit_factor < 1.5:
            expectancy *= 0.6
        
        return -expectancy
    
    @staticmethod
    def profit_factor_loss(results: Dict[str, Any]) -> float:
        """
        Otimiza para Profit Factor
        
        ProfitFactor = GrossProfit / GrossLoss
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value (negativo do profit factor)
        """
        profit_factor = results.get('profit_factor', 0)
        
        # Requer pelo menos 1.0 (breakeven)
        if profit_factor < 1.0:
            return 999999
        
        # Penaliza recovery factor baixo
        recovery_factor = results.get('recovery_factor', 0)
        if recovery_factor < 2.0:
            profit_factor *= 0.8
        
        return -profit_factor
    
    @staticmethod
    def risk_adjusted_return_loss(results: Dict[str, Any]) -> float:
        """
        Return ajustado por múltiplas métricas de risco
        
        Combina Sharpe, Sortino e Calmar
        
        Args:
            results: Dicionário com resultados do backtest
        
        Returns:
            Loss value
        """
        sharpe = results.get('sharpe_ratio', 0)
        sortino = results.get('sortino_ratio', 0)
        calmar = results.get('calmar_ratio', 0)
        
        # Score combinado (média harmônica)
        metrics = [sharpe, sortino, calmar]
        positive_metrics = [m for m in metrics if m > 0]
        
        if not positive_metrics:
            return 999999
        
        # Média harmônica (penaliza se alguma métrica for muito baixa)
        harmonic_mean = len(positive_metrics) / sum(1/m for m in positive_metrics)
        
        # Bônus para consistência
        if len(positive_metrics) == len(metrics):
            harmonic_mean *= 1.1
        
        return -harmonic_mean
    
    @staticmethod
    def win_rate_constrained_loss(results: Dict[str, Any], min_win_rate: float = 0.5) -> float:
        """
        Otimiza retorno mas requer win rate mínima
        
        Args:
            results: Dicionário com resultados do backtest
            min_win_rate: Win rate mínima requerida
        
        Returns:
            Loss value
        """
        win_rate = results.get('win_rate', 0)
        
        # Hard constraint: win rate mínima
        if win_rate < min_win_rate:
            return 999999
        
        # Otimiza total return
        total_return = results.get('total_return_pct', 0)
        
        # Penaliza drawdown
        max_dd = abs(results.get('max_drawdown', 0))
        if max_dd > 0.2:  # Mais de 20%
            total_return *= 0.7
        
        return -total_return


def get_loss_function(loss_name: str, **kwargs):
    """
    Factory function para obter função de loss
    
    Args:
        loss_name: Nome da função de loss
        **kwargs: Argumentos adicionais para a função
    
    Returns:
        Função de loss
    """
    loss_functions = {
        'sharpe': HyperoptLossFunctions.sharpe_ratio_loss,
        'sortino': HyperoptLossFunctions.sortino_ratio_loss,
        'calmar': HyperoptLossFunctions.calmar_ratio_loss,
        'max_drawdown': HyperoptLossFunctions.max_drawdown_loss,
        'profit_drawdown': HyperoptLossFunctions.profit_drawdown_ratio_loss,
        'multi_metric': lambda r: HyperoptLossFunctions.multi_metric_loss(r, kwargs.get('weights')),
        'expectancy': HyperoptLossFunctions.expectancy_loss,
        'profit_factor': HyperoptLossFunctions.profit_factor_loss,
        'risk_adjusted': HyperoptLossFunctions.risk_adjusted_return_loss,
        'win_rate_constrained': lambda r: HyperoptLossFunctions.win_rate_constrained_loss(r, kwargs.get('min_win_rate', 0.5))
    }
    
    if loss_name not in loss_functions:
        logger.warning(f"Loss function '{loss_name}' not found, using sharpe_ratio_loss")
        return loss_functions['sharpe']
    
    return loss_functions[loss_name]
