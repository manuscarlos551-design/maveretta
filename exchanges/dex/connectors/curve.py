"""
Curve Finance Connector - Interface para Curve (stablecoin swaps)
"""
import logging
from typing import Dict
from ..gateway.web3_gateway import Web3Gateway

logger = logging.getLogger(__name__)


class CurveConnector:
    """
    Conector para Curve Finance.
    Especializado em stablecoins com baixo slippage.
    """

    def __init__(self, web3_gateway: Web3Gateway, chain: str = 'ethereum'):
        """
        Inicializa Curve Connector.
        
        Args:
            web3_gateway: Instância do Web3Gateway
            chain: Nome da chain
        """
        self.gateway = web3_gateway
        self.chain = chain
        
        logger.info(f"CurveConnector initialized for {chain}")
        logger.warning("Curve connector ainda não implementado completamente")

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> Dict:
        """
        Obtém cotação para swap.
        
        Note: Curve usa uma estrutura diferente (pools específicas)
        Implementação futura deve identificar pool correta automaticamente.
        """
        return {
            'success': False,
            'error': 'Curve connector em desenvolvimento'
        }

    async def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        amount_out_min: float
    ) -> Dict:
        """
        Executa swap.
        """
        return {
            'success': False,
            'error': 'Curve connector em desenvolvimento'
        }
