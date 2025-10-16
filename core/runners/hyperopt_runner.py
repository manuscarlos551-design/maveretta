# core/runners/hyperopt_runner.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Iterable, Tuple
import itertools
import math
import time

from .backtest_runner import MaverettaBacktestRunner

__all__ = [
    "HyperoptResult",
    "MaverettaHyperoptRunner",
    "optimize_slot_strategy",
]

@dataclass
class HyperoptResult:
    best_params: Dict[str, Any]
    best_score: float
    best_metrics: Dict[str, Any]
    trials: List[Dict[str, Any]]  # cada item: {"params":..., "score":..., "metrics":...}

class MaverettaHyperoptRunner:
    """
    Executa busca de hiperparâmetros simples (grid search limitada)
    delegando a avaliação para o backtester oficial do projeto.

    Premissas:
    - MaverettaBacktestRunner aceita um dict de strategy_params (override).
    - O backtester retorna um dict com ao menos: {"metrics": {...}} contendo
      métricas como "net_profit", "profit_pct", "sharpe", "sortino", "win_rate".
    - A função de score por padrão usa 'net_profit' (maior é melhor).
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        param_space: Dict[str, Iterable[Any]],
        score_key: str = "net_profit",  # pode ser "sharpe", "profit_pct", etc.
        limit_trials: Optional[int] = None,
        since: Optional[int] = None,
        until: Optional[int] = None,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy_name = strategy_name
        self.param_space = param_space or {}
        self.score_key = score_key
        self.limit_trials = limit_trials
        self.since = since
        self.until = until

    def _param_grid(self) -> Iterable[Dict[str, Any]]:
        if not self.param_space:
            yield {}
            return

        keys = list(self.param_space.keys())
        values = [list(self.param_space[k]) for k in keys]
        for combo in itertools.product(*values):
            yield dict(zip(keys, combo))

    @staticmethod
    def _extract_score(metrics: Dict[str, Any], key: str) -> float:
        if not metrics:
            return float("-inf")
        val = metrics.get(key)
        try:
            return float(val)
        except Exception:
            return float("-inf")

    def _backtest_once(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Roda um backtest para um conjunto de parâmetros.
        Espera que o backtester aceite strategy_params=params como override.
        """
        runner = MaverettaBacktestRunner(
            symbol=self.symbol,
            timeframe=self.timeframe,
            strategy_name=self.strategy_name,
            since=self.since,
            until=self.until,
            strategy_params=params,
        )
        result = runner.run()
        # padroniza retorno
        if "metrics" not in result or not isinstance(result["metrics"], dict):
            result["metrics"] = {}
        return result

    def optimize(self) -> HyperoptResult:
        best_params: Dict[str, Any] = {}
        best_metrics: Dict[str, Any] = {}
        best_score: float = float("-inf")
        trials: List[Dict[str, Any]] = []

        count = 0
        for params in self._param_grid():
            if self.limit_trials is not None and count >= self.limit_trials:
                break
            count += 1

            result = self._backtest_once(params)
            metrics = result.get("metrics", {})
            score = self._extract_score(metrics, self.score_key)

            trials.append({"params": params, "score": score, "metrics": metrics})

            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics

        return HyperoptResult(
            best_params=best_params,
            best_score=best_score if not math.isinf(best_score) else float("nan"),
            best_metrics=best_metrics,
            trials=trials,
        )

def optimize_slot_strategy(
    symbol: str,
    timeframe: str,
    strategy_name: str,
    param_space: Dict[str, Iterable[Any]],
    score_key: str = "net_profit",
    limit_trials: Optional[int] = None,
    since: Optional[int] = None,
    until: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Função wrapper usada pelas rotas de API.
    Retorna um dicionário serializável com melhor resultado e histórico dos trials.
    """
    runner = MaverettaHyperoptRunner(
        symbol=symbol,
        timeframe=timeframe,
        strategy_name=strategy_name,
        param_space=param_space,
        score_key=score_key,
        limit_trials=limit_trials,
        since=since,
        until=until,
    )
    res = runner.optimize()
    return {
        "best_params": res.best_params,
        "best_score": res.best_score,
        "best_metrics": res.best_metrics,
        "trials": res.trials,
    }