#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Protection Manager - Etapa 7
Sistema de proteções avançadas de nível institucional
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import threading
from dataclasses import dataclass
from collections import defaultdict, deque

# Adiciona path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Imports do sistema existente
try:
    from risk.managers.risk_manager import RiskManager
    RISK_SYSTEM_AVAILABLE = True
except ImportError:
    RISK_SYSTEM_AVAILABLE = False

@dataclass
class MarketData:
    """Estrutura para dados de mercado"""
    timestamp: datetime
    symbol: str
    price: float
    volume: float
    volatility: float
    liquidity_score: float

@dataclass
class PositionInfo:
    """Informações de posição"""
    symbol: str
    size: float
    entry_price: float
    current_price: float
    pnl: float
    duration: timedelta
    
class AdvancedProtectionManager:
    """
    Sistema de proteções avançadas de nível institucional
    Integra com RiskManager existente e adiciona camadas extras de proteção
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Integração com sistema existente
        self.risk_manager = None
        if RISK_SYSTEM_AVAILABLE:
            try:
                self.risk_manager = RiskManager()
            except Exception as e:
                self.logger.warning(f"Could not initialize RiskManager: {e}")
        
        # Configurações de proteção
        self.protection_config = {
            'real_time_monitoring': {
                'check_interval_seconds': 1,
                'drawdown_critical': 0.15,
                'drawdown_warning': 0.10,
                'volatility_threshold': 0.50,
                'correlation_threshold': 0.80,
                'liquidity_min_score': 0.30
            },
            'adaptive_sizing': {
                'base_risk_per_trade': 0.005,
                'volatility_adjustment_factor': 2.0,
                'max_size_multiplier': 2.0,
                'min_size_multiplier': 0.1,
                'stress_reduction_factor': 0.5
            },
            'circuit_breakers': {
                'max_daily_loss_pct': 0.05,
                'max_hourly_trades': 10,
                'emergency_stop_drawdown': 0.20,
                'cooling_period_minutes': 30,
                'max_consecutive_losses': 5
            }
        }
        
        # Estado do sistema
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Métricas em tempo real
        self.current_drawdown = 0.0
        self.daily_pnl = 0.0
        self.active_positions = {}
        self.correlation_matrix = {}
        self.volatility_cache = {}
        
        # Histórico para análises
        self.price_history = defaultdict(lambda: deque(maxlen=1000))
        self.volume_history = defaultdict(lambda: deque(maxlen=1000))
        self.pnl_history = deque(maxlen=10000)
        
        # Circuit breakers
        self.circuit_breakers_active = {}
        self.consecutive_losses = 0
        self.daily_trade_count = 0
        self.last_trade_reset = datetime.now().date()
        
        # Alertas enviados (para evitar spam)
        self.alert_cooldowns = {}
        
    def setup_logging(self):
        """Configura logging detalhado"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def start_real_time_monitoring(self):
        """Inicia monitoramento em tempo real"""
        
        if self.is_monitoring:
            self.logger.warning("Real-time monitoring already running")
            return
        
        self.logger.info("🛡️  Starting real-time risk monitoring...")
        self.is_monitoring = True
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("✅ Real-time monitoring started")
    
    def stop_real_time_monitoring(self):
        """Para monitoramento em tempo real"""
        
        self.logger.info("🛑 Stopping real-time monitoring...")
        self.is_monitoring = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("✅ Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        
        interval = self.protection_config['real_time_monitoring']['check_interval_seconds']
        
        while self.is_monitoring:
            try:
                # Análise contínua de drawdown
                self._analyze_drawdown()
                
                # Detecção de padrões anômalos
                self._detect_anomalous_patterns()
                
                # Verificação de circuit breakers
                self._check_circuit_breakers()
                
                # Análise de correlações
                self._analyze_correlations()
                
                # Proteção de liquidez
                self._check_liquidity_protection()
                
                # Reset diário de contadores
                self._reset_daily_counters()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(interval)
    
    def _analyze_drawdown(self):
        """Análise contínua de drawdown"""
        
        # Calcula drawdown atual
        if len(self.pnl_history) > 0:
            peak_pnl = max(self.pnl_history) if self.pnl_history else 0
            current_pnl = self.pnl_history[-1] if self.pnl_history else 0
            
            if peak_pnl > 0:
                self.current_drawdown = (peak_pnl - current_pnl) / peak_pnl
            else:
                self.current_drawdown = 0.0
        
        thresholds = self.protection_config['real_time_monitoring']
        
        # Alertas de drawdown
        if self.current_drawdown > thresholds['drawdown_critical']:
            self._trigger_alert('drawdown_critical', f'Critical drawdown: {self.current_drawdown:.2%}')
            self._activate_circuit_breaker('emergency_stop', 'Critical drawdown exceeded')
        elif self.current_drawdown > thresholds['drawdown_warning']:
            self._trigger_alert('drawdown_warning', f'Warning drawdown: {self.current_drawdown:.2%}')
    
    def _detect_anomalous_patterns(self):
        """Detecção de padrões anômalos no mercado"""
        
        # Análise de volatilidade extrema
        for symbol in self.volatility_cache:
            volatility = self.volatility_cache[symbol]
            threshold = self.protection_config['real_time_monitoring']['volatility_threshold']
            
            if volatility > threshold:
                self._trigger_alert('high_volatility', f'{symbol} volatility extreme: {volatility:.2%}')
        
        # Detecção de comportamento anômalo em P&L
        if len(self.pnl_history) >= 50:
            recent_pnl = list(self.pnl_history)[-50:]
            pnl_std = np.std(recent_pnl)
            recent_change = recent_pnl[-1] - recent_pnl[-2] if len(recent_pnl) > 1 else 0
            
            # Mudança anormal no P&L
            if abs(recent_change) > 3 * pnl_std:
                self._trigger_alert('pnl_anomaly', f'Anomalous P&L change: ${recent_change:.2f}')
    
    def _check_circuit_breakers(self):
        """Verifica e ativa circuit breakers quando necessário"""
        
        breakers = self.protection_config['circuit_breakers']
        
        # Circuit breaker por perda diária
        if abs(self.daily_pnl) > breakers['max_daily_loss_pct'] * 10000:  # Assumindo capital de 10k
            if 'daily_loss' not in self.circuit_breakers_active:
                self._activate_circuit_breaker('daily_loss', f'Daily loss limit exceeded: ${self.daily_pnl:.2f}')
        
        # Circuit breaker por número de trades
        if self.daily_trade_count > breakers['max_hourly_trades']:
            if 'trade_frequency' not in self.circuit_breakers_active:
                self._activate_circuit_breaker('trade_frequency', f'Trade frequency limit exceeded: {self.daily_trade_count}')
        
        # Circuit breaker por perdas consecutivas
        if self.consecutive_losses >= breakers['max_consecutive_losses']:
            if 'consecutive_losses' not in self.circuit_breakers_active:
                self._activate_circuit_breaker('consecutive_losses', f'Consecutive losses limit: {self.consecutive_losses}')
    
    def _analyze_correlations(self):
        """Análise de correlações entre símbolos"""
        
        correlation_threshold = self.protection_config['real_time_monitoring']['correlation_threshold']
        
        # Calcula correlações se temos dados suficientes
        symbols_with_data = [symbol for symbol in self.price_history.keys() 
                           if len(self.price_history[symbol]) >= 50]
        
        if len(symbols_with_data) >= 2:
            for i, symbol1 in enumerate(symbols_with_data):
                for symbol2 in symbols_with_data[i+1:]:
                    correlation = self._calculate_correlation(symbol1, symbol2)
                    
                    if abs(correlation) > correlation_threshold:
                        self._trigger_alert('high_correlation', 
                                          f'High correlation between {symbol1} and {symbol2}: {correlation:.3f}')
    
    def _check_liquidity_protection(self):
        """Verifica proteção de liquidez"""
        
        min_liquidity = self.protection_config['real_time_monitoring']['liquidity_min_score']
        
        for symbol in self.active_positions:
            # Simula score de liquidez (em produção seria calculado a partir de dados reais)
            liquidity_score = self._calculate_liquidity_score(symbol)
            
            if liquidity_score < min_liquidity:
                self._trigger_alert('low_liquidity', 
                                  f'Low liquidity detected for {symbol}: {liquidity_score:.2f}')
    
    def _reset_daily_counters(self):
        """Reset de contadores diários"""
        
        current_date = datetime.now().date()
        if current_date > self.last_trade_reset:
            self.daily_trade_count = 0
            self.daily_pnl = 0.0
            self.last_trade_reset = current_date
            
            # Reset circuit breakers diários
            breakers_to_reset = ['daily_loss', 'trade_frequency']
            for breaker in breakers_to_reset:
                if breaker in self.circuit_breakers_active:
                    del self.circuit_breakers_active[breaker]
            
            self.logger.info("📅 Daily counters reset")
    
    def adaptive_position_sizing(self, symbol: str, base_size: float, market_data: MarketData) -> float:
        """
        Ajuste adaptativo de position sizing
        Baseado em volatilidade atual, stress do mercado e correlações
        """
        
        config = self.protection_config['adaptive_sizing']
        
        # Tamanho base
        adjusted_size = base_size
        
        # Ajuste por volatilidade
        volatility_multiplier = 1.0
        if market_data.volatility > 0:
            # Reduz tamanho em alta volatilidade
            volatility_factor = config['volatility_adjustment_factor']
            volatility_multiplier = 1.0 / (1.0 + market_data.volatility * volatility_factor)
        
        # Ajuste por stress do sistema
        stress_multiplier = 1.0
        if self.current_drawdown > 0.05:  # 5% drawdown
            stress_multiplier = config['stress_reduction_factor']
        
        # Ajuste por liquidez
        liquidity_multiplier = market_data.liquidity_score
        
        # Ajuste por correlações (reduz se muitas posições correlacionadas)
        correlation_multiplier = self._get_correlation_adjustment(symbol)
        
        # Aplica todos os multiplicadores
        adjusted_size *= volatility_multiplier
        adjusted_size *= stress_multiplier
        adjusted_size *= liquidity_multiplier
        adjusted_size *= correlation_multiplier
        
        # Limites de segurança
        max_multiplier = config['max_size_multiplier']
        min_multiplier = config['min_size_multiplier']
        
        size_ratio = adjusted_size / base_size
        size_ratio = max(min_multiplier, min(max_multiplier, size_ratio))
        
        final_size = base_size * size_ratio
        
        # Log do ajuste
        self.logger.info(f"📊 Position sizing for {symbol}: {base_size:.4f} -> {final_size:.4f} "
                        f"(vol: {volatility_multiplier:.2f}, stress: {stress_multiplier:.2f}, "
                        f"liq: {liquidity_multiplier:.2f}, corr: {correlation_multiplier:.2f})")
        
        return final_size
    
    def correlation_protection(self, new_symbol: str) -> Dict[str, Any]:
        """
        Sistema de proteção contra correlações
        Previne overexposure em ativos correlacionados
        """
        
        correlation_threshold = self.protection_config['real_time_monitoring']['correlation_threshold']
        
        protection_result = {
            'allowed': True,
            'reason': '',
            'correlations': {},
            'risk_score': 0.0
        }
        
        # Verifica correlações com posições existentes
        high_correlations = []
        
        for existing_symbol in self.active_positions:
            if existing_symbol != new_symbol:
                correlation = self._calculate_correlation(new_symbol, existing_symbol)
                protection_result['correlations'][existing_symbol] = correlation
                
                if abs(correlation) > correlation_threshold:
                    high_correlations.append((existing_symbol, correlation))
        
        # Calcula score de risco por correlação
        if high_correlations:
            avg_correlation = np.mean([abs(corr) for _, corr in high_correlations])
            protection_result['risk_score'] = avg_correlation
            
            # Determina se deve bloquear
            if len(high_correlations) >= 2 or avg_correlation > 0.90:
                protection_result['allowed'] = False
                protection_result['reason'] = f'High correlation risk: {len(high_correlations)} correlated positions'
                
                self._trigger_alert('correlation_block', 
                                  f'Blocked {new_symbol} due to high correlation with existing positions')
        
        return protection_result
    
    def liquidity_protection(self, symbol: str, order_size: float) -> Dict[str, Any]:
        """
        Sistema de proteção de liquidez
        Ajusta ordens baseado na liquidez disponível
        """
        
        liquidity_score = self._calculate_liquidity_score(symbol)
        min_liquidity = self.protection_config['real_time_monitoring']['liquidity_min_score']
        
        protection_result = {
            'original_size': order_size,
            'adjusted_size': order_size,
            'liquidity_score': liquidity_score,
            'adjustment_reason': '',
            'allowed': True
        }
        
        if liquidity_score < min_liquidity:
            # Reduz tamanho da ordem baseado na liquidez
            liquidity_factor = liquidity_score / min_liquidity
            adjusted_size = order_size * liquidity_factor
            
            protection_result['adjusted_size'] = adjusted_size
            protection_result['adjustment_reason'] = f'Low liquidity adjustment: {liquidity_score:.2f}'
            
            # Bloqueia se liquidez extremamente baixa
            if liquidity_score < 0.10:
                protection_result['allowed'] = False
                protection_result['adjustment_reason'] = 'Extremely low liquidity - order blocked'
                
                self._trigger_alert('liquidity_block', 
                                  f'Blocked order for {symbol} due to extremely low liquidity: {liquidity_score:.2f}')
        
        return protection_result
    
    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calcula correlação entre dois símbolos"""
        
        if symbol1 not in self.price_history or symbol2 not in self.price_history:
            return 0.0
        
        prices1 = list(self.price_history[symbol1])
        prices2 = list(self.price_history[symbol2])
        
        if len(prices1) < 10 or len(prices2) < 10:
            return 0.0
        
        # Alinha os arrays pelo tamanho menor
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1[-min_len:]
        prices2 = prices2[-min_len:]
        
        # Calcula retornos
        returns1 = np.diff(prices1) / prices1[:-1]
        returns2 = np.diff(prices2) / prices2[:-1]
        
        if len(returns1) == 0 or len(returns2) == 0:
            return 0.0
        
        # Correlação
        correlation = np.corrcoef(returns1, returns2)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _calculate_liquidity_score(self, symbol: str) -> float:
        """Calcula score de liquidez para um símbolo"""
        
        if symbol not in self.volume_history:
            return 0.5  # Score neutro se não temos dados
        
        volumes = list(self.volume_history[symbol])
        if len(volumes) < 10:
            return 0.5
        
        # Score baseado em volume médio e variabilidade
        avg_volume = np.mean(volumes)
        volume_std = np.std(volumes)
        
        # Normaliza para score 0-1
        # Assume que volume > 1M é boa liquidez
        volume_score = min(1.0, avg_volume / 1000000)
        
        # Penaliza alta variabilidade
        if avg_volume > 0:
            stability_score = 1.0 - min(1.0, volume_std / avg_volume)
        else:
            stability_score = 0.0
        
        # Score final (peso maior para volume)
        liquidity_score = 0.7 * volume_score + 0.3 * stability_score
        
        return max(0.0, min(1.0, liquidity_score))
    
    def _get_correlation_adjustment(self, symbol: str) -> float:
        """Calcula ajuste de tamanho baseado em correlações"""
        
        if not self.active_positions:
            return 1.0
        
        correlations = []
        for existing_symbol in self.active_positions:
            if existing_symbol != symbol:
                corr = self._calculate_correlation(symbol, existing_symbol)
                correlations.append(abs(corr))
        
        if not correlations:
            return 1.0
        
        # Reduz tamanho se muitas correlações altas
        avg_correlation = np.mean(correlations)
        correlation_penalty = avg_correlation * 0.5  # Máximo 50% de redução
        
        return 1.0 - correlation_penalty
    
    def _activate_circuit_breaker(self, breaker_type: str, reason: str):
        """Ativa um circuit breaker"""
        
        if breaker_type in self.circuit_breakers_active:
            return  # Já ativo
        
        self.circuit_breakers_active[breaker_type] = {
            'activated_at': datetime.now(),
            'reason': reason,
            'cooling_period': self.protection_config['circuit_breakers']['cooling_period_minutes']
        }
        
        self.logger.critical(f"🚨 CIRCUIT BREAKER ACTIVATED: {breaker_type} - {reason}")
        self._trigger_alert('circuit_breaker', f'Circuit breaker activated: {breaker_type} - {reason}')
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Dispara alerta com controle de cooldown"""
        
        now = datetime.now()
        cooldown_key = f"{alert_type}_{message[:50]}"  # Hash baseado no tipo e parte da mensagem
        
        # Verifica cooldown (5 minutos)
        if cooldown_key in self.alert_cooldowns:
            last_alert = self.alert_cooldowns[cooldown_key]
            if (now - last_alert).total_seconds() < 300:
                return  # Ainda em cooldown
        
        self.alert_cooldowns[cooldown_key] = now
        
        # Log do alerta
        severity = 'critical' if 'critical' in alert_type or 'emergency' in alert_type else 'warning'
        log_level = logging.CRITICAL if severity == 'critical' else logging.WARNING
        
        self.logger.log(log_level, f"🛡️  PROTECTION ALERT [{alert_type.upper()}]: {message}")
    
    def update_market_data(self, symbol: str, price: float, volume: float):
        """Atualiza dados de mercado para análise"""
        
        # Atualiza histórico de preços
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        
        # Calcula volatilidade rolling
        if len(self.price_history[symbol]) >= 20:
            prices = list(self.price_history[symbol])[-20:]
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * np.sqrt(24 * 60)  # Anualizada para 1min timeframe
            self.volatility_cache[symbol] = volatility
    
    def update_position(self, symbol: str, size: float, entry_price: float, current_price: float):
        """Atualiza informações de posição"""
        
        if size == 0 and symbol in self.active_positions:
            # Remove posição fechada
            del self.active_positions[symbol]
        elif size != 0:
            # Atualiza posição existente ou adiciona nova
            pnl = (current_price - entry_price) * size
            
            self.active_positions[symbol] = PositionInfo(
                symbol=symbol,
                size=size,
                entry_price=entry_price,
                current_price=current_price,
                pnl=pnl,
                duration=timedelta(minutes=1)  # Simplificado
            )
    
    def update_pnl(self, pnl: float):
        """Atualiza P&L para análise de drawdown"""
        
        self.pnl_history.append(pnl)
        
        # Atualiza P&L diário
        # Em implementação real, isso seria calculado corretamente
        self.daily_pnl = pnl
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema de proteções"""
        
        return {
            'timestamp': datetime.now().isoformat(),
            'monitoring_active': self.is_monitoring,
            'current_metrics': {
                'drawdown': self.current_drawdown,
                'daily_pnl': self.daily_pnl,
                'active_positions': len(self.active_positions),
                'daily_trades': self.daily_trade_count,
                'consecutive_losses': self.consecutive_losses
            },
            'circuit_breakers': {
                'active': list(self.circuit_breakers_active.keys()),
                'details': self.circuit_breakers_active
            },
            'risk_levels': {
                'drawdown_risk': 'high' if self.current_drawdown > 0.10 else 'medium' if self.current_drawdown > 0.05 else 'low',
                'correlation_risk': 'high' if len(self.active_positions) > 2 else 'low',
                'liquidity_risk': 'medium'  # Simplificado
            },
            'protection_effectiveness': {
                'alerts_triggered_today': len([ts for ts in self.alert_cooldowns.values() 
                                             if ts.date() == datetime.now().date()]),
                'circuit_breakers_today': len([cb for cb in self.circuit_breakers_active.values() 
                                             if cb['activated_at'].date() == datetime.now().date()])
            }
        }

def main():
    """Função principal para demonstração"""
    print("🛡️  Advanced Protection Manager - Etapa 7")
    print("=" * 60)
    
    # Inicializa sistema de proteções
    protection_manager = AdvancedProtectionManager()
    
    print("🚀 Starting protection systems...")
    protection_manager.start_real_time_monitoring()
    
    # Simula dados de mercado para demonstração
    symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
    
    try:
        for i in range(10):
            print(f"\n📊 Simulation step {i+1}/10:")
            
            for symbol in symbols:
                # Simula dados de mercado
                price = 45000 + np.random.normal(0, 1000) if symbol == 'BTC/USDT' else 3000 + np.random.normal(0, 200)
                volume = np.random.uniform(500000, 2000000)
                
                protection_manager.update_market_data(symbol, price, volume)
                
                # Simula posições
                if i > 2:  # Após alguns steps
                    size = np.random.uniform(0.001, 0.1)
                    entry_price = price * (1 + np.random.uniform(-0.02, 0.02))
                    protection_manager.update_position(symbol, size, entry_price, price)
            
            # Simula P&L
            pnl = np.random.uniform(-500, 1000)
            protection_manager.update_pnl(pnl)
            
            # Testa adaptive sizing
            market_data = MarketData(
                timestamp=datetime.now(),
                symbol='BTC/USDT',
                price=45000,
                volume=1000000,
                volatility=0.15,
                liquidity_score=0.8
            )
            
            adjusted_size = protection_manager.adaptive_position_sizing('BTC/USDT', 0.01, market_data)
            print(f"   Adaptive sizing: 0.01 -> {adjusted_size:.4f}")
            
            # Testa correlation protection
            corr_protection = protection_manager.correlation_protection('ETH/USDT')
            print(f"   Correlation protection: {'✅ Allowed' if corr_protection['allowed'] else '❌ Blocked'}")
            
            time.sleep(2)  # Simula intervalo
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        print("\n📊 Final protection status:")
        status = protection_manager.get_protection_status()
        print(f"   Drawdown: {status['current_metrics']['drawdown']:.2%}")
        print(f"   Active Positions: {status['current_metrics']['active_positions']}")
        print(f"   Circuit Breakers: {len(status['circuit_breakers']['active'])}")
        
        protection_manager.stop_real_time_monitoring()
        print("✅ Protection systems stopped")

if __name__ == "__main__":
    main()