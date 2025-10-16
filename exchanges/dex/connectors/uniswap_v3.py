"""
Uniswap V3 Connector - Interface para Uniswap V3 DEX
"""
import logging
from typing import Dict, Optional, List
from decimal import Decimal
from eth_utils import to_checksum_address
from ..gateway.web3_gateway import Web3Gateway

logger = logging.getLogger(__name__)


class UniswapV3Connector:
    """
    Conector para Uniswap V3.
    Suporta swaps, quotes e informações de pools.
    """

    # Uniswap V3 Router address (Ethereum)
    ROUTER_ADDRESSES = {
        'ethereum': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'polygon': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'arbitrum': '0xE592427A0AEce92De3Edee1F18E0157C05861564'
    }

    # Uniswap V3 Quoter address
    QUOTER_ADDRESSES = {
        'ethereum': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
        'polygon': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
        'arbitrum': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6'
    }

    # Fee tiers (0.01%, 0.05%, 0.3%, 1%)
    FEE_TIERS = [100, 500, 3000, 10000]

    # Simplified Quoter ABI
    QUOTER_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "name": "quoteExactInputSingle",
            "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    # Simplified Router ABI
    ROUTER_ABI = [
        {
            "inputs": [
                {
                    "components": [
                        {"internalType": "address", "name": "tokenIn", "type": "address"},
                        {"internalType": "address", "name": "tokenOut", "type": "address"},
                        {"internalType": "uint24", "name": "fee", "type": "uint24"},
                        {"internalType": "address", "name": "recipient", "type": "address"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                        {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                    ],
                    "internalType": "struct ISwapRouter.ExactInputSingleParams",
                    "name": "params",
                    "type": "tuple"
                }
            ],
            "name": "exactInputSingle",
            "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function"
        }
    ]

    def __init__(self, web3_gateway: Web3Gateway, chain: str = 'ethereum'):
        """
        Inicializa Uniswap V3 Connector.
        
        Args:
            web3_gateway: Instância do Web3Gateway
            chain: Nome da chain
        """
        self.gateway = web3_gateway
        self.chain = chain
        
        if chain not in self.ROUTER_ADDRESSES:
            raise ValueError(f"Uniswap V3 não disponível em {chain}")
        
        self.router_address = self.ROUTER_ADDRESSES[chain]
        self.quoter_address = self.QUOTER_ADDRESSES[chain]
        
        logger.info(f"UniswapV3Connector initialized for {chain}")

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        fee_tier: int = 3000
    ) -> Dict:
        """
        Obtém cotação para swap.
        
        Args:
            token_in: Endereço do token de entrada
            token_out: Endereço do token de saída
            amount_in: Quantidade de entrada
            fee_tier: Fee tier (100, 500, 3000, 10000)
            
        Returns:
            Dict com amount_out, price_impact, fee, route
        """
        try:
            w3 = await self.gateway.connect_to_chain(self.chain)
            
            token_in = to_checksum_address(token_in)
            token_out = to_checksum_address(token_out)
            
            # Obter decimals dos tokens
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
            
            # Converter amount para wei
            amount_in_wei = int(amount_in * (10 ** decimals_in))
            
            # Tentar diferentes fee tiers e escolher o melhor
            best_quote = None
            best_amount_out = 0
            
            for fee in self.FEE_TIERS:
                try:
                    quoter = w3.eth.contract(
                        address=to_checksum_address(self.quoter_address),
                        abi=self.QUOTER_ABI
                    )
                    
                    # Chamar quoter (note: pode falhar se pool não existir)
                    amount_out_wei = quoter.functions.quoteExactInputSingle(
                        token_in,
                        token_out,
                        fee,
                        amount_in_wei,
                        0  # sqrtPriceLimitX96
                    ).call()
                    
                    if amount_out_wei > best_amount_out:
                        best_amount_out = amount_out_wei
                        best_quote = {
                            'fee_tier': fee,
                            'amount_out_wei': amount_out_wei
                        }
                
                except Exception as e:
                    # Pool pode não existir para esse fee tier
                    continue
            
            if best_quote is None:
                return {
                    'success': False,
                    'error': 'Nenhuma pool disponível para esse par'
                }
            
            # Converter amount_out para float
            amount_out = float(best_quote['amount_out_wei']) / (10 ** decimals_out)
            
            # Calcular price e price impact
            price = amount_out / amount_in if amount_in > 0 else 0
            fee_pct = best_quote['fee_tier'] / 10000  # Convert to percentage
            
            # Estimar gas
            gas_estimate = await self._estimate_swap_gas(
                token_in, token_out, amount_in_wei, best_quote['fee_tier']
            )
            
            return {
                'success': True,
                'dex': 'uniswap_v3',
                'chain': self.chain,
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price': price,
                'fee_tier': best_quote['fee_tier'],
                'fee_pct': fee_pct,
                'gas_estimate': gas_estimate,
                'route': f"{token_in} -> {token_out} (fee: {fee_pct}%)"
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter quote Uniswap V3: {e}")
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
        deadline: int = 300,
        fee_tier: int = 3000
    ) -> Dict:
        """
        Executa swap.
        
        Args:
            token_in: Endereço do token de entrada
            token_out: Endereço do token de saída
            amount_in: Quantidade de entrada
            amount_out_min: Quantidade mínima de saída (slippage protection)
            deadline: Prazo em segundos
            fee_tier: Fee tier
            
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
            
            # Verificar e aprovar se necessário
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
                    amount_in * 1.5,  # Aprovar um pouco mais
                    self.chain
                )
                
                if not approve_result.get('success'):
                    return {
                        'success': False,
                        'error': 'Falha na aprovação de tokens'
                    }
            
            # Construir transação de swap
            router = w3.eth.contract(
                address=to_checksum_address(self.router_address),
                abi=self.ROUTER_ABI
            )
            
            deadline_timestamp = w3.eth.get_block('latest')['timestamp'] + deadline
            
            swap_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee_tier,
                'recipient': to_checksum_address(self.gateway.wallet_address),
                'deadline': deadline_timestamp,
                'amountIn': amount_in_wei,
                'amountOutMinimum': amount_out_min_wei,
                'sqrtPriceLimitX96': 0
            }
            
            transaction = router.functions.exactInputSingle(
                swap_params
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
            logger.error(f"Erro ao executar swap Uniswap V3: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_pool_info(
        self,
        token0: str,
        token1: str,
        fee_tier: int = 3000
    ) -> Dict:
        """
        Obtém informações da pool.
        
        Args:
            token0: Endereço do primeiro token
            token1: Endereço do segundo token
            fee_tier: Fee tier
            
        Returns:
            Dict com informações da pool
        """
        # TODO: Implementar usando Pool Factory contract
        return {
            'success': False,
            'error': 'Implementação pendente'
        }

    async def _estimate_swap_gas(
        self,
        token_in: str,
        token_out: str,
        amount_in_wei: int,
        fee_tier: int
    ) -> int:
        """Estima gas para swap"""
        try:
            w3 = await self.gateway.connect_to_chain(self.chain)
            
            router = w3.eth.contract(
                address=to_checksum_address(self.router_address),
                abi=self.ROUTER_ABI
            )
            
            deadline_timestamp = w3.eth.get_block('latest')['timestamp'] + 300
            
            swap_params = {
                'tokenIn': to_checksum_address(token_in),
                'tokenOut': to_checksum_address(token_out),
                'fee': fee_tier,
                'recipient': to_checksum_address(self.gateway.wallet_address),
                'deadline': deadline_timestamp,
                'amountIn': amount_in_wei,
                'amountOutMinimum': 0,
                'sqrtPriceLimitX96': 0
            }
            
            gas = router.functions.exactInputSingle(
                swap_params
            ).estimate_gas({
                'from': to_checksum_address(self.gateway.wallet_address)
            })
            
            return int(gas * 1.2)  # 20% buffer
            
        except Exception as e:
            logger.warning(f"Erro ao estimar gas: {e}")
            return 200000  # Fallback estimate

    def get_router_address(self) -> str:
        """Retorna endereço do router"""
        return self.router_address

    def get_quoter_address(self) -> str:
        """Retorna endereço do quoter"""
        return self.quoter_address
