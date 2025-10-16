#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fee Manager - Gerenciamento de Taxas por Exchange
Garante que take profit cubra todas as taxas antes de sair do trade
"""

import os
import logging
from typing import Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Exchange(str, Enum):
    """Exchanges suportadas"""
    BINANCE = "binance"
    BYBIT = "bybit"
    KUCOIN = "kucoin"
    OKX = "okx"
    COINBASE = "coinbase"


class FeeManager:
    """
    Gerencia taxas de trading por exchange
    Calcula take profit mínimo para cobrir fees
    """
    
    def __init__(self):
        # Taxas padrão por exchange (maker/taker)
        self.exchange_fees = {
            Exchange.BINANCE: {
                'maker': float(os.getenv('BINANCE_MAKER_FEE', '0.001')),  # 0.1%
                'taker': float(os.getenv('BINANCE_TAKER_FEE', '0.001'))   # 0.1%
            },
            Exchange.BYBIT: {
                'maker': float(os.getenv('BYBIT_MAKER_FEE', '0.001')),    # 0.1%
                'taker': float(os.getenv('BYBIT_TAKER_FEE', '0.001'))     # 0.1%
            },
            Exchange.KUCOIN: {
                'maker': float(os.getenv('KUCOIN_MAKER_FEE', '0.001')),   # 0.1%
                'taker': float(os.getenv('KUCOIN_TAKER_FEE', '0.001'))    # 0.1%
            },
            Exchange.OKX: {
                'maker': float(os.getenv('OKX_MAKER_FEE', '0.0008')),     # 0.08%
                'taker': float(os.getenv('OKX_TAKER_FEE', '0.001'))       # 0.1%
            },
            Exchange.COINBASE: {
                'maker': float(os.getenv('COINBASE_MAKER_FEE', '0.006')), # 0.6%
                'taker': float(os.getenv('COINBASE_TAKER_FEE', '0.006'))  # 0.6%
            }
        }
        
        # Buffer de segurança (0.1%)
        self.safety_buffer = 0.001
        
        logger.info("Fee Manager inicializado")
        for exchange, fees in self.exchange_fees.items():
            logger.info(
                f"  {exchange.value}: Maker {fees['maker']:.2%}, "
                f"Taker {fees['taker']:.2%}"
            )
    
    def get_fees(self, exchange: Exchange) -> Dict[str, float]:
        """Retorna taxas da exchange"""
        return self.exchange_fees.get(exchange, {
            'maker': 0.001,
            'taker': 0.001
        })
    
    def calculate_min_profit(self, exchange: Exchange, use_taker: bool = True) -> float:
        """
        Calcula profit mínimo necessário para cobrir taxas
        
        Args:
            exchange: Exchange a ser usada
            use_taker: Se True, assume taker fee (pior caso)
        
        Returns:
            Profit mínimo em percentual (ex: 0.013 = 1.3%)
        """
        fees = self.get_fees(exchange)
        
        # Usa taker fee (pior caso) ou maker fee
        entry_fee = fees['taker'] if use_taker else fees['maker']
        exit_fee = fees['taker'] if use_taker else fees['maker']
        
        # Total de taxas + buffer
        min_profit = entry_fee + exit_fee + self.safety_buffer
        
        return min_profit
    
    def calculate_take_profit(
        self,
        exchange: Exchange,
        entry_price: float,
        side: str,
        min_profit_pct: float = None
    ) -> Tuple[float, float]:
        """
        Calcula preço de take profit que garante lucro após taxas
        
        Args:
            exchange: Exchange a ser usada
            entry_price: Preço de entrada
            side: 'long' ou 'short'
            min_profit_pct: Profit mínimo desejado (além das taxas)
        
        Returns:
            (take_profit_price, effective_profit_pct)
        """
        # Profit mínimo para cobrir taxas
        min_profit_for_fees = self.calculate_min_profit(exchange)
        
        # Se não especificado, usa 3x as taxas como profit mínimo
        if min_profit_pct is None:
            min_profit_pct = min_profit_for_fees * 3
        
        # Garante que profit é maior que as taxas
        effective_profit = max(min_profit_pct, min_profit_for_fees * 1.5)
        
        # Calcula preço de TP
        if side == 'long':
            tp_price = entry_price * (1 + effective_profit)
        else:  # short
            tp_price = entry_price * (1 - effective_profit)
        
        return tp_price, effective_profit
    
    def calculate_stop_loss(
        self,
        exchange: Exchange,
        entry_price: float,
        side: str,
        max_loss_pct: float = 0.03
    ) -> float:
        """
        Calcula preço de stop loss incluindo taxas
        
        Args:
            exchange: Exchange a ser usada
            entry_price: Preço de entrada
            side: 'long' ou 'short'
            max_loss_pct: Perda máxima permitida (default 3%)
        
        Returns:
            stop_loss_price
        """
        fees = self.get_fees(exchange)
        
        # Loss inclui taxas de entrada e saída
        total_loss = max_loss_pct + fees['taker'] * 2
        
        # Calcula preço de SL
        if side == 'long':
            sl_price = entry_price * (1 - total_loss)
        else:  # short
            sl_price = entry_price * (1 + total_loss)
        
        return sl_price
    
    def calculate_net_profit(
        self,
        exchange: Exchange,
        entry_price: float,
        exit_price: float,
        position_size: float,
        side: str
    ) -> Dict[str, float]:
        """
        Calcula profit líquido após taxas
        
        Args:
            exchange: Exchange usada
            entry_price: Preço de entrada
            exit_price: Preço de saída
            position_size: Tamanho da posição (USD)
            side: 'long' ou 'short'
        
        Returns:
            Dict com profit bruto, taxas e profit líquido
        """
        fees = self.get_fees(exchange)
        
        # Calcula profit bruto
        if side == 'long':
            gross_profit_pct = (exit_price - entry_price) / entry_price
        else:  # short
            gross_profit_pct = (entry_price - exit_price) / entry_price
        
        gross_profit_usd = position_size * gross_profit_pct
        
        # Calcula taxas (assumindo taker em ambos)
        entry_fee = position_size * fees['taker']
        exit_fee = position_size * fees['taker']
        total_fees = entry_fee + exit_fee
        
        # Profit líquido
        net_profit_usd = gross_profit_usd - total_fees
        net_profit_pct = net_profit_usd / position_size
        
        return {
            'gross_profit_usd': gross_profit_usd,
            'gross_profit_pct': gross_profit_pct,
            'entry_fee': entry_fee,
            'exit_fee': exit_fee,
            'total_fees': total_fees,
            'net_profit_usd': net_profit_usd,
            'net_profit_pct': net_profit_pct,
            'is_profitable': net_profit_usd > 0
        }
    
    def should_take_profit(
        self,
        exchange: Exchange,
        entry_price: float,
        current_price: float,
        side: str
    ) -> bool:
        """
        Verifica se o profit atual é suficiente para cobrir taxas
        
        Returns:
            True se deve fazer take profit, False caso contrário
        """
        fees = self.get_fees(exchange)
        min_profit = self.calculate_min_profit(exchange)
        
        # Calcula profit atual
        if side == 'long':
            current_profit = (current_price - entry_price) / entry_price
        else:  # short
            current_profit = (entry_price - current_price) / entry_price
        
        # Deve ter pelo menos min_profit + buffer
        return current_profit >= (min_profit + self.safety_buffer)
    
    def get_optimal_exchange(self, symbol: str = None) -> Exchange:
        """
        Retorna a exchange com menores taxas para um símbolo
        
        Para simplicidade, retorna OKX (menores taxas)
        Pode ser expandido para considerar liquidez, spread, etc.
        """
        # OKX tem as menores taxas (0.08% maker)
        # Mas Coinbase tem as maiores (0.6%)
        
        # Ordena por taxas totais
        sorted_exchanges = sorted(
            self.exchange_fees.items(),
            key=lambda x: x[1]['maker'] + x[1]['taker']
        )
        
        return sorted_exchanges[0][0]


# Instância global
fee_manager = FeeManager()
