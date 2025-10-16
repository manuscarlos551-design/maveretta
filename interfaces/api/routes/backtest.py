# interfaces/api/routes/backtest.py
"""
Maveretta Backtest API Routes
Endpoints para execução de backtests integrados com sistema de slots
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

from core.runners import MaverettaBacktestRunner, run_slot_backtest
from core.runners.backtest_cache import MaverettaBacktestCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

# Pydantic Models
class BacktestRequest(BaseModel):
    """Requisição de backtest para slot"""
    slot_id: str = Field(..., description="ID do slot")
    symbol: str = Field(..., description="Par de trading (ex: BTC/USDT)")
    timeframe: str = Field(default="1h", description="Timeframe (1m, 5m, 1h, 1d, etc)")
    start_date: str = Field(..., description="Data início (ISO format)")
    end_date: str = Field(..., description="Data fim (ISO format)")
    initial_capital: float = Field(default=10000.0, description="Capital inicial")
    strategy: str = Field(default="momentum", description="Nome da estratégia")
    fee: float = Field(default=0.001, description="Taxa de fee")

class MultiSlotBacktestRequest(BaseModel):
    """Requisição de backtest para múltiplos slots"""
    slots: List[Dict[str, Any]] = Field(..., description="Lista de configurações dos slots")
    period: Dict[str, str] = Field(..., description="Período global (start, end)")
    
class BacktestResponse(BaseModel):
    """Resposta de backtest"""
    success: bool
    backtest_id: str
    slot_id: str
    pair: str
    timeframe: str
    
    # Resultados
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    
    # Estatísticas
    trades_count: int = 0
    candles_analyzed: int = 0
    execution_time_seconds: float = 0.0
    completed_at: str = ""
    
    # Dados adicionais (opcionais)
    trades: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

# Inicializar runner global
backtest_runner = MaverettaBacktestRunner()
backtest_cache = MaverettaBacktestCache()

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """
    Executa backtest para um slot específico
    
    Args:
        request: Parâmetros do backtest
        
    Returns:
        Resultado do backtest
    """
    try:
        logger.info(f"[API] Starting backtest for slot {request.slot_id}: {request.symbol} {request.timeframe}")
        
        # Validar datas
        try:
            start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
        # Validar período
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if (end_date - start_date).days > 365:
            raise HTTPException(status_code=400, detail="Backtest period cannot exceed 1 year")
        
        # Executar backtest
        result = backtest_runner.run_slot_backtest(
            slot_id=request.slot_id,
            pair=request.symbol,
            timeframe=request.timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=request.initial_capital,
            strategy=request.strategy
        )
        
        # Preparar resposta
        response = BacktestResponse(
            success=True,
            backtest_id=result.backtest_id,
            slot_id=result.slot_id,
            pair=result.pair,
            timeframe=result.timeframe,
            total_return=result.total_return,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            trades_count=len(result.trades),
            candles_analyzed=result.candles_analyzed,
            execution_time_seconds=result.execution_time_seconds,
            completed_at=result.completed_at.isoformat(),
            trades=[
                {
                    'id': trade.id,
                    'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                    'entry_price': trade.entry_price,
                    'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                    'exit_price': trade.exit_price,
                    'profit_abs': trade.profit_abs,
                    'profit_pct': trade.profit_pct,
                    'side': trade.side
                }
                for trade in result.trades
            ]
        )
        
        logger.info(f"[API] Backtest completed for slot {request.slot_id}: "
                   f"{result.total_return:.2%} return, {len(result.trades)} trades")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error in backtest execution: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {str(e)}")

@router.post("/run-multi-slot")
async def run_multi_slot_backtest(request: MultiSlotBacktestRequest) -> Dict[str, Any]:
    """
    Executa backtest para múltiplos slots simultaneamente
    
    Args:
        request: Configurações dos slots e período
        
    Returns:
        Resultados por slot
    """
    try:
        logger.info(f"[API] Starting multi-slot backtest for {len(request.slots)} slots")
        
        # Validar período global
        start_date = datetime.fromisoformat(request.period['start'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.period['end'].replace('Z', '+00:00'))
        
        # Validar configurações dos slots
        for slot_config in request.slots:
            if 'slot_id' not in slot_config or 'symbol' not in slot_config:
                raise HTTPException(status_code=400, detail="Each slot must have slot_id and symbol")
        
        # Executar backtest multi-slot
        results = backtest_runner.run_multi_slot_backtest(
            slot_configs=request.slots,
            start_date=start_date,
            end_date=end_date
        )
        
        # Preparar resposta agregada
        response_data = {
            'success': True,
            'total_slots': len(results),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'results': {}
        }
        
        # Processar resultados por slot
        total_return_sum = 0.0
        for slot_id, result in results.items():
            response_data['results'][slot_id] = {
                'backtest_id': result.backtest_id,
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'trades_count': len(result.trades),
                'execution_time': result.execution_time_seconds
            }
            total_return_sum += result.total_return
        
        # Adicionar estatísticas agregadas
        response_data['portfolio_stats'] = {
            'average_return': total_return_sum / len(results) if results else 0.0,
            'total_trades': sum(len(r.trades) for r in results.values()),
            'best_performer': max(results.keys(), key=lambda k: results[k].total_return) if results else None,
            'worst_performer': min(results.keys(), key=lambda k: results[k].total_return) if results else None
        }
        
        logger.info(f"[API] Multi-slot backtest completed: {len(results)} slots processed")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error in multi-slot backtest: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-slot backtest failed: {str(e)}")

@router.get("/results/{backtest_id}")
async def get_backtest_result(backtest_id: str = Path(..., description="ID do backtest")) -> Dict[str, Any]:
    """
    Recupera resultado de backtest por ID
    
    Args:
        backtest_id: ID único do backtest
        
    Returns:
        Dados completos do backtest
    """
    try:
        result = backtest_runner.get_backtest_result(backtest_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
        
        return {
            'backtest_id': result.backtest_id,
            'slot_id': result.slot_id,
            'pair': result.pair,
            'timeframe': result.timeframe,
            'metrics': {
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate
            },
            'trades': [
                {
                    'id': trade.id,
                    'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                    'entry_price': trade.entry_price,
                    'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                    'exit_price': trade.exit_price,
                    'profit_abs': trade.profit_abs,
                    'profit_pct': trade.profit_pct
                }
                for trade in result.trades
            ],
            'execution_info': {
                'candles_analyzed': result.candles_analyzed,
                'execution_time_seconds': result.execution_time_seconds,
                'completed_at': result.completed_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting backtest result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backtest result: {str(e)}")

@router.get("/history")
async def get_backtest_history(
    slot_id: Optional[str] = Query(None, description="Filtrar por slot ID"),
    limit: int = Query(10, ge=1, le=100, description="Limite de resultados")
) -> List[Dict[str, Any]]:
    """
    Retorna histórico de backtests executados
    
    Args:
        slot_id: Filtrar por slot específico (opcional)
        limit: Número máximo de resultados
        
    Returns:
        Lista de backtests executados
    """
    try:
        history = backtest_runner.get_backtest_history(slot_id=slot_id, limit=limit)
        
        return [
            {
                'backtest_id': item['backtest_id'],
                'slot_id': item['slot_id'],
                'pair': item['pair'],
                'timeframe': item['timeframe'],
                'total_return': item['total_return'],
                'sharpe_ratio': item['sharpe_ratio'],
                'trades_count': item['trades_count'],
                'completed_at': item['completed_at']
            }
            for item in history
        ]
        
    except Exception as e:
        logger.error(f"[API] Error getting backtest history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backtest history: {str(e)}")

@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Retorna estatísticas do cache de backtest
    
    Returns:
        Estatísticas do cache
    """
    try:
        stats = backtest_cache.get_cache_stats()
        return {
            'cache_stats': stats,
            'cache_enabled': True
        }
        
    except Exception as e:
        logger.error(f"[API] Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.delete("/cache/{backtest_id}")
async def clear_backtest_cache(
    backtest_id: str = Path(..., description="ID específico do cache (use 'all' para limpar tudo)")
) -> Dict[str, Any]:
    """
    Limpa cache de backtest
    
    Args:
        backtest_id: ID específico para limpar (None = tudo)
        
    Returns:
        Status da limpeza
    """
    try:
        if backtest_id and backtest_id != "all":
            # Limpar cache específico
            success = backtest_cache.invalidate_cache(backtest_id)
            return {
                'success': success,
                'message': f"Cache cleared for backtest {backtest_id}" if success else "Cache not found"
            }
        else:
            # Limpar todo o cache
            cleared_count = backtest_cache.clear_cache()
            return {
                'success': True,
                'cleared_entries': cleared_count,
                'message': f"Cleared {cleared_count} cache entries"
            }
        
    except Exception as e:
        logger.error(f"[API] Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/status")
async def get_backtest_engine_status() -> Dict[str, Any]:
    """
    Retorna status do engine de backtest
    
    Returns:
        Status do engine
    """
    try:
        cache_stats = backtest_cache.get_cache_stats()
        
        return {
            'engine_status': 'running',
            'version': '1.0.0',
            'cache_info': cache_stats,
            'supported_timeframes': ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d'],
            'supported_strategies': ['momentum', 'mean_reversion', 'breakout'],
            'max_backtest_period_days': 365,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[API] Error getting engine status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get engine status: {str(e)}")