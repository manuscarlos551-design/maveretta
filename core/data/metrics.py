# core/data/metrics.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Dict, Any
import math
import numpy as np
import pandas as pd

__all__ = ["SlotMetrics", "MaverettaMetricsCalculator"]

@dataclass
class SlotMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_pct: float
    max_drawdown_pct: float
    avg_profit: float
    avg_loss: float
    sharpe: float
    sortino: float
    equity_curve: Optional[pd.Series] = None

class MaverettaMetricsCalculator:
    """
    Calcula métricas a partir de uma sequência de trades no formato:
    {
      "timestamp": int|str,  # epoch ms ou ISO
      "side": "buy"|"sell",
      "qty": float,
      "price": float,
      "pnl": float,          # lucro líquido em moeda da conta
      "pnl_pct": float       # lucro % em relação ao capital alocado no trade
    }
    Campos extras são ignorados.
    """

    @staticmethod
    def from_trades(trades: Sequence[Dict[str, Any]]) -> SlotMetrics:
        if not trades:
            return SlotMetrics(
                total_trades=0, wins=0, losses=0, win_rate=0.0,
                gross_profit=0.0, gross_loss=0.0, net_profit=0.0,
                profit_pct=0.0, max_drawdown_pct=0.0,
                avg_profit=0.0, avg_loss=0.0, sharpe=0.0, sortino=0.0,
                equity_curve=pd.Series(dtype=float)
            )

        df = pd.DataFrame(trades).copy()
        # Sanitização
        for col in ("pnl", "pnl_pct"):
            if col not in df.columns:
                df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        total = len(df)
        wins_mask = df["pnl"] > 0
        losses_mask = df["pnl"] < 0
        wins = int(wins_mask.sum())
        losses = int(losses_mask.sum())
        win_rate = (wins / total) * 100.0 if total else 0.0

        gross_profit = float(df.loc[wins_mask, "pnl"].sum())
        gross_loss = float(df.loc[losses_mask, "pnl"].sum())
        net_profit = gross_profit + gross_loss
        profit_pct = float(df["pnl_pct"].sum())

        # Equity curve acumulada (pnl em unidade monetária)
        equity_curve = df["pnl"].cumsum()

        # Máx drawdown em %
        running_max = equity_curve.cummax()
        dd = (equity_curve - running_max)
        # Converter dd (valor absoluto) para % sobre pico anterior; se pico 0, tratar como 0
        peak = running_max.replace(0, np.nan)
        dd_pct = (dd / peak.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0) * 100.0
        max_drawdown_pct = float(dd_pct.min()) if not dd_pct.empty else 0.0

        # Sharpe/Sortino simplificados com retorno = pnl_pct por trade
        r = pd.to_numeric(df["pnl_pct"], errors="coerce").fillna(0.0) / 100.0
        mean_r = r.mean()
        std_r = r.std(ddof=1) if len(r) > 1 else 0.0
        downside = r[r < 0.0]
        std_down = downside.std(ddof=1) if len(downside) > 1 else 0.0

        sharpe = (mean_r / std_r) if std_r > 0 else 0.0
        sortino = (mean_r / std_down) if std_down > 0 else 0.0

        avg_profit = (df.loc[wins_mask, "pnl"].mean() if wins else 0.0)
        avg_loss = (df.loc[losses_mask, "pnl"].mean() if losses else 0.0)

        return SlotMetrics(
            total_trades=total, wins=wins, losses=losses, win_rate=float(win_rate),
            gross_profit=gross_profit, gross_loss=gross_loss, net_profit=net_profit,
            profit_pct=float(profit_pct), max_drawdown_pct=float(max_drawdown_pct),
            avg_profit=float(avg_profit), avg_loss=float(avg_loss),
            sharpe=float(sharpe), sortino=float(sortino),
            equity_curve=equity_curve
        )