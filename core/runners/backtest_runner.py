# core/runners/backtest_runner.py
"""
Maveretta Backtest Runner - Adaptação do Freqtrade para Maveretta
Engine robusto de backtesting integrado com sistema de slots
Origem: freqtrade/optimize/backtesting.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from pathlib import Path
import json
import uuid

from ..data.ohlcv_loader import MaverettaOHLCVLoader
from ..data.data_provider import MaverettaDataProvider  
from ..data.metrics import MaverettaMetricsCalculator, SlotMetrics

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuração de backtest para slot"""
    slot_id: str
    pair: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    fee: float = 0.001
    strategy: str = "momentum"
    max_open_trades: int = 1
    
@dataclass 
class BacktestTrade:
    """Representação de trade no backtest"""
    id: str
    slot_id: str
    pair: str
    side: str  # 'long' ou 'short'
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    fee: float = 0.0
    profit_abs: float = 0.0
    profit_pct: float = 0.0
    exit_reason: Optional[str] = None

@dataclass
class BacktestResult:
    """Resultado completo do backtest"""
    backtest_id: str
    slot_id: str
    pair: str
    timeframe: str
    
    # Configuração
    config: BacktestConfig = field(default_factory=lambda: BacktestConfig("", "", "", datetime.now(), datetime.now()))
    
    # Resultados
    trades: List[BacktestTrade] = field(default_factory=list)
    metrics: Optional[SlotMetrics] = None
    
    # Performance
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    
    # Metadata
    execution_time_seconds: float = 0.0
    candles_analyzed: int = 0
    completed_at: datetime = field(default_factory=datetime.now)

