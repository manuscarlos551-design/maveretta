"""
Validador de Risco Multi-Camadas
Valida decisões de trading antes da execução
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class RiskValidator:
    """Sistema de validação de risco"""
    
    def __init__(self):
        # Carrega limites do .env
        self.max_drawdown_pct = float(os.getenv("MAX_DRAWDOWN_PER_SYMBOL_PCT", "8.0"))
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "0.005"))
        self.max_daily_loss_pct = float(os.getenv("SESSION_EQUITY_PROTECTION_PCT", "10.0"))
        self.max_concurrent_positions = int(os.getenv("MAX_CONCURRENT_POSITIONS", "3"))
        
        # MongoDB client
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
        self.mongo_client = AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[os.getenv("MONGO_DATABASE", "bot")]
        
        logger.info(f"🛡️ Risk Validator inicializado:")
        logger.info(f"  Max Drawdown: {self.max_drawdown_pct}%")
        logger.info(f"  Risk per Trade: {self.risk_per_trade * 100}%")
        logger.info(f"  Max Daily Loss: {self.max_daily_loss_pct}%")
        logger.info(f"  Max Concurrent Positions: {self.max_concurrent_positions}")
    
    async def validate_decision(self, decision: Dict[str, Any], current_equity: float) -> Tuple[bool, str]:
        """
        Valida se decisão respeita regras de risco
        
        Args:
            decision: Decisão do agente com action, symbol, size, etc
            current_equity: Equity atual total
        
        Returns:
            Tupla (is_valid, message)
        """
        try:
            # 1. Verifica posições abertas
            open_positions = await self._get_open_positions()
            
            if len(open_positions) >= self.max_concurrent_positions:
                return False, f"Máximo de {self.max_concurrent_positions} posições simultâneas atingido"
            
            # 2. Verifica perda diária
            daily_pnl_pct = await self._get_daily_pnl_pct()
            
            if daily_pnl_pct < -self.max_daily_loss_pct:
                return False, f"Perda diária de {daily_pnl_pct:.2f}% excede limite de {self.max_daily_loss_pct}%"
            
            # 3. Verifica tamanho da posição
            position_size = decision.get("size", 0)
            price = decision.get("price", 0)
            
            if price == 0 or position_size == 0:
                return False, "Preço ou tamanho da posição inválidos"
            
            position_value = position_size * price
            position_pct = (position_value / current_equity) * 100 if current_equity > 0 else 0
            
            max_position_pct = self.risk_per_trade * 100
            
            if position_pct > max_position_pct:
                return False, f"Tamanho da posição {position_pct:.2f}% excede limite de {max_position_pct:.2f}%"
            
            # 4. Verifica drawdown do símbolo
            symbol = decision.get("symbol")
            symbol_dd = await self._get_symbol_drawdown(symbol)
            
            if symbol_dd > self.max_drawdown_pct:
                return False, f"Símbolo {symbol} em drawdown de {symbol_dd:.2f}% (limite: {self.max_drawdown_pct}%)"
            
            # 5. Verifica se tem capital suficiente
            if position_value > current_equity:
                return False, f"Capital insuficiente: posição requer ${position_value:.2f}, disponível ${current_equity:.2f}"
            
            # Todas as validações passaram
            logger.info(f"✅ Decisão aprovada pelo risk validator")
            return True, "OK"
            
        except Exception as e:
            logger.error(f"❌ Erro na validação de risco: {e}")
            return False, f"Erro na validação: {str(e)}"
    
    async def _get_open_positions(self) -> list:
        """Busca posições abertas no MongoDB"""
        try:
            cursor = self.db.operations.find({"status": "open"})
            positions = await cursor.to_list(length=100)
            return positions
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar posições abertas: {e}")
            return []
    
    async def _get_daily_pnl_pct(self) -> float:
        """Calcula P&L do dia em percentual"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            cursor = self.db.operations.find({
                "closed_at": {"$gte": today_start}
            })
            
            operations = await cursor.to_list(length=1000)
            
            if not operations:
                return 0.0
            
            total_pnl = sum(op.get("pnl", 0) for op in operations)
            total_invested = sum(
                op.get("entry_price", 0) * op.get("size", 0) 
                for op in operations
            )
            
            if total_invested == 0:
                return 0.0
            
            pnl_pct = (total_pnl / total_invested) * 100
            return pnl_pct
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular P&L diário: {e}")
            return 0.0
    
    async def _get_symbol_drawdown(self, symbol: str) -> float:
        """Calcula drawdown do símbolo nas últimas 48h"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=48)
            
            cursor = self.db.operations.find({
                "symbol": symbol,
                "closed_at": {"$gte": cutoff_time}
            })
            
            operations = await cursor.to_list(length=1000)
            
            if not operations:
                return 0.0
            
            # Calcula peak e trough
            cumulative_pnl = []
            running_pnl = 0
            
            for op in sorted(operations, key=lambda x: x.get("closed_at", datetime.utcnow())):
                running_pnl += op.get("pnl", 0)
                cumulative_pnl.append(running_pnl)
            
            if not cumulative_pnl:
                return 0.0
            
            peak = max(cumulative_pnl)
            trough = min(cumulative_pnl[cumulative_pnl.index(peak):]) if peak > 0 else min(cumulative_pnl)
            
            drawdown = ((trough - peak) / peak * 100) if peak != 0 else 0
            
            return abs(drawdown)
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular drawdown: {e}")
            return 0.0


# Instância global
_risk_validator = None

def get_risk_validator():
    """Obtém instância global do validator"""
    global _risk_validator
    if _risk_validator is None:
        _risk_validator = RiskValidator()
    return _risk_validator

async def validate_risk(decision: Dict[str, Any], current_equity: float) -> Tuple[bool, str]:
    """Valida risco de uma decisão"""
    return await get_risk_validator().validate_decision(decision, current_equity)
