# core/data/timeframe.py
"""
Timeframe Utilities - Utilitários para trabalhar com timeframes
Adaptado do Freqtrade
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Mapeamento de timeframes para segundos
TIMEFRAME_SECONDS = {
    '1m': 60,
    '3m': 180,
    '5m': 300,
    '15m': 900,
    '30m': 1800,
    '1h': 3600,
    '2h': 7200,
    '4h': 14400,
    '6h': 21600,
    '8h': 28800,
    '12h': 43200,
    '1d': 86400,
    '3d': 259200,
    '1w': 604800,
    '1M': 2629746,  # Aproximadamente 30.44 dias
}

# Timeframes válidos em ordem crescente
VALID_TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

def timeframe_to_seconds(timeframe: str) -> int:
    """
    Converte timeframe para segundos
    
    Args:
        timeframe: Timeframe (ex: '1h', '5m')
        
    Returns:
        Número de segundos
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"Timeframe inválido: {timeframe}")
    
    return TIMEFRAME_SECONDS[timeframe]

def timeframe_to_minutes(timeframe: str) -> int:
    """
    Converte timeframe para minutos
    
    Args:
        timeframe: Timeframe
        
    Returns:
        Número de minutos
    """
    return timeframe_to_seconds(timeframe) // 60

def timeframe_to_timedelta(timeframe: str) -> timedelta:
    """
    Converte timeframe para timedelta
    
    Args:
        timeframe: Timeframe
        
    Returns:
        Objeto timedelta
    """
    seconds = timeframe_to_seconds(timeframe)
    return timedelta(seconds=seconds)

def validate_timeframe(timeframe: str) -> bool:
    """
    Valida se timeframe é suportado
    
    Args:
        timeframe: Timeframe para validar
        
    Returns:
        True se válido
    """
    return timeframe in TIMEFRAME_SECONDS

def get_higher_timeframes(timeframe: str, count: int = 3) -> List[str]:
    """
    Obtém timeframes superiores ao fornecido
    
    Args:
        timeframe: Timeframe base
        count: Quantos timeframes superiores retornar
        
    Returns:
        Lista de timeframes superiores
    """
    try:
        current_index = VALID_TIMEFRAMES.index(timeframe)
        return VALID_TIMEFRAMES[current_index + 1:current_index + 1 + count]
    except ValueError:
        return []

def get_lower_timeframes(timeframe: str, count: int = 3) -> List[str]:
    """
    Obtém timeframes inferiores ao fornecido
    
    Args:
        timeframe: Timeframe base
        count: Quantos timeframes inferiores retornar
        
    Returns:
        Lista de timeframes inferiores
    """
    try:
        current_index = VALID_TIMEFRAMES.index(timeframe)
        start_index = max(0, current_index - count)
        return VALID_TIMEFRAMES[start_index:current_index]
    except ValueError:
        return []

