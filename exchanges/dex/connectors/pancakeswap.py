"""
PancakeSwap Connector - Interface para PancakeSwap DEX (BSC)
"""
import logging
from typing import Dict, Optional
from eth_utils import to_checksum_address
from ..gateway.web3_gateway import Web3Gateway

logger = logging.getLogger(__name__)


class PancakeSwapConnector:
    """
    Conector para PancakeSwap (BSC).
    Baseado em Uniswap V2 fork.
    """

    # PancakeSwap V2 Router address (BSC)
    ROUTER_ADDRESS = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
    
    # PancakeSwap Factory
    FACTORY_ADDRESS = '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73'

    # Simplified Router ABI
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

    def __init__(self, web3_gateway: Web3Gateway, chain: str = 'bsc'):
        """
        Inicializa PancakeSwap Connector.
        
        Args:
            web3_gateway: Instância do Web3Gateway
            chain: Nome da chain (deve ser 'bsc')
        """
        if chain != 'bsc':
            raise ValueError("PancakeSwap só disponível em BSC")
        
        self.gateway = web3_gateway
        self.chain = chain
        self.router_address = self.ROUTER_ADDRESS
        
        logger.info("PancakeSwapConnector initialized for BSC")

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
            Dict com amount_out, price, fee
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
            
            # Obter quote do router
            router = w3.eth.contract(
                address=to_checksum_address(self.router_address),
                abi=self.ROUTER_ABI
            )
            
            path = [token_in, token_out]
            amounts = router.functions.getAmountsOut(amount_in_wei, path).call()
            
            amount_out_wei = amounts[-1]
            amount_out = float(amount_out_wei) / (10 ** decimals_out)
            
            # Calcular price
            price = amount_out / amount_in if amount_in > 0 else 0
            
            # PancakeSwap V2 tem 0.25% fee
            fee_pct = 0.25
            
            # Estimar gas
            gas_estimate = 150000  # Typical for V2 swap
            
            return {
                'success': True,
                'dex': 'pancakeswap',
                'chain': self.chain,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price': price,
                'fee_pct': fee_pct,
                'gas_estimate': gas_estimate,
                'route': f"{token_in} -> {token_out}"
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter quote PancakeSwap: {e}")
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
        Executa swap.
        
        Args:
            token_in: Endereço do token de entrada
            token_out: Endereço do token de saída
            amount_in: Quantidade de entrada
            amount_out_min: Quantidade mínima de saída
            deadline: Prazo em segundos
            
        Returns:
            Dict com resultado do swap
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
            
            # Converter amounts
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            amount_out_min_wei = int(amount_out_min * (10 ** decimals_out))
            
            # Verificar e aprovar
            allowance = await self.gateway.get_allowance(
                token_in,
                self.gateway.wallet_address,
                self.router_address,
                self.chain
            )
            
            if allowance < amount_in:
                logger.info(f"Aprovando {amount_in} tokens...")
                approve_result = await self.gateway.approve_token(
                    token_in,
                    self.router_address,
                    amount_in * 2,
                    self.chain
                )
                
                if not approve_result.get('success'):
                    return {
                        'success': False,
                        'error': 'Falha na aprovação de tokens'
                    }
            
            # Construir transação
            router = w3.eth.contract(
                address=to_checksum_address(self.router_address),
                abi=self.ROUTER_ABI
            )
            
            deadline_timestamp = w3.eth.get_block('latest')['timestamp'] + deadline
            path = [token_in, token_out]
            
            transaction = router.functions.swapExactTokensForTokens(
                amount_in_wei,
                amount_out_min_wei,
                path,
                to_checksum_address(self.gateway.wallet_address),
                deadline_timestamp
            ).build_transaction({
                'from': to_checksum_address(self.gateway.wallet_address),
                'nonce': w3.eth.get_transaction_count(
                    to_checksum_address(self.gateway.wallet_address)
                )
            })
            
            # Enviar transação
            result = await self.gateway.send_transaction(transaction, self.chain)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar swap PancakeSwap: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_pair_reserves(
        self,
        token0: str,
        token1: str
    ) -> Dict:
        """
        Obtém reservas do par.
        
        Args:
            token0: Endereço do primeiro token
            token1: Endereço do segundo token
            
        Returns:
            Dict com reservas
        """
        # TODO: Implementar usando Pair contract
        return {
            'success': False,
            'error': 'Implementação pendente'
        }
