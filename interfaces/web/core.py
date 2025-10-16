"""
Core DTOs, enums and policies for AI trading orchestration system.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List

# Enums
class State(str, Enum):
    RED = "RED"
    AMBER = "AMBER" 
    GREEN = "GREEN"

class StrategyCode(str, Enum):
    # Basic strategies
    SCALP = "SCALP"
    INTRA = "INTRA"
    DAY = "DAY"
    SWING = "SWING"
    POSI = "POSI"
    HODL = "HODL"
    TEND = "TEND"
    
    # Advanced strategies
    RANGE = "RANGE"
    REV_MED = "REV_MED"
    MOM = "MOM"
    BREAK = "BREAK"
    PULLB = "PULLB"
    GRID = "GRID"
    DCA = "DCA"
    QIND = "QIND"
    
    # Complex strategies
    NEWS = "NEWS"
    XARB = "XARB"
    TARB = "TARB"
    XMM = "XMM"
    XPAIR = "XPAIR"
    BVR = "BVR"

# Paridade Policies
ODD_ALLOWED = {
    StrategyCode.TEND, StrategyCode.SWING, StrategyCode.POSI, StrategyCode.HODL,
    StrategyCode.RANGE, StrategyCode.REV_MED, StrategyCode.MOM, StrategyCode.GRID,
    StrategyCode.DCA, StrategyCode.QIND, StrategyCode.XPAIR, StrategyCode.TARB
}

EVEN_ALLOWED = {
    StrategyCode.SCALP, StrategyCode.INTRA, StrategyCode.DAY, StrategyCode.NEWS,
    StrategyCode.BREAK, StrategyCode.PULLB, StrategyCode.XARB, StrategyCode.XMM, 
    StrategyCode.BVR
}

# DTOs
@dataclass
class IA:
    id: str
    name: str
    role: str  # Leader | Macro | Scalp | Arbitrage | News | Reserva | Data
    provider: str  # openai | claude | sentiai | coingecko | binance
    state: State
    latency_ms: Optional[float] = None
    uptime_pct: Optional[float] = None
    avatar: str = "/static/avatars/ia_maveretta_chip.png"

@dataclass
class Exchange:
    id: str
    name: str
    state: State
    latency_ms: Optional[float] = None
    clock_skew_ms: Optional[float] = None
    balances: Optional[Dict[str, float]] = None

@dataclass
class Slot:
    id: str
    parity: str  # ODD | EVEN
    state: State
    strategy: Optional[StrategyCode] = None
    confidence_pct: Optional[float] = None
    symbol: Optional[str] = None
    side: Optional[str] = None  # LONG | SHORT
    venues: Optional[Dict[str, str]] = None  # {"buy_on":"Binance","sell_on":"OKX"}
    pnl_pct: Optional[float] = None
    cash_allocated: Optional[float] = None
    ia_id: Optional[str] = None

@dataclass
class Decision:
    slot_id: str
    ia_id: str
    strategy: StrategyCode
    confidence_pct: float
    decided_at: str
    ttl_ms: Optional[int] = None

# Avatar Binding - use C:/bot/ paths
AVATAR_BINDING = {
    "ia-openai-avancada": "/static/avatars/ia_openai_avancada.png",
    "ia-claude-orquestradora": "/static/avatars/ia_claude_orquestradora.png", 
    "ia-openai-micro": "/static/avatars/ia_openai_micro.png",
    "ia-maveretta-chip": "/static/avatars/ia_maveretta_chip.png",
    "default": "/static/avatars/ia_maveretta_chip.png"
}

# Team Roster - IDs fixos para orquestração
TEAM_ROSTER = {
    # Líder
    "LEADER": {
        "id": "ia-claude-orquestradora",
        "name": "Claude Orquestradora",
        "role": "Leader",
        "provider": "claude",
        "group": "L"
    },
    
    # G1 (Ímpar - macro/long strategies)
    "G1": [
        {
            "id": "ia-openai-avancada", 
            "name": "OpenAI Avançada",
            "role": "Macro",
            "provider": "openai",
            "group": "G1"
        },
        {
            "id": "ia-quant-indicadores",
            "name": "Quant Indicadores", 
            "role": "Macro",
            "provider": "openai",
            "group": "G1"
        },
        {
            "id": "ia-range-reversion",
            "name": "Range Reversion",
            "role": "Macro", 
            "provider": "openai",
            "group": "G1"
        },
        {
            "id": "ia-reserva-g1",
            "name": "Reserva G1",
            "role": "Reserva",
            "provider": "openai", 
            "group": "G1"
        }
    ],
    
    # G2 (Par - scalp/quick strategies) 
    "G2": [
        {
            "id": "ia-openai-micro",
            "name": "OpenAI Micro",
            "role": "Scalp",
            "provider": "openai",
            "group": "G2"
        },
        {
            "id": "ia-arbitragem-mm",
            "name": "Arbitragem MM", 
            "role": "Arbitrage",
            "provider": "openai",
            "group": "G2"
        },
        {
            "id": "ia-news-events", 
            "name": "News Events",
            "role": "News",
            "provider": "openai",
            "group": "G2"
        },
        {
            "id": "ia-reserva-g2",
            "name": "Reserva G2", 
            "role": "Reserva",
            "provider": "openai",
            "group": "G2"
        }
    ],
    
    # DATA
    "DATA": [
        {
            "id": "coingecko",
            "name": "CoinGecko Data",
            "role": "Data", 
            "provider": "coingecko",
            "group": "DATA"
        },
        {
            "id": "binance",
            "name": "Binance Data",
            "role": "Data",
            "provider": "binance", 
            "group": "DATA"
        }
    ]
}
