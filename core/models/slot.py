# core/models/slot.py
"""
Slot Model - Modelo de dados para slots de trading com suporte a estratégias
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

class SlotStatus(Enum):
    """Status possíveis de um slot"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED" 
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    STARTING = "STARTING"
    STOPPING = "STOPPING"

class StrategyMode(Enum):
    """Modo de seleção de estratégia"""
    AUTO = "auto"
    MANUAL = "manual"

@dataclass
class SlotModel:
    """Modelo de dados para slot de trading"""
    
    # Identificação
    id: str
    exchange: str
    symbol: str
    
    # Status operacional
    status: SlotStatus = SlotStatus.STOPPED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Gestão de capital
    capital_base: float = 1000.0
    capital_current: float = 1000.0
    capital_allocated: float = 0.0
    
    # Performance
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Estratégia - NOVOS CAMPOS
    strategy_active: str = "momentum"
    strategy_mode: StrategyMode = StrategyMode.AUTO
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    strategy_since_ts: float = field(default_factory=time.time)
    forced_by: Optional[str] = None
    
    # IA assignada
    assigned_ia: Optional[str] = None
    ia_group: str = "G1"  # G1 ou G2
    
    # Posição atual
    current_position: Optional[Dict[str, Any]] = None
    pending_orders: List[Dict[str, Any]] = field(default_factory=list)
    
    # Última operação
    last_trade: Optional[Dict[str, Any]] = None
    last_signal: Optional[Dict[str, Any]] = None
    last_decision_ts: float = 0.0
    
    # Configurações
    config: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, Any] = field(default_factory=dict)
    
    # Métricas de cascade (sistema 10%)
    cascade_target_pct: float = 10.0  # Meta para cascade (+10%)
    next_slot_id: Optional[str] = None
    cascade_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        data = asdict(self)
        # Converte enums para strings
        data["status"] = self.status.value
        data["strategy_mode"] = self.strategy_mode.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlotModel':
        """Cria instância a partir de dicionário"""
        # Converte strings para enums
        if "status" in data:
            data["status"] = SlotStatus(data["status"])
        if "strategy_mode" in data:
            data["strategy_mode"] = StrategyMode(data["strategy_mode"])
        
        return cls(**data)
    
    def update_strategy(self, strategy_id: str, mode: StrategyMode, forced_by: Optional[str] = None) -> None:
        """Atualiza estratégia do slot"""
        self.strategy_active = strategy_id
        self.strategy_mode = mode
        self.strategy_since_ts = time.time()
        self.forced_by = forced_by
        self.updated_at = time.time()
    
    def update_pnl(self, new_pnl: float) -> None:
        """Atualiza P&L e calcula percentual"""
        self.pnl = new_pnl
        if self.capital_base > 0:
            self.pnl_percentage = (new_pnl / self.capital_base) * 100
        self.updated_at = time.time()
    
    def check_cascade_trigger(self) -> bool:
        """Verifica se deve triggerar cascade (+10% líquido)"""
        return (self.cascade_enabled and 
                self.pnl_percentage >= self.cascade_target_pct and
                self.next_slot_id is not None)
    
    def execute_cascade_transfer(self) -> Dict[str, Any]:
        """Executa transferência de cascade (apenas lucro)"""
        if not self.check_cascade_trigger():
            return {"success": False, "reason": "Cascade conditions not met"}
        
        # Calcula lucro líquido para transferir
        profit_to_transfer = self.pnl
        
        # Reseta capital atual para capital base
        self.capital_current = self.capital_base
        self.pnl = 0.0
        self.pnl_percentage = 0.0
        
        cascade_info = {
            "success": True,
            "from_slot": self.id,
            "to_slot": self.next_slot_id,
            "profit_transferred": profit_to_transfer,
            "timestamp": time.time()
        }
        
        self.updated_at = time.time()
        return cascade_info
    
    def get_group(self) -> str:
        """Determina grupo (G1/G2) baseado no ID do slot"""
        try:
            import re
            numbers = re.findall(r'\d+', str(self.id))
            if numbers:
                return "G1" if int(numbers[0]) % 2 == 1 else "G2"
        except:
            pass
        return self.ia_group  # Fallback para campo explícito
    
    def is_ready_for_trading(self) -> bool:
        """Verifica se slot está pronto para operar"""
        return (
            self.status == SlotStatus.ACTIVE and
            self.capital_current > 0 and
            self.assigned_ia is not None and
            self.strategy_active is not None
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Retorna resumo de performance"""
        win_rate = 0
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
        
        return {
            "total_trades": self.total_trades,
            "win_rate": win_rate,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "capital_utilization": (self.capital_allocated / self.capital_current * 100) if self.capital_current > 0 else 0,
            "cascade_progress": min(self.pnl_percentage / self.cascade_target_pct * 100, 100) if self.cascade_target_pct > 0 else 0
        }

# Factory functions para criar slots padrão

def create_slot(
    slot_id: str,
    exchange: str, 
    symbol: str,
    capital: float = 1000.0,
    strategy: str = "momentum",
    ia_id: Optional[str] = None
) -> SlotModel:
    """Cria novo slot com configurações padrão"""
    
    slot = SlotModel(
        id=slot_id,
        exchange=exchange,
        symbol=symbol,
        capital_base=capital,
        capital_current=capital,
        strategy_active=strategy,
        assigned_ia=ia_id
    )
    
    # Define grupo baseado no ID
    slot.ia_group = slot.get_group()
    
    return slot

def create_slot_sequence(
    base_id: str,
    count: int,
    exchange: str,
    symbol: str,
    initial_capital: float = 1000.0
) -> List[SlotModel]:
    """Cria sequência de slots conectados para cascade"""
    
    slots = []
    
    for i in range(count):
        slot_id = f"{base_id}_{i+1}"
        
        slot = create_slot(
            slot_id=slot_id,
            exchange=exchange,
            symbol=symbol,
            capital=initial_capital,
            strategy="momentum"
        )
        
        # Conecta ao próximo slot para cascade
        if i < count - 1:
            slot.next_slot_id = f"{base_id}_{i+2}"
        
        slots.append(slot)
    
    return slots

# Validations

def validate_slot_config(slot_data: Dict[str, Any]) -> Dict[str, Any]:
    """Valida configuração de slot"""
    errors = []
    
    # Campos obrigatórios
    required_fields = ["id", "exchange", "symbol"]
    for field in required_fields:
        if not slot_data.get(field):
            errors.append(f"Campo obrigatório: {field}")
    
    # Validações de capital
    capital = slot_data.get("capital_base", 0)
    if capital <= 0:
        errors.append("Capital deve ser maior que zero")
    
    # Validação de estratégia
    strategy = slot_data.get("strategy_active")
    if strategy:
        from core.strategies.registry import get_strategy
        if not get_strategy(strategy):
            errors.append(f"Estratégia '{strategy}' não encontrada")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }