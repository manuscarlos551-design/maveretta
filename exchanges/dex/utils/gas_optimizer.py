"""
Gas Optimizer - Otimizador de gas para transações DEX
"""
import logging
import asyncio
from typing import Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class GasOptimizer:
    """
    Otimizador de gas para transações.
    
    Features:
    - Obtenção de gas price otimizado
    - Estimativa de custo total
    - Aguardar gas price ideal
    - Decisão de execução baseada em custo
    """

    # Preços médios de tokens em USD (atualizados periodicamente)
    TOKEN_PRICES_USD = {
        'ETH': 2500,
        'BNB': 350,
        'MATIC': 0.8,
        'AVAX': 25
    }

    def __init__(self, web3_gateways: Dict):
        """
        Inicializa Gas Optimizer.
        
        Args:
            web3_gateways: Dict de Web3Gateway por chain
        """
        self.gateways = web3_gateways
        logger.info("GasOptimizer initialized")

    async def get_optimal_gas_price(
        self,
        chain: str,
        priority: str = 'standard'
    ) -> Dict:
        """
        Obtém preço de gas otimizado.
        
        Args:
            chain: Nome da chain
            priority: Prioridade (low, standard, fast, urgent)
            
        Returns:
            Dict com maxFeePerGas, maxPriorityFeePerGas (EIP-1559) ou gasPrice
        """
        try:
            if chain not in self.gateways:
                raise ValueError(f"Chain {chain} não disponível")
            
            gateway = self.gateways[chain]
            w3 = await gateway.connect_to_chain(chain)
            
            # Obter gas price atual
            current_gas_price = w3.eth.gas_price
            
            # Multiplicadores por prioridade
            multipliers = {
                'low': 0.8,
                'standard': 1.0,
                'fast': 1.2,
                'urgent': 1.5
            }
            
            multiplier = multipliers.get(priority, 1.0)
            
            # EIP-1559 (Ethereum, Polygon)
            if chain in ['ethereum', 'polygon']:
                # Obter base fee do bloco mais recente
                latest_block = w3.eth.get_block('latest')
                base_fee = latest_block.get('baseFeePerGas', current_gas_price)
                
                # Calcular maxPriorityFeePerGas
                priority_fee_multipliers = {
                    'low': 1,
                    'standard': 1.5,
                    'fast': 2,
                    'urgent': 3
                }
                
                priority_multiplier = priority_fee_multipliers.get(priority, 1.5)
                max_priority_fee = int(base_fee * 0.1 * priority_multiplier)
                
                # Calcular maxFeePerGas
                max_fee = int((base_fee * 2) + max_priority_fee)
                
                return {
                    'success': True,
                    'chain': chain,
                    'type': 'eip1559',
                    'maxFeePerGas': max_fee,
                    'maxPriorityFeePerGas': max_priority_fee,
                    'baseFeePerGas': base_fee,
                    'maxFeePerGas_gwei': max_fee / 1e9,
                    'maxPriorityFeePerGas_gwei': max_priority_fee / 1e9
                }
            
            # Legacy gas price (BSC, Arbitrum)
            else:
                gas_price = int(current_gas_price * multiplier)
                
                return {
                    'success': True,
                    'chain': chain,
                    'type': 'legacy',
                    'gasPrice': gas_price,
                    'gasPrice_gwei': gas_price / 1e9
                }
            
        except Exception as e:
            logger.error(f"Erro ao obter gas price: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def estimate_transaction_cost(
        self,
        transaction: Dict,
        chain: str
    ) -> Dict:
        """
        Estima custo total da transação.
        
        Args:
            transaction: Dict com dados da transação
            chain: Nome da chain
            
        Returns:
            Dict com gas_estimate, gas_price, total_cost_usd
        """
        try:
            if chain not in self.gateways:
                raise ValueError(f"Chain {chain} não disponível")
            
            gateway = self.gateways[chain]
            
            # Estimar gas
            gas_estimate = await gateway.estimate_gas(transaction, chain)
            
            # Obter gas price
            gas_info = await self.get_optimal_gas_price(chain, 'standard')
            
            if not gas_info.get('success'):
                return gas_info
            
            # Calcular custo em wei
            if gas_info['type'] == 'eip1559':
                gas_cost_wei = gas_estimate * gas_info['maxFeePerGas']
            else:
                gas_cost_wei = gas_estimate * gas_info['gasPrice']
            
            # Converter para ETH/BNB/etc
            gas_cost_native = gas_cost_wei / 1e18
            
            # Obter preço do native token
            chain_native_tokens = {
                'ethereum': 'ETH',
                'bsc': 'BNB',
                'polygon': 'MATIC',
                'arbitrum': 'ETH'
            }
            
            native_token = chain_native_tokens.get(chain, 'ETH')
            token_price = self.TOKEN_PRICES_USD.get(native_token, 2500)
            
            # Calcular custo em USD
            gas_cost_usd = gas_cost_native * token_price
            
            return {
                'success': True,
                'chain': chain,
                'gas_estimate': gas_estimate,
                'gas_price_gwei': gas_info.get('maxFeePerGas_gwei') or gas_info.get('gasPrice_gwei'),
                'gas_cost_native': round(gas_cost_native, 6),
                'native_token': native_token,
                'token_price_usd': token_price,
                'gas_cost_usd': round(gas_cost_usd, 2)
            }
            
        except Exception as e:
            logger.error(f"Erro ao estimar custo: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def wait_for_lower_gas(
        self,
        chain: str,
        target_gwei: float,
        timeout: int = 3600,
        check_interval: int = 60
    ) -> bool:
        """
        Aguarda gas price cair abaixo do alvo.
        
        Args:
            chain: Nome da chain
            target_gwei: Preço alvo em gwei
            timeout: Timeout em segundos (default 1 hora)
            check_interval: Intervalo entre checks em segundos
            
        Returns:
            True se gas caiu abaixo do alvo, False se timeout
        """
        logger.info(f"Aguardando gas em {chain} cair para {target_gwei} gwei")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Verificar timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Timeout aguardando gas em {chain}")
                return False
            
            # Obter gas price atual
            gas_info = await self.get_optimal_gas_price(chain, 'standard')
            
            if gas_info.get('success'):
                current_gwei = gas_info.get('maxFeePerGas_gwei') or gas_info.get('gasPrice_gwei')
                
                if current_gwei <= target_gwei:
                    logger.info(f"Gas em {chain} caiu para {current_gwei} gwei")
                    return True
                
                logger.debug(f"Gas atual em {chain}: {current_gwei} gwei (alvo: {target_gwei})")
            
            # Aguardar antes do próximo check
            await asyncio.sleep(check_interval)

    def should_execute_now(
        self,
        chain: str,
        transaction_value: float,
        max_gas_cost_pct: float = 5.0,
        current_gas_cost_usd: float = None
    ) -> Dict:
        """
        Determina se deve executar transação agora baseado em gas.
        
        Args:
            chain: Nome da chain
            transaction_value: Valor da transação em USD
            max_gas_cost_pct: Percentual máximo aceitável de gas
            current_gas_cost_usd: Custo de gas atual (opcional)
            
        Returns:
            Dict com should_execute, reason, current_gas_cost_pct
        """
        if current_gas_cost_usd is None:
            # Estimar gas cost
            # TODO: Precisaríamos do transaction object aqui
            current_gas_cost_usd = 10  # Fallback
        
        # Calcular percentual
        if transaction_value <= 0:
            return {
                'should_execute': False,
                'reason': 'Transaction value inválido',
                'current_gas_cost_pct': None
            }
        
        gas_cost_pct = (current_gas_cost_usd / transaction_value) * 100
        
        if gas_cost_pct <= max_gas_cost_pct:
            return {
                'should_execute': True,
                'reason': f'Gas cost ({gas_cost_pct:.2f}%) está abaixo do limite ({max_gas_cost_pct}%)',
                'current_gas_cost_pct': gas_cost_pct,
                'current_gas_cost_usd': current_gas_cost_usd
            }
        else:
            return {
                'should_execute': False,
                'reason': f'Gas cost ({gas_cost_pct:.2f}%) excede limite ({max_gas_cost_pct}%)',
                'current_gas_cost_pct': gas_cost_pct,
                'current_gas_cost_usd': current_gas_cost_usd,
                'recommendation': 'Aguardar gas mais baixo ou aumentar max_gas_cost_pct'
            }

    def update_token_prices(self, prices: Dict[str, float]):
        """
        Atualiza preços de tokens.
        
        Args:
            prices: Dict com preços atualizados
        """
        self.TOKEN_PRICES_USD.update(prices)
        logger.info(f"Preços de tokens atualizados: {prices}")
