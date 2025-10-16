"""
SushiSwap Connector - Interface para SushiSwap DEX
"""
import logging
from typing import Dict
from eth_utils import to_checksum_address
from ..gateway.web3_gateway import Web3Gateway

logger = logging.getLogger(__name__)


class SushiSwapConnector:
    """
    Conector para SushiSwap.
    Similar ao PancakeSwap (Uniswap V2 fork).
    """

    # SushiSwap Router addresses
    ROUTER_ADDRESSES = {
        'ethereum': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
        'polygon': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
        'arbitrum': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
    }

    # Mesmo ABI do PancakeSwap (Uniswap V2)
    ROUTER_ABI = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"}
            ],
            "name": "getAmountsOut",
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"}
            ],
            "name": "swapExactTokensForTokens",
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    def __init__(self, web3_gateway: Web3Gateway, chain: str = 'ethereum'):
        """
        Inicializa SushiSwap Connector.
        
        Args:
            web3_gateway: Instância do Web3Gateway
            chain: Nome da chain
        """
        if chain not in self.ROUTER_ADDRESSES:
            raise ValueError(f"SushiSwap não disponível em {chain}")
        
        self.gateway = web3_gateway
        self.chain = chain
        self.router_address = self.ROUTER_ADDRESSES[chain]
        
        logger.info(f"SushiSwapConnector initialized for {chain}")

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> Dict:
        """
        Obtém cotação para swap.
        
        Args:
            token_in: Endereço do token de entrada
            token_out: Endereço do token de saída
            amount_in: Quantidade de entrada
            
        Returns:
            Dict com quote
        """
        try:
            w3 = await self.gateway.connect_to_chain(self.chain)
            
            token_in = to_checksum_address(token_in)
            token_out = to_checksum_address(token_out)
            
            # Obter decimals
            token_in_contract = w3.eth.contract(
                address=token_in,
                abi=self.gateway.ERC20_ABI
            )
            decimals_in = token_in_contract.functions.decimals().call()
            
            token_out_contract = w3.eth.contract(
                address=token_out,
                abi=self.gateway.ERC20_ABI
            )
            decimals_out = token_out_contract.functions.decimals().call()
            
            # Converter amount
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            
            # Obter quote
            router = w3.eth.contract(
                address=to_checksum_address(self.router_address),
                abi=self.ROUTER_ABI
            )
            
            path = [token_in, token_out]
            amounts = router.functions.getAmountsOut(amount_in_wei, path).call()
            
            amount_out_wei = amounts[-1]
            amount_out = float(amount_out_wei) / (10 ** decimals_out)
            
            price = amount_out / amount_in if amount_in > 0 else 0
            fee_pct = 0.3  # SushiSwap tem 0.3% fee
            
            return {
                'success': True,
                'dex': 'sushiswap',
                'chain': self.chain,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price': price,
                'fee_pct': fee_pct,
                'gas_estimate': 150000,
                'route': f"{token_in} -> {token_out}"
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter quote SushiSwap: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        amount_out_min: float,
        deadline: int = 300
    ) -> Dict:
        """
        Executa swap (implementação similar ao PancakeSwap).
        """
        # Implementação idêntica ao PancakeSwap
        # Ver pancakeswap.py para referência completa
        return {
            'success': False,
            'error': 'Use implementação do PancakeSwap como referência'
        }
