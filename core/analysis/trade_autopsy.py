
# core/analysis/trade_autopsy.py
"""
Trade Autopsy - Análise post-mortem detalhada de cada trade
Identifica padrões em trades vencedores vs perdedores
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TradeAutopsy:
    """
    Analisa trades fechados para identificar padrões
    """
    
    def __init__(self):
        self.trade_analyses: List[Dict[str, Any]] = []
        self.pattern_library: Dict[str, List[str]] = defaultdict(list)
        
        logger.info("✅ Trade Autopsy initialized")
    
    def analyze_trade(
        self,
        trade_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Análise completa de um trade fechado
        
        Args:
            trade_data: Dados do trade (entry, exit, pnl, etc)
            market_context: Contexto de mercado durante o trade
        
        Returns:
            Análise detalhada
        """
        try:
            analysis = {
                'trade_id': trade_data.get('trade_id'),
                'symbol': trade_data.get('symbol'),
                'entry_time': trade_data.get('entry_time'),
                'exit_time': trade_data.get('exit_time'),
                'entry_price': trade_data.get('entry_price'),
                'exit_price': trade_data.get('exit_price'),
                'pnl': trade_data.get('pnl', 0.0),
                'pnl_pct': trade_data.get('pnl_pct', 0.0),
                'is_winner': trade_data.get('pnl', 0.0) > 0,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Calcula métricas de execução
            analysis['execution_quality'] = self._analyze_execution(trade_data)
            
            # Analisa timing
            analysis['timing_analysis'] = self._analyze_timing(trade_data)
            
            # Analisa gestão de risco
            analysis['risk_management'] = self._analyze_risk_management(trade_data)
            
            # Analisa contexto de mercado
            if market_context:
                analysis['market_context'] = self._analyze_market_context(
                    trade_data,
                    market_context
                )
            
            # Identifica padrões
            analysis['patterns'] = self._identify_patterns(analysis)
            
            # Gera recomendações
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            # Salva análise
            self.trade_analyses.append(analysis)
            
            # Atualiza biblioteca de padrões
            self._update_pattern_library(analysis)
            
            logger.info(
                f"Trade autopsy completed: {trade_data.get('trade_id')} - "
                f"{'WIN' if analysis['is_winner'] else 'LOSS'} "
                f"({analysis['pnl_pct']:.2%})"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in trade autopsy: {e}")
            return {}
    
    def _analyze_execution(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa qualidade da execução"""
        entry_price = trade_data.get('entry_price', 0)
        exit_price = trade_data.get('exit_price', 0)
        
        # Slippage
        expected_entry = trade_data.get('expected_entry_price', entry_price)
        entry_slippage = abs(entry_price - expected_entry) / expected_entry if expected_entry else 0
        
        expected_exit = trade_data.get('expected_exit_price', exit_price)
        exit_slippage = abs(exit_price - expected_exit) / expected_exit if expected_exit else 0
        
        # Score de execução (0-1)
        execution_score = 1.0 - (entry_slippage + exit_slippage) / 2
        
        return {
            'entry_slippage_pct': entry_slippage * 100,
            'exit_slippage_pct': exit_slippage * 100,
            'execution_score': max(0.0, min(1.0, execution_score)),
            'quality': 'excellent' if execution_score > 0.95 else
                      'good' if execution_score > 0.85 else
                      'fair' if execution_score > 0.70 else 'poor'
        }
    
    def _analyze_timing(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa timing de entrada e saída"""
        entry_time = trade_data.get('entry_time')
        exit_time = trade_data.get('exit_time')
        
        if not entry_time or not exit_time:
            return {'hold_time_minutes': 0}
        
        # Duração do trade
        if isinstance(entry_time, str):
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        else:
            entry_dt = entry_time
        
        if isinstance(exit_time, str):
            exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
        else:
            exit_dt = exit_time
        
        hold_duration = (exit_dt - entry_dt).total_seconds() / 60  # minutos
        
        # Analisa se saiu no melhor momento
        max_profit = trade_data.get('max_unrealized_pnl_pct', trade_data.get('pnl_pct', 0))
        actual_profit = trade_data.get('pnl_pct', 0)
        
        profit_capture_ratio = actual_profit / max_profit if max_profit > 0 else 0
        
        return {
            'hold_time_minutes': hold_duration,
            'max_profit_pct': max_profit,
            'profit_capture_ratio': profit_capture_ratio,
            'exit_timing': 'optimal' if profit_capture_ratio > 0.9 else
                          'good' if profit_capture_ratio > 0.7 else
                          'early' if profit_capture_ratio > 0 else 'late'
        }
    
    def _analyze_risk_management(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa gestão de risco"""
        entry_price = trade_data.get('entry_price', 0)
        stop_loss = trade_data.get('stop_loss')
        take_profit = trade_data.get('take_profit')
        
        risk_reward_ratio = None
        if stop_loss and take_profit and entry_price:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Verifica se SL foi atingido
        hit_stop_loss = trade_data.get('close_reason') == 'stop_loss'
        hit_take_profit = trade_data.get('close_reason') == 'take_profit'
        
        return {
            'had_stop_loss': stop_loss is not None,
            'had_take_profit': take_profit is not None,
            'risk_reward_ratio': risk_reward_ratio,
            'hit_stop_loss': hit_stop_loss,
            'hit_take_profit': hit_take_profit,
            'risk_management_score': 1.0 if (stop_loss and take_profit) else 0.5
        }
    
    def _analyze_market_context(
        self,
        trade_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analisa contexto de mercado durante o trade"""
        return {
            'regime': market_context.get('regime', 'unknown'),
            'volatility': market_context.get('volatility', 0),
            'trend': market_context.get('trend', 0),
            'volume_profile': market_context.get('volume_profile', 'normal')
        }
    
    def _identify_patterns(self, analysis: Dict[str, Any]) -> List[str]:
        """Identifica padrões no trade"""
        patterns = []
        
        # Padrão: Winners rápidos
        if analysis['is_winner'] and analysis['timing_analysis']['hold_time_minutes'] < 30:
            patterns.append('quick_winner')
        
        # Padrão: Stop loss efetivo
        if analysis['risk_management']['hit_stop_loss']:
            patterns.append('stopped_out')
        
        # Padrão: Take profit atingido
        if analysis['risk_management']['hit_take_profit']:
            patterns.append('target_hit')
        
        # Padrão: Saída prematura
        if analysis['timing_analysis']['exit_timing'] == 'early':
            patterns.append('early_exit')
        
        # Padrão: Execução ruim
        if analysis['execution_quality']['execution_score'] < 0.7:
            patterns.append('poor_execution')
        
        return patterns
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        # Recomendação: Melhorar execução
        if analysis['execution_quality']['execution_score'] < 0.8:
            recommendations.append(
                "Improve execution: Consider using limit orders to reduce slippage"
            )
        
        # Recomendação: Ajustar stops
        if not analysis['risk_management']['had_stop_loss']:
            recommendations.append(
                "Always set stop loss to protect capital"
            )
        
        # Recomendação: Capturar mais lucro
        if analysis['timing_analysis'].get('profit_capture_ratio', 0) < 0.7:
            recommendations.append(
                "Consider trailing stop to capture more profit"
            )
        
        # Recomendação: Risk/Reward ratio
        rr = analysis['risk_management'].get('risk_reward_ratio')
        if rr and rr < 1.5:
            recommendations.append(
                "Target higher risk/reward ratio (minimum 1.5:1)"
            )
        
        return recommendations
    
    def _update_pattern_library(self, analysis: Dict[str, Any]):
        """Atualiza biblioteca de padrões"""
        trade_id = analysis['trade_id']
        
        for pattern in analysis['patterns']:
            self.pattern_library[pattern].append(trade_id)
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de padrões identificados"""
        stats = {}
        
        for pattern, trade_ids in self.pattern_library.items():
            # Filtra trades com esse padrão
            pattern_trades = [
                t for t in self.trade_analyses
                if t['trade_id'] in trade_ids
            ]
            
            if not pattern_trades:
                continue
            
            wins = sum(1 for t in pattern_trades if t['is_winner'])
            total = len(pattern_trades)
            
            avg_pnl = np.mean([t['pnl_pct'] for t in pattern_trades])
            
            stats[pattern] = {
                'occurrences': total,
                'win_rate': wins / total if total > 0 else 0,
                'avg_pnl_pct': avg_pnl
            }
        
        return stats
    
    def compare_winners_vs_losers(self) -> Dict[str, Any]:
        """Compara características de winners vs losers"""
        if not self.trade_analyses:
            return {}
        
        winners = [t for t in self.trade_analyses if t['is_winner']]
        losers = [t for t in self.trade_analyses if not t['is_winner']]
        
        if not winners or not losers:
            return {}
        
        return {
            'winners': {
                'count': len(winners),
                'avg_hold_time': np.mean([
                    t['timing_analysis']['hold_time_minutes'] for t in winners
                ]),
                'avg_execution_score': np.mean([
                    t['execution_quality']['execution_score'] for t in winners
                ]),
                'avg_pnl_pct': np.mean([t['pnl_pct'] for t in winners])
            },
            'losers': {
                'count': len(losers),
                'avg_hold_time': np.mean([
                    t['timing_analysis']['hold_time_minutes'] for t in losers
                ]),
                'avg_execution_score': np.mean([
                    t['execution_quality']['execution_score'] for t in losers
                ]),
                'avg_pnl_pct': np.mean([t['pnl_pct'] for t in losers])
            }
        }


# Instância global
trade_autopsy = TradeAutopsy()
