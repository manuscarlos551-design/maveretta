# core/runners/backtester.py
"""
Backtester - Sistema de backtesting adaptado do Freqtrade
"""
import logging
import uuid
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, NamedTuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
import redis

from ..data.data_provider import MaverettaDataProvider

# Criar instância do data provider
data_provider = MaverettaDataProvider()
from ..data.metrics import MaverettaMetricsCalculator

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    symbol: str
    timeframe: str = "1h"
    start_date: datetime = None
    end_date: datetime = None
    initial_capital: float = 10000.0
    fee: float = 0.001
    strategy: str = "momentum"
    exchange: str = "binance"

@dataclass
class Trade:
    id: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    side: str = "long"  # long or short
    amount: float = 0.0
    profit_abs: Optional[float] = None
    profit_pct: Optional[float] = None
    duration_minutes: Optional[int] = None
    exit_reason: Optional[str] = None

@dataclass
class BacktestResult:
    backtest_id: str
    slot_id: str
    pair: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    
    # Performance metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_profit_pct: float
    
    # Execution info
    trades: List[Trade]
    candles_analyzed: int
    execution_time_seconds: float
    completed_at: datetime
    
    # Equity curve
    equity_curve: Optional[List[Dict]] = None

class SimpleStrategy:
    """Estratégia simples para backtesting"""
    
    def __init__(self, strategy_type: str = "momentum"):
        self.strategy_type = strategy_type
        self.position = None
        self.last_signal = None
    
    def generate_signals(self, ohlcv_data: List[Dict]) -> List[Dict]:
        """
        Gera sinais de entrada e saída
        
        Returns:
            Lista com sinais para cada candle
        """
        if len(ohlcv_data) < 50:  # Mínimo para cálculos
            return [{'entry': False, 'exit': False} for _ in ohlcv_data]
        
        # Converter para DataFrame
        df = pd.DataFrame(ohlcv_data)
        df['close'] = pd.to_numeric(df['close'])
        
        signals = []
        
        if self.strategy_type == "momentum":
            signals = self._momentum_strategy(df)
        elif self.strategy_type == "mean_reversion":
            signals = self._mean_reversion_strategy(df)
        elif self.strategy_type == "breakout":
            signals = self._breakout_strategy(df)
        else:
            # Estratégia padrão (momentum)
            signals = self._momentum_strategy(df)
        
        return signals
    
    def _momentum_strategy(self, df: pd.DataFrame) -> List[Dict]:
        """Estratégia de momentum usando médias móveis"""
        # Calcular médias móveis
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        signals = []
        
        for i in range(len(df)):
            entry = False
            exit = False
            
            if i > 50:  # Aguardar indicadores estabilizarem
                # Sinal de entrada: SMA20 cruza acima SMA50 + RSI não sobrevvendido
                if (df['sma_20'].iloc[i] > df['sma_50'].iloc[i] and 
                    df['sma_20'].iloc[i-1] <= df['sma_50'].iloc[i-1] and
                    df['rsi'].iloc[i] > 30):
                    entry = True
                
                # Sinal de saída: SMA20 cruza abaixo SMA50 ou RSI sobrecomprado
                if (df['sma_20'].iloc[i] < df['sma_50'].iloc[i] and 
                    df['sma_20'].iloc[i-1] >= df['sma_50'].iloc[i-1]) or df['rsi'].iloc[i] > 80:
                    exit = True
            
            signals.append({'entry': entry, 'exit': exit})
        
        return signals
    
    def _mean_reversion_strategy(self, df: pd.DataFrame) -> List[Dict]:
        """Estratégia de reversão à média usando Bollinger Bands"""
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['std_20'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (df['std_20'] * 2)
        df['bb_lower'] = df['sma_20'] - (df['std_20'] * 2)
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        signals = []
        
        for i in range(len(df)):
            entry = False
            exit = False
            
            if i > 20:
                # Entrada: preço toca banda inferior + RSI sobrevendido
                if (df['close'].iloc[i] <= df['bb_lower'].iloc[i] and 
                    df['rsi'].iloc[i] < 30):
                    entry = True
                
                # Saída: preço cruza média móvel ou toca banda superior
                if (df['close'].iloc[i] >= df['sma_20'].iloc[i] or
                    df['close'].iloc[i] >= df['bb_upper'].iloc[i]):
                    exit = True
            
            signals.append({'entry': entry, 'exit': exit})
        
        return signals
    
    def _breakout_strategy(self, df: pd.DataFrame) -> List[Dict]:
        """Estratégia de breakout usando máximas/mínimas"""
        # Calcular máximas e mínimas de período
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        signals = []
        
        for i in range(len(df)):
            entry = False
            exit = False
            
            if i > 20:
                # Entrada: breakout acima da máxima com volume
                if (df['close'].iloc[i] > df['high_20'].iloc[i-1] and
                    df['volume'].iloc[i] > df['volume_sma'].iloc[i] * 1.5):
                    entry = True
                
                # Saída: preço cai abaixo da mínima recente
                if df['close'].iloc[i] < df['low_20'].iloc[i]:
                    exit = True
            
            signals.append({'entry': entry, 'exit': exit})
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

class MaverettaBacktester:
    """Sistema de backtesting do Maveretta Bot"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.results_cache = {}
    
    def _get_redis_client(self):
        """Obtém cliente Redis"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Erro ao conectar Redis para backtest: {e}")
            return None
    
    async def run_backtest(
        self,
        slot_id: str,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        Executa um backtest completo
        
        Args:
            slot_id: ID do slot
            config: Configuração do backtest
            
        Returns:
            Resultado do backtest
        """
        start_time = datetime.now()
        backtest_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Iniciando backtest {backtest_id} para slot {slot_id}: {config.symbol}")
            
            # Obter dados OHLCV
            ohlcv_data = await data_provider.get_ohlcv(
                symbol=config.symbol,
                timeframe=config.timeframe,
                limit=1000,  # Máximo para análise
                since=config.start_date,
                exchange=config.exchange,
                use_cache=True
            )
            
            if not ohlcv_data:
                raise ValueError(f"Nenhum dado OHLCV encontrado para {config.symbol}")
            
            # Filtrar dados por período se especificado
            if config.start_date or config.end_date:
                ohlcv_data = self._filter_data_by_period(ohlcv_data, config.start_date, config.end_date)
            
            if len(ohlcv_data) < 100:
                raise ValueError("Dados insuficientes para backtest (mínimo 100 candles)")
            
            # Executar simulação
            trades = await self._simulate_trading(ohlcv_data, config)
            
            # Calcular métricas
            metrics = self._calculate_metrics(trades, ohlcv_data, config.initial_capital)
            
            # Criar resultado
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = BacktestResult(
                backtest_id=backtest_id,
                slot_id=slot_id,
                pair=config.symbol,
                timeframe=config.timeframe,
                start_date=config.start_date or datetime.fromisoformat(ohlcv_data[0]['datetime']),
                end_date=config.end_date or datetime.fromisoformat(ohlcv_data[-1]['datetime']),
                trades=trades,
                candles_analyzed=len(ohlcv_data),
                execution_time_seconds=execution_time,
                completed_at=datetime.now(),
                **metrics
            )
            
            # Salvar resultado
            self._save_result(result)
            
            logger.info(f"Backtest concluído: {len(trades)} trades, retorno {metrics['total_return']:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"Erro no backtest {backtest_id}: {e}")
            raise
    
    def _filter_data_by_period(
        self, 
        ohlcv_data: List[Dict], 
        start_date: Optional[datetime], 
        end_date: Optional[datetime]
    ) -> List[Dict]:
        """Filtra dados pelo período especificado"""
        filtered_data = []
        
        for candle in ohlcv_data:
            candle_date = datetime.fromisoformat(candle['datetime'])
            
            if start_date and candle_date < start_date:
                continue
            if end_date and candle_date > end_date:
                continue
            
            filtered_data.append(candle)
        
        return filtered_data
    
    async def _simulate_trading(
        self, 
        ohlcv_data: List[Dict], 
        config: BacktestConfig
    ) -> List[Trade]:
        """
        Simula execução de trades baseada na estratégia
        
        Args:
            ohlcv_data: Dados OHLCV
            config: Configuração do backtest
            
        Returns:
            Lista de trades executados
        """
        try:
            # Inicializar estratégia
            strategy = SimpleStrategy(config.strategy)
            
            # Gerar sinais
            signals = strategy.generate_signals(ohlcv_data)
            
            # Simular execução
            trades = []
            current_trade = None
            
            for i, (candle, signal) in enumerate(zip(ohlcv_data, signals)):
                candle_time = datetime.fromisoformat(candle['datetime'])
                candle_price = float(candle['close'])
                
                # Processar sinal de entrada
                if signal['entry'] and current_trade is None:
                    current_trade = Trade(
                        id=str(uuid.uuid4()),
                        entry_time=candle_time,
                        entry_price=candle_price * (1 + config.fee),  # Incluir fee de entrada
                        side="long"
                    )
                
                # Processar sinal de saída
                if signal['exit'] and current_trade is not None:
                    exit_price = candle_price * (1 - config.fee)  # Incluir fee de saída
                    
                    # Calcular lucro
                    profit_abs = exit_price - current_trade.entry_price
                    profit_pct = (profit_abs / current_trade.entry_price) * 100
                    
                    # Calcular duração
                    duration = (candle_time - current_trade.entry_time).total_seconds() / 60
                    
                    # Finalizar trade
                    current_trade.exit_time = candle_time
                    current_trade.exit_price = exit_price
                    current_trade.profit_abs = profit_abs
                    current_trade.profit_pct = profit_pct
                    current_trade.duration_minutes = int(duration)
                    current_trade.exit_reason = "strategy_signal"
                    
                    trades.append(current_trade)
                    current_trade = None
            
            # Fechar trade em aberto se houver
            if current_trade is not None:
                last_candle = ohlcv_data[-1]
                exit_price = float(last_candle['close']) * (1 - config.fee)
                
                profit_abs = exit_price - current_trade.entry_price
                profit_pct = (profit_abs / current_trade.entry_price) * 100
                duration = (datetime.fromisoformat(last_candle['datetime']) - current_trade.entry_time).total_seconds() / 60
                
                current_trade.exit_time = datetime.fromisoformat(last_candle['datetime'])
                current_trade.exit_price = exit_price
                current_trade.profit_abs = profit_abs
                current_trade.profit_pct = profit_pct
                current_trade.duration_minutes = int(duration)
                current_trade.exit_reason = "end_of_data"
                
                trades.append(current_trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"Erro na simulação de trading: {e}")
            return []
    
    def _calculate_metrics(
        self, 
        trades: List[Trade], 
        ohlcv_data: List[Dict], 
        initial_capital: float
    ) -> Dict[str, Any]:
        """Calcula métricas de performance do backtest"""
        try:
            if not trades:
                return {
                    'total_return': 0.0,
                    'annualized_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'avg_profit': 0.0,
                    'avg_profit_pct': 0.0
                }
            
            # Converter trades para formato de métricas
            trades_data = []
            for trade in trades:
                trades_data.append({
                    'profit_abs': trade.profit_abs,
                    'profit_pct': trade.profit_pct,
                    'duration_minutes': trade.duration_minutes,
                    'close_date': trade.exit_time.isoformat() if trade.exit_time else None,
                    'open_date': trade.entry_time.isoformat()
                })
            
            # Calcular métricas básicas
            # Usar MaverettaMetricsCalculator.from_trades em vez dos métodos antigos
            trades_formatted = [{"pnl": t.get("profit_abs", 0), "pnl_pct": t.get("profit_pct", 0)} for t in trades_data]
            slot_metrics = MaverettaMetricsCalculator.from_trades(trades_formatted)
            
            # Converter para formato compatível
            basic_metrics = {
                "total_trades": slot_metrics.total_trades,
                "winning_trades": slot_metrics.wins,
                "losing_trades": slot_metrics.losses,
                "win_rate": slot_metrics.win_rate,
                "total_profit": slot_metrics.net_profit,
                "avg_profit": slot_metrics.avg_profit,
                "avg_loss": slot_metrics.avg_loss
            }
            
            advanced_metrics = {
                "sharpe_ratio": slot_metrics.sharpe,
                "sortino_ratio": slot_metrics.sortino,
                "max_drawdown": slot_metrics.max_drawdown_pct
            }
            
            # Combinar métricas
            all_metrics = {**basic_metrics, **advanced_metrics}
            
            # Calcular retorno anualizado
            if ohlcv_data and len(ohlcv_data) > 1:
                start_date = datetime.fromisoformat(ohlcv_data[0]['datetime'])
                end_date = datetime.fromisoformat(ohlcv_data[-1]['datetime'])
                days = max(1, (end_date - start_date).days)
                
                total_return = all_metrics.get('total_return', 0) / 100  # Converter de % para decimal
                if days > 0:
                    annualized_return = ((1 + total_return) ** (365 / days)) - 1
                    all_metrics['annualized_return'] = annualized_return * 100  # Converter para %
                else:
                    all_metrics['annualized_return'] = 0
            else:
                all_metrics['annualized_return'] = 0
            
            return all_metrics
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas do backtest: {e}")
            return {}
    
    def _save_result(self, result: BacktestResult):
        """Salva resultado do backtest"""
        try:
            # Cache em memória
            self.results_cache[result.backtest_id] = result
            
            # Salvar no Redis se disponível
            if self.redis_client:
                result_data = {
                    'backtest_id': result.backtest_id,
                    'slot_id': result.slot_id,
                    'pair': result.pair,
                    'timeframe': result.timeframe,
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades,
                    'completed_at': result.completed_at.isoformat(),
                    'execution_time_seconds': result.execution_time_seconds
                }
                
                key = f"backtest_result:{result.backtest_id}"
                self.redis_client.setex(key, 86400 * 7, json.dumps(result_data))  # TTL 7 dias
                
                # Adicionar à lista de histórico
                history_key = f"backtest_history:{result.slot_id}"
                self.redis_client.lpush(history_key, json.dumps(result_data))
                self.redis_client.ltrim(history_key, 0, 99)  # Manter últimos 100
                
        except Exception as e:
            logger.warning(f"Erro ao salvar resultado do backtest: {e}")
    
    def get_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """Obtém resultado de backtest por ID"""
        try:
            # Verificar cache em memória primeiro
            if backtest_id in self.results_cache:
                return self.results_cache[backtest_id]
            
            # Verificar Redis
            if self.redis_client:
                key = f"backtest_result:{backtest_id}"
                result_data = self.redis_client.get(key)
                if result_data:
                    # Retornar dados básicos (sem trades completos)
                    data = json.loads(result_data)
                    return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao obter resultado do backtest: {e}")
            return None
    
    def get_history(self, slot_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Obtém histórico de backtests"""
        try:
            if not self.redis_client:
                return []
            
            if slot_id:
                # Histórico de um slot específico
                history_key = f"backtest_history:{slot_id}"
                history_data = self.redis_client.lrange(history_key, 0, limit - 1)
            else:
                # Histórico geral (implementação simplificada)
                history_data = []
                
                # Buscar de todos os slots conhecidos (implementação básica)
                slot_keys = self.redis_client.keys("backtest_history:*")
                for key in slot_keys[:10]:  # Limitar busca
                    slot_history = self.redis_client.lrange(key, 0, 4)  # 5 mais recentes por slot
                    history_data.extend(slot_history)
            
            # Converter e ordenar por data
            history = []
            for item_str in history_data:
                try:
                    item = json.loads(item_str)
                    history.append(item)
                except:
                    continue
            
            # Ordenar por data decrescente
            history.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
            
            return history[:limit]
            
        except Exception as e:
            logger.warning(f"Erro ao obter histórico de backtests: {e}")
            return []


# Instância global
maveretta_backtester = MaverettaBacktester()