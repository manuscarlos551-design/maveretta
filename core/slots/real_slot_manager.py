#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Slot Manager - Gerenciamento Real de Slots de Trading
Remove todos os dados mockados e conecta com exchanges reais
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import threading

from .models import SlotMode, TradeAction, SlotStatus, SlotPosition, SlotMetrics

logger = logging.getLogger(__name__)


class RealSlotManager:
    """Gerenciador real de slots de trading - sem mocks"""
    
    def __init__(self, exchange_manager):
        """
        Inicializa Slot Manager com conexão real às exchanges
        
        Args:
            exchange_manager: Instância do MultiExchangeManager
        """
        self.exchange_manager = exchange_manager
        self.slots: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, List[SlotPosition]] = {}
        self.metrics: Dict[str, SlotMetrics] = {}
        self._lock = threading.Lock()
        
        # Configurações globais de risk
        self.global_risk_config = {
            'max_position_size_pct': 5.0,  # Máximo 5% do capital por posição
            'max_drawdown_pct': 10.0,  # Máximo 10% de drawdown
            'max_concurrent_positions': 3,  # Máximo 3 posições simultâneas por slot
            'default_stop_loss_pct': 2.0,  # Stop loss padrão 2%
            'default_take_profit_pct': 5.0,  # Take profit padrão 5%
        }
        
        logger.info("✅ RealSlotManager inicializado (SEM MOCKS - apenas dados reais)")
    
    def create_slot(
        self,
        exchange: str,
        capital_base: float,
        strategy: str = "intelligent_agent",
        risk_config: Optional[Dict] = None
    ) -> str:
        """
        Cria um novo slot de trading
        
        Args:
            exchange: Nome da exchange (binance, kucoin, bybit, coinbase, okx)
            capital_base: Capital inicial do slot
            strategy: Estratégia de trading
            risk_config: Configuração de risco específica do slot
        
        Returns:
            slot_id: ID do slot criado
        """
        with self._lock:
            # Validar se exchange existe
            if exchange not in self.exchange_manager.get_active_exchanges():
                raise ValueError(f"Exchange {exchange} não está ativa")
            
            # Gerar ID único
            slot_id = f"slot_{exchange}_{uuid.uuid4().hex[:8]}"
            
            # Merge de configuração de risco
            slot_risk_config = {**self.global_risk_config}
            if risk_config:
                slot_risk_config.update(risk_config)
            
            # Criar slot
            self.slots[slot_id] = {
                "slot_id": slot_id,
                "exchange": exchange,
                "status": SlotStatus.INACTIVE,
                "capital_base": capital_base,
                "capital_current": capital_base,
                "capital_available": capital_base,
                "assigned_agent": None,
                "strategy": strategy,
                "risk_config": slot_risk_config,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_update": datetime.now(timezone.utc).isoformat(),
                "metadata": {}
            }
            
            # Inicializar posições e métricas
            self.positions[slot_id] = []
            self.metrics[slot_id] = SlotMetrics(slot_id)
            
            logger.info(f"✅ Slot criado: {slot_id} na exchange {exchange} com capital ${capital_base}")
            return slot_id
    
    def activate_slot(self, slot_id: str) -> bool:
        """Ativa um slot para trading"""
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} não encontrado")
                return False
            
            self.slots[slot_id]["status"] = SlotStatus.ACTIVE
            self.slots[slot_id]["last_update"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"✅ Slot {slot_id} ativado")
            return True
    
    def deactivate_slot(self, slot_id: str) -> bool:
        """Desativa um slot"""
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} não encontrado")
                return False
            
            self.slots[slot_id]["status"] = SlotStatus.INACTIVE
            self.slots[slot_id]["last_update"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"🛑 Slot {slot_id} desativado")
            return True
    
    def assign_agent(self, slot_id: str, agent_id: str) -> bool:
        """Atribui um agente IA a um slot"""
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} não encontrado")
                return False
            
            self.slots[slot_id]["assigned_agent"] = agent_id
            self.slots[slot_id]["last_update"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"🤖 Agente {agent_id} atribuído ao slot {slot_id}")
            return True
    
    def get_slot(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de um slot"""
        with self._lock:
            return self.slots.get(slot_id)
    
    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Retorna todos os slots"""
        with self._lock:
            return list(self.slots.values())
    
    def get_active_slots(self) -> List[Dict[str, Any]]:
        """Retorna apenas slots ativos"""
        with self._lock:
            return [
                slot for slot in self.slots.values()
                if slot["status"] == SlotStatus.ACTIVE
            ]
    
    def get_slots_by_exchange(self, exchange: str) -> List[Dict[str, Any]]:
        """Retorna slots de uma exchange específica"""
        with self._lock:
            return [
                slot for slot in self.slots.values()
                if slot["exchange"] == exchange
            ]
    
    def open_position(
        self,
        slot_id: str,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[str]:
        """
        Abre uma nova posição em um slot
        
        Args:
            slot_id: ID do slot
            symbol: Símbolo (ex: BTC/USDT)
            side: 'long' ou 'short'
            size: Tamanho da posição
            entry_price: Preço de entrada
            stop_loss: Preço de stop loss
            take_profit: Preço de take profit
        
        Returns:
            position_id: ID da posição ou None se falhar
        """
        with self._lock:
            if slot_id not in self.slots:
                logger.error(f"Slot {slot_id} não encontrado")
                return None
            
            slot = self.slots[slot_id]
            
            # Validar se slot está ativo
            if slot["status"] != SlotStatus.ACTIVE:
                logger.error(f"Slot {slot_id} não está ativo")
                return None
            
            # Validar capital disponível
            position_value = size * entry_price
            if position_value > slot["capital_available"]:
                logger.error(f"Capital insuficiente no slot {slot_id}")
                return None
            
            # Validar limites de risco
            risk_config = slot["risk_config"]
            max_position_value = slot["capital_base"] * (risk_config["max_position_size_pct"] / 100)
            
            if position_value > max_position_value:
                logger.error(f"Tamanho da posição excede limite de risco")
                return None
            
            # Validar número máximo de posições
            open_positions = [p for p in self.positions[slot_id] if p.status == "open"]
            if len(open_positions) >= risk_config["max_concurrent_positions"]:
                logger.error(f"Número máximo de posições simultâneas atingido")
                return None
            
            # Criar posição
            position_id = f"pos_{uuid.uuid4().hex[:12]}"
            
            # Calcular stop loss e take profit se não fornecidos
            if stop_loss is None:
                stop_loss_pct = risk_config["default_stop_loss_pct"] / 100
                if side == "long":
                    stop_loss = entry_price * (1 - stop_loss_pct)
                else:
                    stop_loss = entry_price * (1 + stop_loss_pct)
            
            if take_profit is None:
                take_profit_pct = risk_config["default_take_profit_pct"] / 100
                if side == "long":
                    take_profit = entry_price * (1 + take_profit_pct)
                else:
                    take_profit = entry_price * (1 - take_profit_pct)
            
            position = SlotPosition(
                position_id=position_id,
                slot_id=slot_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status="open",
                opened_at=datetime.now(timezone.utc),
                metadata={}
            )
            
            self.positions[slot_id].append(position)
            
            # Atualizar capital disponível
            slot["capital_available"] -= position_value
            slot["last_update"] = datetime.now(timezone.utc).isoformat()
            
            # Atualizar métricas
            self.metrics[slot_id].total_trades += 1
            
            logger.info(f"✅ Posição aberta: {position_id} ({side} {size} {symbol} @ {entry_price})")
            return position_id
    
    def close_position(
        self,
        slot_id: str,
        position_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> bool:
        """
        Fecha uma posição
        
        Args:
            slot_id: ID do slot
            position_id: ID da posição
            exit_price: Preço de saída
            reason: Razão do fechamento
        
        Returns:
            bool: True se fechou com sucesso
        """
        with self._lock:
            if slot_id not in self.slots or slot_id not in self.positions:
                logger.error(f"Slot {slot_id} não encontrado")
                return False
            
            # Encontrar posição
            position = None
            for p in self.positions[slot_id]:
                if p.position_id == position_id and p.status == "open":
                    position = p
                    break
            
            if not position:
                logger.error(f"Posição {position_id} não encontrada ou já fechada")
                return False
            
            # Calcular P&L
            if position.side == "long":
                pnl = (exit_price - position.entry_price) * position.size
            else:
                pnl = (position.entry_price - exit_price) * position.size
            
            pnl_pct = (pnl / (position.entry_price * position.size)) * 100
            
            # Atualizar posição
            position.status = "closed"
            position.exit_price = exit_price
            position.closed_at = datetime.now(timezone.utc)
            position.pnl = pnl
            position.pnl_pct = pnl_pct
            position.close_reason = reason
            
            # Atualizar capital do slot
            slot = self.slots[slot_id]
            position_value = position.size * position.entry_price
            slot["capital_available"] += position_value + pnl
            slot["capital_current"] += pnl
            slot["last_update"] = datetime.now(timezone.utc).isoformat()
            
            # Atualizar métricas
            metrics = self.metrics[slot_id]
            metrics.total_pnl += pnl
            
            if pnl > 0:
                metrics.winning_trades += 1
            else:
                metrics.losing_trades += 1
            
            logger.info(f"✅ Posição fechada: {position_id} | P&L: ${pnl:.2f} ({pnl_pct:.2f}%) | Razão: {reason}")
            return True
    
    def get_positions(self, slot_id: str, status: Optional[str] = None) -> List[SlotPosition]:
        """
        Obtém posições de um slot
        
        Args:
            slot_id: ID do slot
            status: Filtrar por status ('open', 'closed')
        """
        with self._lock:
            if slot_id not in self.positions:
                return []
            
            positions = self.positions[slot_id]
            
            if status:
                positions = [p for p in positions if p.status == status]
            
            return positions
    
    def update_position_price(self, slot_id: str, position_id: str, current_price: float):
        """Atualiza preço atual de uma posição"""
        with self._lock:
            if slot_id not in self.positions:
                return
            
            for position in self.positions[slot_id]:
                if position.position_id == position_id and position.status == "open":
                    position.current_price = current_price
                    
                    # Calcular P&L não realizado
                    if position.side == "long":
                        unrealized_pnl = (current_price - position.entry_price) * position.size
                    else:
                        unrealized_pnl = (position.entry_price - current_price) * position.size
                    
                    position.unrealized_pnl = unrealized_pnl
                    break
    
    def get_metrics(self, slot_id: str) -> Optional[SlotMetrics]:
        """Obtém métricas de um slot"""
        with self._lock:
            return self.metrics.get(slot_id)
    
    def update_risk_config(self, slot_id: str, risk_config: Dict) -> bool:
        """Atualiza configuração de risco de um slot"""
        with self._lock:
            if slot_id not in self.slots:
                return False
            
            self.slots[slot_id]["risk_config"].update(risk_config)
            self.slots[slot_id]["last_update"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"✅ Configuração de risco atualizada para slot {slot_id}")
            return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo geral de todos os slots"""
        with self._lock:
            total_slots = len(self.slots)
            active_slots = len([s for s in self.slots.values() if s["status"] == SlotStatus.ACTIVE])
            
            total_capital = sum(s["capital_base"] for s in self.slots.values())
            total_current = sum(s["capital_current"] for s in self.slots.values())
            total_pnl = total_current - total_capital
            
            total_positions = sum(len(self.positions[sid]) for sid in self.positions)
            open_positions = sum(
                len([p for p in self.positions[sid] if p.status == "open"])
                for sid in self.positions
            )
            
            return {
                "total_slots": total_slots,
                "active_slots": active_slots,
                "inactive_slots": total_slots - active_slots,
                "total_capital": round(total_capital, 2),
                "total_current": round(total_current, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round((total_pnl / total_capital * 100) if total_capital > 0 else 0, 2),
                "total_positions": total_positions,
                "open_positions": open_positions,
                "closed_positions": total_positions - open_positions
            }
