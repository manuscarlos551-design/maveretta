# -*- coding: utf-8 -*-
"""
Risk Manager Refatorado - Integra com sistema existente
Mantém todas as funcionalidades de risco do bot original
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Gerenciador de risco modular
    Integra com funcionalidades existentes do bot_runner.py
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Configurações de risco do .env
        self.max_drawdown_pct = float(os.getenv("MAX_DRAWDOWN_PER_SYMBOL_PCT", "8.0"))
        self.drawdown_reset_hours = int(os.getenv("DRAWDOWN_RESET_HOURS", "48"))
        self.symbol_block_duration = int(os.getenv("SYMBOL_BLOCK_DURATION_HOURS", "2"))
        self.session_max_daily_loss = float(os.getenv("SESSION_MAX_DAILY_LOSS_PCT", "3.0"))
        self.session_max_trades_hour = int(os.getenv("SESSION_MAX_TRADES_PER_HOUR", "8"))
        self.session_max_losses = int(os.getenv("SESSION_MAX_CONSECUTIVE_LOSSES", "3"))
        
        # Caminhos
        self.data_dir = Path("data")
        self.risk_state_path = self.data_dir / "risk_state.json"
        self.risk_log_path = self.data_dir / "risk_log.jsonl"
        
        # Estado
        self.risk_state = self._load_risk_state()
        
        print("[RISK_MANAGER] Inicializado com configurações do sistema existente")
    
    def _load_risk_state(self) -> Dict[str, Any]:
        """Carrega estado de risco - compatível com sistema existente"""
        try:
            if self.risk_state_path.exists():
                with open(self.risk_state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[RISK_MANAGER] Erro ao carregar estado: {e}")
        
        # Estado padrão compatível com bot_runner.py
        return {
            "symbol_blocks": {},
            "session_state": {
                "consecutive_losses": 0,
                "last_loss_time": 0,
                "session_paused_until": 0,
                "recent_trades": [],
                "daily_reset_date": None,
                "daily_starting_equity": 0,
                "daily_loss_count": 0
            },
            "price_history": {},
            "rebalance": {
                "count_today": 0,
                "cooldowns": {}
            }
        }
    
    def _save_risk_state(self):
        """Salva estado de risco"""
        try:
            with open(self.risk_state_path, 'w', encoding='utf-8') as f:
                json.dump(self.risk_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[RISK_MANAGER] Erro ao salvar estado: {e}")
    
    def _log_risk_event(self, event: Dict[str, Any]):
        """Log de eventos de risco - compatível com sistema existente"""
        event_with_ts = {
            "timestamp": int(time.time() * 1000),
            "datetime": datetime.utcnow().isoformat(),
            **event
        }
        
        try:
            with open(self.risk_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_with_ts, ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def check_symbol_blocked(self, symbol: str) -> bool:
        """
        Verifica se símbolo está bloqueado - compatível com is_symbol_blocked()
        """
        blocks = self.risk_state["symbol_blocks"]
        now = int(time.time() * 1000)
        
        if symbol in blocks:
            if blocks[symbol]["blocked_until"] <= now:
                # Remove bloqueio expirado
                del blocks[symbol]
                self._save_risk_state()
                self._log_risk_event({
                    "event": "symbol_unblocked",
                    "symbol": symbol
                })
                return False
            return True
        
        return False
    
    def check_drawdown_block(self, symbol: str, current_price: float) -> bool:
        """
        Verifica bloqueio por drawdown - compatível com check_drawdown_block()
        """
        self.update_price_history(symbol, current_price)
        
        price_history = self.risk_state["price_history"].get(symbol)
        if not price_history:
            return False
        
        reset_ms = self.drawdown_reset_hours * 3600 * 1000
        now = int(time.time() * 1000)
        
        # Reset automático se muito antigo
        if now - price_history["max_time"] > reset_ms:
            self.risk_state["price_history"][symbol] = {
                "max_price": current_price,
                "max_time": now
            }
            self._save_risk_state()
            return False
        
        # Calcula drawdown
        max_price = price_history["max_price"]
        drawdown = ((max_price - current_price) / max_price) * 100
        
        if drawdown >= self.max_drawdown_pct:
            # Bloqueia símbolo
            until = now + (self.symbol_block_duration * 3600 * 1000)
            self.risk_state["symbol_blocks"][symbol] = {
                "blocked_until": until,
                "reason": f"DD {drawdown:.2f}%",
                "type": "drawdown"
            }
            
            self._save_risk_state()
            self._log_risk_event({
                "event": "symbol_blocked",
                "symbol": symbol,
                "reason": f"drawdown {drawdown:.2f}%",
                "blocked_until": until
            })
            
            print(f"[RISK_MANAGER] {symbol} bloqueado por DD {drawdown:.2f}%")
            return True
        
        return False
    
    def update_price_history(self, symbol: str, price: float):
        """
        Atualiza histórico de preços - compatível com update_price_history()
        """
        now = int(time.time() * 1000)
        current_data = self.risk_state["price_history"].get(symbol)
        
        if not current_data or price > current_data["max_price"]:
            self.risk_state["price_history"][symbol] = {
                "max_price": price,
                "max_time": now
            }
            self._save_risk_state()
    
    def check_session_pause(self) -> bool:
        """
        Verifica se sessão está pausada - compatível com check_session_pause()
        """
        return self.risk_state["session_state"].get("session_paused_until", 0) > int(time.time() * 1000)
    
    def check_daily_loss_limit(self, current_equity: float) -> bool:
        """
        Verifica limite de perda diária - compatível com check_daily_loss_limit()
        """
        if not isinstance(current_equity, (int, float)) or current_equity <= 0:
            return False
        
        session_state = self.risk_state["session_state"]
        today = datetime.utcnow().date().isoformat()
        
        # Reset diário
        if session_state.get("daily_reset_date") != today:
            session_state["daily_reset_date"] = today
            session_state["daily_starting_equity"] = current_equity
            session_state["daily_loss_count"] = 0
            self._save_risk_state()
            print(f"[RISK_MANAGER] Novo dia - equity ${current_equity:.2f}")
            return False
        
        start_equity = session_state.get("daily_starting_equity") or current_equity
        
        # Detecção de discrepâncias
        ratio = max(start_equity, current_equity) / max(1e-9, min(start_equity, current_equity))
        if ratio > 10.0:
            session_state["daily_starting_equity"] = current_equity
            session_state["daily_loss_count"] = 0
            self._save_risk_state()
            self._log_risk_event({
                "event": "equity_discrepancy_reset",
                "old": start_equity,
                "new": current_equity,
                "ratio": ratio
            })
            return False
        
        # Calcula perda
        if start_equity == current_equity:
            return False
        
        loss_pct = ((start_equity - current_equity) / start_equity) * 100
        
        # Proteção contra perdas irreais
        if loss_pct > 50.0:
            session_state["daily_starting_equity"] = current_equity
            session_state["daily_loss_count"] = 0
            self._save_risk_state()
            self._log_risk_event({
                "event": "unrealistic_loss_reset",
                "loss_pct": loss_pct,
                "old": start_equity,
                "new": current_equity
            })
            return False
        
        # Verifica limite
        if loss_pct >= self.session_max_daily_loss:
            tomorrow = int((datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)).timestamp() * 1000)
            session_state["session_paused_until"] = tomorrow
            
            self._save_risk_state()
            self._log_risk_event({
                "event": "daily_loss_limit_reached",
                "loss_pct": loss_pct,
                "limit": self.session_max_daily_loss,
                "paused_until": tomorrow
            })
            
            print(f"[RISK_MANAGER] Limite diário atingido {loss_pct:.2f}% >= {self.session_max_daily_loss}%")
            return True
        
        if loss_pct > 1.0:
            print(f"[RISK_MANAGER] Equity ${current_equity:.2f} / Start ${start_equity:.2f} = -{loss_pct:.2f}%")
        
        return False
    
    def check_trade_frequency_limit(self) -> bool:
        """
        Verifica limite de frequência de trades - compatível com check_trade_frequency_limit()
        """
        session_state = self.risk_state["session_state"]
        now = int(time.time() * 1000)
        one_hour = now - 3600 * 1000
        
        # Limpa trades antigos
        recent_trades = session_state.get("recent_trades", [])
        if not isinstance(recent_trades, list):
            session_state["recent_trades"] = []
        
        session_state["recent_trades"] = [t for t in session_state["recent_trades"] if t > one_hour]
        
        # Verifica limite
        if len(session_state["recent_trades"]) >= self.session_max_trades_hour:
            pause_until = now + 30 * 60 * 1000  # 30 minutos
            session_state["session_paused_until"] = max(
                session_state.get("session_paused_until", 0), 
                pause_until
            )
            
            self._save_risk_state()
            self._log_risk_event({
                "event": "trade_frequency_limit",
                "trades_last_hour": len(session_state["recent_trades"]),
                "limit": self.session_max_trades_hour,
                "paused_until": pause_until
            })
            
            print(f"[RISK_MANAGER] Limite de frequência {self.session_max_trades_hour}/h")
            return True
        
        return False
    
    def record_trade_opening(self):
        """
        Registra abertura de trade - compatível com record_trade_opening()
        """
        session_state = self.risk_state["session_state"]
        now = int(time.time() * 1000)
        
        if "recent_trades" not in session_state or not isinstance(session_state.get("recent_trades"), list):
            session_state["recent_trades"] = []
        
        session_state["recent_trades"].append(now)
        self._save_risk_state()
    
    def record_trade_result(self, pnl: float):
        """
        Registra resultado de trade - compatível com record_trade_result()
        """
        session_state = self.risk_state["session_state"]
        now = int(time.time() * 1000)
        
        if pnl < 0:
            session_state["consecutive_losses"] = session_state.get("consecutive_losses", 0) + 1
            session_state["last_loss_time"] = now
        else:
            session_state["consecutive_losses"] = 0
        
        self._save_risk_state()
    
    def get_risk_state(self) -> Dict[str, Any]:
        """Retorna estado completo de risco"""
        return self.risk_state.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador de risco"""
        return {
            'initialized': True,
            'max_drawdown_pct': self.max_drawdown_pct,
            'session_max_daily_loss': self.session_max_daily_loss,
            'session_max_trades_hour': self.session_max_trades_hour,
            'blocked_symbols': len(self.risk_state["symbol_blocks"]),
            'session_paused': self.check_session_pause(),
            'consecutive_losses': self.risk_state["session_state"].get("consecutive_losses", 0)
        }
    
    # Métodos de acesso direto ao estado (compatibilidade)
    def get_symbol_blocks(self) -> Dict[str, Any]:
        """Retorna bloqueios de símbolos"""
        return self.risk_state["symbol_blocks"]
    
    def get_session_state(self) -> Dict[str, Any]:
        """Retorna estado da sessão"""
        return self.risk_state["session_state"]
    
    def get_price_history(self) -> Dict[str, Any]:
        """Retorna histórico de preços"""
        return self.risk_state["price_history"]

    # =============================================================================
    # MÉTODOS FASE 3 - VALIDAÇÃO DE TRADES
    # =============================================================================
    
    def validate_trade(self, trade_request: Dict[str, Any]) -> tuple[bool, str]:
        """
        Valida se trade pode ser executado
        
        Args:
            trade_request: Dados do trade solicitado
        
        Returns:
            (approved: bool, reason: str)
        """
        # 1. Verifica se está em emergency stop
        if self._is_emergency_stop():
            return False, "Sistema em EMERGENCY STOP"
        
        # 2. Verifica se sessão está pausada
        if self.check_session_pause():
            return False, "Sessão pausada por limites de risco"
        
        # 3. Verifica exposição máxima
        if not self._check_max_exposure(trade_request):
            return False, f"Exposição máxima excedida ({self.config.get('max_exposure_pct', 10)}%)"
        
        # 4. Verifica número de posições abertas
        if not self._check_max_positions():
            return False, f"Máximo de posições abertas atingido ({self.config.get('max_open_positions', 5)})"
        
        # 5. Verifica perda diária
        if not self._check_daily_loss():
            return False, f"Perda diária excedida ({self.config.get('max_daily_loss_pct', 5)}%)"
        
        # 6. Verifica drawdown máximo
        if not self._check_max_drawdown():
            return False, f"Drawdown máximo atingido ({self.config.get('max_drawdown_pct', 15)}%)"
        
        # 7. Verifica frequência de trades
        if self.check_trade_frequency_limit():
            return False, "Limite de frequência de trades excedido"
        
        # 8. Calcula position sizing
        position_size = self._calculate_position_size(trade_request)
        if position_size <= 0:
            return False, "Position size inválido"
        
        # 9. Define stop loss automático
        stop_loss = self._calculate_stop_loss(trade_request)
        
        # 10. Registra aprovação
        self._log_risk_decision(trade_request, approved=True)
        
        return True, f"Trade aprovado - Size: {position_size}"
    
    def _check_max_exposure(self, trade_request: Dict[str, Any]) -> bool:
        """Verifica se exposição total não excede limite"""
        max_exposure_pct = self.config.get("max_exposure_pct", 10.0)
        current_exposure = self.risk_state.get("current_exposure", 0)
        capital = self.config.get("capital", 10000)
        
        trade_value = trade_request.get("quantity", 0) * trade_request.get("price", 0)
        new_exposure = ((current_exposure + trade_value) / capital) * 100
        
        return new_exposure <= max_exposure_pct
    
    def _check_max_positions(self) -> bool:
        """Verifica se número de posições abertas não excede limite"""
        max_positions = self.config.get("max_open_positions", 5)
        open_positions = self.risk_state.get("open_positions_count", 0)
        
        return open_positions < max_positions
    
    def _check_daily_loss(self) -> bool:
        """Verifica se perda diária não excedeu limite"""
        max_daily_loss_pct = self.config.get("max_daily_loss_pct", 5.0)
        daily_pnl = self.risk_state.get("daily_pnl", 0)
        capital = self.config.get("capital", 10000)
        
        daily_loss_pct = (abs(daily_pnl) / capital) * 100 if daily_pnl < 0 else 0
        
        return daily_loss_pct < max_daily_loss_pct
    
    def _check_max_drawdown(self) -> bool:
        """Verifica se drawdown não excedeu limite"""
        max_drawdown_pct = self.config.get("max_drawdown_pct", 15.0)
        peak_capital = self.risk_state.get("peak_capital", 0)
        current_capital = self.config.get("capital", 10000)
        
        if peak_capital == 0:
            self.risk_state["peak_capital"] = current_capital
            self._save_risk_state()
            return True
        
        drawdown_pct = ((peak_capital - current_capital) / peak_capital) * 100
        
        return drawdown_pct < max_drawdown_pct
    
    def _calculate_position_size(self, trade_request: Dict[str, Any]) -> float:
        """
        Calcula tamanho da posição usando Fixed Fractional
        Por simplicidade, usa 2% do capital por trade
        """
        capital = self.config.get("capital", 10000)
        risk_per_trade_pct = self.config.get("max_loss_per_trade_pct", 2.0)
        
        risk_amount = capital * (risk_per_trade_pct / 100)
        
        # Calcula quantidade baseado no risco e stop loss
        price = trade_request.get("price", 0)
        stop_loss_pct = trade_request.get("stop_loss_pct", 2.0)
        
        if price > 0 and stop_loss_pct > 0:
            stop_loss_amount = price * (stop_loss_pct / 100)
            quantity = risk_amount / stop_loss_amount
            return quantity
        
        return 0
    
    def _calculate_stop_loss(self, trade_request: Dict[str, Any]) -> float:
        """Calcula stop loss automático"""
        price = trade_request.get("price", 0)
        side = trade_request.get("side", "buy")
        stop_loss_pct = self.config.get("max_loss_per_trade_pct", 2.0)
        
        if side == "buy":
            return price * (1 - stop_loss_pct / 100)
        else:
            return price * (1 + stop_loss_pct / 100)
    
    def _is_emergency_stop(self) -> bool:
        """Verifica se sistema está em emergency stop"""
        # Verifica flag de emergency via Redis ou estado local
        return self.risk_state.get("emergency_stop", False)
    
    def _log_risk_decision(self, trade_request: Dict[str, Any], approved: bool):
        """Registra decisão de risco"""
        self._log_risk_event({
            "event": "trade_validation",
            "approved": approved,
            "symbol": trade_request.get("symbol"),
            "side": trade_request.get("side"),
            "quantity": trade_request.get("quantity"),
            "price": trade_request.get("price")
        })
    
    def update_state_after_trade(self, trade_result: Dict[str, Any]):
        """
        Atualiza estado do risk manager após execução de trade
        
        Args:
            trade_result: Resultado do trade executado
        """
        # Atualiza P&L diário
        pnl = trade_result.get("pnl", 0)
        self.risk_state["daily_pnl"] = self.risk_state.get("daily_pnl", 0) + pnl
        
        # Atualiza capital
        capital = self.config.get("capital", 10000) + pnl
        self.config["capital"] = capital
        
        # Atualiza peak capital
        if capital > self.risk_state.get("peak_capital", 0):
            self.risk_state["peak_capital"] = capital
        
        # Atualiza contador de posições
        if trade_result.get("status") == "open":
            self.risk_state["open_positions_count"] = self.risk_state.get("open_positions_count", 0) + 1
        elif trade_result.get("status") == "closed":
            self.risk_state["open_positions_count"] = max(0, self.risk_state.get("open_positions_count", 0) - 1)
        
        # Atualiza exposição
        if trade_result.get("status") == "open":
            trade_value = trade_result.get("quantity", 0) * trade_result.get("price", 0)
            self.risk_state["current_exposure"] = self.risk_state.get("current_exposure", 0) + trade_value
        elif trade_result.get("status") == "closed":
            trade_value = trade_result.get("quantity", 0) * trade_result.get("entry_price", 0)
            self.risk_state["current_exposure"] = max(0, self.risk_state.get("current_exposure", 0) - trade_value)
        
        # Registra resultado
        self.record_trade_result(pnl)
        
        # Salva estado
        self._save_risk_state()
        
        logger.info(f"✅ Risk state atualizado - P&L: ${pnl:.2f}, Capital: ${capital:.2f}")
    
    def reset_daily_stats(self):
        """Reseta estatísticas diárias (chamado à meia-noite)"""
        self.risk_state["daily_pnl"] = 0
        self.risk_state["session_state"]["daily_reset_date"] = datetime.utcnow().date().isoformat()
        self.risk_state["session_state"]["daily_loss_count"] = 0
        self.risk_state["session_state"]["consecutive_losses"] = 0
        self._save_risk_state()
        
        self._log_risk_event({
            "event": "daily_stats_reset"
        })
        
        print("[RISK_MANAGER] Estatísticas diárias resetadas")