def timeframe_to_prev_date(timeframe: str, date: datetime) -> datetime:
    """
    Obtém data anterior baseada no timeframe
    
    Args:
        timeframe: Timeframe
        date: Data base
        
    Returns:
        Data anterior alinhada ao timeframe
    """
    seconds = timeframe_to_seconds(timeframe)
    
    # Alinhar ao início do período
    if timeframe.endswith('m'):
        # Para minutos, alinhar aos minutos
        minutes = timeframe_to_minutes(timeframe)
        aligned_minute = (date.minute // minutes) * minutes
        prev_date = date.replace(minute=aligned_minute, second=0, microsecond=0)
    elif timeframe.endswith('h'):
        # Para horas, alinhar às horas
        hours = timeframe_to_seconds(timeframe) // 3600
        aligned_hour = (date.hour // hours) * hours
        prev_date = date.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    elif timeframe == '1d':
        # Para dias, alinhar ao início do dia
        prev_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Para outros timeframes, apenas subtrair o período
        prev_date = date - timedelta(seconds=seconds)
    
    return prev_date

def round_timeframe_date(date: datetime, timeframe: str) -> datetime:
    """
    Arredonda data para o início do período do timeframe
    
    Args:
        date: Data para arredondar
        timeframe: Timeframe
        
    Returns:
        Data arredondada
    """
    if timeframe == '1m':
        return date.replace(second=0, microsecond=0)
    elif timeframe == '5m':
        minute = (date.minute // 5) * 5
        return date.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == '15m':
        minute = (date.minute // 15) * 15
        return date.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == '30m':
        minute = (date.minute // 30) * 30
        return date.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == '1h':
        return date.replace(minute=0, second=0, microsecond=0)
    elif timeframe == '4h':
        hour = (date.hour // 4) * 4
        return date.replace(hour=hour, minute=0, second=0, microsecond=0)
    elif timeframe == '1d':
        return date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Para outros timeframes, usar lógica genérica
        seconds = timeframe_to_seconds(timeframe)
        timestamp = int(date.timestamp())
        rounded_timestamp = (timestamp // seconds) * seconds
        return datetime.fromtimestamp(rounded_timestamp)

def calculate_candles_needed(
    timeframe: str, 
    period_days: int, 
    buffer_candles: int = 0
) -> int:
    """
    Calcula quantos candles são necessários para um período
    
    Args:
        timeframe: Timeframe dos candles
        period_days: Período em dias
        buffer_candles: Candles extras como buffer
        
    Returns:
        Número de candles necessários
    """
    seconds_per_day = 86400
    timeframe_seconds = timeframe_to_seconds(timeframe)
    
    candles_per_day = seconds_per_day // timeframe_seconds
    total_candles = period_days * candles_per_day + buffer_candles
    
    return total_candles

def get_timeframe_info(timeframe: str) -> Dict[str, any]:
    """
    Obtém informações detalhadas sobre um timeframe
    
    Args:
        timeframe: Timeframe
        
    Returns:
        Dicionário com informações
    """
    if not validate_timeframe(timeframe):
        return {'error': 'Timeframe inválido'}
    
    seconds = timeframe_to_seconds(timeframe)
    minutes = seconds // 60
    hours = minutes // 60
    
    # Classificar tipo
    if minutes < 60:
        category = 'intraday'
        frequency = 'high'
    elif hours < 24:
        category = 'hourly'
        frequency = 'medium'
    else:
        category = 'daily'
        frequency = 'low'
    
    return {
        'timeframe': timeframe,
        'seconds': seconds,
        'minutes': minutes,
        'hours': round(hours, 2) if hours >= 1 else 0,
        'category': category,
        'frequency': frequency,
        'valid': True,
        'candles_per_day': 86400 // seconds,
        'candles_per_week': (86400 * 7) // seconds
    }

def suggest_timeframes_for_strategy(strategy_type: str) -> List[str]:
    """
    Sugere timeframes adequados para um tipo de estratégia
    
    Args:
        strategy_type: Tipo de estratégia
        
    Returns:
        Lista de timeframes recomendados
    """
    suggestions = {
        'scalping': ['1m', '3m', '5m'],
        'intraday': ['5m', '15m', '30m', '1h'],
        'swing': ['1h', '4h', '1d'],
        'position': ['1d', '3d', '1w'],
        'momentum': ['15m', '1h', '4h'],
        'mean_reversion': ['5m', '15m', '1h'],
        'breakout': ['1h', '4h', '1d'],
        'trend_following': ['4h', '1d', '3d'],
        'arbitrage': ['1m', '3m', '5m']
    }
    
    return suggestions.get(strategy_type.lower(), ['1h', '4h', '1d'])

def get_multi_timeframe_set(base_timeframe: str) -> Dict[str, str]:
    """
    Obtém conjunto de timeframes para análise multi-timeframe
    
    Args:
        base_timeframe: Timeframe base para trading
        
    Returns:
        Dicionário com timeframes para diferentes análises
    """
    try:
        base_index = VALID_TIMEFRAMES.index(base_timeframe)
        
        # Timeframe menor para entrada precisa
        entry_tf = VALID_TIMEFRAMES[max(0, base_index - 1)]
        
        # Timeframe maior para tendência
        trend_tf = VALID_TIMEFRAMES[min(len(VALID_TIMEFRAMES) - 1, base_index + 2)]
        
        # Timeframe intermediário para confirmação
        confirm_tf = VALID_TIMEFRAMES[min(len(VALID_TIMEFRAMES) - 1, base_index + 1)]
        
        return {
            'entry': entry_tf,
            'base': base_timeframe,
            'confirm': confirm_tf,
            'trend': trend_tf
        }
        
    except ValueError:
        # Fallback se timeframe não encontrado
        return {
            'entry': '15m',
            'base': '1h',
            'confirm': '4h', 
            'trend': '1d'
        }