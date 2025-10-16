# -*- coding: utf-8 -*-
"""
Backtest Engine - Motor principal de backtesting
Integra com sistema de IA existente para simulação precisa
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import time
from pathlib import Path

# Integração com sistema existente
try:
    from ai_orchestrator import AICoordinator
    AI_LEGACY_AVAILABLE = True
except ImportError:
    AI_LEGACY_AVAILABLE = False

try:
    from ai_multi import AICoordinator as MultiAICoordinator
    MULTI_AI_LEGACY_AVAILABLE = True
except ImportError:
    MULTI_AI_LEGACY_AVAILABLE = False

from ..data.data_manager import DataManager
from ..analysis.performance_analyzer import PerformanceAnalyzer


class BacktestEngine:
    """
    Engine completo de backtesting
    USA ESTRATÉGIAS EXISTENTES do sistema atual
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Integração com sistema de IA existente
        self.ai_coordinator = None
        self.multi_ai_coordinator = None
        
        if AI_LEGACY_AVAILABLE:
            try:
                self.ai_coordinator = AICoordinator()
                print("[BACKTEST_ENGINE] ✅ AI Coordinator legado integrado")
            except Exception as e:
                print(f"[BACKTEST_ENGINE] ⚠️  AI Coordinator: {e}")
        
        if MULTI_AI_LEGACY_AVAILABLE:
            try:
                self.multi_ai_coordinator = MultiAICoordinator()
                print("[BACKTEST_ENGINE] ✅ Multi-AI Coordinator integrado")
            except Exception as e:
                print(f"[BACKTEST_ENGINE] ⚠️  Multi-AI: {e}")
        
        # Componentes do backtesting
        self.data_manager = DataManager()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Estado do backtest
        self.results = []
        self.trades = []
        self.equity_curve = []
        
        # Configurações padrão
        self.initial_capital = self.config.get('initial_capital', 10000.0)
        self.commission = self.config.get('commission', 0.001)  # 0.1%
        self.slippage = self.config.get('slippage', 0.0005)    # 0.05%
        
        print("[BACKTEST_ENGINE] Inicializado com integração ao sistema IA existente")
    
    def run_backtest(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        strategy_params: Dict[str, Any] = None,
        timeframe: str = '1m'
    ) -> Dict[str, Any]:
        """
        Executa backtest completo usando estratégias do sistema existente
        """
        
        print(f"[BACKTEST_ENGINE] 🚀 Iniciando backtest {symbol} ({start_date} - {end_date})")
        
        # 1. Carrega dados históricos
        data = self.data_manager.get_historical_data(symbol, start_date, end_date, timeframe)
        if data.empty:
            raise ValueError(f"Nenhum dado encontrado para {symbol}")
        
        # 2. Prepara parâmetros
        params = strategy_params or self._get_default_strategy_params()
        
        # 3. Executa simulação
        backtest_results = self._simulate_trading(data, symbol, params)
        
        # 4. Analisa performance
        performance_metrics = self.performance_analyzer.calculate_metrics(
            self.trades, 
            self.equity_curve, 
            self.initial_capital
        )
        
        # 5. Compila resultados
        results = {
            'backtest_info': {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe,
                'initial_capital': self.initial_capital,
                'strategy_params': params,
                'total_candles': len(data),
                'execution_time': time.time()
            },
            'trades': self.trades.copy(),
            'equity_curve': self.equity_curve.copy(),
            'performance_metrics': performance_metrics,
            'raw_data_sample': data.tail(10).to_dict('records')  # Últimas 10 velas como amostra
        }
        
        print(f"[BACKTEST_ENGINE] ✅ Backtest concluído - {len(self.trades)} trades executados")
        return results
    
    def _simulate_trading(self, data: pd.DataFrame, symbol: str, params: Dict[str, Any]) -> Dict:
        """
        Simula trading usando sistema de IA existente
        """
        
        self.trades = []
        self.equity_curve = []
        
        current_capital = self.initial_capital
        position_size = 0
        entry_price = 0
        entry_time = None
        
        # Configurações de trading
        risk_per_trade = params.get('risk_per_trade', 0.02)
        take_profit_pct = params.get('take_profit', 0.10)
        stop_loss_pct = params.get('stop_loss', 0.03)
        
        print(f"[BACKTEST_ENGINE] Simulando com {len(data)} velas...")
        
        for idx, row in data.iterrows():
            current_price = row['close']
            current_time = row['timestamp'] if 'timestamp' in row else idx
            
            # Adiciona ponto na curva de equity
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': current_capital,
                'price': current_price
            })
            
            # Se não há posição, verifica sinal de entrada
            if position_size == 0:
                entry_signal = self._get_entry_signal(data, idx, symbol, params)
                
                if entry_signal:
                    # Calcula tamanho da posição
                    stop_loss_price = current_price * (1 - stop_loss_pct)
                    risk_amount = current_capital * risk_per_trade
                    risk_per_unit = current_price - stop_loss_price
                    
                    if risk_per_unit > 0:
                        position_size = risk_amount / risk_per_unit
                        entry_price = current_price * (1 + self.slippage)  # Simula slippage
                        entry_time = current_time
                        
                        print(f"[BACKTEST_ENGINE] 🟢 ENTRADA: {position_size:.6f} @ {entry_price:.2f}")
            
            # Se há posição, verifica sinais de saída
            elif position_size > 0:
                exit_signal, exit_reason = self._get_exit_signal(
                    current_price, entry_price, take_profit_pct, stop_loss_pct
                )
                
                if exit_signal:
                    exit_price = current_price * (1 - self.slippage)  # Simula slippage
                    
                    # Calcula PnL
                    gross_pnl = (exit_price - entry_price) * position_size
                    commission_cost = (entry_price * position_size + exit_price * position_size) * self.commission
                    net_pnl = gross_pnl - commission_cost
                    
                    current_capital += net_pnl
                    
                    # Registra trade
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'position_size': position_size,
                        'gross_pnl': gross_pnl,
                        'commission': commission_cost,
                        'net_pnl': net_pnl,
                        'return_pct': (net_pnl / (entry_price * position_size)) * 100,
                        'exit_reason': exit_reason
                    }
                    
                    self.trades.append(trade)
                    
                    print(f"[BACKTEST_ENGINE] 🔴 SAÍDA: {exit_reason} @ {exit_price:.2f} | PnL: ${net_pnl:.2f}")
                    
                    # Reset posição
                    position_size = 0
                    entry_price = 0
                    entry_time = None
        
        print(f"[BACKTEST_ENGINE] ✅ Simulação concluída - Capital final: ${current_capital:.2f}")
        return {'final_capital': current_capital, 'total_trades': len(self.trades)}
    
    def _get_entry_signal(self, data: pd.DataFrame, current_idx: int, symbol: str, params: Dict) -> bool:
        """
        Obtém sinal de entrada usando sistema de IA existente
        """
        
        # Precisa de pelo menos 50 velas para análise
        if current_idx < 50:
            return False
        
        try:
            # USA SISTEMA DE IA EXISTENTE se disponível
            if self.ai_coordinator:
                # Simula decisão do AI Coordinator
                recent_closes = data.iloc[max(0, current_idx-20):current_idx]['close'].tolist()
                
                # Verifica se símbolo é permitido
                if not self.ai_coordinator.allow(symbol):
                    return False
                
                # Decide regime baseado em preços recentes
                current_regime = self.ai_coordinator.decide_regime(recent_closes)
                regime_params = self.ai_coordinator.regime_params(current_regime)
                
                # Lógica de entrada baseada no regime
                if current_regime == 'aggressive':
                    # Mais agressivo em tendências
                    return self._technical_entry_signal(data, current_idx, sensitivity=0.7)
                elif current_regime == 'conservative':
                    # Mais conservador
                    return self._technical_entry_signal(data, current_idx, sensitivity=0.9)
                else:
                    # Regime neutro
                    return self._technical_entry_signal(data, current_idx, sensitivity=0.8)
            
            else:
                # Fallback: análise técnica simples
                return self._technical_entry_signal(data, current_idx, sensitivity=0.75)
                
        except Exception as e:
            print(f"[BACKTEST_ENGINE] ⚠️  Erro em entrada: {e}")
            return False
    
    def _technical_entry_signal(self, data: pd.DataFrame, current_idx: int, sensitivity: float = 0.75) -> bool:
        """
        Análise técnica para sinal de entrada
        """
        
        # Pega últimas 20 velas
        recent_data = data.iloc[max(0, current_idx-20):current_idx+1]
        
        if len(recent_data) < 10:
            return False
        
        # Indicadores simples
        closes = recent_data['close']
        
        # SMA simples
        sma_short = closes.rolling(5).mean().iloc[-1]
        sma_long = closes.rolling(10).mean().iloc[-1]
        current_price = closes.iloc[-1]
        
        # RSI simples
        price_changes = closes.diff()
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)
        avg_gain = gains.rolling(14).mean().iloc[-1]
        avg_loss = losses.rolling(14).mean().iloc[-1]
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Condições de entrada
        conditions = [
            sma_short > sma_long,  # Tendência de alta
            current_price > sma_short,  # Preço acima da média curta
            rsi < 70,  # Não sobrecomprado
            rsi > 30   # Não sobrevendido
        ]
        
        # Ajusta sensibilidade
        required_conditions = int(len(conditions) * sensitivity)
        return sum(conditions) >= required_conditions
    
    def _get_exit_signal(self, current_price: float, entry_price: float, 
                        take_profit_pct: float, stop_loss_pct: float) -> Tuple[bool, str]:
        """
        Verifica sinais de saída (take profit / stop loss)
        """
        
        price_change_pct = (current_price - entry_price) / entry_price
        
        # Take Profit
        if price_change_pct >= take_profit_pct:
            return True, "take_profit"
        
        # Stop Loss
        if price_change_pct <= -stop_loss_pct:
            return True, "stop_loss"
        
        return False, "none"
    
    def _get_default_strategy_params(self) -> Dict[str, Any]:
        """
        Parâmetros padrão baseados no sistema existente
        """
        return {
            'risk_per_trade': 0.02,  # 2% de risco por trade
            'take_profit': 0.10,     # 10% take profit
            'stop_loss': 0.03,       # 3% stop loss
            'ai_threshold': 0.70,    # Threshold IA
            'max_trades_per_day': 10,
            'min_trade_interval_minutes': 15
        }
    
    def run_walk_forward_analysis(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        optimization_window_days: int = 30,
        test_window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Executa análise walk-forward para validação robusta
        """
        
        print(f"[BACKTEST_ENGINE] 🔄 Iniciando Walk-Forward Analysis")
        
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
            
            print(f"[BACKTEST_ENGINE] Otimizando: {opt_start.date()} - {opt_end.date()}")
            print(f"[BACKTEST_ENGINE] Testando: {test_start.date()} - {test_end.date()}")
            
            # TODO: Implementar otimização de parâmetros na janela de otimização
            # Por enquanto usa parâmetros padrão
            optimal_params = self._get_default_strategy_params()
            
            # Testa com parâmetros otimizados
            test_results = self.run_backtest(
                symbol,
                test_start.strftime("%Y-%m-%d"),
                test_end.strftime("%Y-%m-%d"),
                optimal_params
            )
            
            results.append({
                'optimization_period': f"{opt_start.date()} - {opt_end.date()}",
                'test_period': f"{test_start.date()} - {test_end.date()}",
                'optimal_params': optimal_params,
                'test_results': test_results
            })
            
            current_date = test_end
        
        # Calcula métricas agregadas
        aggregate_metrics = self._calculate_walk_forward_metrics(results)
        
        return {
            'walk_forward_results': results,
            'aggregate_metrics': aggregate_metrics,
            'total_periods': len(results)
        }
    
    def _calculate_walk_forward_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Calcula métricas agregadas do walk-forward
        """
        
        all_returns = []
        win_rates = []
        
        for result in results:
            metrics = result['test_results']['performance_metrics']
            all_returns.append(metrics.get('total_return_pct', 0))
            win_rates.append(metrics.get('win_rate', 0))
        
        return {
            'avg_return_pct': np.mean(all_returns) if all_returns else 0,
            'std_return_pct': np.std(all_returns) if all_returns else 0,
            'avg_win_rate': np.mean(win_rates) if win_rates else 0,
            'consistency_score': len([r for r in all_returns if r > 0]) / len(all_returns) if all_returns else 0,
            'total_periods': len(results)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Status do engine de backtesting
        """
        return {
            'ai_integration': {
                'ai_coordinator': self.ai_coordinator is not None,
                'multi_ai_coordinator': self.multi_ai_coordinator is not None
            },
            'data_manager': self.data_manager.get_status(),
            'performance_analyzer': True,
            'last_backtest': {
                'trades_count': len(self.trades),
                'equity_points': len(self.equity_curve)
            }
        }