class MaverettaBacktestRunner:
    """
    Engine de backtesting robusto para sistema Maveretta
    Baseado no engine do Freqtrade mas adaptado para slots
    """
    
    def __init__(self, data_provider: Optional[MaverettaDataProvider] = None):
        """
        Inicializa o backtest runner
        
        Args:
            data_provider: Provider de dados (opcional)
        """
        self.data_provider = data_provider or MaverettaDataProvider()
        self.metrics_calculator = MaverettaMetricsCalculator()
        
        # Cache e configurações
        self.results_cache = {}
        self.cache_dir = Path("./data/backtest_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("[BACKTEST_RUNNER] Initialized Maveretta Backtest Runner")
    
    def run_slot_backtest(
        self,
        slot_id: str,
        pair: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        strategy: str = "momentum",
        **kwargs
    ) -> BacktestResult:
        """
        Executa backtest para um slot específico
        
        Args:
            slot_id: ID do slot
            pair: Par de trading
            timeframe: Timeframe
            start_date: Data de início
            end_date: Data de fim
            initial_capital: Capital inicial
            strategy: Estratégia a ser testada
            **kwargs: Parâmetros adicionais
            
        Returns:
            BacktestResult com resultados completos
        """
        start_time = datetime.now()
        backtest_id = str(uuid.uuid4())[:8]
        
        try:
            logger.info(f"[BACKTEST_RUNNER] Starting backtest {backtest_id} for slot {slot_id}: {pair} {timeframe}")
            
            # Configurar backtest
            config = BacktestConfig(
                slot_id=slot_id,
                pair=pair,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                strategy=strategy
            )
            
            # Carregar dados históricos
            df = self.data_provider.get_pair_dataframe_for_slot(
                slot_id=slot_id,
                pair=pair,
                timeframe=timeframe
            )
            
            if df.empty:
                logger.error(f"[BACKTEST_RUNNER] No data available for {slot_id} {pair}")
                return self._create_empty_result(backtest_id, config)
            
            # Filtrar por período
            df = self._filter_dataframe_by_period(df, start_date, end_date)
            
            if df.empty:
                logger.error(f"[BACKTEST_RUNNER] No data in specified period for {slot_id}")
                return self._create_empty_result(backtest_id, config)
            
            # Executar estratégia de backtesting
            trades = self._execute_strategy_backtest(df, config)
            
            # Calcular métricas
            returns_series = self._calculate_returns_from_trades(trades, df, initial_capital)
            metrics = self.metrics_calculator.calculate_slot_metrics(
                slot_id=slot_id,
                pair=pair,
                timeframe=timeframe,
                returns_data=returns_series,
                trades_data=[trade.__dict__ for trade in trades]
            )
            
            # Criar resultado
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = BacktestResult(
                backtest_id=backtest_id,
                slot_id=slot_id,
                pair=pair,
                timeframe=timeframe,
                config=config,
                trades=trades,
                metrics=metrics,
                total_return=metrics.total_return,
                sharpe_ratio=metrics.sharpe_ratio,
                max_drawdown=metrics.max_drawdown,
                win_rate=metrics.win_rate,
                execution_time_seconds=execution_time,
                candles_analyzed=len(df),
                completed_at=datetime.now()
            )
            
            # Cache resultado
            self._cache_backtest_result(result)
            
            logger.info(f"[BACKTEST_RUNNER] Backtest {backtest_id} completed in {execution_time:.2f}s")
            logger.info(f"[BACKTEST_RUNNER] Results: {len(trades)} trades, {metrics.total_return:.2%} return")
            
            return result
            
        except Exception as e:
            logger.error(f"[BACKTEST_RUNNER] Error in backtest {backtest_id}: {e}")
            return self._create_empty_result(backtest_id, config if 'config' in locals() else None)
    
    def run_multi_slot_backtest(
        self,
        slot_configs: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> Dict[str, BacktestResult]:
        """
        Executa backtest para múltiplos slots simultaneamente
        
        Args:
            slot_configs: Lista de configurações dos slots
            start_date: Data de início global
            end_date: Data de fim global
            **kwargs: Parâmetros adicionais
            
        Returns:
            Dict com slot_id como chave e BacktestResult como valor
        """
        try:
            logger.info(f"[BACKTEST_RUNNER] Starting multi-slot backtest for {len(slot_configs)} slots")
            
            results = {}
            
            for slot_config in slot_configs:
                slot_id = slot_config.get('slot_id')
                pair = slot_config.get('pair')
                timeframe = slot_config.get('timeframe', '1h')
                initial_capital = slot_config.get('initial_capital', 10000.0)
                strategy = slot_config.get('strategy', 'momentum')
                
                if not slot_id or not pair:
                    logger.warning("[BACKTEST_RUNNER] Skipping invalid slot config")
                    continue
                
                # Executar backtest individual
                result = self.run_slot_backtest(
                    slot_id=slot_id,
                    pair=pair,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    strategy=strategy,
                    **kwargs
                )
                
                results[slot_id] = result
            
            logger.info(f"[BACKTEST_RUNNER] Multi-slot backtest completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[BACKTEST_RUNNER] Error in multi-slot backtest: {e}")
            return {}
    
    def get_backtest_result(self, backtest_id: str) -> Optional[BacktestResult]:
        """
        Recupera resultado de backtest por ID
        
        Args:
            backtest_id: ID do backtest
            
        Returns:
            BacktestResult se encontrado, None caso contrário
        """
        # Verificar cache em memória primeiro
        if backtest_id in self.results_cache:
            return self.results_cache[backtest_id]
        
        # Tentar carregar do disco
        cache_file = self.cache_dir / f"backtest_{backtest_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    result_data = json.load(f)
                    # Reconstruir resultado (simplificado para demo)
                    return self._reconstruct_result_from_cache(result_data)
            except Exception as e:
                logger.warning(f"[BACKTEST_RUNNER] Error loading cached result {backtest_id}: {e}")
        
        return None
    
    def get_backtest_history(self, slot_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna histórico de backtests executados
        
        Args:
            slot_id: Filtrar por slot (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista com sumário dos backtests
        """
        history = []
        
        # Listar arquivos de cache
        cache_files = sorted(
            self.cache_dir.glob("backtest_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        for cache_file in cache_files[:limit]:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    
                # Filtrar por slot se especificado
                if slot_id and data.get('slot_id') != slot_id:
                    continue
                    
                history.append({
                    'backtest_id': data.get('backtest_id'),
                    'slot_id': data.get('slot_id'),
                    'pair': data.get('pair'),
                    'timeframe': data.get('timeframe'),
                    'total_return': data.get('total_return', 0),
                    'sharpe_ratio': data.get('sharpe_ratio', 0),
                    'trades_count': len(data.get('trades', [])),
                    'completed_at': data.get('completed_at')
                })
                
            except Exception as e:
                logger.warning(f"[BACKTEST_RUNNER] Error reading history file: {e}")
                continue
        
        return history
    
    def _execute_strategy_backtest(self, df: pd.DataFrame, config: BacktestConfig) -> List[BacktestTrade]:
        """
        Executa estratégia de backtesting nos dados
        Implementação simplificada - em produção integraria com sistema de estratégias
        """
        trades = []
        position = None
        
        # Estratégia simples de momentum para demonstração
        df = df.copy()
        
        # Adicionar indicadores
        df['sma_short'] = df['close'].rolling(window=10).mean()
        df['sma_long'] = df['close'].rolling(window=30).mean()
        df['rsi'] = self._calculate_rsi(df['close'])
        
        for i in range(len(df)):
            current_time = df.index[i]
            current_price = df.iloc[i]['close']
            
            # Sinais de entrada
            if position is None:
                # Sinal de compra: SMA curta > SMA longa e RSI < 70
                sma_short = df.iloc[i]['sma_short'] 
                sma_long = df.iloc[i]['sma_long']
                rsi = df.iloc[i]['rsi']
                
                if (not pd.isna(sma_short) and not pd.isna(sma_long) and 
                    not pd.isna(rsi) and sma_short > sma_long and rsi < 70):
                    
                    # Abrir posição longa
                    quantity = config.initial_capital * 0.95 / current_price  # 95% do capital
                    
                    position = BacktestTrade(
                        id=str(uuid.uuid4())[:8],
                        slot_id=config.slot_id,
                        pair=config.pair,
                        side='long',
                        entry_time=current_time,
                        entry_price=current_price,
                        quantity=quantity,
                        fee=config.fee * quantity * current_price
                    )
            
            # Sinais de saída
            elif position is not None:
                # Sinal de venda: SMA curta < SMA longa ou RSI > 80
                sma_short = df.iloc[i]['sma_short']
                sma_long = df.iloc[i]['sma_long'] 
                rsi = df.iloc[i]['rsi']
                
                exit_condition = (
                    (not pd.isna(sma_short) and not pd.isna(sma_long) and sma_short < sma_long) or
                    (not pd.isna(rsi) and rsi > 80)
                )
                
                if exit_condition:
                    # Fechar posição
                    position.exit_time = current_time
                    position.exit_price = current_price
                    position.profit_abs = ((current_price - position.entry_price) * position.quantity 
                                         - position.fee - config.fee * position.quantity * current_price)
                    position.profit_pct = position.profit_abs / (position.entry_price * position.quantity)
                    position.exit_reason = "strategy_signal"
                    
                    trades.append(position)
                    position = None
        
        # Fechar posição aberta no final
        if position is not None:
            final_price = df.iloc[-1]['close']
            position.exit_time = df.index[-1]
            position.exit_price = final_price
            position.profit_abs = ((final_price - position.entry_price) * position.quantity 
                                 - position.fee - config.fee * position.quantity * final_price)
            position.profit_pct = position.profit_abs / (position.entry_price * position.quantity)
            position.exit_reason = "end_of_data"
            
            trades.append(position)
        
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calcula RSI simples"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_returns_from_trades(
        self, 
        trades: List[BacktestTrade], 
        df: pd.DataFrame, 
        initial_capital: float
    ) -> pd.Series:
        """Calcula série de retornos baseada nos trades"""
        
        # Inicializar série de retornos
        returns = pd.Series(0.0, index=df.index)
        capital = initial_capital
        
        for trade in trades:
            if trade.exit_time is not None:
                # Calcular retorno do trade
                trade_return = trade.profit_abs / capital
                
                # Aplicar retorno no momento da saída
                if trade.exit_time in returns.index:
                    returns[trade.exit_time] = trade_return
                
                # Atualizar capital
                capital += trade.profit_abs
        
        return returns
    
    def _filter_dataframe_by_period(
        self, 
        df: pd.DataFrame, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Filtra DataFrame pelo período especificado"""
        if df.empty:
            return df
        
        try:
            # Garantir que o index seja datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                return df
            
            # Filtrar período
            mask = (df.index >= start_date) & (df.index <= end_date)
            return df[mask]
            
        except Exception as e:
            logger.warning(f"[BACKTEST_RUNNER] Error filtering dataframe by period: {e}")
            return df
    
    def _cache_backtest_result(self, result: BacktestResult) -> None:
        """Salva resultado no cache"""
        try:
            # Cache em memória
            self.results_cache[result.backtest_id] = result
            
            # Cache em disco (simplificado)
            cache_file = self.cache_dir / f"backtest_{result.backtest_id}.json"
            cache_data = {
                'backtest_id': result.backtest_id,
                'slot_id': result.slot_id,
                'pair': result.pair,
                'timeframe': result.timeframe,
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'trades': [
                    {
                        'id': trade.id,
                        'side': trade.side,
                        'entry_time': trade.entry_time.isoformat(),
                        'entry_price': trade.entry_price,
                        'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                        'exit_price': trade.exit_price,
                        'profit_abs': trade.profit_abs,
                        'profit_pct': trade.profit_pct
                    }
                    for trade in result.trades
                ],
                'completed_at': result.completed_at.isoformat(),
                'execution_time_seconds': result.execution_time_seconds
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
        except Exception as e:
            logger.warning(f"[BACKTEST_RUNNER] Error caching result: {e}")
    
    def _create_empty_result(self, backtest_id: str, config: Optional[BacktestConfig]) -> BacktestResult:
        """Cria resultado vazio para casos de erro"""
        return BacktestResult(
            backtest_id=backtest_id,
            slot_id=config.slot_id if config else "unknown",
            pair=config.pair if config else "unknown",
            timeframe=config.timeframe if config else "unknown",
            config=config or BacktestConfig("", "", "", datetime.now(), datetime.now()),
            completed_at=datetime.now()
        )
    
    def _reconstruct_result_from_cache(self, data: Dict[str, Any]) -> BacktestResult:
        """Reconstrói resultado a partir do cache (simplificado)"""
        # Implementação simplificada para demo
        return BacktestResult(
            backtest_id=data.get('backtest_id', ''),
            slot_id=data.get('slot_id', ''),
            pair=data.get('pair', ''),
            timeframe=data.get('timeframe', ''),
            total_return=data.get('total_return', 0),
            sharpe_ratio=data.get('sharpe_ratio', 0),
            max_drawdown=data.get('max_drawdown', 0),
            win_rate=data.get('win_rate', 0)
        )

# Funções de conveniência
def run_slot_backtest(slot_id: str, pair: str, timeframe: str, start_date: datetime, 
                     end_date: datetime, **kwargs) -> BacktestResult:
    """Função de conveniência para backtest de slot"""
    runner = MaverettaBacktestRunner()
    return runner.run_slot_backtest(slot_id, pair, timeframe, start_date, end_date, **kwargs)